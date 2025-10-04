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


class OMRProcessorGradio:
    """Wrapper class for OMR processing with Gradio interface."""

    def __init__(self):
        self.temp_dir = None
        self.output_dir = None

    def setup_temp_directories(self):
        """Create temporary directories for processing."""
        self.temp_dir = tempfile.mkdtemp(prefix="omr_input_")
        self.output_dir = tempfile.mkdtemp(prefix="omr_output_")
        return self.temp_dir, self.output_dir

    def cleanup_temp_directories(self):
        """Clean up temporary directories."""
        import shutil

        if self.temp_dir and os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)
        if self.output_dir and os.path.exists(self.output_dir):
            shutil.rmtree(self.output_dir)

    def process_omr_sheets(
        self,
        image_files: List[str],
        template_file: str,
        config_file: Optional[str] = None,
        evaluation_file: Optional[str] = None,
        marker_file: Optional[str] = None,
        auto_align: bool = False,
        set_layout: bool = False,
    ) -> Tuple[str, Optional[str], List[str], str, Optional[str]]:
        """
        Process OMR sheets with uploaded files.

        Args:
            image_files: List of paths to uploaded image files
            template_file: Path to template.json file
            config_file: Optional path to config.json file
            evaluation_file: Optional path to evaluation.json file
            marker_file: Optional path to custom marker image file
            auto_align: Enable auto-alignment
            set_layout: Enable layout visualization mode

        Returns:
            Tuple of (status_message, results_csv_path, marked_images, log_output, qr_data)
        """
        """
        Process OMR sheets with uploaded files.

        Args:
            image_files: List of paths to uploaded image files
            template_file: Path to template.json file
            config_file: Optional path to config.json file
            evaluation_file: Optional path to evaluation.json file
            marker_file: Optional path to custom marker image file
            auto_align: Enable auto-alignment
            set_layout: Enable layout visualization mode

        Returns:
            Tuple of (status_message, results_csv_path, marked_images, log_output)
        """
        try:
            # Setup temporary directories
            input_dir, output_dir = self.setup_temp_directories()

            # Validate inputs
            if not image_files or len(image_files) == 0:
                return "Error: No image files uploaded", None, [], "Please upload at least one OMR image"

            if not template_file:
                return "Error: No template file uploaded", None, [], "Please upload a template.json file"

            # Copy uploaded files to temp directory
            for img_file in image_files:
                if img_file:  # Check if file exists
                    import shutil

                    dest = Path(input_dir) / Path(img_file).name
                    shutil.copy2(img_file, dest)

            # Copy template file
            import shutil

            template_dest = Path(input_dir) / "template.json"
            shutil.copy2(template_file, template_dest)

            # Check if template requires marker and handle marker file
            with open(template_dest, 'r') as f:
                template_data = json.load(f)

            # Check for CropOnMarkers preprocessor
            for preprocessor in template_data.get("preProcessors", []):
                if preprocessor.get("name") == "CropOnMarkers":
                    marker_path = preprocessor.get("options", {}).get("relativePath", "")
                    if marker_path:
                        marker_dest_file = Path(input_dir) / marker_path

                        # Use custom marker if provided by user
                        if marker_file and os.path.exists(marker_file):
                            logger.info(f"Using custom marker file: {marker_file}")
                            import shutil
                            shutil.copy2(marker_file, marker_dest_file)
                            logger.info(f"✅ Copied custom marker to: {marker_dest_file}")
                        # Otherwise generate marker if it doesn't exist
                        elif not marker_dest_file.exists():
                            logger.info(f"Auto-generating missing marker: {marker_path}")
                            # Get page dimensions from template to calculate marker size (1/10 of page width)
                            page_dims = template_data.get("pageDimensions", [config.GENERATOR_PAGE_WIDTH, config.GENERATOR_PAGE_HEIGHT])
                            page_width = page_dims[0]
                            marker_size = int(page_width * config.MARKER_SIZE_RATIO)

                            # Generate concentric circles marker using utility function
                            marker_img = generate_concentric_circle_marker(marker_size, config)

                            cv2.imwrite(str(marker_dest_file), marker_img)
                            logger.info(f"✅ Generated marker at: {marker_dest_file} (size: {marker_size}x{marker_size})")

            # Copy optional files if provided
            if config_file:
                config_dest = Path(input_dir) / "config.json"
                shutil.copy2(config_file, config_dest)

            if evaluation_file:
                eval_dest = Path(input_dir) / "evaluation.json"
                shutil.copy2(evaluation_file, eval_dest)

            # Prepare arguments
            args = {
                "input_paths": [input_dir],
                "output_dir": output_dir,
                "autoAlign": auto_align,
                "setLayout": set_layout,
                "debug": False,  # Disable GUI windows in web environment
            }

            # Process using existing entry point
            logger.info(f"Processing OMR sheets from {input_dir}")
            logger.info(f"Output will be saved to {output_dir}")

            # Call the main processing function
            from src.entry import entry_point

            entry_point(Path(input_dir), args)

            # Collect results
            results_csv = None
            marked_images = []
            status_msg = "Processing completed successfully!"

            # Find results CSV in Results directory
            results_dir = Path(output_dir) / "Results"
            if results_dir.exists():
                csv_files = list(results_dir.glob("*.csv"))
                if csv_files:
                    results_csv = str(csv_files[0])

            # Find marked images
            marked_dir = Path(output_dir) / "CheckedOMRs"
            if marked_dir.exists():
                image_exts = ["*.png", "*.jpg", "*.jpeg"]
                for ext in image_exts:
                    marked_images.extend([str(p) for p in marked_dir.glob(ext)])

            # Generate summary
            if results_csv:
                df = pd.read_csv(results_csv)
                status_msg = f"✅ Successfully processed {len(df)} OMR sheet(s)\n"
                status_msg += f"📁 Results saved to: {results_csv}\n"
                status_msg += f"🖼️  Found {len(marked_images)} marked image(s)"
            else:
                status_msg = "⚠️ Processing completed but no results found. Check logs."

            log_output = f"Input directory: {input_dir}\nOutput directory: {output_dir}\n"
            log_output += f"Processed {len(image_files)} file(s)\n"

            return status_msg, results_csv, marked_images, log_output

        except Exception as e:
            error_msg = f"❌ Error during processing: {str(e)}"
            logger.error(error_msg)
            import traceback

            traceback.print_exc()
            return error_msg, None, [], str(traceback.format_exc())


