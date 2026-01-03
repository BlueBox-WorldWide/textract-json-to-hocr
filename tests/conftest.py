"""Pytest configuration and shared fixtures."""

import json
import pytest
from pathlib import Path
from PIL import Image
from io import BytesIO


@pytest.fixture
def sample_textract_single_page():
    """Sample Textract JSON for a single-page document."""
    return {
        "DocumentMetadata": {"Pages": 1},
        "Blocks": [
            {
                "BlockType": "PAGE",
                "Id": "page-1",
                "Page": 1,
                "Geometry": {
                    "BoundingBox": {
                        "Width": 1,
                        "Height": 1,
                        "Left": 0,
                        "Top": 0,
                    },
                    "Polygon": [
                        {"X": 0, "Y": 0},
                        {"X": 1, "Y": 0},
                        {"X": 1, "Y": 1},
                        {"X": 0, "Y": 1},
                    ],
                },
                "Relationships": [{"Type": "CHILD", "Ids": ["line-1"]}],
            },
            {
                "BlockType": "LINE",
                "Id": "line-1",
                "Page": 1,
                "Text": "Hello World",
                "Confidence": 99.5,
                "Geometry": {
                    "BoundingBox": {
                        "Width": 0.2,
                        "Height": 0.05,
                        "Left": 0.1,
                        "Top": 0.1,
                    },
                    "Polygon": [
                        {"X": 0.1, "Y": 0.1},
                        {"X": 0.3, "Y": 0.1},
                        {"X": 0.3, "Y": 0.15},
                        {"X": 0.1, "Y": 0.15},
                    ],
                },
                "Relationships": [{"Type": "CHILD", "Ids": ["word-1", "word-2"]}],
            },
            {
                "BlockType": "WORD",
                "Id": "word-1",
                "Page": 1,
                "Text": "Hello",
                "Confidence": 99.8,
                "TextType": "PRINTED",
                "Geometry": {
                    "BoundingBox": {
                        "Width": 0.08,
                        "Height": 0.05,
                        "Left": 0.1,
                        "Top": 0.1,
                    },
                    "Polygon": [
                        {"X": 0.1, "Y": 0.1},
                        {"X": 0.18, "Y": 0.1},
                        {"X": 0.18, "Y": 0.15},
                        {"X": 0.1, "Y": 0.15},
                    ],
                },
            },
            {
                "BlockType": "WORD",
                "Id": "word-2",
                "Page": 1,
                "Text": "World",
                "Confidence": 99.2,
                "TextType": "PRINTED",
                "Geometry": {
                    "BoundingBox": {
                        "Width": 0.1,
                        "Height": 0.05,
                        "Left": 0.2,
                        "Top": 0.1,
                    },
                    "Polygon": [
                        {"X": 0.2, "Y": 0.1},
                        {"X": 0.3, "Y": 0.1},
                        {"X": 0.3, "Y": 0.15},
                        {"X": 0.2, "Y": 0.15},
                    ],
                },
            },
        ],
    }


