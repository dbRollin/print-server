#!/usr/bin/env python3
"""
Generate test label images for print server testing.

Creates valid 720px wide monochrome PNGs that pass validation.

Usage:
    python scripts/generate_test_label.py                    # Default test label
    python scripts/generate_test_label.py --text "Hello"     # Custom text
    python scripts/generate_test_label.py --output my.png    # Custom filename
    python scripts/generate_test_label.py --height 200       # Custom height
"""

import argparse
from pathlib import Path

try:
    from PIL import Image, ImageDraw, ImageFont
except ImportError:
    print("Pillow not installed. Run: pip install pillow")
    exit(1)


def create_test_label(
    text: str = "TEST LABEL",
    width: int = 720,
    height: int = 150,
    output: str = "test_label.png"
) -> Path:
    """Create a valid test label image."""

    # Create white image
    img = Image.new("1", (width, height), 1)  # 1-bit, white background
    draw = ImageDraw.Draw(img)

    # Try to use a nice font, fall back to default
    font_size = 48
    try:
        font = ImageFont.truetype("arial.ttf", font_size)
    except OSError:
        try:
            font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", font_size)
        except OSError:
            font = ImageFont.load_default()

    # Center the text
    bbox = draw.textbbox((0, 0), text, font=font)
    text_width = bbox[2] - bbox[0]
    text_height = bbox[3] - bbox[1]

    x = (width - text_width) // 2
    y = (height - text_height) // 2

    # Draw black text
    draw.text((x, y), text, fill=0, font=font)

    # Add border
    draw.rectangle([0, 0, width - 1, height - 1], outline=0, width=2)

    # Add some test elements
    draw.line([(10, height - 20), (width - 10, height - 20)], fill=0, width=1)

    # Save
    output_path = Path(output)
    img.save(output_path, "PNG")

    print(f"Created: {output_path}")
    print(f"  Size: {width}x{height}")
    print(f"  Mode: 1-bit monochrome")
    print(f"  Text: {text}")

    return output_path


def create_barcode_label(
    code: str = "1234567890",
    width: int = 720,
    output: str = "test_barcode.png"
) -> Path:
    """Create a simple barcode-style label (not a real barcode, just for testing)."""

    height = 100
    img = Image.new("1", (width, height), 1)
    draw = ImageDraw.Draw(img)

    # Fake barcode pattern (just alternating bars for visual testing)
    bar_x = 50
    for i, char in enumerate(code):
        bar_width = (ord(char) % 4) + 2
        if i % 2 == 0:
            draw.rectangle([bar_x, 20, bar_x + bar_width, 70], fill=0)
        bar_x += bar_width + 2

    # Code text below
    try:
        font = ImageFont.truetype("arial.ttf", 16)
    except OSError:
        font = ImageFont.load_default()

    draw.text((50, 75), code, fill=0, font=font)

    output_path = Path(output)
    img.save(output_path, "PNG")

    print(f"Created barcode label: {output_path}")
    return output_path


def main():
    parser = argparse.ArgumentParser(description="Generate test label images")
    parser.add_argument("--text", default="TEST LABEL", help="Label text")
    parser.add_argument("--width", type=int, default=720, help="Image width (default: 720)")
    parser.add_argument("--height", type=int, default=150, help="Image height")
    parser.add_argument("--output", "-o", default="test_label.png", help="Output filename")
    parser.add_argument("--barcode", action="store_true", help="Generate barcode-style label")
    parser.add_argument("--code", default="1234567890", help="Barcode value")

    args = parser.parse_args()

    if args.barcode:
        create_barcode_label(args.code, args.width, args.output)
    else:
        create_test_label(args.text, args.width, args.height, args.output)


if __name__ == "__main__":
    main()
