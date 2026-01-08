"""
Core conversion functions for Textract JSON to hOCR format.

This module provides the main functionality for converting AWS Textract
JSON output to hOCR HTML format, which is widely used for OCR output.
"""

import json
import logging
from typing import Dict, Union, Optional
from yattag import Doc, indent
from PIL import Image

# Set up module logger
logger = logging.getLogger(__name__)

# Textract uses normalized coordinates (0-1), but reports dimensions as 1000x1000
TEXTRACT_DEFAULT_WIDTH = 1000
TEXTRACT_DEFAULT_HEIGHT = 1000


def get_document_dimensions(
    file_path: Optional[str] = None,
    page_number: int = 1,
    dimensions: Optional[Dict[str, int]] = None,
) -> Dict[str, int]:
    """
    Get page dimensions from an image file or explicit dimensions parameter.

    **IMPORTANT FOR PDFs**: When processing PDFs with Textract, you MUST provide
    explicit dimensions via the `dimensions` parameter. These should match the
    resolution at which Textract rasterized the PDF (typically 200-300 DPI).

    For example, if your PDF was processed at 300 DPI:
    - A4 page (8.27" x 11.69") -> dimensions={'width': 2480, 'height': 3507}
    - Letter page (8.5" x 11") -> dimensions={'width': 2550, 'height': 3300}

    Args:
        file_path: Path to the source image file. Cannot reliably extract PDF dimensions.
        page_number: Page number (1-indexed, currently unused for images).
        dimensions: **Required for PDFs**. Dict with 'width' and 'height' in pixels
                   matching Textract's rasterization resolution.

    Returns:
        Dictionary with 'width' and 'height' keys in pixels.
        Falls back to Textract's default 1000x1000 if file cannot be read.

    Raises:
        ValueError: If file_path is a PDF without explicit dimensions.

    Examples:
        # For images - dimensions are auto-detected
        dims = get_document_dimensions('scan.png')

        # For PDFs - you MUST provide dimensions
        dims = get_document_dimensions('doc.pdf', dimensions={'width': 2480, 'height': 3507})
    """
    # Use provided dimensions if specified
    if dimensions is not None:
        logger.info(
            f"Using provided dimensions: {dimensions['width']}x{dimensions['height']}"
        )
        return dimensions

    if not file_path:
        logger.info(
            f"No source file provided, using Textract defaults: {TEXTRACT_DEFAULT_WIDTH}x{TEXTRACT_DEFAULT_HEIGHT}"
        )
        return {"width": TEXTRACT_DEFAULT_WIDTH, "height": TEXTRACT_DEFAULT_HEIGHT}

    # Check if it's a PDF - we cannot reliably extract dimensions
    if file_path.lower().endswith(".pdf"):
        error_msg = (
            f"PDF file '{file_path}' requires explicit dimensions parameter. "
            f"PDFs are rasterized by Textract at a specific DPI, and we cannot determine "
            f"this from the PDF file alone. Please provide dimensions using the --width and --height options "
            f"matching the resolution Textract used (typically 200-300 DPI). "
            f"Example for A4 at 300 DPI: --width 2480 --height 3507"
        )
        raise ValueError(error_msg)

    try:
        # Try to open as image
        with Image.open(file_path) as img:
            logger.info(
                f"Extracted dimensions from image '{file_path}': {img.width}x{img.height}"
            )
            return {"width": img.width, "height": img.height}

    except Exception as e:
        error_msg = (
            f"Could not extract dimensions from '{file_path}'. "
            f"For PDFs, you must provide the dimensions parameter. "
            f"For images, ensure the file is a valid image format. Error: {e}"
        )
        raise ValueError(error_msg)


