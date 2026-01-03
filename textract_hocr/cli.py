"""
Command-line interface for textract-hocr converter.

This module provides the CLI entry point for converting Textract JSON
output to hOCR format.
"""

import argparse
import json
import sys
from pathlib import Path
from typing import Optional

from .converter import textract_to_hocr


def main(args: Optional[list] = None) -> int:
    """
    Main entry point for the CLI.

    Args:
        args: Command-line arguments (defaults to sys.argv).

    Returns:
        Exit code (0 for success, 1 for error).
    """
    parser = argparse.ArgumentParser(
        description="Convert AWS Textract JSON output to hOCR HTML format",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Convert entire document
  textract-to-hocr input.json output.html
  
  # Convert with source image for accurate dimensions
  textract-to-hocr input.json output.html --source image.png
  
  # Convert specific page only
  textract-to-hocr input.json output.html --first-page 2 --last-page 2
  
  # Convert page range
  textract-to-hocr input.json output.html --first-page 2 --last-page 5
  
  # Convert from page 3 to end
  textract-to-hocr input.json output.html --first-page 3
  
  # Convert PDF pages with dimension extraction
  textract-to-hocr input.json output.html --source document.pdf --first-page 3 --last-page 5
  
  # Force specific dimensions (override auto-detection)
  textract-to-hocr input.json output.html --width 2550 --height 3300

Based on amazon-textract-hocr-output by AWS Samples:
https://github.com/aws-samples/amazon-textract-hocr-output
        """,
    )

    parser.add_argument(
        "input",
        type=str,
        help="Input Textract JSON file path",
    )

    parser.add_argument(
        "output",
        type=str,
        help="Output hOCR HTML file path",
    )

    parser.add_argument(
        "--source",
        type=str,
        default=None,
        help="Source image or PDF file to extract dimensions (optional). "
        "Supports common image formats (PNG, JPEG, TIFF) and PDF. "
        "Falls back to Textract's default 1000x1000 if not provided or unreadable.",
    )

    parser.add_argument(
        "--first-page",
        type=int,
        default=None,
        help="First page to convert (1-indexed). "
        "If not specified, starts from page 1.",
    )

    parser.add_argument(
        "--last-page",
        type=int,
        default=None,
        help="Last page to convert (1-indexed). "
        "If not specified, goes to the last page.",
    )

    parser.add_argument(
        "--width",
        type=int,
        default=None,
        help="Force page width in pixels (overrides auto-detection).",
    )

    parser.add_argument(
        "--height",
        type=int,
        default=None,
        help="Force page height in pixels (overrides auto-detection).",
    )

    parser.add_argument(
        "--version",
        action="version",
        version="%(prog)s 0.1.0",
    )

    parsed_args = parser.parse_args(args)

    # Validate input file exists
    input_path = Path(parsed_args.input)
    if not input_path.exists():
        print(f"Error: Input file '{parsed_args.input}' not found.", file=sys.stderr)
        return 1

    # Validate source file if provided
    if parsed_args.source:
        source_path = Path(parsed_args.source)
        if not source_path.exists():
            print(
                f"Warning: Source file '{parsed_args.source}' not found. "
                "Using Textract default dimensions (1000x1000).",
                file=sys.stderr,
            )
            parsed_args.source = None

    try:
        # Load Textract JSON
        print(f"Loading Textract results from {parsed_args.input}...")
        with open(input_path, "r", encoding="utf-8") as f:
            textract_json = json.load(f)

        # Prepare dimensions override if provided
        dimensions = None
        if parsed_args.width is not None and parsed_args.height is not None:
            dimensions = {"width": parsed_args.width, "height": parsed_args.height}
            print(f"Using forced dimensions: {parsed_args.width}x{parsed_args.height}")
        elif parsed_args.width is not None or parsed_args.height is not None:
            print(
                "Warning: Both --width and --height must be specified to force dimensions.",
                file=sys.stderr,
            )

        # Determine pages to convert
        total_pages = textract_json["DocumentMetadata"]["Pages"]
        first_page = parsed_args.first_page
        last_page = parsed_args.last_page

        if first_page is None and last_page is None:
            print(f"Converting {total_pages} page(s) to hOCR format...")
        elif first_page is not None and last_page is not None:
            if first_page == last_page:
                print(f"Converting page {first_page} to hOCR format...")
            else:
                print(f"Converting pages {first_page}-{last_page} to hOCR format...")
        elif first_page is not None:
            print(f"Converting pages {first_page}-{total_pages} to hOCR format...")
        else:  # last_page is not None
            print(f"Converting pages 1-{last_page} to hOCR format...")

        # Convert to hOCR
        hocr_output = textract_to_hocr(
            textract_json,
            source_file=parsed_args.source,
            first_page=first_page,
            last_page=last_page,
            dimensions=dimensions,
        )

        # Write output
        output_path = Path(parsed_args.output)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        with open(output_path, "w", encoding="utf-8") as f:
            f.write(hocr_output)

        print(f"✓ Successfully wrote hOCR output to {parsed_args.output}")
        return 0

    except ValueError as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1
    except KeyError as e:
        print(
            f"Error: Invalid Textract JSON format. Missing key: {e}",
            file=sys.stderr,
        )
        return 1
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
