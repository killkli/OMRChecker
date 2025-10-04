"""
Batch Generation Tab

This module contains the UI components for batch OMR sheet generation.
"""

import os
import tempfile
import traceback
import zipfile
from pathlib import Path
from typing import TYPE_CHECKING

import gradio as gr

from frontend.config.constants import config
from frontend.utils.text_utils import calculate_text_positioning

if TYPE_CHECKING:
    from batch_generate_sheets import BatchOMRGenerator


def create_tab(batch_generator: "BatchOMRGenerator") -> None:
    """
    Create the batch generation tab.

    Args:
        batch_generator: BatchOMRGenerator instance for handling batch generation
    """
    with gr.Tab("📦 批次產生答案卡"):
        gr.Markdown(
            """
        ### 從學生名單批次產生 OMR 答案卡

        上傳包含學生資料的 Excel 或 CSV 檔案，自動為每位學生產生專屬的 OMR 答案卡，
        每張答案卡都包含獨一無二的 QR Code，用於快速識別學生身份。

        **功能特色：**
        - 支援 Excel (.xlsx, .xls) 或 CSV 檔案
        - 為每位學生產生專屬答案卡
        - 每張答案卡包含獨特的 QR Code（編碼學生 ID）
        - 可印上學生個人資料（姓名、班級等）
        - 下載包含所有答案卡和模板的 ZIP 檔案
        """
        )

        with gr.Row():
            with gr.Column(scale=1):
                gr.Markdown("### 📤 上傳學生名單")

                batch_file_input = gr.File(
                    label="Excel/CSV 檔案（包含學生資料）",
                    file_count="single",
                    file_types=[".xlsx", ".xls", ".csv"],
                    type="filepath",
                )

                batch_column_name = gr.Textbox(
                    label="ID 欄位名稱（選填）",
                    placeholder="例如：student_id、學號、編號（留空則使用第一欄）",
                    value="",
                )

                batch_data_columns = gr.Textbox(
                    label="學生資料欄位（選填）",
                    placeholder="例如：name,class,section 或 姓名,班級,座號（逗號分隔，留空則使用所有欄位）",
                    value="",
                    info="要印在答案卡上的欄位（如：學生姓名、班級、座號等）",
                )

                batch_sheet_name = gr.Textbox(
                    label="Excel 工作表名稱/索引（選填）",
                    placeholder="0 代表第一個工作表，或輸入工作表名稱",
                    value="0",
                )

                gr.Markdown("### ⚙️ 答案卡設定")

                with gr.Group():
                    gr.Markdown("#### 題目設定")
                    batch_num_questions = gr.Number(
                        label="題目數量",
                        value=config.DEFAULT_NUM_QUESTIONS,
                        minimum=config.NUM_QUESTIONS_MIN,
                        maximum=config.NUM_QUESTIONS_MAX,
                        step=1,
                    )

                    batch_question_type = gr.Dropdown(
                        label="題型",
                        choices=["QTYPE_MCQ4", "QTYPE_MCQ5", "QTYPE_INT"],
                        value="QTYPE_MCQ4",
                    )

                    batch_num_columns = gr.Number(
                        label="欄數（橫向排列）",
                        value=4,
                        minimum=config.NUM_COLUMNS_MIN,
                        maximum=config.NUM_COLUMNS_MAX,
                        step=1,
                    )

                with gr.Group():
                    gr.Markdown("#### 其他選項")
                    batch_include_markers = gr.Checkbox(
                        label="包含對齊標記（建議勾選）",
                        value=True,
                    )

                # Custom Text Fields for Batch
                with gr.Group():
                    gr.Markdown("#### 共用標題文字（選填）")
                    batch_custom_text1 = gr.Textbox(
                        label="標題第一行（粗體、大字）",
                        placeholder="例如：期末考試 - 數學科",
                        value="",
                    )
                    batch_custom_text2 = gr.Textbox(
                        label="標題第二行",
                        placeholder="例如：班級：_____ 座號：_____",
                        value="",
                    )
                    batch_custom_text3 = gr.Textbox(
                        label="標題第三行",
                        placeholder="例如：日期：_____ 分數：_____",
                        value="",
                    )

                with gr.Accordion("進階設定", open=False):
                    with gr.Row():
                        batch_page_width = gr.Number(
                            label="頁面寬度（像素）",
                            value=config.GENERATOR_PAGE_WIDTH,
                        )
                        batch_page_height = gr.Number(
                            label="頁面高度（像素）",
                            value=config.GENERATOR_PAGE_HEIGHT,
                        )

                    batch_bubble_size = gr.Number(
                        label="圓圈大小（像素）",
                        value=config.GENERATOR_BUBBLE_SIZE,
                    )

                batch_generate_btn = gr.Button(
                    "🚀 批次產生答案卡",
                    variant="primary",
                    size="lg",
                )

            with gr.Column(scale=2):
                gr.Markdown("### 📊 產生進度")

                batch_status = gr.Textbox(
                    label="狀態訊息",
                    lines=config.DEFAULT_STATUS_LINES,
                    interactive=False,
                )

                batch_output_file = gr.File(
                    label="下載所有答案卡（ZIP 檔案）",
                )

                gr.Markdown(
                    """
                ### 💡 輸出檔案結構

                ZIP 檔案將包含：
                ```
                generated_sheets.zip
                ├── sheets/              # 個別答案卡圖檔
                │   ├── ID001.png
                │   ├── ID002.png
                │   └── ...
                └── templates/           # 對應的模板檔案
                    ├── ID001_template.json
                    ├── ID002_template.json
                    └── ...
                ```
                """
                )

        # === Event Handler for Batch Generation ===
        def batch_generate_wrapper(
            excel_file,
            column_name,
            data_columns_str,
            sheet_name,
            num_q,
            q_type,
            num_cols,
            inc_mark,
            pw,
            ph,
            bs,
            text1,
            text2,
            text3,
        ):
            """Wrapper function for batch generation in Gradio."""
            try:
                if excel_file is None:
                    return "❌ Please upload an Excel or CSV file", None

                # Parse sheet name (can be index or name)
                try:
                    sheet_idx = int(sheet_name) if sheet_name else 0
                except ValueError:
                    sheet_idx = sheet_name if sheet_name else 0

                # Parse data columns
                data_columns = None
                if data_columns_str and data_columns_str.strip():
                    data_columns = [col.strip() for col in data_columns_str.split(',') if col.strip()]

                # Read student data from Excel/CSV
                status_msg = "📖 Reading student data from file...\n"

                # Check if we need to read full student data or just IDs
                if data_columns or not column_name:
                    # Read full student data
                    student_data = batch_generator.read_student_data_from_excel(
                        excel_file,
                        id_column=column_name if column_name else None,
                        data_columns=data_columns,
                        sheet_name=sheet_idx,
                    )

                    if not student_data:
                        return "❌ No student data found in the file", None

                    status_msg += f"✓ Found {len(student_data)} students\n"
                    status_msg += f"Sample: {student_data[0]}\n"
                    if data_columns:
                        status_msg += f"Data columns: {', '.join(data_columns)}\n"
                    status_msg += "\n🔨 Generating sheets with student data...\n"
                else:
                    # Read only IDs
                    ids = batch_generator.read_ids_from_excel(
                        excel_file,
                        column_name=column_name,
                        sheet_name=sheet_idx,
                    )

                    if not ids:
                        return "❌ No IDs found in the file", None

                    student_data = None
                    status_msg += f"✓ Found {len(ids)} IDs\n"
                    status_msg += f"Sample IDs: {', '.join(ids[:5])}\n\n"
                    status_msg += "🔨 Generating sheets...\n"

                # Create temporary output directory
                temp_output = tempfile.mkdtemp(prefix="batch_omr_")

                # Build text lines list (filter empty strings)
                page_w = int(pw)
                text_lines = [t for t in [text1, text2, text3] if t and t.strip()]

                # Calculate text positioning using utility function
                custom_texts = calculate_text_positioning(
                    text_lines, page_w, inc_mark, config
                )

                # Generate batch
                success, failed = batch_generator.generate_batch(
                    ids=ids if student_data is None else None,
                    student_data=student_data,
                    output_dir=Path(temp_output),
                    num_questions=int(num_q),
                    question_type=q_type,
                    num_columns=int(num_cols),
                    include_markers=inc_mark,
                    page_width=page_w,
                    page_height=int(ph),
                    bubble_size=int(bs),
                    custom_texts=custom_texts if custom_texts else None,
                )

                status_msg += f"\n{'='*50}\n"
                status_msg += f"✅ Successfully generated: {success}\n"
                status_msg += f"❌ Failed: {failed}\n"
                status_msg += f"{'='*50}\n\n"

                if success == 0:
                    return status_msg + "❌ No sheets were generated successfully", None

                # Create ZIP file
                status_msg += "📦 Creating ZIP archive...\n"
                zip_path = temp_output + "_sheets.zip"
                with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
                    for root, dirs, files in os.walk(temp_output):
                        for file in files:
                            file_path = os.path.join(root, file)
                            arcname = os.path.relpath(file_path, temp_output)
                            zipf.write(file_path, arcname)

                # Determine total count based on what data we used
                total_count = len(student_data) if student_data else len(ids)
                status_msg += f"✓ ZIP archive created: {total_count} sheets\n"
                status_msg += f"\n🎉 Batch generation complete!\n"
                status_msg += f"Download the ZIP file below."

                return status_msg, zip_path

            except Exception as e:
                error_msg = f"❌ Error during batch generation:\n{str(e)}\n\n"
                error_msg += traceback.format_exc()
                return error_msg, None

        batch_generate_btn.click(
            fn=batch_generate_wrapper,
            inputs=[
                batch_file_input,
                batch_column_name,
                batch_data_columns,
                batch_sheet_name,
                batch_num_questions,
                batch_question_type,
                batch_num_columns,
                batch_include_markers,
                batch_page_width,
                batch_page_height,
                batch_bubble_size,
                batch_custom_text1,
                batch_custom_text2,
                batch_custom_text3,
            ],
            outputs=[
                batch_status,
                batch_output_file,
            ],
        )
