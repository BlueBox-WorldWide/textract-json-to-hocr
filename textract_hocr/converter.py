"""
Core conversion functions for Textract JSON to hOCR format.

This module provides the main functionality for converting AWS Textract
JSON output to hOCR HTML format, which is widely used for OCR output.
"""

import json
from typing import Dict, Union, Optional
from yattag import Doc, indent
from PIL import Image
try:
    from PyPDF2 import PdfReader
except ImportError:
    PdfReader = None


# Textract uses normalized coordinates (0-1), but reports dimensions as 1000x1000
TEXTRACT_DEFAULT_WIDTH = 1000
TEXTRACT_DEFAULT_HEIGHT = 1000


def get_document_dimensions(
    file_path: Optional[str] = None,
    page_number: int = 1,
    dimensions: Optional[Dict[str, int]] = None,
) -> Dict[str, int]:
    """
    Get page dimensions from an image or PDF file.

    Args:
        file_path: Path to the source image or PDF file. If None, returns Textract defaults.
        page_number: Page number to extract (1-indexed, used for PDFs).
        dimensions: Optional dict with 'width' and 'height' to force specific dimensions.

    Returns:
        Dictionary with 'width' and 'height' keys in pixels.
        Falls back to Textract's default 1000x1000 if file cannot be read.
    """
    # Use provided dimensions if specified
    if dimensions is not None:
        return dimensions
    if not file_path:
        return {"width": TEXTRACT_DEFAULT_WIDTH, "height": TEXTRACT_DEFAULT_HEIGHT}

    try:
        # Try to open as image first
        with Image.open(file_path) as img:
            return {"width": img.width, "height": img.height}
    except Exception:
        # If not an image, try as PDF
        if PdfReader is not None:
            try:
                with open(file_path, "rb") as pdf_file:
                    pdf = PdfReader(pdf_file)
                    if len(pdf.pages) >= page_number:
                        page = pdf.pages[page_number - 1]
                        # Get mediabox dimensions (in points, 72 points = 1 inch)
                        # Convert to pixels at 72 DPI (common for PDFs)
                        mediabox = page.mediabox
                        width = float(mediabox.width)
                        height = float(mediabox.height)
                        return {"width": int(width), "height": int(height)}
            except Exception:
                pass

    # Fallback to Textract defaults
    return {"width": TEXTRACT_DEFAULT_WIDTH, "height": TEXTRACT_DEFAULT_HEIGHT}


