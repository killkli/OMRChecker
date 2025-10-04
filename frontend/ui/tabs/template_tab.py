"""
Template Builder Tab

This module contains the UI components for the interactive template builder.
"""

from typing import TYPE_CHECKING

import gradio as gr

from frontend.config.constants import config

if TYPE_CHECKING:
    from frontend.core.template_builder import TemplateBuilder


def create_tab(template_builder: "TemplateBuilder") -> None:
    """
    Create the template builder tab.

    Args:
        template_builder: TemplateBuilder instance for handling template creation
    """
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
        def handle_image_click(evt: gr.SelectData):
            """Extract coordinates from Gradio event and pass to business logic."""
            x, y = evt.index[0], evt.index[1]
            return template_builder.get_coordinates_from_click(x, y)

        ref_image_display.select(
            fn=handle_image_click,
            inputs=None,  # Gradio auto-passes SelectData
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