def textract_to_hocr(
    textract_result: Union[str, dict],
    source_file: Optional[str] = None,
    first_page: Optional[int] = None,
    last_page: Optional[int] = None,
    dimensions: Optional[Dict[str, int]] = None,
) -> str:
    """
    Convert Textract JSON output to hOCR HTML format.

    **IMPORTANT FOR PDFs**: When processing PDFs, you MUST provide the `dimensions`
    parameter with the width and height (in pixels) matching the resolution at which
    Textract rasterized the PDF. This is typically 200-300 DPI.

    Args:
        textract_result: Textract JSON output as dict or JSON string.
        source_file: Optional path to source image file for dimension extraction.
                    For PDFs, dimensions parameter is required instead.
        first_page: Optional first page to convert (1-indexed). If None, starts from page 1.
        last_page: Optional last page to convert (1-indexed). If None, goes to last page.
        dimensions: **Required for PDFs**. Dict with 'width' and 'height' in pixels.
                   For images, this overrides auto-detection if provided.
                   Example: {'width': 2480, 'height': 3507} for A4 at 300 DPI

    Returns:
        hOCR HTML string with specified pages.

    Raises:
        ValueError: If page range is invalid or if PDF provided without dimensions.

    Examples:
        # Convert image with auto-detected dimensions
        hocr = textract_to_hocr(data, source_file='scan.png')

        # Convert PDF with explicit dimensions (300 DPI A4)
        hocr = textract_to_hocr(data, source_file='doc.pdf',
                               dimensions={'width': 2480, 'height': 3507})

        # Convert specific pages
        hocr = textract_to_hocr(data, first_page=2, last_page=5,
                               dimensions={'width': 2480, 'height': 3507})
    """
    # Parse JSON string if needed
    if isinstance(textract_result, str):
        logger.info("Parsing Textract JSON string")
        textract_result = json.loads(textract_result)

    total_pages = textract_result["DocumentMetadata"]["Pages"]
    logger.info(f"Document has {total_pages} page(s)")

    # Determine page range
    first = first_page if first_page is not None else 1
    last = last_page if last_page is not None else total_pages

    # Validate page range
    if first < 1 or first > total_pages:
        error_msg = (
            f"first_page {first} is out of range. Document has {total_pages} pages."
        )
        logger.error(error_msg)
        raise ValueError(error_msg)
    if last < 1 or last > total_pages:
        error_msg = (
            f"last_page {last} is out of range. Document has {total_pages} pages."
        )
        logger.error(error_msg)
        raise ValueError(error_msg)
    if first > last:
        error_msg = f"first_page ({first}) cannot be greater than last_page ({last})."
        logger.error(error_msg)
        raise ValueError(error_msg)

    logger.info(f"Converting pages {first}-{last} to hOCR format")

    # Single page conversion
    if total_pages == 1:
        logger.info("Using single-page conversion path")
        return _convert_single_page(textract_result, source_file, dimensions)

    # Multi-page: extract requested range
    if first == 1 and last == total_pages:
        # All pages - use optimized path
        logger.info("Using multi-page conversion path (all pages)")
        return _convert_multiple_pages(textract_result, source_file, dimensions)
    else:
        # Specific range
        logger.info(f"Using page range extraction path (pages {first}-{last})")
        return _extract_page_range(
            textract_result, first, last, source_file, dimensions
        )


def _convert_single_page(
    result: dict,
    source_file: Optional[str] = None,
    dimensions: Optional[Dict[str, int]] = None,
) -> str:
    """Convert single-page Textract results to hOCR."""
    result_data = {1: {"lines": {}, "tables": {}}}
    page_dimensions = {1: get_document_dimensions(source_file, 1, dimensions)}

    # First pass: collect all WORD IDs that belong to table cells
    table_word_ids = set()
    table_line_ids = set()

    for block in result["Blocks"]:
        if block["BlockType"] == "TABLE":
            # Find all CELL children of this table
            if "Relationships" in block:
                for relationship in block["Relationships"]:
                    if relationship["Type"] == "CHILD":
                        for cell_id in relationship["Ids"]:
                            # Find the cell block and get its children (WORD or LINE)
                            for cell_block in result["Blocks"]:
                                if (
                                    cell_block["Id"] == cell_id
                                    and cell_block["BlockType"] == "CELL"
                                ):
                                    if "Relationships" in cell_block:
                                        for cell_rel in cell_block["Relationships"]:
                                            if cell_rel["Type"] == "CHILD":
                                                # Collect all child IDs (could be WORD or LINE)
                                                for child_id in cell_rel["Ids"]:
                                                    for child_block in result["Blocks"]:
                                                        if (
                                                            child_block["Id"]
                                                            == child_id
                                                        ):
                                                            if (
                                                                child_block["BlockType"]
                                                                == "LINE"
                                                            ):
                                                                table_line_ids.add(
                                                                    child_id
                                                                )
                                                            elif (
                                                                child_block["BlockType"]
                                                                == "WORD"
                                                            ):
                                                                table_word_ids.add(
                                                                    child_id
                                                                )
                                                            break
                                    break

    # Find all LINE blocks that contain any of the table words
    for block in result["Blocks"]:
        if block["BlockType"] == "LINE" and "Relationships" in block:
            for relationship in block["Relationships"]:
                if relationship["Type"] == "CHILD":
                    # Check if any word in this line belongs to a table
                    for word_id in relationship["Ids"]:
                        if word_id in table_word_ids:
                            table_line_ids.add(block["Id"])
                            break

    # Second pass: process all blocks
    for block in result["Blocks"]:
        if block["BlockType"] == "LINE":
            # Skip lines that belong to tables
            if block["Id"] not in table_line_ids:
                _add_line_block(result_data[1]["lines"], block, result["Blocks"])
        elif block["BlockType"] == "TABLE":
            _add_table_block(result_data[1]["tables"], block, result["Blocks"])

    return _build_hocr_html(result_data, page_dimensions)


