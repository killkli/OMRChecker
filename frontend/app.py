"""
OMRChecker Gradio Frontend

A modern web-based interface for OMR sheet processing using Gradio.

Author: Generated with Claude Code
"""

import json
import os
import sys
import tempfile
import zipfile
import shutil
from pathlib import Path
from typing import List, Optional, Tuple, Dict, Any

import cv2
import gradio as gr
import numpy as np
import pandas as pd

# Add parent directory to path to import src modules
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.constants import FIELD_TYPES
from src.defaults import CONFIG_DEFAULTS
from src.entry import process_dir
from src.logger import logger
from src.template import Template
from src.utils.parsing import open_config_with_defaults
from batch_generate_sheets import BatchOMRGenerator
from frontend.config.constants import config
from frontend.utils.marker_utils import generate_concentric_circle_marker
from frontend.utils.text_utils import calculate_text_positioning, calculate_max_text_y
from frontend.utils.coordinate_utils import calculate_coordinate_system
from frontend.core.processor import OMRProcessorGradio
from frontend.core.template_builder import TemplateBuilder
from frontend.core.sheet_generator import OMRSheetGenerator


# Initialize processor
processor = OMRProcessorGradio()


# Initialize template builder
template_builder = TemplateBuilder()


# Initialize sheet generator and batch generator
sheet_generator = OMRSheetGenerator()
batch_generator = BatchOMRGenerator()


