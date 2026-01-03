"""
textract-hocr: Convert AWS Textract JSON output to hOCR format.

Based on amazon-textract-hocr-output by AWS Samples:
https://github.com/aws-samples/amazon-textract-hocr-output
"""

__version__ = "0.1.0"
__author__ = "textract-hocr contributors"
__license__ = "MIT"

from .converter import (
    textract_to_hocr,
    get_document_dimensions,
)

__all__ = [
    "textract_to_hocr",
    "get_document_dimensions",
]
