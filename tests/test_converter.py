"""Tests for the converter module."""

import json
import pytest
from textract_hocr.converter import (
    textract_to_hocr,
    get_document_dimensions,
    TEXTRACT_DEFAULT_WIDTH,
    TEXTRACT_DEFAULT_HEIGHT,
)


class TestGetDocumentDimensions:
    """Test dimension extraction functionality."""

    def test_default_dimensions(self):
        """Test default Textract dimensions when no file provided."""
        dims = get_document_dimensions()
        assert dims == {"width": TEXTRACT_DEFAULT_WIDTH, "height": TEXTRACT_DEFAULT_HEIGHT}
        assert dims == {"width": 1000, "height": 1000}

    def test_custom_dimensions_override(self):
        """Test forcing custom dimensions."""
        custom = {"width": 2550, "height": 3300}
        dims = get_document_dimensions(dimensions=custom)
        assert dims == custom

    def test_custom_dimensions_priority(self):
        """Test that custom dimensions override file detection."""
        custom = {"width": 1234, "height": 5678}
        # Even with a file path, custom dimensions should win
        dims = get_document_dimensions(
            file_path="nonexistent.png", dimensions=custom
        )
        assert dims == custom

    def test_image_dimensions(self, temp_image):
        """Test dimension extraction from image file."""
        dims = get_document_dimensions(temp_image)
        assert dims == {"width": 800, "height": 600}

    def test_nonexistent_file_fallback(self):
        """Test fallback to defaults when file doesn't exist."""
        dims = get_document_dimensions("nonexistent_file.png")
        assert dims == {"width": 1000, "height": 1000}


class TestTextractToHocrSinglePage:
    """Test single-page conversion."""

    def test_basic_conversion(self, sample_textract_single_page):
        """Test basic single-page conversion."""
        result = textract_to_hocr(sample_textract_single_page)
        
        # Check HTML structure
        assert '<?xml version="1.0" encoding="UTF-8"?>' in result
        assert 'DOCTYPE html' in result
        assert 'xmlns="http://www.w3.org/1999/xhtml"' in result
        
        # Check metadata
        assert 'ocr-system' in result
        assert 'aws-textract' in result
        
        # Check content
        assert 'Hello' in result
        assert 'World' in result
        assert 'ocr_page' in result
        assert 'ocr_line' in result
        assert 'ocrx_word' in result

    def test_conversion_with_json_string(self, sample_textract_single_page):
        """Test conversion from JSON string input."""
        json_str = json.dumps(sample_textract_single_page)
        result = textract_to_hocr(json_str)
        assert 'Hello' in result
        assert 'World' in result

    def test_confidence_scores(self, sample_textract_single_page):
        """Test that confidence scores are preserved."""
        result = textract_to_hocr(sample_textract_single_page)
        assert 'x_wconf 99' in result  # Should have confidence scores

    def test_bounding_boxes(self, sample_textract_single_page):
        """Test that bounding boxes are included."""
        result = textract_to_hocr(sample_textract_single_page)
        assert 'bbox' in result
        # Check for pixel coordinates (not normalized)
        assert 'bbox 100 100' in result or 'bbox 200 100' in result

    def test_custom_dimensions(self, sample_textract_single_page):
        """Test conversion with custom dimensions."""
        custom_dims = {"width": 2000, "height": 3000}
        result = textract_to_hocr(sample_textract_single_page, dimensions=custom_dims)
        
        # Check page dimensions in output
        assert 'bbox 0 0 2000 3000' in result


