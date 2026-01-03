# Example: Using textract-hocr as a library

This directory contains examples of using textract-hocr in your Python projects.

## Basic Usage

```python
from textract_hocr import textract_to_hocr
import json

# Load your Textract JSON
with open('textract_output.json', 'r') as f:
    textract_data = json.load(f)

# Convert to hOCR
hocr_output = textract_to_hocr(textract_data, source_file='original_image.png')

# Save to file
with open('output.html', 'w', encoding='utf-8') as f:
    f.write(hocr_output)
```

## Processing Multiple Files

```python
from pathlib import Path
from textract_hocr import textract_to_hocr
import json

# Process all JSON files in a directory
input_dir = Path('textract_outputs')
output_dir = Path('hocr_outputs')
output_dir.mkdir(exist_ok=True)

for json_file in input_dir.glob('*.json'):
    with open(json_file, 'r') as f:
        textract_data = json.load(f)
    
    hocr_output = textract_to_hocr(textract_data)
    
    output_file = output_dir / f"{json_file.stem}.html"
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(hocr_output)
    
    print(f"Converted {json_file.name} -> {output_file.name}")
```

## Extracting Individual Pages from PDFs

```python
from textract_hocr import textract_to_hocr
import json

# Load multi-page Textract results
with open('multipage_textract.json', 'r') as f:
    textract_data = json.load(f)

# Extract each page separately
total_pages = textract_data['DocumentMetadata']['Pages']

for page_num in range(1, total_pages + 1):
    hocr_output = textract_to_hocr(
        textract_data,
        first_page=page_num,
        last_page=page_num,
        source_file='document.pdf'
    )
    
    with open(f'page_{page_num}.html', 'w', encoding='utf-8') as f:
        f.write(hocr_output)
    
    print(f"Extracted page {page_num}/{total_pages}")
```

## Converting Page Ranges

```python
from textract_hocr import textract_to_hocr
import json

with open('textract_output.json', 'r') as f:
    textract_data = json.load(f)

# Convert pages 5-10
hocr_output = textract_to_hocr(
    textract_data,
    first_page=5,
    last_page=10,
    source_file='document.pdf'
)

with open('pages_5_10.html', 'w', encoding='utf-8') as f:
    f.write(hocr_output)

# Convert from page 15 to end
hocr_output = textract_to_hocr(
    textract_data,
    first_page=15,
    source_file='document.pdf'
)

with open('pages_15_end.html', 'w', encoding='utf-8') as f:
    f.write(hocr_output)
```

## Forcing Custom Dimensions

```python
from textract_hocr import textract_to_hocr
import json

with open('textract_output.json', 'r') as f:
    textract_data = json.load(f)

# Force Letter size at 300 DPI (8.5" x 11" = 2550 x 3300 pixels)
hocr_output = textract_to_hocr(
    textract_data,
    dimensions={'width': 2550, 'height': 3300}
)

with open('output.html', 'w', encoding='utf-8') as f:
    f.write(hocr_output)
```

## Dimension Detection

```python
from textract_hocr import get_document_dimensions

# Check dimensions before conversion
image_dims = get_document_dimensions('scan.png')
print(f"Image: {image_dims['width']}x{image_dims['height']} pixels")

pdf_dims = get_document_dimensions('document.pdf', page_number=1)
print(f"PDF Page 1: {pdf_dims['width']}x{pdf_dims['height']} points")

# Force specific dimensions
custom_dims = get_document_dimensions(
    dimensions={'width': 2550, 'height': 3300}
)
print(f"Custom: {custom_dims['width']}x{custom_dims['height']}")

# Default dimensions (when no file provided)
default_dims = get_document_dimensions()
print(f"Textract default: {default_dims['width']}x{default_dims['height']}")
```

## Working with Tables

```python
from textract_hocr import textract_to_hocr
import json

# Load Textract results with table detection
with open('textract_with_tables.json', 'r') as f:
    textract_data = json.load(f)

# Convert to hOCR (tables are automatically included)
hocr_output = textract_to_hocr(textract_data, source_file='invoice.pdf')

with open('invoice.html', 'w', encoding='utf-8') as f:
    f.write(hocr_output)

# The output will contain:
# - <table class="ocr_table"> for each detected table
# - <tr> for each row
# - <td class="ocrx_table_cell"> for each cell
# - rowspan/colspan attributes for merged cells
# - Bounding boxes and confidence scores for all elements
```
