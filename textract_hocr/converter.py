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
                                if cell_block["Id"] == cell_id and cell_block["BlockType"] == "CELL":
                                    if "Relationships" in cell_block:
                                        for cell_rel in cell_block["Relationships"]:
                                            if cell_rel["Type"] == "CHILD":
                                                # Collect all child IDs (could be WORD or LINE)
                                                for child_id in cell_rel["Ids"]:
                                                    for child_block in result["Blocks"]:
                                                        if child_block["Id"] == child_id:
                                                            if child_block["BlockType"] == "LINE":
                                                                table_line_ids.add(child_id)
                                                            elif child_block["BlockType"] == "WORD":
                                                                table_word_ids.add(child_id)
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
                                if cell_block["Id"] == cell_id and cell_block["BlockType"] == "CELL":
                                    if "Relationships" in cell_block:
                                        for cell_rel in cell_block["Relationships"]:
                                            if cell_rel["Type"] == "CHILD":
                                                # Collect all child IDs (could be WORD or LINE)
                                                for child_id in cell_rel["Ids"]:
                                                    for child_block in result["Blocks"]:
                                                        if child_block["Id"] == child_id:
                                                            if child_block["BlockType"] == "LINE":
                                                                table_line_ids.add(child_id)
                                                            elif child_block["BlockType"] == "WORD":
                                                                table_word_ids.add(child_id)
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
                                    if child_block["BlockType"] == "LINE" and line_id not in table_line_ids:
                                        result_data[page_num]["lines"][line_id] = {}
                                    break

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
                                if cell_block["Id"] == cell_id and cell_block["BlockType"] == "CELL":
                                    if "Relationships" in cell_block:
                                        for cell_rel in cell_block["Relationships"]:
                                            if cell_rel["Type"] == "CHILD":
                                                # Collect all child IDs (could be WORD or LINE)
                                                for child_id in cell_rel["Ids"]:
                                                    for child_block in result["Blocks"]:
                                                        if child_block["Id"] == child_id:
                                                            if child_block["BlockType"] == "LINE":
                                                                table_line_ids.add(child_id)
                                                            elif child_block["BlockType"] == "WORD":
                                                                table_word_ids.add(child_id)
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
                                    if child_block["BlockType"] == "LINE" and child_id not in table_line_ids:
                                        child_is_line = True
                                    break
                            if child_is_line:
                                result_data[page_num]["lines"][child_id] = {}

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
                                                    if child_block["BlockType"] == "LINE":
                                                        line_ids.append(child_id)
                                                    elif child_block["BlockType"] == "WORD":
                                                        # Store complete word data
                                                        words_data.append({
                                                            "Id": child_id,
                                                            "Text": child_block["Text"],
                                                            "Confidence": child_block.get("Confidence", 100.0),
                                                            "TextType": child_block.get("TextType", "PRINTED"),
                                                            "BoundingBox": child_block["Geometry"]["BoundingBox"],
                                                            "Polygon": child_block["Geometry"]["Polygon"],
                                                        })
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
                content="ocr_page ocr_block ocr_table ocr_line ocrx_word",
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
                top_pos = table_data["BoundingBox"]["Top"]
                content_items.append((top_pos, "table", table_id, table_data))
        
        # Add lines with their top position, excluding table lines
        for line_id, line_data in page_data.get("lines", {}).items():
            if line_data and line_id not in table_line_ids:  # Skip empty placeholders and table lines
                top_pos = line_data["BoundingBox"]["Top"]
                content_items.append((top_pos, "line", line_id, line_data))
        
        # Sort by vertical position (top to bottom)
        content_items.sort(key=lambda x: x[0])
        
        # Group lines into blocks based on bbox intersection
        current_block_lines = []
        block_counter = 1
        last_line_bbox = None
        
        for _, content_type, content_id, content_data in content_items:
            if content_type == "table":
                # Output any pending block first
                if current_block_lines:
                    _add_block_with_lines(doc, tag, text, block_counter, page_num, current_block_lines, width, height)
                    current_block_lines = []
                    block_counter += 1
                
                # Output the table
                _add_table_content(doc, tag, text, content_id, content_data, width, height, page_data.get("lines", {}))
                last_line_bbox = None  # Reset bbox tracking after table
            else:
                # Check if this line's bbox intersects with the last line's bbox
                current_bbox = content_data["BoundingBox"]
                
                if last_line_bbox is not None and not _bboxes_intersect(last_line_bbox, current_bbox):
                    # No intersection - start a new block
                    if current_block_lines:
                        _add_block_with_lines(doc, tag, text, block_counter, page_num, current_block_lines, width, height)
                        current_block_lines = []
                        block_counter += 1
                
                # Add line to current block
                current_block_lines.append((content_id, content_data))
                last_line_bbox = current_bbox
        
        # Output any remaining block
        if current_block_lines:
            _add_block_with_lines(doc, tag, text, block_counter, page_num, current_block_lines, width, height)