# Initialize processor
processor = OMRProcessorGradio()


class TemplateBuilder:
    """Template builder for creating OMR templates interactively."""

    def __init__(self):
        self.reference_image = None
        self.template_data = {
            "pageDimensions": [config.DEFAULT_PAGE_WIDTH, config.DEFAULT_PAGE_HEIGHT],
            "bubbleDimensions": [config.DEFAULT_BUBBLE_WIDTH, config.DEFAULT_BUBBLE_HEIGHT],
            "fieldBlocks": {},
            "customLabels": {},
            "preProcessors": [],
        }
        self.field_blocks_list = []

    def load_reference_image(self, image_path: str) -> Tuple[Any, str]:
        """Load reference image and auto-detect dimensions."""
        if not image_path:
            return None, "Please upload a reference image"

        try:
            img = cv2.imread(image_path)
            if img is None:
                return None, "Failed to load image"

            self.reference_image = img
            height, width = img.shape[:2]
            self.template_data["pageDimensions"] = [width, height]

            msg = f"✅ Image loaded successfully!\nDimensions: {width} x {height} pixels"
            return img, msg
        except Exception as e:
            return None, f"Error loading image: {str(e)}"

    def update_page_dimensions(self, width: int, height: int) -> str:
        """Update page dimensions."""
        self.template_data["pageDimensions"] = [int(width), int(height)]
        return f"Page dimensions updated: {width} x {height}"

    def update_bubble_dimensions(self, width: int, height: int) -> str:
        """Update default bubble dimensions."""
        self.template_data["bubbleDimensions"] = [int(width), int(height)]
        return f"Bubble dimensions updated: {width} x {height}"

    def add_field_block(
        self,
        block_name: str,
        origin_x: int,
        origin_y: int,
        field_type: str,
        field_labels: str,
        bubbles_gap: int,
        labels_gap: int,
        direction: str,
        custom_bubble_values: str = "",
        bubble_width: int = None,
        bubble_height: int = None,
    ) -> Tuple[str, str]:
        """Add a field block to the template."""
        try:
            if not block_name:
                return "Error: Block name is required", self._format_field_blocks()

            if block_name in self.template_data["fieldBlocks"]:
                return (
                    f"Error: Block '{block_name}' already exists",
                    self._format_field_blocks(),
                )

            # Parse field labels
            labels_list = [label.strip() for label in field_labels.split(",")]

            # Build field block
            block_data = {
                "origin": [int(origin_x), int(origin_y)],
                "bubblesGap": int(bubbles_gap),
                "labelsGap": int(labels_gap),
                "fieldLabels": labels_list,
                "direction": direction,
            }

            # Add bubble dimensions if custom
            if bubble_width and bubble_height:
                block_data["bubbleDimensions"] = [int(bubble_width), int(bubble_height)]

            # Set field type or custom bubble values
            if field_type != "CUSTOM":
                block_data["fieldType"] = field_type
            else:
                if not custom_bubble_values:
                    return (
                        "Error: Custom bubble values required for QTYPE_CUSTOM type",
                        self._format_field_blocks(),
                    )
                bubble_values_list = [
                    val.strip() for val in custom_bubble_values.split(",")
                ]
                block_data["bubbleValues"] = bubble_values_list

            self.template_data["fieldBlocks"][block_name] = block_data

            return (
                f"✅ Field block '{block_name}' added successfully",
                self._format_field_blocks(),
            )

        except Exception as e:
            return f"Error adding field block: {str(e)}", self._format_field_blocks()

    def remove_field_block(self, block_name: str) -> Tuple[str, str]:
        """Remove a field block from the template."""
        if not block_name:
            return "Error: Block name is required", self._format_field_blocks()

        if block_name in self.template_data["fieldBlocks"]:
            del self.template_data["fieldBlocks"][block_name]
            return (
                f"✅ Field block '{block_name}' removed",
                self._format_field_blocks(),
            )
        else:
            return (
                f"Error: Block '{block_name}' not found",
                self._format_field_blocks(),
            )

    def _format_field_blocks(self) -> str:
        """Format field blocks for display."""
        if not self.template_data["fieldBlocks"]:
            return "No field blocks added yet"

        output = "Current Field Blocks:\n" + "=" * 50 + "\n"
        for name, block in self.template_data["fieldBlocks"].items():
            output += f"\n📌 {name}:\n"
            output += f"  Origin: {block['origin']}\n"
            output += f"  Direction: {block['direction']}\n"
            output += f"  Field Labels: {block['fieldLabels']}\n"
            if "fieldType" in block:
                output += f"  Field Type: {block['fieldType']}\n"
            else:
                output += f"  Bubble Values: {block.get('bubbleValues', [])}\n"
            output += f"  Bubbles Gap: {block['bubblesGap']}\n"
            output += f"  Labels Gap: {block['labelsGap']}\n"
            output += "-" * 50 + "\n"

        return output

    def add_custom_label(self, label_name: str, field_list: str) -> Tuple[str, str]:
        """Add a custom label combining multiple fields."""
        try:
            if not label_name or not field_list:
                return (
                    "Error: Label name and field list are required",
                    self._format_custom_labels(),
                )

            fields = [f.strip() for f in field_list.split(",")]
            self.template_data["customLabels"][label_name] = fields

            return (
                f"✅ Custom label '{label_name}' added",
                self._format_custom_labels(),
            )
        except Exception as e:
            return (
                f"Error adding custom label: {str(e)}",
                self._format_custom_labels(),
            )

    def remove_custom_label(self, label_name: str) -> Tuple[str, str]:
        """Remove a custom label."""
        if label_name in self.template_data["customLabels"]:
            del self.template_data["customLabels"][label_name]
            return (
                f"✅ Custom label '{label_name}' removed",
                self._format_custom_labels(),
            )
        else:
            return (
                f"Error: Label '{label_name}' not found",
                self._format_custom_labels(),
            )

    def _format_custom_labels(self) -> str:
        """Format custom labels for display."""
        if not self.template_data["customLabels"]:
            return "No custom labels added yet"

        output = "Current Custom Labels:\n" + "=" * 50 + "\n"
        for name, fields in self.template_data["customLabels"].items():
            output += f"📝 {name}: {fields}\n"

        return output

    def add_preprocessor(
        self, preprocessor_name: str, options_json: str
    ) -> Tuple[str, str]:
        """Add a preprocessor to the template."""
        try:
            options = json.loads(options_json) if options_json else {}
            preprocessor = {"name": preprocessor_name, "options": options}

            self.template_data["preProcessors"].append(preprocessor)

            return (
                f"✅ Preprocessor '{preprocessor_name}' added",
                self._format_preprocessors(),
            )
        except json.JSONDecodeError:
            return "Error: Invalid JSON in options", self._format_preprocessors()
        except Exception as e:
            return f"Error adding preprocessor: {str(e)}", self._format_preprocessors()

    def remove_preprocessor(self, index: int) -> Tuple[str, str]:
        """Remove a preprocessor by index."""
        try:
            if 0 <= index < len(self.template_data["preProcessors"]):
                removed = self.template_data["preProcessors"].pop(index)
                return (
                    f"✅ Preprocessor '{removed['name']}' removed",
                    self._format_preprocessors(),
                )
            else:
                return "Error: Invalid index", self._format_preprocessors()
        except Exception as e:
            return f"Error: {str(e)}", self._format_preprocessors()

    def _format_preprocessors(self) -> str:
        """Format preprocessors for display."""
        if not self.template_data["preProcessors"]:
            return "No preprocessors added yet"

        output = "Current Preprocessors:\n" + "=" * 50 + "\n"
        for idx, proc in enumerate(self.template_data["preProcessors"]):
            output += f"{idx}. {proc['name']}\n"
            output += f"   Options: {json.dumps(proc['options'], indent=2)}\n"

        return output

    def visualize_template(self) -> Tuple[Any, str]:
        """Visualize the template on the reference image."""
        if self.reference_image is None:
            return None, "Please load a reference image first"

        try:
            # Create a copy of the image
            img = self.reference_image.copy()

            # Draw field blocks
            for block_name, block in self.template_data["fieldBlocks"].items():
                origin = block["origin"]
                bubble_dims = block.get(
                    "bubbleDimensions", self.template_data["bubbleDimensions"]
                )
                direction = block["direction"]
                bubbles_gap = block["bubblesGap"]
                labels_gap = block["labelsGap"]
                field_labels = block["fieldLabels"]

                # Get bubble values
                if "fieldType" in block and block["fieldType"] in FIELD_TYPES:
                    bubble_values = FIELD_TYPES[block["fieldType"]]["bubbleValues"]
                else:
                    bubble_values = block.get("bubbleValues", [])

                # Draw each bubble
                for label_idx, label in enumerate(field_labels):
                    for bubble_idx, value in enumerate(bubble_values):
                        if direction == "vertical":
                            x = origin[0]
                            y = origin[1] + label_idx * labels_gap + bubble_idx * bubbles_gap
                        else:
                            x = origin[0] + bubble_idx * bubbles_gap
                            y = origin[1] + label_idx * labels_gap

                        # Draw rectangle
                        cv2.rectangle(
                            img,
                            (int(x), int(y)),
                            (int(x + bubble_dims[0]), int(y + bubble_dims[1])),
                            config.COLOR_GREEN,
                            config.CV2_BUBBLE_BORDER_THICKNESS,
                        )

                # Add block name label
                cv2.putText(
                    img,
                    block_name,
                    (origin[0], origin[1] - 10),
                    config.CV2_FONT_FACE,
                    config.CV2_BLOCK_NAME_FONT_SCALE,
                    config.COLOR_RED,
                    config.CV2_BLOCK_NAME_FONT_THICKNESS,
                )

            return img, "Template visualized successfully"

        except Exception as e:
            return None, f"Error visualizing template: {str(e)}"

    def export_template(self) -> Tuple[str, str]:
        """Export template as JSON."""
        try:
            # Clean up template data
            template_export = {}

            # Add required fields
            template_export["pageDimensions"] = self.template_data["pageDimensions"]
            template_export["bubbleDimensions"] = self.template_data["bubbleDimensions"]
            template_export["fieldBlocks"] = self.template_data["fieldBlocks"]
            template_export["preProcessors"] = self.template_data["preProcessors"]

            # Add optional fields if present
            if self.template_data["customLabels"]:
                template_export["customLabels"] = self.template_data["customLabels"]

            # Validate that we have at least one field block
            if not template_export["fieldBlocks"]:
                return None, "Error: Template must have at least one field block"

            # Create temporary file
            temp_file = tempfile.NamedTemporaryFile(
                mode="w", suffix=".json", delete=False
            )
            json.dump(template_export, temp_file, indent=2)
            temp_file.close()

            return temp_file.name, "✅ Template exported successfully!"

        except Exception as e:
            return None, f"Error exporting template: {str(e)}"

    def get_coordinates_from_click(self, img, evt: gr.SelectData) -> Tuple[int, int, str]:
        """Get coordinates from image click event."""
        if evt is None:
            return 0, 0, "Click on the image to select coordinates"

        x, y = evt.index[0], evt.index[1]
        return x, y, f"Selected coordinates: ({x}, {y})"


# Initialize template builder
template_builder = TemplateBuilder()


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
            import qrcode  # For QR generation
            from qrcode.image.pil import PilImage
            from PIL import Image, ImageDraw, ImageFont

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
                    inputs=[ref_image_display],
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