def _convert_multiple_pages(
    result: dict,
    source_file: Optional[str] = None,
    dimensions: Optional[Dict[str, int]] = None,
) -> str:
    """Convert multi-page Textract results to hOCR."""
    result_data = {}
    page_dimensions = {}

    # First pass: collect all WORD IDs that belong to table cells
    table_word_ids = set()
    table_line_ids = set()

    for block in result["Blocks"]:
        if block["BlockType"] == "TABLE":
            # Find all CELL children of this table
            if "Relationships" in block:
                for relationship in block["Relationships"]:
                    if relationship["Type"] == "CHILD":
                        for cell_id in relationship["Ids"]:
                            # Find the cell block and get its children (WORD or LINE)
                            for cell_block in result["Blocks"]:
                                if (
                                    cell_block["Id"] == cell_id
                                    and cell_block["BlockType"] == "CELL"
                                ):
                                    if "Relationships" in cell_block:
                                        for cell_rel in cell_block["Relationships"]:
                                            if cell_rel["Type"] == "CHILD":
                                                # Collect all child IDs (could be WORD or LINE)
                                                for child_id in cell_rel["Ids"]:
                                                    for child_block in result["Blocks"]:
                                                        if (
                                                            child_block["Id"]
                                                            == child_id
                                                        ):
                                                            if (
                                                                child_block["BlockType"]
                                                                == "LINE"
                                                            ):
                                                                table_line_ids.add(
                                                                    child_id
                                                                )
                                                            elif (
                                                                child_block["BlockType"]
                                                                == "WORD"
                                                            ):
                                                                table_word_ids.add(
                                                                    child_id
                                                                )
                                                            break
                                    break

    # Find all LINE blocks that contain any of the table words
    for block in result["Blocks"]:
        if block["BlockType"] == "LINE" and "Relationships" in block:
            for relationship in block["Relationships"]:
                if relationship["Type"] == "CHILD":
                    # Check if any word in this line belongs to a table
                    for word_id in relationship["Ids"]:
                        if word_id in table_word_ids:
                            table_line_ids.add(block["Id"])
                            break

    # Second pass: process PAGE blocks and initialize
    for block in result["Blocks"]:
        if block["BlockType"] == "PAGE":
            page_num = block["Page"]
            result_data[page_num] = {"lines": {}, "tables": {}}
            page_dimensions[page_num] = get_document_dimensions(
                source_file, page_num, dimensions
            )

            # Initialize line placeholders, excluding table lines
            if "Relationships" in block and block["Relationships"]:
                for relationship in block["Relationships"]:
                    if relationship["Type"] == "CHILD":
                        for line_id in relationship["Ids"]:
                            # Only add if it's a LINE and not part of a table
                            for child_block in result["Blocks"]:
                                if child_block["Id"] == line_id:
                                    if (
                                        child_block["BlockType"] == "LINE"
                                        and line_id not in table_line_ids
                                    ):
                                        result_data[page_num]["lines"][line_id] = {}
                                    break

        elif block["BlockType"] == "LINE":
            page_num = block["Page"]
            # Skip lines that belong to tables
            if block["Id"] not in table_line_ids:
                _add_line_block(result_data[page_num]["lines"], block, result["Blocks"])
        elif block["BlockType"] == "TABLE":
            page_num = block["Page"]
            _add_table_block(result_data[page_num]["tables"], block, result["Blocks"])

    return _build_hocr_html(result_data, page_dimensions)


def _extract_page_range(
    result: dict,
    first_page: int,
    last_page: int,
    source_file: Optional[str] = None,
    dimensions: Optional[Dict[str, int]] = None,
) -> str:
    """Extract a page range from multi-page Textract results."""
    result_data = {}
    page_dimensions = {}

    # Initialize all pages in range
    for page_num in range(first_page, last_page + 1):
        result_data[page_num] = {"lines": {}, "tables": {}}
        page_dimensions[page_num] = get_document_dimensions(
            source_file, page_num, dimensions
        )

    # First pass: collect all WORD IDs that belong to table cells
    # Then find all LINE blocks that contain those words
    table_word_ids = set()
    table_line_ids = set()

    for block in result["Blocks"]:
        page_num = block.get("Page")
        if page_num is None or page_num < first_page or page_num > last_page:
            continue

        if block["BlockType"] == "TABLE":
            # Find all CELL children of this table
            if "Relationships" in block:
                for relationship in block["Relationships"]:
                    if relationship["Type"] == "CHILD":
                        for cell_id in relationship["Ids"]:
                            # Find the cell block and get its children (WORD or LINE)
                            for cell_block in result["Blocks"]:
                                if (
                                    cell_block["Id"] == cell_id
                                    and cell_block["BlockType"] == "CELL"
                                ):
                                    if "Relationships" in cell_block:
                                        for cell_rel in cell_block["Relationships"]:
                                            if cell_rel["Type"] == "CHILD":
                                                # Collect all child IDs (could be WORD or LINE)
                                                for child_id in cell_rel["Ids"]:
                                                    for child_block in result["Blocks"]:
                                                        if (
                                                            child_block["Id"]
                                                            == child_id
                                                        ):
                                                            if (
                                                                child_block["BlockType"]
                                                                == "LINE"
                                                            ):
                                                                table_line_ids.add(
                                                                    child_id
                                                                )
                                                            elif (
                                                                child_block["BlockType"]
                                                                == "WORD"
                                                            ):
                                                                table_word_ids.add(
                                                                    child_id
                                                                )
                                                            break
                                    break

    # Now find all LINE blocks that contain any of the table words
    for block in result["Blocks"]:
        if block["BlockType"] == "LINE" and "Relationships" in block:
            for relationship in block["Relationships"]:
                if relationship["Type"] == "CHILD":
                    # Check if any word in this line belongs to a table
                    for word_id in relationship["Ids"]:
                        if word_id in table_word_ids:
                            table_line_ids.add(block["Id"])
                            break

    # Second pass: find all blocks belonging to the requested page range
    for block in result["Blocks"]:
        page_num = block.get("Page")
        if page_num is None or page_num < first_page or page_num > last_page:
            continue

        if block["BlockType"] == "PAGE":
            # Get line IDs for this page, excluding those that belong to tables
            if "Relationships" in block:
                for relationship in block["Relationships"]:
                    if relationship["Type"] == "CHILD":
                        for child_id in relationship["Ids"]:
                            # Skip if this child is a TABLE or a LINE that belongs to a table
                            # Check if it's a LINE (not a TABLE)
                            child_is_line = False
                            for child_block in result["Blocks"]:
                                if child_block["Id"] == child_id:
                                    if (
                                        child_block["BlockType"] == "LINE"
                                        and child_id not in table_line_ids
                                    ):
                                        child_is_line = True
                                    break
                            if child_is_line:
                                result_data[page_num]["lines"][child_id] = {}

        elif block["BlockType"] == "LINE":
            # Skip lines that belong to tables
            if block["Id"] not in table_line_ids:
                _add_line_block(result_data[page_num]["lines"], block, result["Blocks"])
        elif block["BlockType"] == "TABLE":
            _add_table_block(result_data[page_num]["tables"], block, result["Blocks"])

    return _build_hocr_html(result_data, page_dimensions)


