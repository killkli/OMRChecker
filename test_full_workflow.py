"""
Test complete workflow: generate blank sheet -> process it
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from frontend.app import OMRSheetGenerator, OMRProcessorGradio

def test_full_workflow():
    """Test generating and processing a blank sheet."""

    # Step 1: Generate blank sheet with markers
    print("=" * 60)
    print("Step 1: Generating blank OMR sheet...")
    print("=" * 60)

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

    print(msg)
    print(f"Sheet: {sheet_path}")
    print(f"Template: {template_path}")

    # Step 2: Process the blank sheet
    print("\n" + "=" * 60)
    print("Step 2: Processing the blank sheet...")
    print("=" * 60)

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

    if "Error" in status or "error" in status:
        print("\n❌ Test FAILED")
        print("\nLog:")
        print(log)
        return False
    else:
        print("\n✅ Test PASSED - Full workflow completed!")
        return True

if __name__ == "__main__":
    success = test_full_workflow()
    sys.exit(0 if success else 1)
