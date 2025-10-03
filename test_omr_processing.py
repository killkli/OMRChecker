"""
Test OMR processing without GUI
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from frontend.app import OMRProcessorGradio

def test_processing():
    """Test OMR processing in headless mode."""
    processor = OMRProcessorGradio()

    # Use sample2 for testing
    sample_dir = Path(__file__).parent / "samples" / "sample2"
    template_file = sample_dir / "template.json"

    # Find sample images (including subdirectories)
    image_files = list(sample_dir.glob("**/*.jpg")) + list(sample_dir.glob("**/*.png"))

    if not image_files:
        print("❌ No sample images found in samples/sample2")
        return False

    if not template_file.exists():
        print("❌ Template file not found in samples/sample2")
        return False

    print(f"Testing with {len(image_files)} image(s)...")
    print(f"Template: {template_file}")

    # Process
    status, results_csv, marked_images, log = processor.process_omr_sheets(
        image_files=[str(f) for f in image_files[:1]],  # Test with just first image
        template_file=str(template_file),
        config_file=None,
        evaluation_file=None,
        auto_align=False,
        set_layout=False,
    )

    print("=" * 60)
    print("Status:")
    print(status)
    print("=" * 60)

    if "Error" in status or "error" in status:
        print("\n❌ Test FAILED")
        print("Log:")
        print(log)
        return False
    else:
        print("\n✅ Test PASSED - Processing completed without GUI errors!")
        return True

if __name__ == "__main__":
    success = test_processing()
    sys.exit(0 if success else 1)
