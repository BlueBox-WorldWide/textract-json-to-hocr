"""Tests for the CLI module."""

import json
import pytest
from pathlib import Path
from textract_hocr.cli import main


class TestCLIBasic:
    """Test basic CLI functionality."""

    def test_main_with_basic_conversion(
        self, tmp_path, sample_textract_single_page
    ):
        """Test basic conversion through CLI."""
        # Create input file
        input_file = tmp_path / "input.json"
        input_file.write_text(json.dumps(sample_textract_single_page))
        
        # Create output path
        output_file = tmp_path / "output.html"
        
        # Run CLI
        exit_code = main([str(input_file), str(output_file)])
        
        assert exit_code == 0
        assert output_file.exists()
        
        # Check output content
        content = output_file.read_text()
        assert "Hello" in content
        assert "World" in content
        assert "ocr_page" in content

    def test_main_with_multipage(self, tmp_path, sample_textract_multi_page):
        """Test multi-page conversion through CLI."""
        input_file = tmp_path / "input.json"
        input_file.write_text(json.dumps(sample_textract_multi_page))
        
        output_file = tmp_path / "output.html"
        
        exit_code = main([str(input_file), str(output_file)])
        
        assert exit_code == 0
        content = output_file.read_text()
        assert "Page One" in content
        assert "Page Two" in content
        assert "Page Three" in content

    def test_input_file_not_found(self, tmp_path):
        """Test error handling when input file doesn't exist."""
        output_file = tmp_path / "output.html"
        
        exit_code = main(["nonexistent.json", str(output_file)])
        
        assert exit_code == 1
        assert not output_file.exists()

    def test_invalid_json(self, tmp_path):
        """Test error handling for invalid JSON."""
        input_file = tmp_path / "invalid.json"
        input_file.write_text("not valid json")
        
        output_file = tmp_path / "output.html"
        
        exit_code = main([str(input_file), str(output_file)])
        
        assert exit_code == 1

    def test_missing_metadata(self, tmp_path):
        """Test error handling for invalid Textract JSON."""
        input_file = tmp_path / "invalid.json"
        input_file.write_text('{"Blocks": []}')
        
        output_file = tmp_path / "output.html"
        
        exit_code = main([str(input_file), str(output_file)])
        
        assert exit_code == 1


class TestCLIPageRange:
    """Test CLI page range options."""

    def test_single_page_extraction(self, tmp_path, sample_textract_multi_page):
        """Test extracting a single page via CLI."""
        input_file = tmp_path / "input.json"
        input_file.write_text(json.dumps(sample_textract_multi_page))
        
        output_file = tmp_path / "output.html"
        
        exit_code = main([
            str(input_file),
            str(output_file),
            "--first-page", "2",
            "--last-page", "2"
        ])
        
        assert exit_code == 0
        content = output_file.read_text()
        assert "Page Two" in content
        assert "Page One" not in content
        assert "Page Three" not in content

    def test_page_range(self, tmp_path, sample_textract_multi_page):
        """Test extracting a page range via CLI."""
        input_file = tmp_path / "input.json"
        input_file.write_text(json.dumps(sample_textract_multi_page))
        
        output_file = tmp_path / "output.html"
        
        exit_code = main([
            str(input_file),
            str(output_file),
            "--first-page", "1",
            "--last-page", "2"
        ])
        
        assert exit_code == 0
        content = output_file.read_text()
        assert "Page One" in content
        assert "Page Two" in content
        assert "Page Three" not in content

    def test_from_page_to_end(self, tmp_path, sample_textract_multi_page):
        """Test extracting from a page to the end via CLI."""
        input_file = tmp_path / "input.json"
        input_file.write_text(json.dumps(sample_textract_multi_page))
        
        output_file = tmp_path / "output.html"
        
        exit_code = main([
            str(input_file),
            str(output_file),
            "--first-page", "2"
        ])
        
        assert exit_code == 0
        content = output_file.read_text()
        assert "Page One" not in content
        assert "Page Two" in content
        assert "Page Three" in content

    def test_invalid_page_number(self, tmp_path, sample_textract_multi_page):
        """Test error handling for invalid page numbers."""
        input_file = tmp_path / "input.json"
        input_file.write_text(json.dumps(sample_textract_multi_page))
        
        output_file = tmp_path / "output.html"
        
        exit_code = main([
            str(input_file),
            str(output_file),
            "--first-page", "10"
        ])
        
        assert exit_code == 1


class TestCLIDimensions:
    """Test CLI dimension options."""

    def test_custom_dimensions(self, tmp_path, sample_textract_single_page):
        """Test forcing custom dimensions via CLI."""
        input_file = tmp_path / "input.json"
        input_file.write_text(json.dumps(sample_textract_single_page))
        
        output_file = tmp_path / "output.html"
        
        exit_code = main([
            str(input_file),
            str(output_file),
            "--width", "2550",
            "--height", "3300"
        ])
        
        assert exit_code == 0
        content = output_file.read_text()
        assert "bbox 0 0 2550 3300" in content

    def test_width_only_warning(self, tmp_path, sample_textract_single_page):
        """Test that providing only width shows warning but works."""
        input_file = tmp_path / "input.json"
        input_file.write_text(json.dumps(sample_textract_single_page))
        
        output_file = tmp_path / "output.html"
        
        exit_code = main([
            str(input_file),
            str(output_file),
            "--width", "2550"
        ])
        
        # Should still succeed but use default dimensions
        assert exit_code == 0
        assert output_file.exists()

    def test_with_source_image(self, tmp_path, sample_textract_single_page, temp_image):
        """Test using source image for dimensions."""
        input_file = tmp_path / "input.json"
        input_file.write_text(json.dumps(sample_textract_single_page))
        
        output_file = tmp_path / "output.html"
        
        exit_code = main([
            str(input_file),
            str(output_file),
            "--source", temp_image
        ])
        
        assert exit_code == 0
        content = output_file.read_text()
        # Image is 800x600
        assert "bbox 0 0 800 600" in content

    def test_nonexistent_source_file(self, tmp_path, sample_textract_single_page):
        """Test handling of nonexistent source file."""
        input_file = tmp_path / "input.json"
        input_file.write_text(json.dumps(sample_textract_single_page))
        
        output_file = tmp_path / "output.html"
        
        # Should work but use defaults
        exit_code = main([
            str(input_file),
            str(output_file),
            "--source", "nonexistent.png"
        ])
        
        assert exit_code == 0
        content = output_file.read_text()
        # Should fall back to 1000x1000
        assert "bbox 0 0 1000 1000" in content


class TestCLIOutputDirectory:
    """Test CLI output directory creation."""

    def test_creates_output_directory(self, tmp_path, sample_textract_single_page):
        """Test that CLI creates output directory if it doesn't exist."""
        input_file = tmp_path / "input.json"
        input_file.write_text(json.dumps(sample_textract_single_page))
        
        # Output in nested directory
        output_file = tmp_path / "nested" / "dir" / "output.html"
        
        exit_code = main([str(input_file), str(output_file)])
        
        assert exit_code == 0
        assert output_file.exists()
        assert output_file.parent.exists()
