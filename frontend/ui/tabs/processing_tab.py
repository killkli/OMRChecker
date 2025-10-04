"""
OMR Sheet Processing Tab

This module contains the UI components for the OMR sheet processing functionality.
"""

from typing import TYPE_CHECKING

import gradio as gr

from frontend.config.constants import config

if TYPE_CHECKING:
    from frontend.core.processor import OMRProcessorGradio


def create_tab(processor: "OMRProcessorGradio") -> None:
    """
    Create the OMR sheet processing tab.

    Args:
        processor: OMRProcessorGradio instance for handling sheet processing
    """
    with gr.Tab("📋 辨識答案卡"):
        gr.Markdown(
            """
            ### 快速開始：
            1. 上傳 OMR 答案卡圖檔（PNG/JPG）
            2. 上傳模板檔案（template.json，必要）
            3. 選填：上傳設定檔、評分標準、自訂標記圖檔
            4. 點擊「🚀 開始辨識答案卡」

            **💡 提示：** 如果標記偵測不準確，可以上傳符合你的答案卡的自訂標記圖檔。
            """
        )

        with gr.Row():
            with gr.Column(scale=1):
                gr.Markdown("### 📤 上傳檔案")

                image_input = gr.File(
                    label="OMR 答案卡圖檔",
                    file_count="multiple",
                    file_types=["image"],
                    type="filepath",
                )

                template_input = gr.File(
                    label="模板檔案（template.json）",
                    file_count="single",
                    file_types=[".json"],
                    type="filepath",
                )

                with gr.Accordion("選填設定檔案", open=False):
                    config_input = gr.File(
                        label="設定檔（config.json）",
                        file_count="single",
                        file_types=[".json"],
                        type="filepath",
                    )

                    evaluation_input = gr.File(
                        label="評分標準檔（evaluation.json）",
                        file_count="single",
                        file_types=[".json"],
                        type="filepath",
                    )

                    marker_input = gr.File(
                        label="自訂標記圖檔（選填 - 如果自動產生的標記不符合，請上傳）",
                        file_count="single",
                        file_types=["image"],
                        type="filepath",
                    )

                with gr.Accordion("處理選項", open=False):
                    auto_align_check = gr.Checkbox(
                        label="啟用自動對齊",
                        value=False,
                        info="實驗功能：自動對齊輕微偏移的掃描圖",
                    )

                    set_layout_check = gr.Checkbox(
                        label="版面配置模式",
                        value=False,
                        info="視覺化模板配置，而非進行辨識",
                    )

                process_btn = gr.Button(
                    "🚀 開始辨識答案卡", variant="primary", size="lg"
                )

            with gr.Column(scale=2):
                gr.Markdown("### 📊 辨識結果")

                status_output = gr.Textbox(
                    label="狀態訊息",
                    lines=4,
                    interactive=False,
                )

                results_csv_output = gr.File(
                    label="結果 CSV 檔案",
                    interactive=False,
                )

                marked_images_gallery = gr.Gallery(
                    label="標記後的答案卡圖檔",
                    show_label=True,
                    columns=2,
                    height="auto",
                )

                with gr.Accordion("處理記錄", open=False):
                    log_output = gr.Textbox(
                        label="詳細記錄",
                        lines=config.DEFAULT_LOG_LINES,
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
                marker_input,
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