def _bboxes_intersect(bbox1: dict, bbox2: dict) -> bool:
    """Check if two bounding boxes have overlapping Y-axis (vertical overlap)."""
    # Get Y coordinates (vertical positions)
    top1 = bbox1["Top"]
    bottom1 = bbox1["Top"] + bbox1["Height"]
    
    top2 = bbox2["Top"]
    bottom2 = bbox2["Top"] + bbox2["Height"]
    
    # Check for Y-axis overlap (same reading order)
    return top1 < bottom2 and bottom1 > top2


def _add_block_with_lines(
    doc, tag, text, block_counter: int, page_num: int, lines: list, width: int, height: int
) -> None:
    """Add a block containing multiple lines with a synthetic ID."""
    # Calculate combined bbox for all lines in the block
    min_left = min(line_data["BoundingBox"]["Left"] for _, line_data in lines)
    min_top = min(line_data["BoundingBox"]["Top"] for _, line_data in lines)
    max_right = max(line_data["BoundingBox"]["Left"] + line_data["BoundingBox"]["Width"] for _, line_data in lines)
    max_bottom = max(line_data["BoundingBox"]["Top"] + line_data["BoundingBox"]["Height"] for _, line_data in lines)
    
    # Convert to pixels
    left = int(min_left * width)
    top = int(min_top * height)
    right = int(max_right * width)
    bottom = int(max_bottom * height)
    
    block_bbox = f"bbox {left} {top} {right} {bottom}"
    block_title = f"{block_bbox}"
    
    with tag("div", klass="ocr_block", id=f"block_{block_counter}_{page_num}", title=block_title, lang="eng"):
        for line_id, line_data in lines:
            _add_line_content(doc, tag, text, line_id, line_data, width, height)


def _add_table_content(
    doc, tag, text, table_id: str, table_data: dict, width: int, height: int, all_lines: dict
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
            key=lambda x: (x[1]["RowIndex"], x[1]["ColumnIndex"])
        )
        
        # Add lines and words from each cell in reading order
        for cell_id, cell_data in sorted_cells:
            line_ids = cell_data.get("LineIds", [])
            words_data = cell_data.get("Words", [])
            
            # Render existing LINE blocks
            for line_id in line_ids:
                if line_id in all_lines:
                    _add_line_content(doc, tag, text, line_id, all_lines[line_id], width, height)
            
            # For cells with direct WORD children (no LINE), create synthetic line
            if words_data and not line_ids:
                # Create a synthetic line span for the cell's words
                cell_bbox = cell_data["BoundingBox"]
                left = int(cell_bbox["Left"] * width)
                top = int(cell_bbox["Top"] * height)
                right = int((cell_bbox["Left"] + cell_bbox["Width"]) * width)
                bottom = int((cell_bbox["Top"] + cell_bbox["Height"]) * height)
                line_bbox = f"bbox {left} {top} {right} {bottom}"
                line_title = f"{line_bbox}; baseline 0 0"
                
                with tag("span", klass="ocr_line", id=f"{cell_id}_line", title=line_title):
                    for word_data in words_data:
                        word_id = word_data["Id"]
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
