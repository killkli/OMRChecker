"""
OMRChecker Gradio Frontend

A modern web-based interface for OMR sheet processing using Gradio.

Author: Generated with Claude Code
"""

import os
import sys
import tempfile
import zipfile
from pathlib import Path
from typing import List, Optional, Tuple

import cv2
import gradio as gr
import pandas as pd

# Add parent directory to path to import src modules
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.defaults import CONFIG_DEFAULTS
from src.entry import process_dir
from src.logger import logger
from src.template import Template
from src.utils.parsing import open_config_with_defaults


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
        import shutil

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
                    import shutil

                    dest = Path(input_dir) / Path(img_file).name
                    shutil.copy2(img_file, dest)

            # Copy template file
            import shutil

            template_dest = Path(input_dir) / "template.json"
            shutil.copy2(template_file, template_dest)

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
                "debug": True,
            }

            # Process using existing entry point
            logger.info(f"Processing OMR sheets from {input_dir}")
            logger.info(f"Output will be saved to {output_dir}")

            # Call the main processing function
            from src.entry import entry_point

            entry_point(Path(input_dir), args)

            # Collect results
            results_csv = None
            marked_images = []
            status_msg = "Processing completed successfully!"

            # Find results CSV
            results_dir = Path(output_dir) / "CheckedOMRs"
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


# Initialize processor
processor = OMRProcessorGradio()


def create_gradio_interface():
    """Create and configure the Gradio interface."""

    with gr.Blocks(
        title="OMRChecker - OMR Sheet Processor",
        theme=gr.themes.Soft(),
    ) as demo:
        gr.Markdown(
            """
        # 📝 OMRChecker - Optical Mark Recognition

        Upload your OMR sheets and template to automatically process and evaluate responses.

        ### Quick Start:
        1. Upload OMR image(s) (PNG/JPG)
        2. Upload template.json (required)
        3. Optional: Upload config.json and evaluation.json
        4. Click "Process OMR Sheets"
        """
        )

        with gr.Row():
            with gr.Column(scale=1):
                gr.Markdown("### 📤 Upload Files")

                image_input = gr.File(
                    label="OMR Images",
                    file_count="multiple",
                    file_types=["image"],
                    type="filepath",
                )

                template_input = gr.File(
                    label="Template File (template.json)",
                    file_count="single",
                    file_types=[".json"],
                    type="filepath",
                )

                with gr.Accordion("Optional Configuration Files", open=False):
                    config_input = gr.File(
                        label="Config File (config.json)",
                        file_count="single",
                        file_types=[".json"],
                        type="filepath",
                    )

                    evaluation_input = gr.File(
                        label="Evaluation File (evaluation.json)",
                        file_count="single",
                        file_types=[".json"],
                        type="filepath",
                    )

                with gr.Accordion("Processing Options", open=False):
                    auto_align_check = gr.Checkbox(
                        label="Enable Auto-Alignment",
                        value=False,
                        info="Experimental: Automatically align slightly misaligned scans",
                    )

                    set_layout_check = gr.Checkbox(
                        label="Set Layout Mode",
                        value=False,
                        info="Visualize template layout instead of processing",
                    )

                process_btn = gr.Button(
                    "🚀 Process OMR Sheets", variant="primary", size="lg"
                )

            with gr.Column(scale=2):
                gr.Markdown("### 📊 Results")

                status_output = gr.Textbox(
                    label="Status",
                    lines=4,
                    interactive=False,
                )

                results_csv_output = gr.File(
                    label="Results CSV",
                    interactive=False,
                )

                marked_images_gallery = gr.Gallery(
                    label="Marked OMR Images",
                    show_label=True,
                    columns=2,
                    height="auto",
                )

                with gr.Accordion("Processing Log", open=False):
                    log_output = gr.Textbox(
                        label="Detailed Log",
                        lines=10,
                        interactive=False,
                    )

        # Connect the processing function
        process_btn.click(
            fn=processor.process_omr_sheets,
            inputs=[
                image_input,
                template_input,
                config_input,
                evaluation_input,
                auto_align_check,
                set_layout_check,
            ],
            outputs=[
                status_output,
                results_csv_output,
                marked_images_gallery,
                log_output,
            ],
        )

        gr.Markdown(
            """
        ---
        ### 📖 Documentation

        - **Template**: Define the layout and structure of your OMR sheet
        - **Config**: Tune image processing parameters
        - **Evaluation**: Define answer keys and scoring rules

        For more information, visit [OMRChecker GitHub](https://github.com/Udayraj123/OMRChecker)
        """
        )

    return demo


if __name__ == "__main__":
    demo = create_gradio_interface()
    demo.launch(
        server_name="0.0.0.0",
        server_port=7860,
        share=False,
        show_error=True,
    )