@pytest.fixture
def sample_textract_multi_page():
    """Sample Textract JSON for a multi-page document."""
    return {
        "DocumentMetadata": {"Pages": 3},
        "Blocks": [
            # Page 1
            {
                "BlockType": "PAGE",
                "Id": "page-1",
                "Page": 1,
                "Geometry": {
                    "BoundingBox": {
                        "Width": 1,
                        "Height": 1,
                        "Left": 0,
                        "Top": 0,
                    },
                    "Polygon": [
                        {"X": 0, "Y": 0},
                        {"X": 1, "Y": 0},
                        {"X": 1, "Y": 1},
                        {"X": 0, "Y": 1},
                    ],
                },
                "Relationships": [{"Type": "CHILD", "Ids": ["line-1-1"]}],
            },
            {
                "BlockType": "LINE",
                "Id": "line-1-1",
                "Page": 1,
                "Text": "Page One",
                "Confidence": 98.0,
                "Geometry": {
                    "BoundingBox": {
                        "Width": 0.2,
                        "Height": 0.05,
                        "Left": 0.1,
                        "Top": 0.1,
                    },
                    "Polygon": [
                        {"X": 0.1, "Y": 0.1},
                        {"X": 0.3, "Y": 0.1},
                        {"X": 0.3, "Y": 0.15},
                        {"X": 0.1, "Y": 0.15},
                    ],
                },
                "Relationships": [{"Type": "CHILD", "Ids": ["word-1-1"]}],
            },
            {
                "BlockType": "WORD",
                "Id": "word-1-1",
                "Page": 1,
                "Text": "Page One",
                "Confidence": 98.0,
                "TextType": "PRINTED",
                "Geometry": {
                    "BoundingBox": {
                        "Width": 0.2,
                        "Height": 0.05,
                        "Left": 0.1,
                        "Top": 0.1,
                    },
                    "Polygon": [
                        {"X": 0.1, "Y": 0.1},
                        {"X": 0.3, "Y": 0.1},
                        {"X": 0.3, "Y": 0.15},
                        {"X": 0.1, "Y": 0.15},
                    ],
                },
            },
            # Page 2
            {
                "BlockType": "PAGE",
                "Id": "page-2",
                "Page": 2,
                "Geometry": {
                    "BoundingBox": {
                        "Width": 1.0,
                        "Height": 1.0,
                        "Left": 0.0,
                        "Top": 0.0,
                    },
                    "Polygon": [
                        {"X": 0.0, "Y": 0.0},
                        {"X": 1.0, "Y": 0.0},
                        {"X": 1.0, "Y": 1.0},
                        {"X": 0.0, "Y": 1.0},
                    ],
                },
                "Relationships": [{"Type": "CHILD", "Ids": ["line-2-1"]}],
            },
            {
                "BlockType": "LINE",
                "Id": "line-2-1",
                "Page": 2,
                "Text": "Page Two",
                "Confidence": 97.5,
                "Geometry": {
                    "BoundingBox": {
                        "Width": 0.2,
                        "Height": 0.05,
                        "Left": 0.2,
                        "Top": 0.2,
                    },
                    "Polygon": [
                        {"X": 0.2, "Y": 0.2},
                        {"X": 0.4, "Y": 0.2},
                        {"X": 0.4, "Y": 0.25},
                        {"X": 0.2, "Y": 0.25},
                    ],
                },
                "Relationships": [{"Type": "CHILD", "Ids": ["word-2-1"]}],
            },
            {
                "BlockType": "WORD",
                "Id": "word-2-1",
                "Page": 2,
                "Text": "Page Two",
                "Confidence": 97.5,
                "TextType": "PRINTED",
                "Geometry": {
                    "BoundingBox": {
                        "Width": 0.2,
                        "Height": 0.05,
                        "Left": 0.2,
                        "Top": 0.2,
                    },
                    "Polygon": [
                        {"X": 0.2, "Y": 0.2},
                        {"X": 0.4, "Y": 0.2},
                        {"X": 0.4, "Y": 0.25},
                        {"X": 0.2, "Y": 0.25},
                    ],
                },
            },
            # Page 3
            {
                "BlockType": "PAGE",
                "Id": "page-3",
                "Page": 3,
                "Geometry": {
                    "BoundingBox": {
                        "Width": 1,
                        "Height": 1,
                        "Left": 0,
                        "Top": 0,
                    },
                    "Polygon": [
                        {"X": 0, "Y": 0},
                        {"X": 1, "Y": 0},
                        {"X": 1, "Y": 1},
                        {"X": 0, "Y": 1},
                    ],
                },
                "Relationships": [{"Type": "CHILD", "Ids": ["line-3-1"]}],
            },
            {
                "BlockType": "LINE",
                "Id": "line-3-1",
                "Page": 3,
                "Text": "Page Three",
                "Confidence": 99.0,
                "Geometry": {
                    "BoundingBox": {
                        "Width": 0.2,
                        "Height": 0.05,
                        "Left": 0.3,
                        "Top": 0.3,
                    },
                    "Polygon": [
                        {"X": 0.3, "Y": 0.3},
                        {"X": 0.5, "Y": 0.3},
                        {"X": 0.5, "Y": 0.35},
                        {"X": 0.3, "Y": 0.35},
                    ],
                },
                "Relationships": [{"Type": "CHILD", "Ids": ["word-3-1"]}],
            },
            {
                "BlockType": "WORD",
                "Id": "word-3-1",
                "Page": 3,
                "Text": "Page Three",
                "Confidence": 99.0,
                "TextType": "PRINTED",
                "Geometry": {
                    "BoundingBox": {
                        "Width": 0.2,
                        "Height": 0.05,
                        "Left": 0.3,
                        "Top": 0.3,
                    },
                    "Polygon": [
                        {"X": 0.3, "Y": 0.3},
                        {"X": 0.5, "Y": 0.3},
                        {"X": 0.5, "Y": 0.35},
                        {"X": 0.3, "Y": 0.35},
                    ],
                },
            },
        ],
    }


