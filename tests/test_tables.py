"""Tests for table and cell handling."""

import pytest
from textract_hocr.converter import textract_to_hocr


class TestTableHandling:
    """Test TABLE and CELL block handling."""

    def test_basic_table_conversion(self, sample_textract_with_table):
        """Test basic table conversion."""
        result = textract_to_hocr(sample_textract_with_table)
        
        # Check HTML structure
        assert '<?xml version="1.0" encoding="UTF-8"?>' in result
        assert 'ocr_table' in result
        
        # Check table content
        assert 'Header1' in result
        assert 'Header2' in result
        assert 'Value1' in result
        assert 'Value2' in result

    def test_table_structure(self, sample_textract_with_table):
        """Test that table is a float div element with ocr_table class."""
        result = textract_to_hocr(sample_textract_with_table)
        
        # Check for div float structure
        assert '<div' in result
        assert 'class="ocr_table"' in result
        
        # Should NOT use HTML table structure
        assert '<table' not in result
        assert '<tr>' not in result
        assert '<td' not in result

    def test_table_bounding_boxes(self, sample_textract_with_table):
        """Test that table and cells have bounding boxes."""
        result = textract_to_hocr(sample_textract_with_table)
        
        # Table should have bbox
        assert 'bbox 200 300 800 600' in result  # Table bbox
        
        # Cells should have bbox too
        assert 'bbox' in result

    def test_table_confidence_scores(self, sample_textract_with_table):
        """Test that cell confidence scores are preserved."""
        result = textract_to_hocr(sample_textract_with_table)
        
        # Should have confidence scores for cells
        assert 'x_wconf' in result

    def test_mixed_content_with_tables(self, sample_textract_with_table):
        """Test document with both tables and regular text."""
        # Add a line to the document
        sample_textract_with_table["Blocks"].insert(1, {
            "BlockType": "LINE",
            "Id": "line-1",
            "Page": 1,
            "Text": "Some text before table",
            "Confidence": 99.0,
            "Geometry": {
                "BoundingBox": {"Width": 0.5, "Height": 0.05, "Left": 0.1, "Top": 0.1},
                "Polygon": [
                    {"X": 0.1, "Y": 0.1},
                    {"X": 0.6, "Y": 0.1},
                    {"X": 0.6, "Y": 0.15},
                    {"X": 0.1, "Y": 0.15},
                ],
            },
            "Relationships": [{"Type": "CHILD", "Ids": ["word-line1"]}],
        })
        sample_textract_with_table["Blocks"].insert(2, {
            "BlockType": "WORD",
            "Id": "word-line1",
            "Page": 1,
            "Text": "Some text before table",
            "Confidence": 99.0,
            "TextType": "PRINTED",
            "Geometry": {
                "BoundingBox": {"Width": 0.5, "Height": 0.05, "Left": 0.1, "Top": 0.1},
                "Polygon": [
                    {"X": 0.1, "Y": 0.1},
                    {"X": 0.6, "Y": 0.1},
                    {"X": 0.6, "Y": 0.15},
                    {"X": 0.1, "Y": 0.15},
                ],
            },
        })
        
        result = textract_to_hocr(sample_textract_with_table)
        
        # Both table and text should be present
        assert 'Some text before table' in result
        assert 'Header1' in result
        assert 'ocr_table' in result
        assert 'ocr_line' in result

    def test_empty_table_cells(self):
        """Test handling of empty table cells."""
        data = {
            "DocumentMetadata": {"Pages": 1},
            "Blocks": [
                {
                    "BlockType": "TABLE",
                    "Id": "table-1",
                    "Page": 1,
                    "Confidence": 98.0,
                    "Geometry": {
                        "BoundingBox": {"Width": 0.4, "Height": 0.2, "Left": 0.3, "Top": 0.4},
                        "Polygon": [
                            {"X": 0.3, "Y": 0.4},
                            {"X": 0.7, "Y": 0.4},
                            {"X": 0.7, "Y": 0.6},
                            {"X": 0.3, "Y": 0.6},
                        ],
                    },
                    "Relationships": [{"Type": "CHILD", "Ids": ["cell-1"]}],
                },
                {
                    "BlockType": "CELL",
                    "Id": "cell-1",
                    "Page": 1,
                    "RowIndex": 1,
                    "ColumnIndex": 1,
                    "RowSpan": 1,
                    "ColumnSpan": 1,
                    "Confidence": 98.0,
                    "Geometry": {
                        "BoundingBox": {"Width": 0.4, "Height": 0.2, "Left": 0.3, "Top": 0.4},
                        "Polygon": [
                            {"X": 0.3, "Y": 0.4},
                            {"X": 0.7, "Y": 0.4},
                            {"X": 0.7, "Y": 0.6},
                            {"X": 0.3, "Y": 0.6},
                        ],
                    },
                    # No Relationships - empty cell
                },
            ],
        }
        
        # Should not crash on empty cells
        result = textract_to_hocr(data)
        assert 'ocr_table' in result
        assert '<div' in result

    def test_table_with_rowspan_colspan(self):
        """Test handling of cells with rowspan/colspan."""
        data = {
            "DocumentMetadata": {"Pages": 1},
            "Blocks": [
                {
                    "BlockType": "TABLE",
                    "Id": "table-1",
                    "Page": 1,
                    "Confidence": 98.0,
                    "Geometry": {
                        "BoundingBox": {"Width": 0.6, "Height": 0.3, "Left": 0.2, "Top": 0.3},
                        "Polygon": [
                            {"X": 0.2, "Y": 0.3},
                            {"X": 0.8, "Y": 0.3},
                            {"X": 0.8, "Y": 0.6},
                            {"X": 0.2, "Y": 0.6},
                        ],
                    },
                    "Relationships": [{"Type": "CHILD", "Ids": ["cell-merged"]}],
                },
                {
                    "BlockType": "CELL",
                    "Id": "cell-merged",
                    "Page": 1,
                    "RowIndex": 1,
                    "ColumnIndex": 1,
                    "RowSpan": 2,
                    "ColumnSpan": 3,
                    "Confidence": 98.0,
                    "Geometry": {
                        "BoundingBox": {"Width": 0.6, "Height": 0.3, "Left": 0.2, "Top": 0.3},
                        "Polygon": [
                            {"X": 0.2, "Y": 0.3},
                            {"X": 0.8, "Y": 0.3},
                            {"X": 0.8, "Y": 0.6},
                            {"X": 0.2, "Y": 0.6},
                        ],
                    },
                    "Relationships": [{"Type": "CHILD", "Ids": ["word-merged"]}],
                },
                {
                    "BlockType": "WORD",
                    "Id": "word-merged",
                    "Page": 1,
                    "Text": "Merged Cell",
                    "Confidence": 98.0,
                    "TextType": "PRINTED",
                    "Geometry": {
                        "BoundingBox": {"Width": 0.5, "Height": 0.25, "Left": 0.25, "Top": 0.35},
                        "Polygon": [
                            {"X": 0.25, "Y": 0.35},
                            {"X": 0.75, "Y": 0.35},
                            {"X": 0.75, "Y": 0.6},
                            {"X": 0.25, "Y": 0.6},
                        ],
                    },
                },
            ],
        }
        
        result = textract_to_hocr(data)
        
        # Float div structure doesn't use rowspan/colspan
        assert 'class="ocr_table"' in result
        assert 'Merged Cell' in result
        # No HTML table attributes
        assert 'rowspan=' not in result
        assert 'colspan=' not in result

    def test_multipage_with_tables(self):
        """Test multi-page document with tables on different pages."""
        data = {
            "DocumentMetadata": {"Pages": 2},
            "Blocks": [
                # Page 1 with table
                {
                    "BlockType": "PAGE",
                    "Id": "page-1",
                    "Page": 1,
                    "Geometry": {
                        "BoundingBox": {"Width": 1.0, "Height": 1.0, "Left": 0.0, "Top": 0.0},
                        "Polygon": [
                            {"X": 0.0, "Y": 0.0},
                            {"X": 1.0, "Y": 0.0},
                            {"X": 1.0, "Y": 1.0},
                            {"X": 0.0, "Y": 1.0},
                        ],
                    },
                },
                {
                    "BlockType": "TABLE",
                    "Id": "table-p1",
                    "Page": 1,
                    "Confidence": 98.0,
                    "Geometry": {
                        "BoundingBox": {"Width": 0.4, "Height": 0.2, "Left": 0.3, "Top": 0.3},
                        "Polygon": [
                            {"X": 0.3, "Y": 0.3},
                            {"X": 0.7, "Y": 0.3},
                            {"X": 0.7, "Y": 0.5},
                            {"X": 0.3, "Y": 0.5},
                        ],
                    },
                    "Relationships": [{"Type": "CHILD", "Ids": ["cell-p1"]}],
                },
                {
                    "BlockType": "CELL",
                    "Id": "cell-p1",
                    "Page": 1,
                    "RowIndex": 1,
                    "ColumnIndex": 1,
                    "RowSpan": 1,
                    "ColumnSpan": 1,
                    "Confidence": 98.0,
                    "Geometry": {
                        "BoundingBox": {"Width": 0.4, "Height": 0.2, "Left": 0.3, "Top": 0.3},
                        "Polygon": [
                            {"X": 0.3, "Y": 0.3},
                            {"X": 0.7, "Y": 0.3},
                            {"X": 0.7, "Y": 0.5},
                            {"X": 0.3, "Y": 0.5},
                        ],
                    },
                    "Relationships": [{"Type": "CHILD", "Ids": ["word-p1"]}],
                },
                {
                    "BlockType": "WORD",
                    "Id": "word-p1",
                    "Page": 1,
                    "Text": "Page1Table",
                    "Confidence": 98.0,
                    "TextType": "PRINTED",
                    "Geometry": {
                        "BoundingBox": {"Width": 0.35, "Height": 0.15, "Left": 0.32, "Top": 0.32},
                        "Polygon": [
                            {"X": 0.32, "Y": 0.32},
                            {"X": 0.67, "Y": 0.32},
                            {"X": 0.67, "Y": 0.47},
                            {"X": 0.32, "Y": 0.47},
                        ],
                    },
                },
                # Page 2 with table
                {
                    "BlockType": "PAGE",
                    "Id": "page-2",
                    "Page": 2,
                    "Geometry": {
                        "BoundingBox": {"Width": 1.0, "Height": 1.0, "Left": 0.0, "Top": 0.0},
                        "Polygon": [
                            {"X": 0.0, "Y": 0.0},
                            {"X": 1.0, "Y": 0.0},
                            {"X": 1.0, "Y": 1.0},
                            {"X": 0.0, "Y": 1.0},
                        ],
                    },
                },
                {
                    "BlockType": "TABLE",
                    "Id": "table-p2",
                    "Page": 2,
                    "Confidence": 97.5,
                    "Geometry": {
                        "BoundingBox": {"Width": 0.4, "Height": 0.2, "Left": 0.3, "Top": 0.4},
                        "Polygon": [
                            {"X": 0.3, "Y": 0.4},
                            {"X": 0.7, "Y": 0.4},
                            {"X": 0.7, "Y": 0.6},
                            {"X": 0.3, "Y": 0.6},
                        ],
                    },
                    "Relationships": [{"Type": "CHILD", "Ids": ["cell-p2"]}],
                },
                {
                    "BlockType": "CELL",
                    "Id": "cell-p2",
                    "Page": 2,
                    "RowIndex": 1,
                    "ColumnIndex": 1,
                    "RowSpan": 1,
                    "ColumnSpan": 1,
                    "Confidence": 97.5,
                    "Geometry": {
                        "BoundingBox": {"Width": 0.4, "Height": 0.2, "Left": 0.3, "Top": 0.4},
                        "Polygon": [
                            {"X": 0.3, "Y": 0.4},
                            {"X": 0.7, "Y": 0.4},
                            {"X": 0.7, "Y": 0.6},
                            {"X": 0.3, "Y": 0.6},
                        ],
                    },
                    "Relationships": [{"Type": "CHILD", "Ids": ["word-p2"]}],
                },
                {
                    "BlockType": "WORD",
                    "Id": "word-p2",
                    "Page": 2,
                    "Text": "Page2Table",
                    "Confidence": 97.5,
                    "TextType": "PRINTED",
                    "Geometry": {
                        "BoundingBox": {"Width": 0.35, "Height": 0.15, "Left": 0.32, "Top": 0.42},
                        "Polygon": [
                            {"X": 0.32, "Y": 0.42},
                            {"X": 0.67, "Y": 0.42},
                            {"X": 0.67, "Y": 0.57},
                            {"X": 0.32, "Y": 0.57},
                        ],
                    },
                },
            ],
        }
        
        result = textract_to_hocr(data)
        
        # Both pages should have tables
        assert 'Page1Table' in result
        assert 'Page2Table' in result
        assert result.count('ocr_table') >= 2

    def test_content_ordering_by_vertical_position(self):
        """Test that content (tables and text) are ordered by vertical position."""
        data = {
            "DocumentMetadata": {"Pages": 1},
            "Blocks": [
                # Line at top (0.1)
                {
                    "BlockType": "LINE",
                    "Id": "line-top",
                    "Page": 1,
                    "Text": "Text at top",
                    "Confidence": 99.0,
                    "Geometry": {
                        "BoundingBox": {"Width": 0.5, "Height": 0.05, "Left": 0.1, "Top": 0.1},
                        "Polygon": [
                            {"X": 0.1, "Y": 0.1},
                            {"X": 0.6, "Y": 0.1},
                            {"X": 0.6, "Y": 0.15},
                            {"X": 0.1, "Y": 0.15},
                        ],
                    },
                    "Relationships": [{"Type": "CHILD", "Ids": ["word-top"]}],
                },
                {
                    "BlockType": "WORD",
                    "Id": "word-top",
                    "Page": 1,
                    "Text": "Text at top",
                    "Confidence": 99.0,
                    "TextType": "PRINTED",
                    "Geometry": {
                        "BoundingBox": {"Width": 0.5, "Height": 0.05, "Left": 0.1, "Top": 0.1},
                        "Polygon": [
                            {"X": 0.1, "Y": 0.1},
                            {"X": 0.6, "Y": 0.1},
                            {"X": 0.6, "Y": 0.15},
                            {"X": 0.1, "Y": 0.15},
                        ],
                    },
                },
                # Table in middle (0.3)
                {
                    "BlockType": "TABLE",
                    "Id": "table-middle",
                    "Page": 1,
                    "Confidence": 98.0,
                    "Geometry": {
                        "BoundingBox": {"Width": 0.4, "Height": 0.2, "Left": 0.3, "Top": 0.3},
                        "Polygon": [
                            {"X": 0.3, "Y": 0.3},
                            {"X": 0.7, "Y": 0.3},
                            {"X": 0.7, "Y": 0.5},
                            {"X": 0.3, "Y": 0.5},
                        ],
                    },
                    "Relationships": [{"Type": "CHILD", "Ids": ["cell-middle"]}],
                },
                {
                    "BlockType": "CELL",
                    "Id": "cell-middle",
                    "Page": 1,
                    "RowIndex": 1,
                    "ColumnIndex": 1,
                    "RowSpan": 1,
                    "ColumnSpan": 1,
                    "Confidence": 98.0,
                    "Geometry": {
                        "BoundingBox": {"Width": 0.4, "Height": 0.2, "Left": 0.3, "Top": 0.3},
                        "Polygon": [
                            {"X": 0.3, "Y": 0.3},
                            {"X": 0.7, "Y": 0.3},
                            {"X": 0.7, "Y": 0.5},
                            {"X": 0.3, "Y": 0.5},
                        ],
                    },
                    "Relationships": [{"Type": "CHILD", "Ids": ["word-middle"]}],
                },
                {
                    "BlockType": "WORD",
                    "Id": "word-middle",
                    "Page": 1,
                    "Text": "Table",
                    "Confidence": 98.0,
                    "TextType": "PRINTED",
                    "Geometry": {
                        "BoundingBox": {"Width": 0.35, "Height": 0.15, "Left": 0.32, "Top": 0.32},
                        "Polygon": [
                            {"X": 0.32, "Y": 0.32},
                            {"X": 0.67, "Y": 0.32},
                            {"X": 0.67, "Y": 0.47},
                            {"X": 0.32, "Y": 0.47},
                        ],
                    },
                },
                # Line at bottom (0.7)
                {
                    "BlockType": "LINE",
                    "Id": "line-bottom",
                    "Page": 1,
                    "Text": "Text at bottom",
                    "Confidence": 99.0,
                    "Geometry": {
                        "BoundingBox": {"Width": 0.5, "Height": 0.05, "Left": 0.1, "Top": 0.7},
                        "Polygon": [
                            {"X": 0.1, "Y": 0.7},
                            {"X": 0.6, "Y": 0.7},
                            {"X": 0.6, "Y": 0.75},
                            {"X": 0.1, "Y": 0.75},
                        ],
                    },
                    "Relationships": [{"Type": "CHILD", "Ids": ["word-bottom"]}],
                },
                {
                    "BlockType": "WORD",
                    "Id": "word-bottom",
                    "Page": 1,
                    "Text": "Text at bottom",
                    "Confidence": 99.0,
                    "TextType": "PRINTED",
                    "Geometry": {
                        "BoundingBox": {"Width": 0.5, "Height": 0.05, "Left": 0.1, "Top": 0.7},
                        "Polygon": [
                            {"X": 0.1, "Y": 0.7},
                            {"X": 0.6, "Y": 0.7},
                            {"X": 0.6, "Y": 0.75},
                            {"X": 0.1, "Y": 0.75},
                        ],
                    },
                },
            ],
        }
        
        result = textract_to_hocr(data)
        
        # Check order: text should appear before table, table before bottom text
        top_text_pos = result.find("Text at top")
        table_pos = result.find("Table")
        bottom_text_pos = result.find("Text at bottom")
        
        assert top_text_pos < table_pos, "Top text should appear before table"
        assert table_pos < bottom_text_pos, "Table should appear before bottom text"
        
        # Should use div tags for blocks
        assert '<div class="ocr_block"' in result
