"""
Test without markers to verify coordinates
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from frontend.app import OMRSheetGenerator, OMRProcessorGradio

# Generate WITHOUT markers
generator = OMRSheetGenerator()
sheet_path, template_path, msg = generator.generate_sheet(
    num_questions=10,
    question_type="QTYPE_MCQ4",
    num_columns=2,
    include_roll_number=True,
    roll_digits=5,
    include_markers=False,  # NO MARKERS
    page_width=2100,
    page_height=2970,
    bubble_size=40,
)

print("Generated WITHOUT markers:")
print(msg)
print(f"Sheet: {sheet_path}")
print(f"Template: {template_path}")

# Process
processor = OMRProcessorGradio()
status, results_csv, marked_images, log = processor.process_omr_sheets(
    image_files=[sheet_path],
    template_file=template_path,
    config_file=None,
    evaluation_file=None,
    auto_align=False,
    set_layout=False,
)

print("\nProcessing Status:")
print(status)

if "Error" not in status and "error" not in status:
    print("\n✅ Test PASSED - Coordinates are correct without markers!")
else:
    print("\n❌ Test FAILED")
    print("Log:", log)
