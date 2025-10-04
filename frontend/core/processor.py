import json
import os
import sys
import tempfile
import zipfile
import shutil
from pathlib import Path
from typing import List, Optional, Tuple, Dict, Any

import cv2
import numpy as np
import pandas as pd

# Add parent directory to path to import src modules
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.entry import entry_point
from src.logger import logger
from frontend.config.constants import config
from frontend.utils.marker_utils import generate_concentric_circle_marker


class OMRProcessorGradio:
    """Wrapper class for OMR processing with Gradio interface."""

    def __init__(self):
        self.temp_dir = None
        self.output_dir = None

    def setup_temp_directories(self):
        """Create temporary directories for processing."""
        self.temp_dir = tempfile.mkdtemp(prefix="omr_input_")
        self.output_dir = tempfile.mkdtemp(prefix="omr_output_")
        return self.temp_dir, self.output_dir

    def cleanup_temp_directories(self):
        """Clean up temporary directories."""
        if self.temp_dir and os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)
        if self.output_dir and os.path.exists(self.output_dir):
            shutil.rmtree(self.output_dir)

    def process_omr_sheets(
        self,
        image_files: List[str],
        template_file: str,
        config_file: Optional[str] = None,
        evaluation_file: Optional[str] = None,
        marker_file: Optional[str] = None,
        auto_align: bool = False,
        set_layout: bool = False,
    ) -> Tuple[str, Optional[str], List[str], str]:
        """
        Process OMR sheets with uploaded files.

        Args:
            image_files: List of paths to uploaded image files
            template_file: Path to template.json file
            config_file: Optional path to config.json file
            evaluation_file: Optional path to evaluation.json file
            marker_file: Optional path to custom marker image file
            auto_align: Enable auto-alignment
            set_layout: Enable layout visualization mode

        Returns:
            Tuple of (status_message, results_csv_path, marked_images, log_output)
        """
        try:
            # Setup temporary directories
            input_dir, output_dir = self.setup_temp_directories()

            # Validate inputs
            if not image_files or len(image_files) == 0:
                return "Error: No image files uploaded", None, [], "Please upload at least one OMR image"

            if not template_file:
                return "Error: No template file uploaded", None, [], "Please upload a template.json file"

            # Copy uploaded files to temp directory
            for img_file in image_files:
                if img_file:  # Check if file exists
                    dest = Path(input_dir) / Path(img_file).name
                    shutil.copy2(img_file, dest)

            # Copy template file
            template_dest = Path(input_dir) / "template.json"
            shutil.copy2(template_file, template_dest)

            # Check if template requires marker and handle marker file
            with open(template_dest, 'r') as f:
                template_data = json.load(f)

            # Check for CropOnMarkers preprocessor
            for preprocessor in template_data.get("preProcessors", []):
                if preprocessor.get("name") == "CropOnMarkers":
                    marker_path = preprocessor.get("options", {}).get("relativePath", "")
                    if marker_path:
                        marker_dest_file = Path(input_dir) / marker_path

                        # Use custom marker if provided by user
                        if marker_file and os.path.exists(marker_file):
                            logger.info(f"Using custom marker file: {marker_file}")
                            shutil.copy2(marker_file, marker_dest_file)
                            logger.info(f"✅ Copied custom marker to: {marker_dest_file}")
                        # Otherwise generate marker if it doesn't exist
                        elif not marker_dest_file.exists():
                            logger.info(f"Auto-generating missing marker: {marker_path}")
                            # Get page dimensions from template to calculate marker size (1/10 of page width)
                            page_dims = template_data.get("pageDimensions", [config.GENERATOR_PAGE_WIDTH, config.GENERATOR_PAGE_HEIGHT])
                            page_width = page_dims[0]
                            marker_size = int(page_width * config.MARKER_SIZE_RATIO)

                            # Generate concentric circles marker using utility function
                            marker_img = generate_concentric_circle_marker(marker_size, config)

                            cv2.imwrite(str(marker_dest_file), marker_img)
                            logger.info(f"✅ Generated marker at: {marker_dest_file} (size: {marker_size}x{marker_size})")

            # Copy optional files if provided
            if config_file:
                config_dest = Path(input_dir) / "config.json"
                shutil.copy2(config_file, config_dest)

            if evaluation_file:
                eval_dest = Path(input_dir) / "evaluation.json"
                shutil.copy2(evaluation_file, eval_dest)

            # Prepare arguments
            args = {
                "input_paths": [input_dir],
                "output_dir": output_dir,
                "autoAlign": auto_align,
                "setLayout": set_layout,
                "debug": False,  # Disable GUI windows in web environment
            }

            # Process using existing entry point
            logger.info(f"Processing OMR sheets from {input_dir}")
            logger.info(f"Output will be saved to {output_dir}")

            # Call the main processing function
            entry_point(Path(input_dir), args)

            # Collect results
            results_csv = None
            marked_images = []
            status_msg = "Processing completed successfully!"

            # Find results CSV in Results directory
            results_dir = Path(output_dir) / "Results"
            if results_dir.exists():
                csv_files = list(results_dir.glob("*.csv"))
                if csv_files:
                    results_csv = str(csv_files[0])

            # Find marked images
            marked_dir = Path(output_dir) / "CheckedOMRs"
            if marked_dir.exists():
                image_exts = ["*.png", "*.jpg", "*.jpeg"]
                for ext in image_exts:
                    marked_images.extend([str(p) for p in marked_dir.glob(ext)])

            # Generate summary
            if results_csv:
                df = pd.read_csv(results_csv)
                status_msg = f"✅ Successfully processed {len(df)} OMR sheet(s)\n"
                status_msg += f"📁 Results saved to: {results_csv}\n"
                status_msg += f"🖼️  Found {len(marked_images)} marked image(s)"
            else:
                status_msg = "⚠️ Processing completed but no results found. Check logs."

            log_output = f"Input directory: {input_dir}\nOutput directory: {output_dir}\n"
            log_output += f"Processed {len(image_files)} file(s)\n"

            return status_msg, results_csv, marked_images, log_output

        except Exception as e:
            error_msg = f"❌ Error during processing: {str(e)}"
            logger.error(error_msg)
            import traceback

            traceback.print_exc()
            return error_msg, None, [], str(traceback.format_exc())
