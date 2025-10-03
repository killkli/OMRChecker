"""
Test with filled answers to verify template coordinates
"""
import sys
from pathlib import Path
import cv2
import json
import numpy as np

sys.path.insert(0, str(Path(__file__).parent))

from frontend.app import OMRSheetGenerator, OMRProcessorGradio
from src.constants import FIELD_TYPES

# Step 1: Generate blank sheet
generator = OMRSheetGenerator()
sheet_path, template_path, msg = generator.generate_sheet(
    num_questions=10,
    question_type="QTYPE_MCQ4",
    num_columns=2,
    include_roll_number=False,
    roll_digits=0,
    include_markers=False,
    page_width=1500,
    page_height=2000,
    bubble_size=40,
)

print("=" * 60)
print("Step 1: Generated blank sheet")
print("=" * 60)
print(msg)

# Step 2: Fill in some answers programmatically
print("\n" + "=" * 60)
print("Step 2: Filling in answers...")
print("=" * 60)

img = cv2.imread(sheet_path)
with open(template_path, 'r') as f:
    template = json.load(f)

# Fill specific answers: q1=A, q2=B, q3=C, q4=D
answers = {'q1': 'A', 'q2': 'B', 'q3': 'C', 'q4': 'D'}

for block_name, block in template['fieldBlocks'].items():
    if block_name.startswith('Block_Q'):
        field_label = block['fieldLabels'][0]

        if field_label in answers:
            answer = answers[field_label]
            origin = block['origin']
            bubbles_gap = block['bubblesGap']
            bubble_dims = template['bubbleDimensions']

            # Get bubble values
            bubble_values = FIELD_TYPES[block['fieldType']]['bubbleValues']
            direction = FIELD_TYPES[block['fieldType']]['direction']

            # Find the answer index
            answer_idx = bubble_values.index(answer)

            # Calculate bubble position
            if direction == 'horizontal':
                x = origin[0] + answer_idx * bubbles_gap
                y = origin[1]
            else:
                x = origin[0]
                y = origin[1] + answer_idx * bubbles_gap

            # Fill the bubble (black filled circle)
            cv2.circle(
                img,
                (int(x + bubble_dims[0]//2), int(y + bubble_dims[1]//2)),
                int(bubble_dims[0]//2 - 2),
                (0, 0, 0),
                -1  # Filled
            )
            print(f"Filled {field_label} = {answer}")

# Save filled sheet
filled_path = '/tmp/filled_omr.png'
cv2.imwrite(filled_path, img)
print(f"\nFilled sheet saved to: {filled_path}")

# Step 3: Process the filled sheet
print("\n" + "=" * 60)
print("Step 3: Processing filled sheet...")
print("=" * 60)

processor = OMRProcessorGradio()
status, results_csv, marked_images, log = processor.process_omr_sheets(
    image_files=[filled_path],
    template_file=template_path,
    config_file=None,
    evaluation_file=None,
    auto_align=False,
    set_layout=False,
)

print("\nProcessing Status:")
print(status)

# Check if answers match
if "Error" not in status and "error" not in status:
    print("\n" + "=" * 60)
    print("VERIFICATION")
    print("=" * 60)
    print(f"Expected answers: {answers}")
    print(f"\nCheck the processing log above for 'Read Response' to verify!")
    print("\n✅ If detected answers match expected, coordinates are PERFECT!")
else:
    print("\n❌ Processing failed")
    print(log)
