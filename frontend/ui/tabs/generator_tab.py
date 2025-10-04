"""
Sheet Generator Tab

This module contains the UI components for the blank OMR sheet generator.
"""

from typing import TYPE_CHECKING

import gradio as gr

from frontend.config.constants import config
from frontend.utils.text_utils import calculate_text_positioning

if TYPE_CHECKING:
    from frontend.core.sheet_generator import OMRSheetGenerator


def create_tab(sheet_generator: "OMRSheetGenerator") -> None:
    """
    Create the sheet generator tab.

    Args:
        sheet_generator: OMRSheetGenerator instance for handling sheet generation
    """
    with gr.Tab("📄 產生空白答案卡"):
        gr.Markdown(
            """
        ### 自動產生空白 OMR 答案卡

        只需指定你的需求，系統會自動產生：
        1. 📄 空白 OMR 答案卡圖檔（可直接列印）
        2. 📋 對應的模板檔案（template.json）

        **最適合快速建立自訂 OMR 答案卡！**
        """
        )

        with gr.Row():
            with gr.Column(scale=1):
                gr.Markdown("### ⚙️ 答案卡設定")

                # Basic settings
                with gr.Group():
                    gr.Markdown("#### 題目設定")
                    gen_num_questions = gr.Number(
                        label="題目數量",
                        value=config.DEFAULT_NUM_QUESTIONS,
                        minimum=config.NUM_QUESTIONS_MIN,
                        maximum=config.NUM_QUESTIONS_MAX,
                        step=1,
                    )

                    gen_question_type = gr.Dropdown(
                        label="題型",
                        choices=["QTYPE_MCQ4", "QTYPE_MCQ5", "QTYPE_INT", "QTYPE_INT_FROM_1"],
                        value="QTYPE_MCQ4",
                        info="MCQ4=A/B/C/D, MCQ5=A/B/C/D/E, INT=0-9 數字",
                    )

                    gen_num_columns = gr.Number(
                        label="欄數（橫向排列）",
                        value=4,
                        minimum=config.NUM_COLUMNS_MIN,
                        maximum=config.NUM_COLUMNS_MAX,
                        step=1,
                        info="題目橫向排列幾欄（X 軸，由左至右）",
                    )

                # QR Code settings
                with gr.Group():
                    gr.Markdown("#### QR Code ID（選填）")
                    gen_include_qr = gr.Checkbox(
                        label="包含 QR Code",
                        value=False,
                    )
                    gen_qr_content = gr.Textbox(
                        label="QR Code 內容",
                        placeholder="例如：student_001 或 ID:123",
                        visible=False,
                    )

                gen_include_qr.change(
                    fn=lambda inc: gr.update(visible=inc),
                    inputs=[gen_include_qr],
                    outputs=[gen_qr_content],
                )

                # Custom Text Fields
                with gr.Group():
                    gr.Markdown("#### 自訂文字（選填）")
                    gen_custom_text1 = gr.Textbox(
                        label="標題第一行",
                        placeholder="例如：期末考試 - 數學科",
                        value="",
                    )
                    gen_custom_text2 = gr.Textbox(
                        label="標題第二行",
                        placeholder="例如：班級：_____ 姓名：_____",
                        value="",
                    )
                    gen_custom_text3 = gr.Textbox(
                        label="標題第三行",
                        placeholder="例如：日期：_____ 分數：_____",
                        value="",
                    )

                # Alignment markers
                with gr.Group():
                    gr.Markdown("#### 對齊標記")
                    gen_include_markers = gr.Checkbox(
                        label="包含對齊標記",
                        value=True,
                        info="✓ 建議啟用。可校正拍照或掃描時的旋轉和傾斜。",
                    )

                # Page settings
                with gr.Accordion("進階設定", open=False):
                    with gr.Row():
                        gen_page_width = gr.Number(
                            label="頁面寬度（像素）",
                            value=config.GENERATOR_PAGE_WIDTH,
                            minimum=config.PAGE_WIDTH_MIN,
                            maximum=config.PAGE_WIDTH_MAX,
                        )
                        gen_page_height = gr.Number(
                            label="頁面高度（像素）",
                            value=config.GENERATOR_PAGE_HEIGHT,
                            minimum=config.PAGE_HEIGHT_MIN,
                            maximum=config.PAGE_HEIGHT_MAX,
                        )

                    gen_bubble_size = gr.Number(
                        label="圓圈大小（像素）",
                        value=config.GENERATOR_BUBBLE_SIZE,
                        minimum=config.BUBBLE_SIZE_MIN,
                        maximum=config.BUBBLE_SIZE_MAX,
                    )

                # Generate button
                gen_generate_btn = gr.Button(
                    "✨ 產生空白答案卡",
                    variant="primary",
                    size="lg",
                )

            with gr.Column(scale=2):
                gr.Markdown("### 📊 產生結果")

                gen_status = gr.Textbox(
                    label="產生狀態",
                    lines=8,
                    interactive=False,
                )

                gen_sheet_image = gr.Image(
                    label="產生的空白答案卡（預覽）",
                    type="filepath",
                )

                with gr.Row():
                    gen_sheet_file = gr.File(
                        label="下載空白答案卡圖檔",
                    )
                    gen_template_file = gr.File(
                        label="下載模板 JSON 檔案",
                    )

                gr.Markdown(
                    """
                ### 💡 後續步驟

                1. **下載兩個檔案**（答案卡圖檔和模板檔案）
                2. **列印空白答案卡** 或數位使用
                3. 在答案卡上填寫答案（或模擬填答）
                4. 使用「📋 辨識答案卡」標籤頁進行辨識：
                   - 上傳填寫完成的答案卡圖檔
                   - 上傳產生的 template.json 模板檔案
                """
                )

        # === Event Handlers for Sheet Generator ===

        # Generate sheet button click
        def generate_sheet_wrapper(
            num_q, q_type, num_cols, inc_mark, pw, ph, bs, inc_qr, qr_content,
            text1, text2, text3
        ):
            # Build text lines list (filter empty strings)
            page_w = int(pw)
            page_h = int(ph)
            text_lines = [t for t in [text1, text2, text3] if t and t.strip()]

            # Calculate text positioning using utility function
            custom_texts = calculate_text_positioning(
                text_lines, page_w, inc_mark, config
            )

            sheet_path, template_path, msg = sheet_generator.generate_sheet(
                num_questions=int(num_q),
                question_type=q_type,
                num_columns=int(num_cols),
                include_markers=inc_mark,
                page_width=page_w,
                page_height=page_h,
                bubble_size=int(bs),
                include_qr=inc_qr,
                qr_content=qr_content or "",
                custom_texts=custom_texts if custom_texts else None,
            )
            return sheet_path, sheet_path, template_path, msg

        gen_generate_btn.click(
            fn=generate_sheet_wrapper,
            inputs=[
                gen_num_questions,
                gen_question_type,
                gen_num_columns,
                gen_include_markers,
                gen_page_width,
                gen_page_height,
                gen_bubble_size,
                gen_include_qr,
                gen_qr_content,
                gen_custom_text1,
                gen_custom_text2,
                gen_custom_text3,
            ],
            outputs=[
                gen_sheet_image,
                gen_sheet_file,
                gen_template_file,
                gen_status,
            ],
        )