def _add_table_block(page_data: dict, table_block: dict, all_blocks: list) -> None:
    """
    Add a TABLE block and its CELL children to the page data structure.

    Args:
        page_data: Dictionary to add table data to.
        table_block: The TABLE block from Textract.
        all_blocks: All blocks to search for cell data.
    """
    table_id = table_block["Id"]
    page_data[table_id] = {
        "BlockType": table_block["BlockType"],
        "Confidence": table_block.get("Confidence", 100.0),
        "BoundingBox": {
            "Width": table_block["Geometry"]["BoundingBox"]["Width"],
            "Height": table_block["Geometry"]["BoundingBox"]["Height"],
            "Left": table_block["Geometry"]["BoundingBox"]["Left"],
            "Top": table_block["Geometry"]["BoundingBox"]["Top"],
        },
        "Polygon": [
            {
                "X": table_block["Geometry"]["Polygon"][i]["X"],
                "Y": table_block["Geometry"]["Polygon"][i]["Y"],
            }
            for i in range(4)
        ],
        "Cells": {},
    }

    # Add cell blocks
    if "Relationships" in table_block and table_block["Relationships"]:
        for relationship in table_block["Relationships"]:
            if relationship["Type"] == "CHILD":
                for cell_id in relationship["Ids"]:
                    for cell_block in all_blocks:
                        if (
                            cell_block["Id"] == cell_id
                            and cell_block["BlockType"] == "CELL"
                        ):
                            row_index = cell_block.get("RowIndex", 0)
                            col_index = cell_block.get("ColumnIndex", 0)
                            row_span = cell_block.get("RowSpan", 1)
                            col_span = cell_block.get("ColumnSpan", 1)

                            # Extract LINE IDs and WORD data from cell
                            line_ids = []
                            words_data = []
                            if "Relationships" in cell_block:
                                for rel in cell_block["Relationships"]:
                                    if rel["Type"] == "CHILD":
                                        for child_id in rel["Ids"]:
                                            # Check if this is a LINE or WORD block
                                            for child_block in all_blocks:
                                                if child_block["Id"] == child_id:
                                                    if (
                                                        child_block["BlockType"]
                                                        == "LINE"
                                                    ):
                                                        line_ids.append(child_id)
                                                    elif (
                                                        child_block["BlockType"]
                                                        == "WORD"
                                                    ):
                                                        # Store complete word data
                                                        words_data.append(
                                                            {
                                                                "Id": child_id,
                                                                "Text": child_block[
                                                                    "Text"
                                                                ],
                                                                "Confidence": child_block.get(
                                                                    "Confidence", 100.0
                                                                ),
                                                                "TextType": child_block.get(
                                                                    "TextType",
                                                                    "PRINTED",
                                                                ),
                                                                "BoundingBox": child_block[
                                                                    "Geometry"
                                                                ][
                                                                    "BoundingBox"
                                                                ],
                                                                "Polygon": child_block[
                                                                    "Geometry"
                                                                ]["Polygon"],
                                                            }
                                                        )
                                                    break

                            page_data[table_id]["Cells"][cell_id] = {
                                "BlockType": cell_block["BlockType"],
                                "Confidence": cell_block.get("Confidence", 100.0),
                                "RowIndex": row_index,
                                "ColumnIndex": col_index,
                                "RowSpan": row_span,
                                "ColumnSpan": col_span,
                                "LineIds": line_ids,
                                "Words": words_data,
                                "BoundingBox": {
                                    "Width": cell_block["Geometry"]["BoundingBox"][
                                        "Width"
                                    ],
                                    "Height": cell_block["Geometry"]["BoundingBox"][
                                        "Height"
                                    ],
                                    "Left": cell_block["Geometry"]["BoundingBox"][
                                        "Left"
                                    ],
                                    "Top": cell_block["Geometry"]["BoundingBox"]["Top"],
                                },
                                "Polygon": [
                                    {
                                        "X": cell_block["Geometry"]["Polygon"][i]["X"],
                                        "Y": cell_block["Geometry"]["Polygon"][i]["Y"],
                                    }
                                    for i in range(4)
                                ],
                            }
                            break


