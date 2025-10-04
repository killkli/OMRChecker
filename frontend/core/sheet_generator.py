import json
import os
import sys
import tempfile
import zipfile
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional, Tuple, Dict, Any

import cv2
import numpy as np
import qrcode  # For QR generation
from qrcode.image.pil import PilImage
from PIL import Image, ImageDraw, ImageFont

# Add parent directory to path to import src modules
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.constants import FIELD_TYPES
from src.logger import logger
from frontend.config.constants import config
from frontend.utils.marker_utils import generate_concentric_circle_marker
from frontend.utils.text_utils import calculate_text_positioning, calculate_max_text_y
from frontend.utils.coordinate_utils import calculate_coordinate_system


@dataclass
class PageSetupParams:
    """Parameters for page setup and coordinate system calculation."""
    page_width: int
    page_height: int
    bubble_size: int
    num_options: int
    num_columns: int
    default_direction: str
    include_markers: bool


@dataclass
class QuestionLayoutParams:
    """Parameters for question layout generation."""
    num_questions: int
    num_columns: int
    bubble_values: List[Any]
    default_direction: str
    margin: int
    bubble_size: int
    bubble_gap: int
    single_question_width: int
    column_gap: int
    row_gap: int
    question_type: str


@dataclass
class QRCodeParams:
    """Parameters for QR code generation and placement."""
    page_width: int
    page_height: int
    bubble_size: int
    margin: int
    qr_content: str
    coord_offset_x: int
    coord_offset_y: int


@dataclass
class SheetMetadata:
    """Metadata for saving sheet and template."""
    num_questions: int
    question_type: str
    num_columns: int
    questions_per_column: int
    include_markers: bool
    include_qr: bool
    marker_size: int
    page_width: int
    qr_msg: str = ""


