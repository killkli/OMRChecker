"""
Debug template generation - check coordinates
"""
import sys
import json
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from frontend.app import OMRSheetGenerator
import cv2

# Generate a test sheet
generator = OMRSheetGenerator()
sheet_path, template_path, msg = generator.generate_sheet(
    num_questions=10,
    question_type="QTYPE_MCQ4",
    num_columns=2,
    include_roll_number=True,
    roll_digits=5,
    include_markers=True,
    page_width=2100,
    page_height=2970,
    bubble_size=40,
)

print("Generated files:")
print(f"Sheet: {sheet_path}")
print(f"Template: {template_path}")

# Load and display template
with open(template_path, 'r') as f:
    template = json.load(f)

print("\n" + "=" * 80)
print("TEMPLATE STRUCTURE:")
print("=" * 80)
print(json.dumps(template, indent=2))

# Load image and check dimensions
img = cv2.imread(sheet_path)
print("\n" + "=" * 80)
print("IMAGE INFO:")
print("=" * 80)
print(f"Image shape: {img.shape}")
print(f"Template pageDimensions: {template['pageDimensions']}")

# Check if dimensions match
if img.shape[1] != template['pageDimensions'][0] or img.shape[0] != template['pageDimensions'][1]:
    print("\n⚠️  WARNING: Image dimensions don't match template!")
    print(f"Image: width={img.shape[1]}, height={img.shape[0]}")
    print(f"Template: width={template['pageDimensions'][0]}, height={template['pageDimensions'][1]}")

# Analyze first few field blocks
print("\n" + "=" * 80)
print("FIELD BLOCKS ANALYSIS:")
print("=" * 80)
for i, (name, block) in enumerate(list(template['fieldBlocks'].items())[:3]):
    print(f"\n{name}:")
    print(f"  Origin: {block['origin']}")
    print(f"  Bubbles Gap: {block['bubblesGap']}")
    print(f"  Labels Gap: {block['labelsGap']}")
    if 'fieldType' in block:
        print(f"  Field Type: {block['fieldType']}")
    if 'bubbleValues' in block:
        print(f"  Bubble Values: {block['bubbleValues']}")