def _add_line_block(page_data: dict, line_block: dict, all_blocks: list) -> None:
    """
    Add a LINE block and its WORD children to the page data structure.

    Args:
        page_data: Dictionary to add line data to.
        line_block: The LINE block from Textract.
        all_blocks: All blocks to search for word data.
    """
    line_id = line_block["Id"]
    page_data[line_id] = {
        "BlockType": line_block["BlockType"],
        "Confidence": line_block["Confidence"],
        "Text": line_block["Text"],
        "BoundingBox": {
            "Width": line_block["Geometry"]["BoundingBox"]["Width"],
            "Height": line_block["Geometry"]["BoundingBox"]["Height"],
            "Left": line_block["Geometry"]["BoundingBox"]["Left"],
            "Top": line_block["Geometry"]["BoundingBox"]["Top"],
        },
        "Polygon": [
            {
                "X": line_block["Geometry"]["Polygon"][i]["X"],
                "Y": line_block["Geometry"]["Polygon"][i]["Y"],
            }
            for i in range(4)
        ],
        "Words": {},
    }

    # Add word blocks
    if "Relationships" in line_block and line_block["Relationships"]:
        for word_id in line_block["Relationships"][0]["Ids"]:
            for word_block in all_blocks:
                if word_block["Id"] == word_id:
                    page_data[line_id]["Words"][word_id] = {
                        "BlockType": word_block["BlockType"],
                        "Confidence": word_block["Confidence"],
                        "Text": word_block["Text"],
                        "TextType": word_block["TextType"],
                        "BoundingBox": {
                            "Width": word_block["Geometry"]["BoundingBox"]["Width"],
                            "Height": word_block["Geometry"]["BoundingBox"]["Height"],
                            "Left": word_block["Geometry"]["BoundingBox"]["Left"],
                            "Top": word_block["Geometry"]["BoundingBox"]["Top"],
                        },
                        "Polygon": [
                            {
                                "X": word_block["Geometry"]["Polygon"][i]["X"],
                                "Y": word_block["Geometry"]["Polygon"][i]["Y"],
                            }
                            for i in range(4)
                        ],
                    }
                    break


def _build_hocr_html(result_data: dict, page_dimensions: dict) -> str:
    """
    Build hOCR HTML from parsed Textract data.

    Args:
        result_data: Dictionary mapping page numbers to line/word data.
        page_dimensions: Dictionary mapping page numbers to dimensions.

    Returns:
        Formatted hOCR HTML string.
    """
    doc, tag, text = Doc().tagtext()

    doc.asis('<?xml version="1.0" encoding="UTF-8"?>')
    doc.asis(
        '<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 Transitional//EN" '
        '"http://www.w3.org/TR/xhtml1/DTD/xhtml1-transitional.dtd">'
    )

    with tag("html", xmlns="http://www.w3.org/1999/xhtml", lang="en"):
        with tag("head"):
            with tag("title"):
                text("")
            doc.stag(
                "meta",
                ("http-equiv", "Content-Type"),
                content="text/html;charset=utf-8",
            )
            doc.stag("meta", name="ocr-system", content="aws-textract")
            doc.stag(
                "meta",
                name="ocr-capabilities",
                content="ocr_page ocr_block ocr_par ocr_table ocr_line ocrx_word",
            )

        with tag("body"):
            for page_num in sorted(result_data.keys()):
                _add_page_content(
                    doc,
                    tag,
                    text,
                    page_num,
                    result_data[page_num],
                    page_dimensions[page_num],
                )

    return indent(doc.getvalue())


