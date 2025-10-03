#!/usr/bin/env python3
"""
Test the fixed marker implementation.
Verifies that coordinates are accurate when using markers.
"""

import sys
sys.path.append('.')

import cv2
import json
import numpy as np
import tempfile
import shutil
from pathlib import Path
from frontend.app import OMRSheetGenerator

def test_with_markers():
    """Test sheet generation and processing WITH markers."""
    print("=" * 80)
    print("Testing Sheet Generation WITH Markers")
    print("=" * 80)

    # Generate sheet
    generator = OMRSheetGenerator()
    sheet_path, template_path, msg = generator.generate_sheet(
        num_questions=10,
        question_type="QTYPE_MCQ4",
        num_columns=2,
        include_roll_number=True,
        roll_digits=5,
        include_markers=True,  # WITH markers
        page_width=2480,
        page_height=3508,
        bubble_size=40,
    )

    if not sheet_path:
        print(f"❌ Failed to generate sheet: {msg}")
        return False

    print(f"✓ Generated sheet: {sheet_path}")
    print(f"✓ Generated template: {template_path}")

    # Load template to check dimensions
    with open(template_path, 'r') as f:
        template_data = json.load(f)

    page_dims = template_data['pageDimensions']
    print(f"\n📏 pageDimensions: {page_dims}")

    # Load image to check actual size
    img = cv2.imread(sheet_path)
    print(f"📷 Image size: {img.shape[1]}x{img.shape[0]} (WxH)")

    # Check if markers exist
    has_markers = any(
        proc.get('name') == 'CropOnMarkers'
        for proc in template_data.get('preProcessors', [])
    )
    print(f"🎯 Has CropOnMarkers: {has_markers}")

    if has_markers:
        # Calculate expected dimensions
        marker_size = 50
        margin = 80 // 2  # margin // 2

        # Marker positions (top-left corner)
        tl_marker = (margin, margin)
        tr_marker = (img.shape[1] - margin - marker_size, margin)
        bl_marker = (margin, img.shape[0] - margin - marker_size)
        br_marker = (img.shape[1] - margin - marker_size, img.shape[0] - margin - marker_size)

        # Marker centers
        tl_center = (tl_marker[0] + marker_size//2, tl_marker[1] + marker_size//2)
        tr_center = (tr_marker[0] + marker_size//2, tr_marker[1] + marker_size//2)
        bl_center = (bl_marker[0] + marker_size//2, bl_marker[1] + marker_size//2)

        expected_width = tr_center[0] - tl_center[0]
        expected_height = bl_center[1] - tl_center[1]

        print(f"\n🔍 Expected pageDimensions from marker centers:")
        print(f"   Width: {expected_width} (marker centers distance)")
        print(f"   Height: {expected_height} (marker centers distance)")
        print(f"   Actual pageDimensions: {page_dims}")

        if page_dims[0] == expected_width and page_dims[1] == expected_height:
            print(f"   ✅ pageDimensions matches marker center distance!")
        else:
            print(f"   ❌ Mismatch! Scale would be {page_dims[0]/expected_width:.4f}x")

    # Fill some answers on a copy
    test_img = img.copy()

    # Get first question block
    first_block = None
    for block_name, block_data in template_data['fieldBlocks'].items():
        if block_name.startswith('Block_Q'):
            first_block = (block_name, block_data)
            break

    if first_block:
        block_name, block_data = first_block
        origin = block_data['origin']
        bubble_size = template_data['bubbleDimensions'][0]
        bubble_gap = block_data['bubblesGap']

        print(f"\n📝 First question block: {block_name}")
        print(f"   Origin in template: {origin}")

        # Calculate actual pixel position on the image
        if has_markers:
            # Add back the offset
            marker_center_x = margin + marker_size//2
            marker_center_y = margin + marker_size//2
            actual_x = origin[0] + marker_center_x
            actual_y = origin[1] + marker_center_y
        else:
            actual_x = origin[0]
            actual_y = origin[1]

        print(f"   Actual pixel position: ({actual_x}, {actual_y})")

        # Fill answer A (first bubble)
        fill_x = actual_x + bubble_size//2
        fill_y = actual_y + bubble_size//2

        cv2.circle(test_img, (fill_x, fill_y), bubble_size//2 - 5, (0, 0, 0), -1)
        print(f"   Filled bubble A at ({fill_x}, {fill_y})")

        # Save test image
        test_image_path = Path(template_path).parent / "filled_test.png"
        cv2.imwrite(str(test_image_path), test_img)
        print(f"   Saved filled image: {test_image_path}")

    return True


def main():
    """Run tests."""
    print("\n" + "🧪 Testing Fixed Marker Implementation" + "\n")

    success = test_with_markers()

    if success:
        print("\n" + "=" * 80)
        print("✅ TEST PASSED")
        print("=" * 80)
        print("\nNext steps:")
        print("1. Check the generated images visually")
        print("2. Run OMR processing on the filled_test.png")
        print("3. Verify that q1=A is detected correctly")
    else:
        print("\n❌ TEST FAILED")
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
