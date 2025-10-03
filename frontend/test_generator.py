"""
Test script for OMR sheet generator
"""
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from frontend.app import OMRSheetGenerator

def test_generator():
    """Test the OMR sheet generator."""
    generator = OMRSheetGenerator()

    # Test with simple parameters - 20 questions in 4 columns
    sheet_path, template_path, msg = generator.generate_sheet(
        num_questions=20,
        question_type="QTYPE_MCQ4",
        num_columns=4,
        include_roll_number=True,
        roll_digits=5,
        include_markers=True,
        page_width=2100,
        page_height=2970,
        bubble_size=40,
    )

    print("=" * 60)
    print("Test Results:")
    print("=" * 60)
    print(f"\nSheet Image: {sheet_path}")
    print(f"Template JSON: {template_path}")
    print(f"\nStatus Message:\n{msg}")
    print("=" * 60)

    if sheet_path and template_path:
        print("\n✅ Test PASSED - Files generated successfully!")
        return True
    else:
        print("\n❌ Test FAILED - File generation failed!")
        return False

if __name__ == "__main__":
    success = test_generator()
    sys.exit(0 if success else 1)