def _add_page_content(
    doc, tag, text, page_num: int, page_data: dict, dimensions: dict
) -> None:
    """Add a single page's content to the hOCR document."""
    width = dimensions["width"]
    height = dimensions["height"]
    page_bbox = f"bbox 0 0 {width} {height}; ppageno {page_num - 1}"

    with tag("div", klass="ocr_page", id=f"page_{page_num}", title=page_bbox):
        # Collect all content (tables and lines) with their vertical positions
        content_items = []

        # Collect all line IDs that belong to tables
        table_line_ids = set()
        for table_id, table_data in page_data.get("tables", {}).items():
            if table_data:
                for cell_id, cell_data in table_data["Cells"].items():
                    table_line_ids.update(cell_data.get("LineIds", []))

        # Add tables with their top position
        for table_id, table_data in page_data.get("tables", {}).items():
            if table_data:  # Skip empty placeholders
                bbox = table_data["BoundingBox"]
                top_pos = bbox["Top"]
                left_pos = bbox["Left"]
                height_val = bbox["Height"]
                content_items.append(
                    (top_pos, height_val, left_pos, "table", table_id, table_data)
                )

        # Add lines with their top position, excluding table lines
        for line_id, line_data in page_data.get("lines", {}).items():
            if (
                line_data and line_id not in table_line_ids
            ):  # Skip empty placeholders and table lines
                bbox = line_data["BoundingBox"]
                top_pos = bbox["Top"]
                left_pos = bbox["Left"]
                height_val = bbox["Height"]
                content_items.append(
                    (top_pos, height_val, left_pos, "line", line_id, line_data)
                )

        # Group lines by vertical overlap and sort within groups by left position
        # This ensures proper left-to-right reading order for lines on the same visual line
        def lines_overlap_vertically(item1, item2):
            """Check if two items have vertically overlapping bounding boxes."""
            top1, height1 = item1[0], item1[1]
            top2, height2 = item2[0], item2[1]
            bottom1 = top1 + height1
            bottom2 = top2 + height2
            # Lines overlap if one's bottom is >= the other's top and vice versa
            return bottom1 >= top2 and bottom2 >= top1

        # First, sort by top position to process from top to bottom
        content_items.sort(key=lambda item: item[0])
        
        # Group items that overlap vertically
        groups = []
        for item in content_items:
            # Find a group this item overlaps with
            placed = False
            for group in groups:
                # Check if item overlaps with any item in this group
                if any(lines_overlap_vertically(item, group_item) for group_item in group):
                    group.append(item)
                    placed = True
                    break
            if not placed:
                # Create a new group
                groups.append([item])
        
        # Sort each group by left position, then flatten
        content_items = []
        for group in groups:
            group.sort(key=lambda item: item[2])  # Sort by left position
            content_items.extend(group)

        # Group lines into blocks based on bbox intersection
        current_block_lines = []
        block_counter = 1
        last_line_bbox = None

        for (
            top_pos,
            height_val,
            left_pos,
            content_type,
            content_id,
            content_data,
        ) in content_items:
            if content_type == "table":
                # Output any pending block first
                if current_block_lines:
                    _add_block_with_lines(
                        doc,
                        tag,
                        text,
                        block_counter,
                        page_num,
                        current_block_lines,
                        width,
                        height,
                    )
                    current_block_lines = []
                    block_counter += 1

                # Output the table
                _add_table_content(
                    doc,
                    tag,
                    text,
                    content_id,
                    content_data,
                    width,
                    height,
                    page_data.get("lines", {}),
                )
                last_line_bbox = None  # Reset bbox tracking after table
            else:
                # Check if this line's bbox intersects with the last line's bbox
                current_bbox = content_data["BoundingBox"]

                if last_line_bbox is not None and not _bboxes_intersect(
                    last_line_bbox, current_bbox
                ):
                    # No intersection - start a new block
                    if current_block_lines:
                        _add_block_with_lines(
                            doc,
                            tag,
                            text,
                            block_counter,
                            page_num,
                            current_block_lines,
                            width,
                            height,
                        )
                        current_block_lines = []
                        block_counter += 1

                # Add line to current block
                current_block_lines.append((content_id, content_data))
                last_line_bbox = current_bbox

        # Output any remaining block
        if current_block_lines:
            _add_block_with_lines(
                doc,
                tag,
                text,
                block_counter,
                page_num,
                current_block_lines,
                width,
                height,
            )


def _bboxes_intersect(bbox1: dict, bbox2: dict) -> bool:
    """Check if two bounding boxes should be considered part of the same block.

    This includes:
    - Direct vertical overlap
    - Small vertical gaps (less than 0.3x the average line height)

    This ensures lines that are visually close are kept together in the same block.
    """
    # Get Y coordinates (vertical positions)
    top1 = bbox1["Top"]
    bottom1 = bbox1["Top"] + bbox1["Height"]
    height1 = bbox1["Height"]

    top2 = bbox2["Top"]
    bottom2 = bbox2["Top"] + bbox2["Height"]
    height2 = bbox2["Height"]

    # Calculate average height for tolerance
    avg_height = (height1 + height2) / 2

    # Allow small gaps (up to 30% of average line height)
    # This keeps closely spaced lines together
    tolerance = 0.3 * avg_height

    # Check for overlap or close proximity
    # Lines are considered part of the same block if:
    # 1. They overlap vertically, OR
    # 2. The gap between them is less than the tolerance
    gap = max(0, top2 - bottom1)  # Gap if line2 is below line1

    return gap <= tolerance


def _detect_paragraph_break(line1_data: dict, line2_data: dict) -> bool:
    """Detect if there should be a paragraph break between two consecutive lines.

    A paragraph break is detected when the vertical spacing between lines
    is significantly larger than the line height, indicating a visual break.

    Args:
        line1_data: Data for the first line (should come before line2)
        line2_data: Data for the second line

    Returns:
        True if a paragraph break should be inserted between the lines
    """
    bbox1 = line1_data["BoundingBox"]
    bbox2 = line2_data["BoundingBox"]

    # Calculate bottom of line1 and top of line2
    line1_bottom = bbox1["Top"] + bbox1["Height"]
    line2_top = bbox2["Top"]

    # Calculate the gap between lines
    gap = line2_top - line1_bottom

    # Use the average height of the two lines as reference
    avg_height = (bbox1["Height"] + bbox2["Height"]) / 2

    # Threshold: if gap is more than 0.5x the average line height, it's a new paragraph
    # This is a heuristic that can be tuned based on your data
    threshold = 0.5 * avg_height

    return gap > threshold