def textract_to_hocr(
    textract_result: Union[str, dict],
    source_file: Optional[str] = None,
    first_page: Optional[int] = None,
    last_page: Optional[int] = None,
    dimensions: Optional[Dict[str, int]] = None,
) -> str:
    """
    Convert Textract JSON output to hOCR HTML format.

    Args:
        textract_result: Textract JSON output as dict or JSON string.
        source_file: Optional path to source image/PDF for dimension extraction.
        first_page: Optional first page to convert (1-indexed). If None, starts from page 1.
        last_page: Optional last page to convert (1-indexed). If None, goes to last page.
        dimensions: Optional dict with 'width' and 'height' to override dimension detection.
                   Example: {'width': 2550, 'height': 3300}

    Returns:
        hOCR HTML string with specified pages.

    Raises:
        ValueError: If page range is invalid.

    Examples:
        # Convert all pages
        hocr = textract_to_hocr(data)
        
        # Convert page 3 only
        hocr = textract_to_hocr(data, first_page=3, last_page=3)
        
        # Convert pages 2-5
        hocr = textract_to_hocr(data, first_page=2, last_page=5)
        
        # Force specific dimensions
        hocr = textract_to_hocr(data, dimensions={'width': 2550, 'height': 3300})
    """
    # Parse JSON string if needed
    if isinstance(textract_result, str):
        textract_result = json.loads(textract_result)

    total_pages = textract_result["DocumentMetadata"]["Pages"]

    # Determine page range
    first = first_page if first_page is not None else 1
    last = last_page if last_page is not None else total_pages

    # Validate page range
    if first < 1 or first > total_pages:
        raise ValueError(
            f"first_page {first} is out of range. Document has {total_pages} pages."
        )
    if last < 1 or last > total_pages:
        raise ValueError(
            f"last_page {last} is out of range. Document has {total_pages} pages."
        )
    if first > last:
        raise ValueError(
            f"first_page ({first}) cannot be greater than last_page ({last})."
        )

    # Single page conversion
    if total_pages == 1:
        return _convert_single_page(textract_result, source_file, dimensions)

    # Multi-page: extract requested range
    if first == 1 and last == total_pages:
        # All pages - use optimized path
        return _convert_multiple_pages(textract_result, source_file, dimensions)
    else:
        # Specific range
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

    for block in result["Blocks"]:
        if block["BlockType"] == "LINE":
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

    for block in result["Blocks"]:
        if block["BlockType"] == "PAGE":
            page_num = block["Page"]
            result_data[page_num] = {"lines": {}, "tables": {}}
            page_dimensions[page_num] = get_document_dimensions(
                source_file, page_num, dimensions
            )

            # Initialize line placeholders
            if "Relationships" in block and block["Relationships"]:
                for line_id in block["Relationships"][0]["Ids"]:
                    result_data[page_num]["lines"][line_id] = {}

        elif block["BlockType"] == "LINE":
            page_num = block["Page"]
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

    # Find all blocks belonging to the requested page range
    for block in result["Blocks"]:
        page_num = block.get("Page")
        if page_num is None or page_num < first_page or page_num > last_page:
            continue

        if block["BlockType"] == "PAGE":
            # Get line IDs for this page
            if "Relationships" in block and len(block["Relationships"]) > 0:
                for line in block["Relationships"][0]["Ids"]:
                    result_data[page_num]["lines"][line] = {}

        elif block["BlockType"] == "LINE":
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
                        if cell_block["Id"] == cell_id and cell_block["BlockType"] == "CELL":
                            row_index = cell_block.get("RowIndex", 0)
                            col_index = cell_block.get("ColumnIndex", 0)
                            row_span = cell_block.get("RowSpan", 1)
                            col_span = cell_block.get("ColumnSpan", 1)
                            
                            # Extract text from cell
                            cell_text = ""
                            if "Relationships" in cell_block:
                                for rel in cell_block["Relationships"]:
                                    if rel["Type"] == "CHILD":
                                        for word_id in rel["Ids"]:
                                            for word_block in all_blocks:
                                                if word_block["Id"] == word_id and word_block["BlockType"] == "WORD":
                                                    if cell_text:
                                                        cell_text += " "
                                                    cell_text += word_block["Text"]
                            
                            page_data[table_id]["Cells"][cell_id] = {
                                "BlockType": cell_block["BlockType"],
                                "Confidence": cell_block.get("Confidence", 100.0),
                                "RowIndex": row_index,
                                "ColumnIndex": col_index,
                                "RowSpan": row_span,
                                "ColumnSpan": col_span,
                                "Text": cell_text,
                                "BoundingBox": {
                                    "Width": cell_block["Geometry"]["BoundingBox"]["Width"],
                                    "Height": cell_block["Geometry"]["BoundingBox"]["Height"],
                                    "Left": cell_block["Geometry"]["BoundingBox"]["Left"],
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
                text("AWS Textract hOCR Output")
            doc.stag(
                "meta",
                ("http-equiv", "Content-Type"),
                content="text/html;charset=utf-8",
            )
            doc.stag("meta", name="ocr-system", content="aws-textract")
            doc.stag(
                "meta",
                name="ocr-capabilities",
                content="ocr_page ocr_carea ocr_par ocr_line ocrx_word ocr_table ocrx_table_cell",
            )

        with tag("body"):
            for page_num in sorted(result_data.keys()):
                _add_page_content(
                    doc, tag, text, page_num, result_data[page_num], page_dimensions[page_num]
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
        with tag("div", klass="ocr_carea", id=f"carea_1_{page_num}"):
            # Add tables first
            for table_id, table_data in page_data.get("tables", {}).items():
                if not table_data:  # Skip empty placeholders
                    continue
                _add_table_content(doc, tag, text, table_id, table_data, width, height)
            
            # Add lines (text outside tables)
            with tag("p", klass="ocr_par", id=f"par_1_{page_num}", lang="eng"):
                for line_id, line_data in page_data.get("lines", {}).items():
                    if not line_data:  # Skip empty placeholders
                        continue
                    _add_line_content(doc, tag, text, line_id, line_data, width, height)


def _add_table_content(
    doc, tag, text, table_id: str, table_data: dict, width: int, height: int
) -> None:
    """Add a table and its cells to the hOCR document."""
    bbox = table_data["BoundingBox"]

    # Convert normalized coordinates to pixels
    left = int(bbox["Left"] * width)
    top = int(bbox["Top"] * height)
    right = int((bbox["Left"] + bbox["Width"]) * width)
    bottom = int((bbox["Top"] + bbox["Height"]) * height)

    table_bbox = f"bbox {left} {top} {right} {bottom}"
    
    # Determine table dimensions (rows and columns)
    max_row = 0
    max_col = 0
    for cell_data in table_data["Cells"].values():
        max_row = max(max_row, cell_data["RowIndex"] + cell_data["RowSpan"] - 1)
        max_col = max(max_col, cell_data["ColumnIndex"] + cell_data["ColumnSpan"] - 1)

    with tag("table", klass="ocr_table", id=table_id, title=table_bbox):
        # Build table structure row by row
        for row in range(1, max_row + 2):  # RowIndex is 1-based
            row_cells = []
            for cell_id, cell_data in table_data["Cells"].items():
                if cell_data["RowIndex"] == row:
                    row_cells.append((cell_data["ColumnIndex"], cell_id, cell_data))
            
            if row_cells:
                row_cells.sort(key=lambda x: x[0])  # Sort by column index
                with tag("tr"):
                    for col_idx, cell_id, cell_data in row_cells:
                        _add_cell_content(doc, tag, text, cell_id, cell_data, width, height)


def _add_cell_content(
    doc, tag, text, cell_id: str, cell_data: dict, width: int, height: int
) -> None:
    """Add a table cell to the hOCR document."""
    bbox = cell_data["BoundingBox"]

    # Convert normalized coordinates to pixels
    cell_left = int(bbox["Left"] * width)
    cell_top = int(bbox["Top"] * height)
    cell_right = int((bbox["Left"] + bbox["Width"]) * width)
    cell_bottom = int((bbox["Top"] + bbox["Height"]) * height)

    cell_bbox = f"bbox {cell_left} {cell_top} {cell_right} {cell_bottom}"
    cell_title = f"{cell_bbox}; x_wconf {int(cell_data['Confidence'])}"

    # Add rowspan/colspan attributes if needed
    attrs = {
        "class": "ocrx_table_cell",
        "id": cell_id,
        "title": cell_title,
    }
    if cell_data["RowSpan"] > 1:
        attrs["rowspan"] = str(cell_data["RowSpan"])
    if cell_data["ColumnSpan"] > 1:
        attrs["colspan"] = str(cell_data["ColumnSpan"])

    with tag("td", **attrs):
        text(cell_data["Text"])


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
