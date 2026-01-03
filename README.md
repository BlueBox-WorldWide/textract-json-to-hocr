# textract-hocr

Convert AWS Textract JSON output to hOCR format for use with document processing tools.

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.7+](https://img.shields.io/badge/python-3.7+-blue.svg)](https://www.python.org/downloads/)

Based on [amazon-textract-hocr-output](https://github.com/aws-samples/amazon-textract-hocr-output) by AWS Samples.

## Features

- ✅ Convert Textract JSON to hOCR HTML format
- ✅ hOCR 1.2 compliant output
- ✅ Support for single and multi-page documents
- ✅ Basic Table extraction with full line/word structure
- ✅ Block grouping based on vertical overlap
- ✅ Extract specific pages or page ranges from multi-page documents
- ✅ Automatic dimension detection from source images (PNG, JPEG, TIFF)
- ✅ PDF dimension extraction support
- ✅ Force custom dimensions (override auto-detection)
- ✅ Fallback to Textract's default 1000x1000 dimensions
- ✅ Command-line interface and Python library
- ✅ Preserves text confidence scores and bounding boxes

## Installation

### From PyPI (when published)

```bash
pip install textract-hocr
```

### From source

```bash
git clone https://github.com/your-username/textract-json-to-hocr.git
cd textract-json-to-hocr
pip install -e .
```

### Development installation

```bash
git clone https://github.com/your-username/textract-json-to-hocr.git
cd textract-json-to-hocr
pip install -e ".[dev]"
```

## Usage

### Command Line

Convert entire document:
```bash
textract-to-hocr input.json output.html
```

Convert with source image for accurate dimensions:
```bash
textract-to-hocr input.json output.html --source image.png
```

Convert specific page only:
```bash
textract-to-hocr input.json output.html --first-page 2 --last-page 2
```

Convert page range:
```bash
textract-to-hocr input.json output.html --first-page 2 --last-page 5
```

Convert from page 3 to end:
```bash
textract-to-hocr input.json output.html --first-page 3
```

Force specific dimensions (override auto-detection):
```bash
textract-to-hocr input.json output.html --width 2550 --height 3300
```

### Python Library

#### Convert entire document

```python
from textract_hocr import textract_to_hocr
import json

# Load Textract JSON output
with open('textract_output.json', 'r') as f:
    textract_result = json.load(f)

# Convert to hOCR
hocr_html = textract_to_hocr(textract_result)

# Save to file
with open('output.html', 'w', encoding='utf-8') as f:
    f.write(hocr_html)
```

#### Convert with source image for accurate dimensions

```python
from textract_hocr import textract_to_hocr
import json

with open('textract_output.json', 'r') as f:
    textract_result = json.load(f)

# Provide source image path
hocr_html = textract_to_hocr(textract_result, source_file='scan.png')

with open('output.html', 'w', encoding='utf-8') as f:
    f.write(hocr_html)
```

#### Convert specific page

```python
from textract_hocr import textract_to_hocr
import json

with open('textract_output.json', 'r') as f:
    textract_result = json.load(f)

# Extract page 2 only
hocr_html = textract_to_hocr(
    textract_result, 
    first_page=2,
    last_page=2,
    source_file='document.pdf'
)

with open('page2.html', 'w', encoding='utf-8') as f:
    f.write(hocr_html)
```

#### Convert page range

```python
from textract_hocr import textract_to_hocr
import json

with open('textract_output.json', 'r') as f:
    textract_result = json.load(f)

# Extract pages 3-5
hocr_html = textract_to_hocr(
    textract_result,
    first_page=3,
    last_page=5,
    source_file='document.pdf'
)

with open('pages_3_5.html', 'w', encoding='utf-8') as f:
    f.write(hocr_html)
```

#### Force custom dimensions

```python
from textract_hocr import textract_to_hocr
import json

with open('textract_output.json', 'r') as f:
    textract_result = json.load(f)

# Override dimension detection
hocr_html = textract_to_hocr(
    textract_result,
    dimensions={'width': 2550, 'height': 3300}
)

with open('output.html', 'w', encoding='utf-8') as f:
    f.write(hocr_html)
```

#### Get document dimensions

```python
from textract_hocr import get_document_dimensions

# From image
dims = get_document_dimensions('image.png')
print(f"Width: {dims['width']}, Height: {dims['height']}")

# From PDF (specific page)
dims = get_document_dimensions('document.pdf', page_number=3)

# Force specific dimensions
dims = get_document_dimensions(dimensions={'width': 2550, 'height': 3300})

# Fallback to Textract defaults
dims = get_document_dimensions()  # Returns {'width': 1000, 'height': 1000}
```

## What is hOCR?

hOCR is an open standard for representing OCR results in HTML format. It embeds text content along with layout information (bounding boxes, confidence scores, etc.) that can be used by document processing tools.

The hOCR format is widely supported by:
- Tesseract OCR
- OCRopus
- ABBYY FineReader
- Document analysis tools
- PDF overlay generators

## Dimension Handling

The converter handles document dimensions in the following priority order:

1. **Image files** (PNG, JPEG, TIFF, etc.): Extracts actual pixel dimensions
2. **PDF files**: Extracts page dimensions from PDF mediabox
3. **Fallback**: Uses Textract's default 1000×1000 normalized dimensions

Textract returns normalized coordinates (0-1 range). This tool converts them to pixel coordinates using the actual document dimensions for accuracy.

## Output Format

The generated hOCR HTML includes:

- hOCR 1.2 compliant structure with proper DOCTYPE and metadata
- `ocr_page` divs with page dimensions
- `ocr_block` divs grouping lines with overlapping vertical positions
- `ocr_table` divs for tables with complete line and word structure
- `ocr_line` spans for text lines
- `ocrx_word` spans for individual words
- Bounding boxes in `bbox left top right bottom` format
- Confidence scores in `x_wconf` property
- Proper baseline information for line elements
- Content ordered by vertical position (top to bottom on page)

### Block Grouping

Lines are grouped into `ocr_block` divs based on vertical overlap:
- Lines with overlapping Y-axis positions are grouped together
- Creates natural paragraph-like blocks without explicit paragraph detection
- Blocks use synthetic IDs (e.g., `block_1_1`, `block_2_1`)
- Each block's bounding box encompasses all contained lines

### Table Support

Tables detected by Textract are converted to float div elements with `ocr_table` class:
- `ocr_table` rendered as `<div>` float elements (no HTML table structure)
- Each cell's content rendered as `ocr_line` spans containing `ocrx_word` spans
- Cell content in reading order (row by row, left to right)
- Bounding box and confidence score for the table region

## Requirements

- Python 3.7+
- yattag >= 1.14.0
- Pillow >= 9.0.0 (for image dimension extraction)
- PyPDF2 >= 3.0.0 (for PDF dimension extraction)

## License

MIT License - see [LICENSE](LICENSE) file for details.

Based on [amazon-textract-hocr-output](https://github.com/aws-samples/amazon-textract-hocr-output) by AWS Samples.

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add some amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## Related Projects

- [aws-samples/amazon-textract-hocr-output](https://github.com/aws-samples/amazon-textract-hocr-output) - Original implementation
- [AWS Textract](https://aws.amazon.com/textract/) - AWS OCR service
- [hOCR 1.2 Spec](http://kba.github.io/hocr-spec/1.2/) - hOCR 1.2 spec documentation
- [Tesseract OCR](https://github.com/tesseract-ocr/tesseract) - Popular open-source OCR engine with hOCR support

## Support

If you encounter any issues or have questions:

1. Check existing [GitHub Issues](https://github.com/BlueBox-WorldWide/textract-json-to-hocr/issues)
2. Create a new issue with:
   - Your Python version
   - The error message or unexpected behavior
   - Sample input (if possible)
   - Steps to reproduce

## Changelog

### 0.1.0 (2026-01-03)

- Initial release
- Support for single and multi-page conversion
- Image and PDF dimension extraction
- Command-line interface
- Python library API
- Textract default dimension fallback