def _add_block_with_lines(
    doc,
    tag,
    text,
    block_counter: int,
    page_num: int,
    lines: list,
    width: int,
    height: int,
) -> None:
    """Add a block containing multiple lines with a synthetic ID.

    Lines within the block are grouped into paragraphs based on vertical spacing.
    Each paragraph is wrapped in a <p class='ocr_par'> tag.
    """
    # Calculate combined bbox for all lines in the block
    min_left = min(line_data["BoundingBox"]["Left"] for _, line_data in lines)
    min_top = min(line_data["BoundingBox"]["Top"] for _, line_data in lines)
    max_right = max(
        line_data["BoundingBox"]["Left"] + line_data["BoundingBox"]["Width"]
        for _, line_data in lines
    )
    max_bottom = max(
        line_data["BoundingBox"]["Top"] + line_data["BoundingBox"]["Height"]
        for _, line_data in lines
    )

    # Convert to pixels
    left = int(min_left * width)
    top = int(min_top * height)
    right = int(max_right * width)
    bottom = int(max_bottom * height)

    block_bbox = f"bbox {left} {top} {right} {bottom}"
    block_title = f"{block_bbox}"

    with tag(
        "div",
        klass="ocr_block",
        id=f"block_{block_counter}_{page_num}",
        title=block_title,
    ):
        # Group lines into paragraphs based on spacing
        paragraphs = []
        current_paragraph = []

        for i, (line_id, line_data) in enumerate(lines):
            if i == 0:
                # First line always starts a paragraph
                current_paragraph.append((line_id, line_data))
            else:
                # Check if we should start a new paragraph
                prev_line_data = lines[i - 1][1]
                if _detect_paragraph_break(prev_line_data, line_data):
                    # Save current paragraph and start a new one
                    if current_paragraph:
                        paragraphs.append(current_paragraph)
                    current_paragraph = [(line_id, line_data)]
                else:
                    # Continue current paragraph
                    current_paragraph.append((line_id, line_data))

        # Add the last paragraph
        if current_paragraph:
            paragraphs.append(current_paragraph)

        # Render each paragraph with ocr_par wrapper
        for par_num, paragraph_lines in enumerate(paragraphs, start=1):
            # Calculate paragraph bbox
            par_min_left = min(ld["BoundingBox"]["Left"] for _, ld in paragraph_lines)
            par_min_top = min(ld["BoundingBox"]["Top"] for _, ld in paragraph_lines)
            par_max_right = max(
                ld["BoundingBox"]["Left"] + ld["BoundingBox"]["Width"]
                for _, ld in paragraph_lines
            )
            par_max_bottom = max(
                ld["BoundingBox"]["Top"] + ld["BoundingBox"]["Height"]
                for _, ld in paragraph_lines
            )

            par_left = int(par_min_left * width)
            par_top = int(par_min_top * height)
            par_right = int(par_max_right * width)
            par_bottom = int(par_max_bottom * height)

            par_bbox = f"bbox {par_left} {par_top} {par_right} {par_bottom}"

            with tag(
                "p",
                klass="ocr_par",
                id=f"par_{block_counter}_{page_num}_{par_num}",
                title=par_bbox,
                lang="eng",
            ):
                for line_id, line_data in paragraph_lines:
                    _add_line_content(doc, tag, text, line_id, line_data, width, height)