@pytest.fixture
def temp_image(tmp_path):
    """Create a temporary test image."""
    image_path = tmp_path / "test_image.png"
    img = Image.new("RGB", (800, 600), color="white")
    img.save(image_path)
    return str(image_path)


@pytest.fixture
def temp_textract_json(tmp_path, sample_textract_single_page):
    """Create a temporary Textract JSON file."""
    json_path = tmp_path / "textract.json"
    json_path.write_text(json.dumps(sample_textract_single_page, indent=2))
    return str(json_path)


@pytest.fixture
def sample_textract_with_table():
    """Sample Textract JSON with a table."""
    return {
        "DocumentMetadata": {"Pages": 1},
        "Blocks": [
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
                "Id": "table-1",
                "Page": 1,
                "Confidence": 98.5,
                "Geometry": {
                    "BoundingBox": {"Width": 0.6, "Height": 0.3, "Left": 0.2, "Top": 0.3},
                    "Polygon": [
                        {"X": 0.2, "Y": 0.3},
                        {"X": 0.8, "Y": 0.3},
                        {"X": 0.8, "Y": 0.6},
                        {"X": 0.2, "Y": 0.6},
                    ],
                },
                "Relationships": [
                    {
                        "Type": "CHILD",
                        "Ids": ["cell-1-1", "cell-1-2", "cell-2-1", "cell-2-2"],
                    }
                ],
            },
            # Row 1, Col 1
            {
                "BlockType": "CELL",
                "Id": "cell-1-1",
                "Page": 1,
                "RowIndex": 1,
                "ColumnIndex": 1,
                "RowSpan": 1,
                "ColumnSpan": 1,
                "Confidence": 99.0,
                "Geometry": {
                    "BoundingBox": {"Width": 0.3, "Height": 0.15, "Left": 0.2, "Top": 0.3},
                    "Polygon": [
                        {"X": 0.2, "Y": 0.3},
                        {"X": 0.5, "Y": 0.3},
                        {"X": 0.5, "Y": 0.45},
                        {"X": 0.2, "Y": 0.45},
                    ],
                },
                "Relationships": [{"Type": "CHILD", "Ids": ["word-t1"]}],
            },
            {
                "BlockType": "WORD",
                "Id": "word-t1",
                "Page": 1,
                "Text": "Header1",
                "Confidence": 99.0,
                "TextType": "PRINTED",
                "Geometry": {
                    "BoundingBox": {"Width": 0.25, "Height": 0.1, "Left": 0.22, "Top": 0.32},
                    "Polygon": [
                        {"X": 0.22, "Y": 0.32},
                        {"X": 0.47, "Y": 0.32},
                        {"X": 0.47, "Y": 0.42},
                        {"X": 0.22, "Y": 0.42},
                    ],
                },
            },
            # Row 1, Col 2
            {
                "BlockType": "CELL",
                "Id": "cell-1-2",
                "Page": 1,
                "RowIndex": 1,
                "ColumnIndex": 2,
                "RowSpan": 1,
                "ColumnSpan": 1,
                "Confidence": 99.0,
                "Geometry": {
                    "BoundingBox": {"Width": 0.3, "Height": 0.15, "Left": 0.5, "Top": 0.3},
                    "Polygon": [
                        {"X": 0.5, "Y": 0.3},
                        {"X": 0.8, "Y": 0.3},
                        {"X": 0.8, "Y": 0.45},
                        {"X": 0.5, "Y": 0.45},
                    ],
                },
                "Relationships": [{"Type": "CHILD", "Ids": ["word-t2"]}],
            },
            {
                "BlockType": "WORD",
                "Id": "word-t2",
                "Page": 1,
                "Text": "Header2",
                "Confidence": 99.0,
                "TextType": "PRINTED",
                "Geometry": {
                    "BoundingBox": {"Width": 0.25, "Height": 0.1, "Left": 0.52, "Top": 0.32},
                    "Polygon": [
                        {"X": 0.52, "Y": 0.32},
                        {"X": 0.77, "Y": 0.32},
                        {"X": 0.77, "Y": 0.42},
                        {"X": 0.52, "Y": 0.42},
                    ],
                },
            },
            # Row 2, Col 1
            {
                "BlockType": "CELL",
                "Id": "cell-2-1",
                "Page": 1,
                "RowIndex": 2,
                "ColumnIndex": 1,
                "RowSpan": 1,
                "ColumnSpan": 1,
                "Confidence": 98.5,
                "Geometry": {
                    "BoundingBox": {"Width": 0.3, "Height": 0.15, "Left": 0.2, "Top": 0.45},
                    "Polygon": [
                        {"X": 0.2, "Y": 0.45},
                        {"X": 0.5, "Y": 0.45},
                        {"X": 0.5, "Y": 0.6},
                        {"X": 0.2, "Y": 0.6},
                    ],
                },
                "Relationships": [{"Type": "CHILD", "Ids": ["word-t3"]}],
            },
            {
                "BlockType": "WORD",
                "Id": "word-t3",
                "Page": 1,
                "Text": "Value1",
                "Confidence": 98.5,
                "TextType": "PRINTED",
                "Geometry": {
                    "BoundingBox": {"Width": 0.25, "Height": 0.1, "Left": 0.22, "Top": 0.47},
                    "Polygon": [
                        {"X": 0.22, "Y": 0.47},
                        {"X": 0.47, "Y": 0.47},
                        {"X": 0.47, "Y": 0.57},
                        {"X": 0.22, "Y": 0.57},
                    ],
                },
            },
            # Row 2, Col 2
            {
                "BlockType": "CELL",
                "Id": "cell-2-2",
                "Page": 1,
                "RowIndex": 2,
                "ColumnIndex": 2,
                "RowSpan": 1,
                "ColumnSpan": 1,
                "Confidence": 98.0,
                "Geometry": {
                    "BoundingBox": {"Width": 0.3, "Height": 0.15, "Left": 0.5, "Top": 0.45},
                    "Polygon": [
                        {"X": 0.5, "Y": 0.45},
                        {"X": 0.8, "Y": 0.45},
                        {"X": 0.8, "Y": 0.6},
                        {"X": 0.5, "Y": 0.6},
                    ],
                },
                "Relationships": [{"Type": "CHILD", "Ids": ["word-t4"]}],
            },
            {
                "BlockType": "WORD",
                "Id": "word-t4",
                "Page": 1,
                "Text": "Value2",
                "Confidence": 98.0,
                "TextType": "PRINTED",
                "Geometry": {
                    "BoundingBox": {"Width": 0.25, "Height": 0.1, "Left": 0.52, "Top": 0.47},
                    "Polygon": [
                        {"X": 0.52, "Y": 0.47},
                        {"X": 0.77, "Y": 0.47},
                        {"X": 0.77, "Y": 0.57},
                        {"X": 0.52, "Y": 0.57},
                    ],
                },
            },
        ],
    }