class TestTextractToHocrMultiPage:
    """Test multi-page conversion."""

    def test_all_pages_conversion(self, sample_textract_multi_page):
        """Test converting all pages."""
        result = textract_to_hocr(sample_textract_multi_page)
        
        # All three pages should be present
        assert 'Page One' in result
        assert 'Page Two' in result
        assert 'Page Three' in result
        
        # Should have multiple page divs
        assert result.count('ocr_page') >= 3

    def test_single_page_extraction(self, sample_textract_multi_page):
        """Test extracting a single page from multi-page document."""
        result = textract_to_hocr(
            sample_textract_multi_page, first_page=2, last_page=2
        )
        
        # Only page 2 should be present
        assert 'Page Two' in result
        assert 'Page One' not in result
        assert 'Page Three' not in result

    def test_page_range_extraction(self, sample_textract_multi_page):
        """Test extracting a page range."""
        result = textract_to_hocr(
            sample_textract_multi_page, first_page=1, last_page=2
        )
        
        # Pages 1-2 should be present
        assert 'Page One' in result
        assert 'Page Two' in result
        assert 'Page Three' not in result

    def test_page_range_from_middle_to_end(self, sample_textract_multi_page):
        """Test extracting from middle page to end."""
        result = textract_to_hocr(sample_textract_multi_page, first_page=2)
        
        # Pages 2-3 should be present
        assert 'Page One' not in result
        assert 'Page Two' in result
        assert 'Page Three' in result

    def test_invalid_page_range(self, sample_textract_multi_page):
        """Test error handling for invalid page ranges."""
        # Page number too high
        with pytest.raises(ValueError, match="out of range"):
            textract_to_hocr(sample_textract_multi_page, first_page=5)
        
        # Page number too low
        with pytest.raises(ValueError, match="out of range"):
            textract_to_hocr(sample_textract_multi_page, first_page=0)
        
        # First page > last page
        with pytest.raises(ValueError, match="cannot be greater than"):
            textract_to_hocr(
                sample_textract_multi_page, first_page=3, last_page=1
            )

    def test_page_numbers_in_output(self, sample_textract_multi_page):
        """Test that page numbers are correctly set in hOCR."""
        result = textract_to_hocr(sample_textract_multi_page)
        
        # Check for page identifiers
        assert 'id="page_1"' in result
        assert 'id="page_2"' in result
        assert 'id="page_3"' in result


class TestTextractToHocrEdgeCases:
    """Test edge cases and error handling."""

    def test_empty_relationships(self):
        """Test handling of blocks without relationships."""
        data = {
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
                            {"X": 0.0, "Y": 0.0},
                            {"X": 1.0, "Y": 0.0},
                            {"X": 1.0, "Y": 1.0},
                            {"X": 0.0, "Y": 1.0},
                        ],
                    },
                    # No relationships
                }
            ],
        }
        
        # Should not crash
        result = textract_to_hocr(data)
        assert 'ocr_page' in result

    def test_line_without_words(self):
        """Test handling of lines without word relationships."""
        data = {
            "DocumentMetadata": {"Pages": 1},
            "Blocks": [
                {
                    "BlockType": "LINE",
                    "Id": "line-1",
                    "Page": 1,
                    "Text": "Solo Line",
                    "Confidence": 95.0,
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
                    # No word relationships
                }
            ],
        }
        
        # Should not crash
        result = textract_to_hocr(data)
        assert 'ocr_line' in result

    def test_invalid_json_string(self):
        """Test error handling for invalid JSON."""
        with pytest.raises(json.JSONDecodeError):
            textract_to_hocr("not valid json")

    def test_missing_metadata(self):
        """Test error handling for missing DocumentMetadata."""
        with pytest.raises(KeyError):
            textract_to_hocr({"Blocks": []})


class TestHocrOutput:
    """Test hOCR output format compliance."""

    def test_html_structure(self, sample_textract_single_page):
        """Test basic HTML structure."""
        result = textract_to_hocr(sample_textract_single_page)
        
        # XML declaration
        assert result.startswith('<?xml version="1.0" encoding="UTF-8"?>')
        
        # DOCTYPE
        assert '<!DOCTYPE html' in result
        
        # HTML tag with namespace
        assert '<html xmlns="http://www.w3.org/1999/xhtml"' in result
        
        # Required sections
        assert '<head>' in result
        assert '<body>' in result
        assert '</html>' in result

    def test_hocr_metadata(self, sample_textract_single_page):
        """Test hOCR metadata tags."""
        result = textract_to_hocr(sample_textract_single_page)
        
        # OCR system metadata
        assert 'name="ocr-system"' in result
        assert 'content="aws-textract"' in result
        
        # Capabilities
        assert 'name="ocr-capabilities"' in result
        assert 'ocr_page' in result
        assert 'ocr_line' in result
        assert 'ocrx_word' in result

    def test_page_properties(self, sample_textract_single_page):
        """Test page-level hOCR properties."""
        result = textract_to_hocr(sample_textract_single_page)
        
        # Page class and bbox
        assert 'class="ocr_page"' in result
        assert 'title="bbox 0 0 1000 1000' in result
        assert 'ppageno' in result

    def test_line_properties(self, sample_textract_single_page):
        """Test line-level hOCR properties."""
        result = textract_to_hocr(sample_textract_single_page)
        
        # Line class and bbox
        assert 'class="ocr_line"' in result
        assert 'baseline' in result

    def test_word_properties(self, sample_textract_single_page):
        """Test word-level hOCR properties."""
        result = textract_to_hocr(sample_textract_single_page)
        
        # Word class, bbox, and confidence
        assert 'class="ocrx_word"' in result
        assert 'x_wconf' in result