def _add_table_content(
    doc,
    tag,
    text,
    table_id: str,
    table_data: dict,
    width: int,
    height: int,
    all_lines: dict,
) -> None:
    """Add a table as a float element with ocr_table class, including line and word structure."""
    bbox = table_data["BoundingBox"]

    # Convert normalized coordinates to pixels
    left = int(bbox["Left"] * width)
    top = int(bbox["Top"] * height)
    right = int((bbox["Left"] + bbox["Width"]) * width)
    bottom = int((bbox["Top"] + bbox["Height"]) * height)

    table_bbox = f"bbox {left} {top} {right} {bottom}"
    confidence = int(table_data.get("Confidence", 0))
    table_title = f"{table_bbox}; x_wconf {confidence}"

    # Render as a float div element with ocr_table class
    with tag("div", klass="ocr_table", id=table_id, title=table_title):
        # Sort cells by row, then column for reading order
        sorted_cells = sorted(
            table_data["Cells"].items(),
            key=lambda x: (x[1]["RowIndex"], x[1]["ColumnIndex"]),
        )

        # Group cells by row
        rows = {}
        for cell_id, cell_data in sorted_cells:
            row_idx = cell_data["RowIndex"]
            if row_idx not in rows:
                rows[row_idx] = []
            rows[row_idx].append((cell_id, cell_data))

        # Process each row
        for row_idx in sorted(rows.keys()):
            row_cells = rows[row_idx]

            # Calculate row bounding box
            row_min_left = min(cd["BoundingBox"]["Left"] for _, cd in row_cells)
            row_min_top = min(cd["BoundingBox"]["Top"] for _, cd in row_cells)
            row_max_right = max(
                cd["BoundingBox"]["Left"] + cd["BoundingBox"]["Width"]
                for _, cd in row_cells
            )
            row_max_bottom = max(
                cd["BoundingBox"]["Top"] + cd["BoundingBox"]["Height"]
                for _, cd in row_cells
            )

            row_left = int(row_min_left * width)
            row_top = int(row_min_top * height)
            row_right = int(row_max_right * width)
            row_bottom = int(row_max_bottom * height)
            row_bbox_str = f"bbox {row_left} {row_top} {row_right} {row_bottom}"

            # Wrap the entire row in a paragraph
            with tag(
                "p",
                klass="ocr_par",
                id=f"{table_id}_row{row_idx}_par",
                title=row_bbox_str,
                lang="eng",
            ):
                # Process each cell in the row
                for cell_id, cell_data in row_cells:
                    line_ids = cell_data.get("LineIds", [])
                    words_data = cell_data.get("Words", [])

                    # Collect line data for this cell and sort by position
                    cell_lines = []
                    for line_id in line_ids:
                        if line_id in all_lines:
                            line_data = all_lines[line_id]
                            bbox = line_data["BoundingBox"]
                            top_pos = bbox["Top"]
                            left_pos = bbox["Left"]
                            height_val = bbox["Height"]
                            # Use same sorting logic as page content
                            quantized_top = round(top_pos / (height_val * 0.5)) * (
                                height_val * 0.5
                            )
                            cell_lines.append(
                                (quantized_top, left_pos, line_id, line_data)
                            )

                    # Sort lines in the cell by position
                    cell_lines.sort(key=lambda x: (x[0], x[1]))

                    if cell_lines:
                        # Render lines from the cell
                        for _, _, line_id, line_data in cell_lines:
                            _add_line_content(
                                doc, tag, text, line_id, line_data, width, height
                            )

                    # For cells with direct WORD children (no LINE), create synthetic line
                    elif words_data:
                        # Create a synthetic line span for the cell's words
                        cell_bbox = cell_data["BoundingBox"]
                        cell_left = int(cell_bbox["Left"] * width)
                        cell_top = int(cell_bbox["Top"] * height)
                        cell_right = int(
                            (cell_bbox["Left"] + cell_bbox["Width"]) * width
                        )
                        cell_bottom = int(
                            (cell_bbox["Top"] + cell_bbox["Height"]) * height
                        )
                        cell_bbox_str = (
                            f"bbox {cell_left} {cell_top} {cell_right} {cell_bottom}"
                        )
                        line_title = f"{cell_bbox_str}; baseline 0 0"

                        with tag(
                            "span",
                            klass="ocr_line",
                            id=f"{cell_id}_line",
                            title=line_title,
                        ):
                            for word_data in words_data:
                                word_id = word_data["Id"]
                                word_bbox = word_data["BoundingBox"]
                                word_left = int(word_bbox["Left"] * width)
                                word_top = int(word_bbox["Top"] * height)
                                word_right = int(
                                    (word_bbox["Left"] + word_bbox["Width"]) * width
                                )
                                word_bottom = int(
                                    (word_bbox["Top"] + word_bbox["Height"]) * height
                                )
                                word_title = (
                                    f"bbox {word_left} {word_top} {word_right} {word_bottom}; "
                                    f"x_wconf {int(word_data['Confidence'])}"
                                )
                                with tag(
                                    "span",
                                    klass="ocrx_word",
                                    id=word_id,
                                    title=word_title,
                                ):
                                    text(word_data["Text"])


def _add_line_content(
    doc, tag, text, line_id: str, line_data: dict, width: int, height: int
) -> None:
    """Add a single line and its words to the hOCR document."""
    bbox = line_data["BoundingBox"]

    # Convert normalized coordinates to pixels
    left = int(bbox["Left"] * width)
    top = int(bbox["Top"] * height)
    right = int((bbox["Left"] + bbox["Width"]) * width)
    bottom = int((bbox["Top"] + bbox["Height"]) * height)

    line_bbox = f"bbox {left} {top} {right} {bottom}"
    line_title = f"{line_bbox}; baseline 0 0"

    with tag("span", klass="ocr_line", id=line_id, title=line_title):
        for word_id, word_data in line_data["Words"].items():
            _add_word_content(doc, tag, text, word_id, word_data, width, height)


def _add_word_content(
    doc, tag, text, word_id: str, word_data: dict, width: int, height: int
) -> None:
    """Add a single word to the hOCR document."""
    word_bbox = word_data["BoundingBox"]

    word_left = int(word_bbox["Left"] * width)
    word_top = int(word_bbox["Top"] * height)
    word_right = int((word_bbox["Left"] + word_bbox["Width"]) * width)
    word_bottom = int((word_bbox["Top"] + word_bbox["Height"]) * height)

    word_title = (
        f"bbox {word_left} {word_top} {word_right} {word_bottom}; "
        f"x_wconf {int(word_data['Confidence'])}"
    )

    with tag("span", klass="ocrx_word", id=word_id, title=word_title):
        text(word_data["Text"])
