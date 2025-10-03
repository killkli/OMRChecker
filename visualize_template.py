"""
Visualize template coordinates on generated image
"""
import sys
import json
from pathlib import Path
import cv2

sys.path.insert(0, str(Path(__file__).parent))

from frontend.app import OMRSheetGenerator
from src.constants import FIELD_TYPES

# Generate a simple sheet
generator = OMRSheetGenerator()
sheet_path, template_path, msg = generator.generate_sheet(
    num_questions=4,
    question_type="QTYPE_MCQ4",
    num_columns=2,
    include_roll_number=False,  # Simplify - no roll number
    roll_digits=0,
    include_markers=False,
    page_width=1000,
    page_height=1000,
    bubble_size=40,
)

print(f"Generated: {sheet_path}")
print(f"Template: {template_path}")

# Load image and template
img = cv2.imread(sheet_path)
with open(template_path, 'r') as f:
    template = json.load(f)

# Draw template coordinates in different color
img_debug = img.copy()

bubble_dims = template['bubbleDimensions']

for block_name, block in template['fieldBlocks'].items():
    origin = block['origin']
    bubbles_gap = block['bubblesGap']
    labels_gap = block.get('labelsGap', bubbles_gap)

    # Get bubble values
    if 'fieldType' in block and block['fieldType'] in FIELD_TYPES:
        bubble_values = FIELD_TYPES[block['fieldType']]['bubbleValues']
        direction = FIELD_TYPES[block['fieldType']]['direction']
    else:
        bubble_values = block.get('bubbleValues', [])
        direction = block.get('direction', 'horizontal')

    field_labels = block['fieldLabels']

    print(f"\n{block_name}:")
    print(f"  Origin: {origin}")
    print(f"  Direction: {direction}")
    print(f"  Bubble values: {bubble_values}")
    print(f"  Field labels: {field_labels}")

    # Draw template bubbles in BLUE
    for label_idx, label in enumerate(field_labels):
        for bubble_idx, value in enumerate(bubble_values):
            if direction == 'horizontal':
                x = origin[0] + bubble_idx * bubbles_gap
                y = origin[1] + label_idx * labels_gap
            else:
                x = origin[0] + label_idx * labels_gap
                y = origin[1] + bubble_idx * bubbles_gap

            # Draw rectangle (template position)
            cv2.rectangle(
                img_debug,
                (int(x), int(y)),
                (int(x + bubble_dims[0]), int(y + bubble_dims[1])),
                (255, 0, 0),  # BLUE for template
                2,
            )

# Save debug image
debug_path = '/tmp/template_debug.png'
cv2.imwrite(debug_path, img_debug)
print(f"\nDebug image saved to: {debug_path}")
print("Green circles = Generated bubbles")
print("Blue rectangles = Template coordinates")
print("\nIf they don't overlap, coordinates are wrong!")