def create_gradio_interface():
    """Create and configure the Gradio interface."""

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
            # ===== ORIGINAL PROCESSING TAB =====
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

            # ===== NEW TEMPLATE BUILDER TAB =====
            with gr.Tab("🔧 模板建立工具"):
                gr.Markdown(
                    """
                ### 互動式建立新模板

                1. **上傳參考圖檔**：上傳範例 OMR 答案卡圖檔
                2. **設定參數**：設定頁面和圓圈尺寸
                3. **新增欄位區塊**：點擊圖片取得座標，然後新增欄位區塊
                4. **預覽**：在圖片上視覺化你的模板
                5. **匯出**：下載你的 template.json 檔案
                """
                )

                with gr.Row():
                    with gr.Column(scale=1):
                        # Step 1: Upload Reference Image
                        gr.Markdown("### 1️⃣ 參考圖檔")
                        ref_image_input = gr.File(
                            label="上傳參考 OMR 圖檔",
                            file_count="single",
                            file_types=["image"],
                            type="filepath",
                        )
                        load_image_btn = gr.Button("載入圖檔", variant="secondary")
                        image_status = gr.Textbox(label="狀態", lines=2, interactive=False)

                        # Step 2: Basic Settings
                        gr.Markdown("### 2️⃣ 基本設定")
                        with gr.Row():
                            page_width = gr.Number(label="頁面寬度", value=config.DEFAULT_PAGE_WIDTH)
                            page_height = gr.Number(label="頁面高度", value=config.DEFAULT_PAGE_HEIGHT)
                        update_page_btn = gr.Button("更新頁面尺寸", size="sm")

                        with gr.Row():
                            bubble_width = gr.Number(label="預設圓圈寬度", value=config.DEFAULT_BUBBLE_WIDTH)
                            bubble_height = gr.Number(label="預設圓圈高度", value=config.DEFAULT_BUBBLE_HEIGHT)
                        update_bubble_btn = gr.Button("更新圓圈尺寸", size="sm")

                        dimension_status = gr.Textbox(label="尺寸狀態", lines=1, interactive=False)

                    with gr.Column(scale=2):
                        # Image display with click coordinates
                        gr.Markdown("### 📍 點擊圖片以取得座標")
                        ref_image_display = gr.Image(
                            label="參考圖檔（點擊以選擇座標）",
                            interactive=False,
                        )
                        click_coords_output = gr.Textbox(
                            label="已選座標",
                            value="點擊圖片以選擇座標",
                            interactive=False,
                        )
                        with gr.Row():
                            selected_x = gr.Number(label="X 座標", value=0)
                            selected_y = gr.Number(label="Y 座標", value=0)

                # Step 3: Add Field Blocks
                with gr.Accordion("3️⃣ 新增欄位區塊", open=True):
                    with gr.Row():
                        with gr.Column():
                            block_name_input = gr.Textbox(label="區塊名稱", placeholder="例如：MCQ_Block_Q1")

                            with gr.Row():
                                origin_x_input = gr.Number(label="起始 X 座標", value=config.DEFAULT_ORIGIN_X)
                                origin_y_input = gr.Number(label="起始 Y 座標", value=config.DEFAULT_ORIGIN_Y)

                            use_selected_coords_btn = gr.Button("📍 使用已選座標", size="sm")

                            field_type_input = gr.Dropdown(
                                label="欄位類型",
                                choices=["QTYPE_INT", "QTYPE_INT_FROM_1", "QTYPE_MCQ4", "QTYPE_MCQ5", "CUSTOM"],
                                value="QTYPE_MCQ4",
                            )

                            custom_bubble_values_input = gr.Textbox(
                                label="自訂圓圈值（逗號分隔，用於 CUSTOM 類型）",
                                placeholder="例如：A,B,C,D",
                                visible=False,
                            )

                        with gr.Column():
                            field_labels_input = gr.Textbox(
                                label="欄位標籤（逗號分隔）",
                                placeholder="例如：q1,q2,q3 或 q1..10",
                            )

                            direction_input = gr.Radio(
                                label="方向",
                                choices=["horizontal", "vertical"],
                                value="horizontal",
                            )

                            with gr.Row():
                                bubbles_gap_input = gr.Number(label="圓圈間距", value=config.SMALL_BUBBLE_GAP)
                                labels_gap_input = gr.Number(label="標籤間距", value=config.SMALL_BUBBLE_GAP)

                            with gr.Row():
                                custom_bubble_w = gr.Number(label="自訂圓圈寬度（選填）", value=None)
                                custom_bubble_h = gr.Number(label="自訂圓圈高度（選填）", value=None)

                    with gr.Row():
                        add_block_btn = gr.Button("➕ 新增欄位區塊", variant="primary")
                        remove_block_name = gr.Textbox(label="要移除的區塊名稱", placeholder="輸入區塊名稱")
                        remove_block_btn = gr.Button("🗑️ 移除欄位區塊", variant="stop")

                    field_blocks_display = gr.Textbox(
                        label="目前欄位區塊",
                        lines=config.DEFAULT_FIELD_BLOCKS_LINES,
                        value="尚未新增任何欄位區塊",
                        interactive=False,
                    )

                # Step 4: Custom Labels (Optional)
                with gr.Accordion("4️⃣ 自訂標籤（選填）", open=False):
                    with gr.Row():
                        custom_label_name = gr.Textbox(label="標籤名稱", placeholder="例如：Roll")
                        custom_label_fields = gr.Textbox(
                            label="欄位清單（逗號分隔）",
                            placeholder="例如：Medium,roll1..9",
                        )

                    with gr.Row():
                        add_custom_label_btn = gr.Button("➕ 新增自訂標籤", variant="primary")
                        remove_custom_label_name = gr.Textbox(label="要移除的標籤名稱")
                        remove_custom_label_btn = gr.Button("🗑️ 移除自訂標籤", variant="stop")

                    custom_labels_display = gr.Textbox(
                        label="目前自訂標籤",
                        lines=5,
                        value="尚未新增任何自訂標籤",
                        interactive=False,
                    )

                # Step 5: Preprocessors (Optional)
                with gr.Accordion("5️⃣ 前處理器（選填）", open=False):
                    with gr.Row():
                        preprocessor_name = gr.Dropdown(
                            label="Preprocessor Name",
                            choices=[
                                "CropPage",
                                "CropOnMarkers",
                                "FeatureBasedAlignment",
                                "GaussianBlur",
                                "Levels",
                                "MedianBlur",
                            ],
                            value="CropPage",
                        )
                        preprocessor_options = gr.Textbox(
                            label="Options (JSON)",
                            placeholder='e.g., {"morphKernel": [10, 10]}',
                        )

                    with gr.Row():
                        add_preprocessor_btn = gr.Button("➕ Add Preprocessor", variant="primary")
                        remove_preprocessor_idx = gr.Number(label="Index to Remove", value=0)
                        remove_preprocessor_btn = gr.Button("🗑️ Remove Preprocessor", variant="stop")

                    preprocessors_display = gr.Textbox(
                        label="Current Preprocessors",
                        lines=5,
                        value="No preprocessors added yet",
                        interactive=False,
                    )

                # Step 6: Preview and Export
                with gr.Row():
                    with gr.Column():
                        gr.Markdown("### 6️⃣ Preview Template")
                        preview_btn = gr.Button("👁️ Preview Template", variant="secondary", size="lg")
                        preview_image = gr.Image(label="Template Visualization")
                        preview_status = gr.Textbox(label="Preview Status", lines=2, interactive=False)

                    with gr.Column():
                        gr.Markdown("### 7️⃣ Export Template")
                        export_btn = gr.Button("📥 Export Template JSON", variant="primary", size="lg")
                        export_file = gr.File(label="Download Template")
                        export_status = gr.Textbox(label="Export Status", lines=2, interactive=False)

                # === Event Handlers for Template Builder ===

                # Load reference image
                load_image_btn.click(
                    fn=template_builder.load_reference_image,
                    inputs=[ref_image_input],
                    outputs=[ref_image_display, image_status],
                )

                # Update dimensions
                update_page_btn.click(
                    fn=template_builder.update_page_dimensions,
                    inputs=[page_width, page_height],
                    outputs=[dimension_status],
                )

                update_bubble_btn.click(
                    fn=template_builder.update_bubble_dimensions,
                    inputs=[bubble_width, bubble_height],
                    outputs=[dimension_status],
                )

                # Image click to get coordinates
                ref_image_display.select(
                    fn=template_builder.get_coordinates_from_click,
                    inputs=[],  # Gradio auto-passes SelectData
                    outputs=[selected_x, selected_y, click_coords_output],
                )

                # Use selected coordinates for origin
                def use_coords(x, y):
                    return x, y

                use_selected_coords_btn.click(
                    fn=use_coords,
                    inputs=[selected_x, selected_y],
                    outputs=[origin_x_input, origin_y_input],
                )

                # Show/hide custom bubble values based on field type
                def toggle_custom_values(field_type):
                    return gr.update(visible=(field_type == "CUSTOM"))

                field_type_input.change(
                    fn=toggle_custom_values,
                    inputs=[field_type_input],
                    outputs=[custom_bubble_values_input],
                )

                # Add field block
                add_block_btn.click(
                    fn=template_builder.add_field_block,
                    inputs=[
                        block_name_input,
                        origin_x_input,
                        origin_y_input,
                        field_type_input,
                        field_labels_input,
                        bubbles_gap_input,
                        labels_gap_input,
                        direction_input,
                        custom_bubble_values_input,
                        custom_bubble_w,
                        custom_bubble_h,
                    ],
                    outputs=[dimension_status, field_blocks_display],
                )

                # Remove field block
                remove_block_btn.click(
                    fn=template_builder.remove_field_block,
                    inputs=[remove_block_name],
                    outputs=[dimension_status, field_blocks_display],
                )

                # Add custom label
                add_custom_label_btn.click(
                    fn=template_builder.add_custom_label,
                    inputs=[custom_label_name, custom_label_fields],
                    outputs=[dimension_status, custom_labels_display],
                )

                # Remove custom label
                remove_custom_label_btn.click(
                    fn=template_builder.remove_custom_label,
                    inputs=[remove_custom_label_name],
                    outputs=[dimension_status, custom_labels_display],
                )

                # Add preprocessor
                add_preprocessor_btn.click(
                    fn=template_builder.add_preprocessor,
                    inputs=[preprocessor_name, preprocessor_options],
                    outputs=[dimension_status, preprocessors_display],
                )

                # Remove preprocessor
                remove_preprocessor_btn.click(
                    fn=template_builder.remove_preprocessor,
                    inputs=[remove_preprocessor_idx],
                    outputs=[dimension_status, preprocessors_display],
                )

                # Preview template
                preview_btn.click(
                    fn=template_builder.visualize_template,
                    inputs=[],
                    outputs=[preview_image, preview_status],
                )

                # Export template
                export_btn.click(
                    fn=template_builder.export_template,
                    inputs=[],
                    outputs=[export_file, export_status],
                )

            # ===== BLANK SHEET GENERATOR TAB =====
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

            # ===== BATCH GENERATION TAB =====
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
                        import traceback
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
        server_name=config.GRADIO_SERVER_NAME,
        server_port=config.GRADIO_SERVER_PORT,
        share=config.GRADIO_SHARE,
        show_error=config.GRADIO_SHOW_ERROR,
    )
