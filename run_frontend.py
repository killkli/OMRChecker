#!/usr/bin/env python3
"""
OMRChecker Frontend Launcher

Simple launcher script for the Gradio-based web interface.
"""

import sys
from pathlib import Path

# Add project root to path to allow absolute imports
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from batch_generate_sheets import BatchOMRGenerator
from frontend.config.constants import config
from frontend.core.processor import OMRProcessorGradio
from frontend.core.sheet_generator import OMRSheetGenerator
from frontend.core.template_builder import TemplateBuilder
from frontend.ui.interface import create_gradio_interface

if __name__ == "__main__":
    print("=" * 60)
    print("OMRChecker - Gradio Frontend")
    print("=" * 60)
    print("\nStarting web interface...")
    print("Once started, open your browser to the URL shown below\n")

    # Initialize business logic instances
    processor = OMRProcessorGradio()
    template_builder = TemplateBuilder()
    sheet_generator = OMRSheetGenerator()
    batch_generator = BatchOMRGenerator()

    # Create and launch the Gradio interface
    demo = create_gradio_interface(
        processor=processor,
        template_builder=template_builder,
        sheet_generator=sheet_generator,
        batch_generator=batch_generator,
    )

    demo.launch(
        server_name=config.GRADIO_SERVER_NAME,
        server_port=config.GRADIO_SERVER_PORT,
        share=config.GRADIO_SHARE,
        show_error=config.GRADIO_SHOW_ERROR,
    )
