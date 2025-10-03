"""
Test markers with fixed scale (no resizing)
"""
import sys
from pathlib import Path
import cv2

sys.path.insert(0, str(Path(__file__).parent))

from frontend.app import OMRSheetGenerator, OMRProcessorGradio
from src.constants import FIELD_TYPES

# Generate with markers but fixed scale
generator = OMRSheetGenerator()
sheet_path, template_path, msg = generator.generate_sheet(
    num_questions=10,
    question_type="QTYPE_MCQ4",
    num_columns=2,
    include_roll_number=False,
    roll_digits=0,
    include_markers=True,  # WITH MARKERS
    page_width=1500,
    page_height=2000,
    bubble_size=40,
)

print("=" * 60)
print("Generated with MARKERS (fixed scale)")
print("=" * 60)
print(msg)

# Fill some answers
import json
img = cv2.imread(sheet_path)
with open(template_path, 'r') as f:
    template = json.load(f)

answers = {'q1': 'A', 'q2': 'B', 'q3': 'C'}

for block_name, block in template['fieldBlocks'].items():
    if block_name.startswith('Block_Q'):
        field_label = block['fieldLabels'][0]
        if field_label in answers:
            answer = answers[field_label]
            origin = block['origin']
            bubbles_gap = block['bubblesGap']
            bubble_dims = template['bubbleDimensions']
            bubble_values = FIELD_TYPES[block['fieldType']]['bubbleValues']
            direction = FIELD_TYPES[block['fieldType']]['direction']
            answer_idx = bubble_values.index(answer)

            if direction == 'horizontal':
                x = origin[0] + answer_idx * bubbles_gap
                y = origin[1]
            else:
                x = origin[0]
                y = origin[1] + answer_idx * bubbles_gap

            cv2.circle(img, (int(x + bubble_dims[0]//2), int(y + bubble_dims[1]//2)),
                      int(bubble_dims[0]//2 - 2), (0, 0, 0), -1)

filled_path = '/tmp/filled_with_markers.png'
cv2.imwrite(filled_path, img)
print(f"\nFilled answers: {answers}")

# Process
print("\n" + "=" * 60)
print("Processing with markers...")
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

print("\nStatus:", status)

# Extract detected answers from log
import re
if 'Read Response' in log:
    match = re.search(r"Read Response.*?(\{[^}]+\})", log, re.DOTALL)
    if match:
        print("\n" + "=" * 60)
        print("VERIFICATION")
        print("=" * 60)
        print(f"Expected: {answers}")
        print(f"Detected: {match.group(1)}")

        if all(f"'{k}': '{v}'" in match.group(1) for k, v in answers.items()):
            print("\n✅ SUCCESS! Markers with fixed scale work perfectly!")
        else:
            print("\n⚠️  Answers don't match - need more adjustment")
