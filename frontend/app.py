"""
OMRChecker Gradio Frontend - Entry Point

A modern web-based interface for OMR sheet processing using Gradio.

Author: Generated with Claude Code
"""

import sys
from pathlib import Path

# Add parent directory to path to import src modules
sys.path.insert(0, str(Path(__file__).parent.parent))

from batch_generate_sheets import BatchOMRGenerator
from frontend.config.constants import config
from frontend.core.processor import OMRProcessorGradio
from frontend.core.template_builder import TemplateBuilder
from frontend.core.sheet_generator import OMRSheetGenerator
from frontend.ui.interface import create_gradio_interface


# Initialize business logic instances
processor = OMRProcessorGradio()
template_builder = TemplateBuilder()
sheet_generator = OMRSheetGenerator()
batch_generator = BatchOMRGenerator()


if __name__ == "__main__":
    # Create interface
    demo = create_gradio_interface(
        processor=processor,
        template_builder=template_builder,
        sheet_generator=sheet_generator,
        batch_generator=batch_generator,
    )

    # Launch
    demo.launch(
        server_name=config.GRADIO_SERVER_NAME,
        server_port=config.GRADIO_SERVER_PORT,
        share=config.GRADIO_SHARE,
        show_error=config.GRADIO_SHOW_ERROR,
    )