class OMRSheetGenerator:
    """Generate blank OMR sheets with automatic template creation."""

    def __init__(self):
        self.sheet_image = None
        self.template_data = None

    def _setup_page_and_coordinate_system(
        self,
        params: PageSetupParams,
    ) -> Dict[str, Any]:
        """
        Calculate page dimensions, marker settings, and coordinate offsets.

        Args:
            params: Page setup parameters

        Returns:
            Dict with template dimensions, offsets, and layout parameters
        """
        # Calculate marker size first (if markers are included)
        if params.include_markers:
            marker_size = int(params.page_width * config.MARKER_SIZE_RATIO)
            # Margin must be larger than marker to avoid overlap
            margin = marker_size + config.MARKER_EXTRA_SPACING
            header_height = marker_size + config.MARKER_HEADER_HEIGHT
        else:
            marker_size = 0
            margin = config.DEFAULT_MARGIN
            header_height = config.DEFAULT_HEADER_HEIGHT

        bubble_gap = params.bubble_size + config.DEFAULT_BUBBLE_GAP

        # Calculate available width for questions
        available_width = params.page_width - 2 * margin

        # Calculate question block width based on direction
        if params.default_direction == "horizontal":
            # For horizontal bubbles: question needs space for all options
            single_question_width = params.num_options * bubble_gap + config.QUESTION_BLOCK_PADDING_HORIZONTAL
        else:
            # For vertical bubbles: question needs space for one bubble width + label
            single_question_width = bubble_gap + config.QUESTION_BLOCK_PADDING_VERTICAL

        # Calculate spacing between columns
        total_questions_width = params.num_columns * single_question_width
        if params.num_columns > 1:
            column_gap = (available_width - total_questions_width) // (params.num_columns - 1)
            column_gap = max(config.COLUMN_GAP_MIN, min(column_gap, config.COLUMN_GAP_MAX))
        else:
            column_gap = 0

        # Row gap based on question type
        if params.default_direction == "horizontal":
            row_gap = params.bubble_size + config.ROW_GAP_HORIZONTAL
        else:
            row_gap = params.num_options * bubble_gap + config.ROW_GAP_VERTICAL

        # Calculate coordinate system using utility function
        coord_system = calculate_coordinate_system(
            params.page_width, params.page_height, params.include_markers, config
        )

        return {
            "margin": margin,
            "header_height": header_height,
            "bubble_gap": bubble_gap,
            "single_question_width": single_question_width,
            "column_gap": column_gap,
            "row_gap": row_gap,
            "template_width": coord_system["template_width"],
            "template_height": coord_system["template_height"],
            "coord_offset_x": coord_system["coord_offset_x"],
            "coord_offset_y": coord_system["coord_offset_y"],
            "marker_positions": coord_system["marker_positions"],
            "marker_size": coord_system["marker_size"],
        }

    def _draw_markers_on_image(
        self,
        img: np.ndarray,
        marker_positions: List[Tuple[int, int]],
        marker_size: int,
    ) -> None:
        """
        Draw concentric circle markers at 4 corners.

        Args:
            img: Image array to draw on (modified in place)
            marker_positions: List of (x, y) positions for markers
            marker_size: Size of each marker
        """
        if marker_positions:
            for x, y in marker_positions:
                # Generate marker and paste onto image at marker position
                marker_img = generate_concentric_circle_marker(marker_size, config)
                img[y:y+marker_size, x:x+marker_size] = marker_img

    def _render_custom_text_fields(
        self,
        img: np.ndarray,
        custom_texts: Optional[List[Dict[str, Any]]],
        header_height: int,
    ) -> int:
        """
        Handle custom text rendering using text_utils.

        Args:
            img: Image array to draw on (modified in place)
            custom_texts: List of custom text fields
            header_height: Default header height

        Returns:
            Y position where questions should start
        """
        if not custom_texts:
            return header_height

        # Convert to PIL Image for text rendering
        pil_img = Image.fromarray(img)
        draw = ImageDraw.Draw(pil_img)

        # Try to load Chinese font from project directory, fallback to system fonts
        try:
            font_paths = config.get_font_paths()
            font_path = None
            for path in font_paths:
                if os.path.exists(path):
                    font_path = path
                    logger.info(f"Using font: {path}")
                    break

            if not font_path:
                logger.warning("No suitable font found, using default")
        except Exception as e:
            logger.warning(f"Font loading error: {e}")
            font_path = None

        for text_field in custom_texts:
            text = text_field.get("text", "")
            x = text_field.get("x", 100)
            y = text_field.get("y", 50)
            font_size_scale = text_field.get("font_size", 1.0)
            bold = text_field.get("bold", False)

            # Calculate actual font size in pixels (larger for better readability)
            actual_font_size = int(config.BASE_FONT_SIZE * font_size_scale)

            # Load font
            try:
                if font_path:
                    font = ImageFont.truetype(font_path, actual_font_size)
                else:
                    font = ImageFont.load_default()
            except:
                font = ImageFont.load_default()

            # Draw text with PIL (supports Chinese)
            draw.text((x, y), text, font=font, fill=config.COLOR_BLACK)

            # If bold, draw again with slight offset for thickness
            if bold:
                draw.text((x+config.BOLD_OFFSET_X, y), text, font=font, fill=config.COLOR_BLACK)
                draw.text((x, y+config.BOLD_OFFSET_Y), text, font=font, fill=config.COLOR_BLACK)
                draw.text((x+config.BOLD_OFFSET_X, y+config.BOLD_OFFSET_Y), text, font=font, fill=config.COLOR_BLACK)

        # Convert back to numpy array
        img_array = np.array(pil_img)
        img[:] = img_array  # Update in place

        # Calculate the maximum Y position used by custom texts
        max_text_y = calculate_max_text_y(custom_texts, config)

        # Questions start below all custom text + extra spacing
        return max(header_height, max_text_y + config.CUSTOM_TEXT_SPACING)

    def _generate_question_layout(
        self,
        img: np.ndarray,
        params: QuestionLayoutParams,
        coord_offset_x: int,
        coord_offset_y: int,
        current_y: int,
    ) -> int:
        """
        Calculate question positions in column-first ordering and draw them.

        Args:
            img: Image array to draw on
            params: Question layout parameters
            coord_offset_x: X coordinate offset for template
            coord_offset_y: Y coordinate offset for template
            current_y: Starting Y position

        Returns:
            Number of questions drawn
        """

        questions_drawn = 0
        num_options = len(params.bubble_values)

        # Calculate how many rows per column we need
        questions_per_column = (params.num_questions + params.num_columns - 1) // params.num_columns

        # Iterate column-first (left to right), then row (top to bottom)
        for col in range(params.num_columns):
            # Reset Y position for each new column
            column_y = current_y

            for row in range(questions_per_column):
                if questions_drawn >= params.num_questions:
                    break

                # Calculate position for this question block
                # X position: margin + column_index * (question_width + column_gap)
                block_x = params.margin + col * (params.single_question_width + params.column_gap)

                # Y position: start_y + row_index * row_gap
                block_y = column_y

                # Question metadata
                block_name = f"Block_Q{questions_drawn + 1}"
                field_label = f"q{questions_drawn + 1}"

                # Draw question number
                cv2.putText(
                    img,
                    f"Q{questions_drawn + 1}",
                    (block_x + config.QUESTION_LABEL_OFFSET_X, block_y + params.bubble_size // 2 + config.QUESTION_LABEL_OFFSET_Y),
                    config.CV2_FONT_FACE,
                    config.CV2_QUESTION_FONT_SCALE,
                    config.COLOR_BLACK,
                    config.CV2_QUESTION_FONT_THICKNESS,
                )

                # Draw bubbles based on direction
                for opt_idx, opt_value in enumerate(params.bubble_values):
                    if params.default_direction == "horizontal":
                        bubble_x = block_x + opt_idx * params.bubble_gap
                        bubble_y = block_y
                    else:
                        bubble_x = block_x
                        bubble_y = block_y + opt_idx * params.bubble_gap

                    # Draw circle
                    cv2.circle(
                        img,
                        (bubble_x + params.bubble_size // 2, bubble_y + params.bubble_size // 2),
                        params.bubble_size // 2,
                        config.COLOR_BLACK,
                        config.CV2_BUBBLE_BORDER_THICKNESS,
                    )

                    # Draw option label
                    if params.default_direction == "horizontal":
                        label_x = bubble_x + params.bubble_size // 2 + config.BUBBLE_LABEL_OFFSET_X_HORIZONTAL
                        label_y = bubble_y + config.BUBBLE_LABEL_OFFSET_Y_HORIZONTAL
                    else:
                        label_x = bubble_x + params.bubble_size + config.BUBBLE_LABEL_OFFSET_X_VERTICAL
                        label_y = bubble_y + params.bubble_size // 2 + config.BUBBLE_LABEL_OFFSET_Y_VERTICAL

                    cv2.putText(
                        img,
                        str(opt_value),
                        (label_x, label_y),
                        config.CV2_FONT_FACE,
                        config.CV2_BUBBLE_LABEL_FONT_SCALE,
                        config.COLOR_BLACK,
                        config.CV2_BUBBLE_LABEL_FONT_THICKNESS,
                    )

                # Add to template (coordinates relative to pageDimensions)
                template_block_x = block_x - coord_offset_x
                template_block_y = block_y - coord_offset_y

                self.template_data["fieldBlocks"][block_name] = {
                    "fieldType": params.question_type,
                    "fieldLabels": [field_label],
                    "origin": [template_block_x, template_block_y],
                    "bubblesGap": params.bubble_gap,
                    "labelsGap": params.bubble_gap,
                }

                questions_drawn += 1

                # Move to next row within this column (Y-axis downward)
                column_y += params.row_gap

        return questions_drawn

    def _add_qr_code_to_sheet(
        self,
        img: np.ndarray,
        params: QRCodeParams,
    ) -> str:
        """
        Generate and embed QR code.

        Args:
            img: Image array to draw on
            params: QR code generation parameters

        Returns:
            Status message about QR code
        """
        qr_size = max(config.QR_SIZE_MIN, params.bubble_size * config.QR_SIZE_BUBBLE_MULTIPLIER)
        qr_x = params.page_width - params.margin - qr_size
        qr_y = params.page_height - params.margin - qr_size

        # Generate QR Code
        qr = qrcode.QRCode(
            version=config.QR_VERSION,
            error_correction=qrcode.constants.ERROR_CORRECT_L,
            box_size=config.QR_BOX_SIZE,
            border=config.QR_BORDER_SIZE,
        )
        qr.add_data(params.qr_content)
        qr.make(fit=True)

        # Create QR image as RGB
        qr_img = qr.make_image(fill_color="black", back_color="white").convert("RGB")

        # Convert to numpy array (ensure uint8 RGB)
        qr_np = np.array(qr_img)
        if qr_np.dtype != np.uint8:
            qr_np = qr_np.astype(np.uint8)

        # Resize QR
        qr_resized = cv2.resize(qr_np, (qr_size, qr_size), interpolation=cv2.INTER_AREA)

        # Convert to BGR for OpenCV
        qr_bgr = cv2.cvtColor(qr_resized, cv2.COLOR_RGB2BGR)

        # Paste QR on sheet
        img[qr_y:qr_y+qr_size, qr_x:qr_x+qr_size] = qr_bgr

        # Add to template as special field (custom for QR)
        qr_block_name = "QR_Code"
        template_qr_x = qr_x - params.coord_offset_x
        template_qr_y = qr_y - params.coord_offset_y
        self.template_data["fieldBlocks"][qr_block_name] = {
            "fieldType": "QTYPE_CUSTOM",
            "fieldLabels": ["qr_id"],
            "origin": [template_qr_x, template_qr_y],
            "bubbleValues": [params.qr_content],  # Placeholder for custom decoding
            "bubblesGap": 0,
            "labelsGap": 0,
            "direction": "horizontal",
        }

        logger.info(f"Generated QR block origin: [template_qr_x, template_qr_y] = [{template_qr_x}, {template_qr_y}]")

        return "\nQR Code: Added with content"

    def _save_sheet_and_template(
        self,
        img: np.ndarray,
        metadata: SheetMetadata,
    ) -> Tuple[str, str, str]:
        """
        Save sheet image and template JSON to temp files.

        Args:
            img: Generated sheet image
            metadata: Sheet metadata for saving

        Returns:
            Tuple of (sheet_path, template_path, status_message)
        """
        # Add preprocessors if markers are included
        if metadata.include_markers:
            # Save marker image using utility function
            marker_temp = tempfile.NamedTemporaryFile(
                suffix=".jpg", delete=False, mode="wb"
            )
            marker_img = generate_concentric_circle_marker(metadata.marker_size, config)
            cv2.imwrite(marker_temp.name, marker_img)
            marker_temp.close()

            # Use CropOnMarkers with wider range for photo-based recognition
            # Range is in percentage: 100 = 1.0x scale
            self.template_data["preProcessors"] = [
                {
                    "name": "CropOnMarkers",
                    "options": {
                        "relativePath": config.MARKER_FILENAME,
                        "sheetToMarkerWidthRatio": metadata.page_width // metadata.marker_size,
                        # Wider range for photos (60-130%) with lower threshold
                        "marker_rescale_range": [config.MARKER_RESCALE_RANGE_MIN, config.MARKER_RESCALE_RANGE_MAX],
                        "marker_rescale_steps": config.MARKER_RESCALE_STEPS,
                        "min_matching_threshold": config.MARKER_MIN_MATCHING_THRESHOLD,
                        "max_matching_variation": config.MARKER_MAX_MATCHING_VARIATION,
                    },
                },
            ]

        # Save sheet image
        self.sheet_image = img
        sheet_temp = tempfile.NamedTemporaryFile(
            suffix=".png", delete=False, mode="wb"
        )
        cv2.imwrite(sheet_temp.name, img)
        sheet_temp.close()

        # Save template JSON
        template_temp = tempfile.NamedTemporaryFile(
            mode="w", suffix=".json", delete=False
        )
        json.dump(self.template_data, template_temp, indent=2)
        template_temp.close()

        msg = f"✅ Generated OMR sheet successfully!\n"
        msg += f"Questions: {metadata.num_questions} ({metadata.question_type})\n"
        msg += f"Layout: {metadata.num_columns} columns × {int(metadata.questions_per_column)} rows per column\n"
        if metadata.include_markers:
            msg += "Alignment markers: Yes\n"
        if metadata.include_qr:
            msg += "QR Code: Added\n"
        msg += f"\n📄 Image saved\n📋 Template JSON generated"

        return sheet_temp.name, template_temp.name, msg

    def generate_sheet(
        self,
        num_questions: int,
        question_type: str,
        num_columns: int,
        include_markers: bool,
        page_width: int,
        page_height: int,
        bubble_size: int,
        include_qr: bool,
        qr_content: str = "",
        custom_texts: Optional[List[Dict[str, Any]]] = None,
    ) -> Tuple[Any, str, str]:
        """Generate blank OMR sheet with automatic layout and QR Code.

        Returns: Tuple of (sheet_path, template_path, status_message)
        """
        try:
            # Create blank white image
            img = np.ones((page_height, page_width, 3), dtype=np.uint8) * 255

            # Get bubble values based on question type
            if question_type in FIELD_TYPES:
                bubble_values = FIELD_TYPES[question_type]["bubbleValues"]
                default_direction = FIELD_TYPES[question_type]["direction"]
            else:
                return None, None, f"Error: Unknown question type '{question_type}'"

            num_options = len(bubble_values)

            # 1. Setup page dimensions and coordinate system
            page_setup_params = PageSetupParams(
                page_width=page_width,
                page_height=page_height,
                bubble_size=bubble_size,
                num_options=num_options,
                num_columns=num_columns,
                default_direction=default_direction,
                include_markers=include_markers,
            )
            layout_params = self._setup_page_and_coordinate_system(page_setup_params)

            # 2. Draw markers on image
            if include_markers:
                self._draw_markers_on_image(
                    img, layout_params["marker_positions"], layout_params["marker_size"]
                )

            # 3. Initialize template data
            self.template_data = {
                "pageDimensions": [layout_params["template_width"], layout_params["template_height"]],
                "bubbleDimensions": [bubble_size, bubble_size],
                "fieldBlocks": {},
                "customLabels": {},
                "preProcessors": [],
            }

            # 4. Render custom text fields
            current_y = self._render_custom_text_fields(
                img, custom_texts, layout_params["header_height"]
            )

            # 5. Generate question layout
            questions_per_column = (num_questions + num_columns - 1) // num_columns
            question_layout_params = QuestionLayoutParams(
                num_questions=num_questions,
                num_columns=num_columns,
                bubble_values=bubble_values,
                default_direction=default_direction,
                margin=layout_params["margin"],
                bubble_size=bubble_size,
                bubble_gap=layout_params["bubble_gap"],
                single_question_width=layout_params["single_question_width"],
                column_gap=layout_params["column_gap"],
                row_gap=layout_params["row_gap"],
                question_type=question_type,
            )
            questions_drawn = self._generate_question_layout(
                img,
                question_layout_params,
                layout_params["coord_offset_x"],
                layout_params["coord_offset_y"],
                current_y,
            )

            # 6. Add QR code if requested
            qr_msg = ""
            if include_qr and qr_content:
                qr_params = QRCodeParams(
                    page_width=page_width,
                    page_height=page_height,
                    bubble_size=bubble_size,
                    margin=layout_params["margin"],
                    qr_content=qr_content,
                    coord_offset_x=layout_params["coord_offset_x"],
                    coord_offset_y=layout_params["coord_offset_y"],
                )
                qr_msg = self._add_qr_code_to_sheet(img, qr_params)

            # 7. Save sheet and template
            sheet_metadata = SheetMetadata(
                num_questions=num_questions,
                question_type=question_type,
                num_columns=num_columns,
                questions_per_column=questions_per_column,
                include_markers=include_markers,
                include_qr=include_qr,
                marker_size=layout_params["marker_size"],
                page_width=page_width,
                qr_msg=qr_msg,
            )
            return self._save_sheet_and_template(img, sheet_metadata)

        except ImportError as e:
            if "qrcode" in str(e):
                return None, None, "Error: qrcode library not installed. Run 'pip install qrcode[pil]'"
            raise e
        except Exception as e:
            import traceback
            return None, None, f"Error generating OMR sheet: {str(e)}\n{traceback.format_exc()}"
