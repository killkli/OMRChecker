import json
import os
import sys
import tempfile
import zipfile
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


class OMRSheetGenerator:
    """Generate blank OMR sheets with automatic template creation."""

    def __init__(self):
        self.sheet_image = None
        self.template_data = None

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
        """
        Generate a blank OMR sheet with automatic layout and QR Code.

        Args:
            num_questions: Total number of questions
            question_type: Type of questions (QTYPE_MCQ4, QTYPE_MCQ5, QTYPE_INT, etc.)
            num_columns: Number of columns (questions horizontally, X-axis)
            include_markers: Whether to include alignment markers
            page_width: Width of the page
            page_height: Height of the page
            bubble_size: Size of bubbles (width and height)
            include_qr: Whether to include QR Code
            qr_content: Content to encode in QR Code
            custom_texts: Optional list of custom text fields with format:
                [{"text": "Exam Title", "x": 100, "y": 50, "font_size": 1.2, "bold": True}, ...]

        Returns:
            Tuple of (generated_image, template_json_path, status_message)
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

            # Calculate marker size first (if markers are included)
            if include_markers:
                marker_size = int(page_width * config.MARKER_SIZE_RATIO)
                # Margin must be larger than marker to avoid overlap
                margin = marker_size + config.MARKER_EXTRA_SPACING
                header_height = marker_size + config.MARKER_HEADER_HEIGHT
            else:
                marker_size = 0
                margin = config.DEFAULT_MARGIN
                header_height = config.DEFAULT_HEADER_HEIGHT

            bubble_gap = bubble_size + config.DEFAULT_BUBBLE_GAP

            # Calculate available width for questions
            available_width = page_width - 2 * margin

            # Calculate question block width based on direction
            if default_direction == "horizontal":
                # For horizontal bubbles: question needs space for all options
                single_question_width = num_options * bubble_gap + config.QUESTION_BLOCK_PADDING_HORIZONTAL
            else:
                # For vertical bubbles: question needs space for one bubble width + label
                single_question_width = bubble_gap + config.QUESTION_BLOCK_PADDING_VERTICAL

            # Calculate spacing between columns
            total_questions_width = num_columns * single_question_width
            if num_columns > 1:
                column_gap = (available_width - total_questions_width) // (num_columns - 1)
                column_gap = max(config.COLUMN_GAP_MIN, min(column_gap, config.COLUMN_GAP_MAX))
            else:
                column_gap = 0

            # Row gap based on question type
            if default_direction == "horizontal":
                row_gap = bubble_size + config.ROW_GAP_HORIZONTAL
            else:
                row_gap = num_options * bubble_gap + config.ROW_GAP_VERTICAL

            # Calculate coordinate system using utility function
            coord_system = calculate_coordinate_system(
                page_width, page_height, include_markers, config
            )
            template_width = coord_system["template_width"]
            template_height = coord_system["template_height"]
            coord_offset_x = coord_system["coord_offset_x"]
            coord_offset_y = coord_system["coord_offset_y"]
            marker_positions = coord_system["marker_positions"]
            marker_size = coord_system["marker_size"]

            # Draw markers on the image if included
            if include_markers and marker_positions:
                for x, y in marker_positions:
                    center_x = x + marker_size // 2
                    center_y = y + marker_size // 2

                    # Generate marker and paste onto image at marker position
                    marker_img = generate_concentric_circle_marker(marker_size, config)
                    img[y:y+marker_size, x:x+marker_size] = marker_img

            # Initialize template data with calculated dimensions
            self.template_data = {
                "pageDimensions": [template_width, template_height],
                "bubbleDimensions": [bubble_size, bubble_size],
                "fieldBlocks": {},
                "customLabels": {},
                "preProcessors": [],
            }

            # Draw custom text fields using PIL (for Chinese support)
            if custom_texts:
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
                img = np.array(pil_img)

                # Calculate the maximum Y position used by custom texts
                max_text_y = calculate_max_text_y(custom_texts, config)

                # Questions start below all custom text + extra spacing
                current_y = max(header_height, max_text_y + config.CUSTOM_TEXT_SPACING)
            else:
                # No custom text, use default header height
                current_y = header_height

            # Calculate questions layout using grid system - COLUMN-FIRST ordering
            # Each column contains questions from top to bottom, then move to next column
            questions_drawn = 0

            # Calculate how many rows per column we need
            questions_per_column = (num_questions + num_columns - 1) // num_columns

            # Iterate column-first (left to right), then row (top to bottom)
            for col in range(num_columns):
                # Reset Y position for each new column
                column_y = current_y

                for row in range(questions_per_column):
                    if questions_drawn >= num_questions:
                        break

                    # Calculate position for this question block
                    # X position: margin + column_index * (question_width + column_gap)
                    block_x = margin + col * (single_question_width + column_gap)

                    # Y position: start_y + row_index * row_gap
                    block_y = column_y

                    # Question metadata
                    block_name = f"Block_Q{questions_drawn + 1}"
                    field_label = f"q{questions_drawn + 1}"

                    # Draw question number
                    cv2.putText(
                        img,
                        f"Q{questions_drawn + 1}",
                        (block_x + config.QUESTION_LABEL_OFFSET_X, block_y + bubble_size // 2 + config.QUESTION_LABEL_OFFSET_Y),
                        config.CV2_FONT_FACE,
                        config.CV2_QUESTION_FONT_SCALE,
                        config.COLOR_BLACK,
                        config.CV2_QUESTION_FONT_THICKNESS,
                    )

                    # Draw bubbles based on direction
                    for opt_idx, opt_value in enumerate(bubble_values):
                        if default_direction == "horizontal":
                            bubble_x = block_x + opt_idx * bubble_gap
                            bubble_y = block_y
                        else:
                            bubble_x = block_x
                            bubble_y = block_y + opt_idx * bubble_gap

                        # Draw circle
                        cv2.circle(
                            img,
                            (bubble_x + bubble_size // 2, bubble_y + bubble_size // 2),
                            bubble_size // 2,
                            config.COLOR_BLACK,
                            config.CV2_BUBBLE_BORDER_THICKNESS,
                        )

                        # Draw option label
                        if default_direction == "horizontal":
                            label_x = bubble_x + bubble_size // 2 + config.BUBBLE_LABEL_OFFSET_X_HORIZONTAL
                            label_y = bubble_y + config.BUBBLE_LABEL_OFFSET_Y_HORIZONTAL
                        else:
                            label_x = bubble_x + bubble_size + config.BUBBLE_LABEL_OFFSET_X_VERTICAL
                            label_y = bubble_y + bubble_size // 2 + config.BUBBLE_LABEL_OFFSET_Y_VERTICAL

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
                        "fieldType": question_type,
                        "fieldLabels": [field_label],
                        "origin": [template_block_x, template_block_y],
                        "bubblesGap": bubble_gap,
                        "labelsGap": bubble_gap,
                    }

                    questions_drawn += 1

                    # Move to next row within this column (Y-axis downward)
                    column_y += row_gap

            # Add QR Code if requested
            msg = ''  # Initialize msg for QR block
            if include_qr and qr_content:
                qr_size = max(config.QR_SIZE_MIN, bubble_size * config.QR_SIZE_BUBBLE_MULTIPLIER)
                qr_x = page_width - margin - qr_size
                qr_y = page_height - margin - qr_size

                # Generate QR Code
                qr = qrcode.QRCode(
                    version=config.QR_VERSION,
                    error_correction=qrcode.constants.ERROR_CORRECT_L,
                    box_size=config.QR_BOX_SIZE,
                    border=config.QR_BORDER_SIZE,
                )
                qr.add_data(qr_content)
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
                template_qr_x = qr_x - coord_offset_x
                template_qr_y = qr_y - coord_offset_y
                self.template_data["fieldBlocks"][qr_block_name] = {
                    "fieldType": "QTYPE_CUSTOM",
                    "fieldLabels": ["qr_id"],
                    "origin": [template_qr_x, template_qr_y],
                    "bubbleValues": [qr_content],  # Placeholder for custom decoding
                    "bubblesGap": 0,
                    "labelsGap": 0,
                    "direction": "horizontal",
                }

                logger.info(f"Generated QR block origin: [template_qr_x, template_qr_y] = [{template_qr_x}, {template_qr_y}]")

                msg += "\nQR Code: Added with content"

            # Add preprocessors if markers are included
            if include_markers:
                # Save marker image using utility function
                marker_temp = tempfile.NamedTemporaryFile(
                    suffix=".jpg", delete=False, mode="wb"
                )
                marker_img = generate_concentric_circle_marker(marker_size, config)
                cv2.imwrite(marker_temp.name, marker_img)
                marker_temp.close()

                # Use CropOnMarkers with wider range for photo-based recognition
                # Range is in percentage: 100 = 1.0x scale
                self.template_data["preProcessors"] = [
                    {
                        "name": "CropOnMarkers",
                        "options": {
                            "relativePath": config.MARKER_FILENAME,
                            "sheetToMarkerWidthRatio": page_width // marker_size,
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
            msg += f"Questions: {num_questions} ({question_type})\n"
            msg += f"Layout: {num_columns} columns × {int(questions_per_column)} rows per column\n"
            if include_markers:
                msg += "Alignment markers: Yes\n"
            if include_qr:
                msg += "QR Code: Added\n"
            msg += f"\n📄 Image saved\n📋 Template JSON generated"

            return sheet_temp.name, template_temp.name, msg

        except ImportError as e:
            if "qrcode" in str(e):
                return None, None, "Error: qrcode library not installed. Run 'pip install qrcode[pil]'"
            raise e

        except Exception as e:
            import traceback

            error_msg = f"Error generating OMR sheet: {str(e)}\n{traceback.format_exc()}"
            return None, None, error_msg
