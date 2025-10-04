"""
Gradio Interface Module

This module contains the main Gradio interface creation function.
"""

from typing import TYPE_CHECKING

import gradio as gr

from frontend.ui.tabs import processing_tab, template_tab, generator_tab, batch_tab

if TYPE_CHECKING:
    from frontend.core.processor import OMRProcessorGradio
    from frontend.core.template_builder import TemplateBuilder
    from frontend.core.sheet_generator import OMRSheetGenerator
    from batch_generate_sheets import BatchOMRGenerator


def create_gradio_interface(
    processor: "OMRProcessorGradio",
    template_builder: "TemplateBuilder",
    sheet_generator: "OMRSheetGenerator",
    batch_generator: "BatchOMRGenerator",
) -> gr.Blocks:
    """
    Create the main Gradio interface.

    Args:
        processor: OMRProcessorGradio instance for handling sheet processing
        template_builder: TemplateBuilder instance for handling template creation
        sheet_generator: OMRSheetGenerator instance for handling sheet generation
        batch_generator: BatchOMRGenerator instance for handling batch generation

    Returns:
        gr.Blocks: Configured Gradio interface
    """
    with gr.Blocks(
        title="OMRChecker - OMR Sheet Processor",
        theme=gr.themes.Soft(),
    ) as demo:
        gr.Markdown(
            """
        # 📝 OMRChecker - Optical Mark Recognition

        Process OMR sheets and create templates interactively.
        """
        )

        with gr.Tabs():
            # Create all tabs by calling their respective creation functions
            processing_tab.create_tab(processor)
            template_tab.create_tab(template_builder)
            generator_tab.create_tab(sheet_generator)
            batch_tab.create_tab(batch_generator)

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
