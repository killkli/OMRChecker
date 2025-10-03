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
        auto_align: bool = False,
        set_layout: bool = False,
    ) -> Tuple[str, Optional[str], List[str], str]:
        """
        Process OMR sheets with uploaded files.

        Args:
            image_files: List of paths to uploaded image files
            template_file: Path to template.json file
            config_file: Optional path to config.json file
            evaluation_file: Optional path to evaluation.json file
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

            # Check if template requires marker and generate if missing
            with open(template_dest, 'r') as f:
                template_data = json.load(f)

            # Check for CropOnMarkers preprocessor
            for preprocessor in template_data.get("preProcessors", []):
                if preprocessor.get("name") == "CropOnMarkers":
                    marker_path = preprocessor.get("options", {}).get("relativePath", "")
                    if marker_path:
                        marker_file = Path(input_dir) / marker_path
                        # Generate marker if it doesn't exist
                        if not marker_file.exists():
                            logger.info(f"Auto-generating missing marker: {marker_path}")
                            # Generate standard marker (50x50 with white center)
                            marker_size = 50
                            marker_img = np.ones((marker_size, marker_size, 3), dtype=np.uint8) * 255
                            cv2.rectangle(marker_img, (0, 0), (marker_size, marker_size), (0, 0, 0), -1)
                            cv2.rectangle(
                                marker_img,
                                (10, 10),
                                (marker_size - 10, marker_size - 10),
                                (255, 255, 255),
                                -1,
                            )
                            cv2.imwrite(str(marker_file), marker_img)
                            logger.info(f"✅ Generated marker at: {marker_file}")

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

            # Find results CSV
            results_dir = Path(output_dir) / "CheckedOMRs"
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
            "pageDimensions": [1846, 1500],
            "bubbleDimensions": [40, 40],
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
                        "Error: Custom bubble values required for CUSTOM type",
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
                            (0, 255, 0),
                            2,
                        )

                # Add block name label
                cv2.putText(
                    img,
                    block_name,
                    (origin[0], origin[1] - 10),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.6,
                    (255, 0, 0),
                    2,
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
        include_roll_number: bool,
        roll_digits: int,
        include_markers: bool,
        page_width: int,
        page_height: int,
        bubble_size: int,
    ) -> Tuple[Any, str, str]:
        """
        Generate a blank OMR sheet with automatic layout.

        Args:
            num_questions: Total number of questions
            question_type: Type of questions (QTYPE_MCQ4, QTYPE_MCQ5, QTYPE_INT, etc.)
            num_columns: Number of columns (questions horizontally, X-axis)
            include_roll_number: Whether to include roll number field
            roll_digits: Number of digits in roll number
            include_markers: Whether to include alignment markers
            page_width: Width of the page
            page_height: Height of the page
            bubble_size: Size of bubbles (width and height)

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

            # Calculate layout parameters with optimized spacing
            margin = 80
            header_height = 120
            bubble_gap = bubble_size + 8

            # Calculate available width for questions
            available_width = page_width - 2 * margin

            # Calculate question block width based on direction
            if default_direction == "horizontal":
                # For horizontal bubbles: question needs space for all options
                single_question_width = num_options * bubble_gap + 40  # 40 for Q label
            else:
                # For vertical bubbles: question needs space for one bubble width + label
                single_question_width = bubble_gap + 60  # 60 for Q label and value labels

            # Calculate spacing between columns
            total_questions_width = num_columns * single_question_width
            if num_columns > 1:
                column_gap = (available_width - total_questions_width) // (num_columns - 1)
                column_gap = max(20, min(column_gap, 50))  # Clamp between 20-50
            else:
                column_gap = 0

            # Row gap based on question type
            if default_direction == "horizontal":
                row_gap = bubble_size + 30
            else:
                row_gap = num_options * bubble_gap + 40

            # Calculate coordinate space based on whether markers are used
            if include_markers:
                marker_size = 50
                # Markers will be placed at page corners
                marker_positions = [
                    (margin // 2, margin // 2),
                    (page_width - margin // 2 - marker_size, margin // 2),
                    (margin // 2, page_height - margin // 2 - marker_size),
                    (
                        page_width - margin // 2 - marker_size,
                        page_height - margin // 2 - marker_size,
                    ),
                ]

                # Calculate marker centers
                marker_centers = [
                    (x + marker_size // 2, y + marker_size // 2)
                    for x, y in marker_positions
                ]

                # pageDimensions = distance between marker centers
                # This ensures no scaling after four_point_transform
                template_width = marker_centers[1][0] - marker_centers[0][0]
                template_height = marker_centers[2][1] - marker_centers[0][1]

                # Coordinate offset: all content coordinates are relative to top-left marker center
                coord_offset_x = marker_centers[0][0]
                coord_offset_y = marker_centers[0][1]

                # Draw markers on the image
                for x, y in marker_positions:
                    cv2.rectangle(
                        img,
                        (x, y),
                        (x + marker_size, y + marker_size),
                        (0, 0, 0),
                        -1,
                    )
                    cv2.rectangle(
                        img,
                        (x + 10, y + 10),
                        (x + marker_size - 10, y + marker_size - 10),
                        (255, 255, 255),
                        -1,
                    )
            else:
                # No markers: pageDimensions = full page size, no offset
                template_width = page_width
                template_height = page_height
                coord_offset_x = 0
                coord_offset_y = 0

            # Initialize template data with calculated dimensions
            self.template_data = {
                "pageDimensions": [template_width, template_height],
                "bubbleDimensions": [bubble_size, bubble_size],
                "fieldBlocks": {},
                "customLabels": {},
                "preProcessors": [],
            }

            current_y = header_height

            # Add roll number field if requested
            if include_roll_number:
                roll_start_x = margin
                roll_start_y = current_y

                # Draw roll number label
                cv2.putText(
                    img,
                    "Roll Number:",
                    (roll_start_x, roll_start_y - 10),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.8,
                    (0, 0, 0),
                    2,
                )

                # Draw roll number bubbles
                for digit_idx in range(roll_digits):
                    digit_x = roll_start_x + digit_idx * (bubble_size + 20)

                    # Draw digit label
                    cv2.putText(
                        img,
                        str(digit_idx + 1),
                        (digit_x + bubble_size // 2 - 5, roll_start_y - 5),
                        cv2.FONT_HERSHEY_SIMPLEX,
                        0.5,
                        (0, 0, 0),
                        1,
                    )

                    # Draw bubbles for each digit (0-9)
                    for val_idx in range(10):
                        bubble_y = roll_start_y + val_idx * bubble_gap
                        cv2.circle(
                            img,
                            (digit_x + bubble_size // 2, bubble_y + bubble_size // 2),
                            bubble_size // 2,
                            (0, 0, 0),
                            2,
                        )

                        # Draw value label
                        cv2.putText(
                            img,
                            str(val_idx),
                            (digit_x - 25, bubble_y + bubble_size // 2 + 5),
                            cv2.FONT_HERSHEY_SIMPLEX,
                            0.5,
                            (0, 0, 0),
                            1,
                        )

                # Add to template using range notation
                if roll_digits > 1:
                    field_labels_range = f"roll1..{roll_digits}"
                else:
                    field_labels_range = "roll1"

                # Template coordinates are relative to pageDimensions coordinate space
                template_roll_x = roll_start_x - coord_offset_x
                template_roll_y = roll_start_y - coord_offset_y

                self.template_data["fieldBlocks"]["Roll"] = {
                    "fieldType": "QTYPE_INT",
                    "fieldLabels": [field_labels_range],
                    "origin": [template_roll_x, template_roll_y],
                    "bubblesGap": bubble_gap,
                    "labelsGap": bubble_size + 20,
                }

                # Add custom label for roll number (using range notation)
                self.template_data["customLabels"]["Roll"] = [field_labels_range]

                current_y = roll_start_y + 10 * bubble_gap + 50

            # Calculate questions layout using grid system
            questions_drawn = 0
            row_idx = 0

            # Calculate how many rows we need
            num_rows = (num_questions + num_columns - 1) // num_columns

            for row in range(num_rows):
                for col in range(num_columns):
                    if questions_drawn >= num_questions:
                        break

                    # Calculate position for this question block
                    # X position: margin + column_index * (question_width + column_gap)
                    block_x = margin + col * (single_question_width + column_gap)

                    # Y position: current_y for this row
                    block_y = current_y

                    # Question metadata
                    block_name = f"Block_Q{questions_drawn + 1}"
                    field_label = f"q{questions_drawn + 1}"

                    # Draw question number
                    cv2.putText(
                        img,
                        f"Q{questions_drawn + 1}",
                        (block_x - 35, block_y + bubble_size // 2 + 5),
                        cv2.FONT_HERSHEY_SIMPLEX,
                        0.55,
                        (0, 0, 0),
                        2,
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
                            (0, 0, 0),
                            2,
                        )

                        # Draw option label
                        if default_direction == "horizontal":
                            label_x = bubble_x + bubble_size // 2 - 8
                            label_y = bubble_y - 10
                        else:
                            label_x = bubble_x + bubble_size + 10
                            label_y = bubble_y + bubble_size // 2 + 5

                        cv2.putText(
                            img,
                            str(opt_value),
                            (label_x, label_y),
                            cv2.FONT_HERSHEY_SIMPLEX,
                            0.5,
                            (0, 0, 0),
                            1,
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

                # Move to next row (Y-axis downward)
                current_y += row_gap

            # Add preprocessors if markers are included
            if include_markers:
                # Save marker image
                marker_temp = tempfile.NamedTemporaryFile(
                    suffix=".jpg", delete=False, mode="wb"
                )
                marker_img = np.ones((marker_size, marker_size, 3), dtype=np.uint8) * 255
                cv2.rectangle(marker_img, (0, 0), (marker_size, marker_size), (0, 0, 0), -1)
                cv2.rectangle(
                    marker_img,
                    (10, 10),
                    (marker_size - 10, marker_size - 10),
                    (255, 255, 255),
                    -1,
                )
                cv2.imwrite(marker_temp.name, marker_img)
                marker_temp.close()

                # Use CropOnMarkers with tight rescale range to minimize scaling
                # Range is in percentage: 100 = 1.0x scale
                self.template_data["preProcessors"] = [
                    {
                        "name": "CropOnMarkers",
                        "options": {
                            "relativePath": "omr_marker.jpg",
                            "sheetToMarkerWidthRatio": page_width // marker_size,
                            # Tight range around 100% for minimal scaling (99-101%)
                            "marker_rescale_range": [99, 101],
                            "marker_rescale_steps": 2,
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
            msg += f"Layout: {num_columns} columns × {num_rows} rows\n"
            if include_roll_number:
                msg += f"Roll Number: {roll_digits} digits\n"
            if include_markers:
                msg += "Alignment markers: Yes\n"
            msg += f"\n📄 Image saved\n📋 Template JSON generated"

            return sheet_temp.name, template_temp.name, msg

        except Exception as e:
            import traceback

            error_msg = f"Error generating OMR sheet: {str(e)}\n{traceback.format_exc()}"
            return None, None, error_msg


# Initialize sheet generator
sheet_generator = OMRSheetGenerator()


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
            with gr.Tab("📋 Process OMR Sheets"):
                gr.Markdown(
                    """
                ### Quick Start:
                1. Upload OMR image(s) (PNG/JPG)
                2. Upload template.json (required)
                3. Optional: Upload config.json and evaluation.json
                4. Click "Process OMR Sheets"
                """
                )

                with gr.Row():
                    with gr.Column(scale=1):
                        gr.Markdown("### 📤 Upload Files")

                        image_input = gr.File(
                            label="OMR Images",
                            file_count="multiple",
                            file_types=["image"],
                            type="filepath",
                        )

                        template_input = gr.File(
                            label="Template File (template.json)",
                            file_count="single",
                            file_types=[".json"],
                            type="filepath",
                        )

                        with gr.Accordion("Optional Configuration Files", open=False):
                            config_input = gr.File(
                                label="Config File (config.json)",
                                file_count="single",
                                file_types=[".json"],
                                type="filepath",
                            )

                            evaluation_input = gr.File(
                                label="Evaluation File (evaluation.json)",
                                file_count="single",
                                file_types=[".json"],
                                type="filepath",
                            )

                        with gr.Accordion("Processing Options", open=False):
                            auto_align_check = gr.Checkbox(
                                label="Enable Auto-Alignment",
                                value=False,
                                info="Experimental: Automatically align slightly misaligned scans",
                            )

                            set_layout_check = gr.Checkbox(
                                label="Set Layout Mode",
                                value=False,
                                info="Visualize template layout instead of processing",
                            )

                        process_btn = gr.Button(
                            "🚀 Process OMR Sheets", variant="primary", size="lg"
                        )

                    with gr.Column(scale=2):
                        gr.Markdown("### 📊 Results")

                        status_output = gr.Textbox(
                            label="Status",
                            lines=4,
                            interactive=False,
                        )

                        results_csv_output = gr.File(
                            label="Results CSV",
                            interactive=False,
                        )

                        marked_images_gallery = gr.Gallery(
                            label="Marked OMR Images",
                            show_label=True,
                            columns=2,
                            height="auto",
                        )

                        with gr.Accordion("Processing Log", open=False):
                            log_output = gr.Textbox(
                                label="Detailed Log",
                                lines=10,
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
            with gr.Tab("🔧 Template Builder"):
                gr.Markdown(
                    """
                ### Create a New Template Interactively

                1. **Upload Reference Image**: Upload a sample OMR sheet image
                2. **Configure Settings**: Set page and bubble dimensions
                3. **Add Field Blocks**: Click on image to get coordinates, then add field blocks
                4. **Preview**: Visualize your template on the image
                5. **Export**: Download your template.json file
                """
                )

                with gr.Row():
                    with gr.Column(scale=1):
                        # Step 1: Upload Reference Image
                        gr.Markdown("### 1️⃣ Reference Image")
                        ref_image_input = gr.File(
                            label="Upload Reference OMR Image",
                            file_count="single",
                            file_types=["image"],
                            type="filepath",
                        )
                        load_image_btn = gr.Button("Load Image", variant="secondary")
                        image_status = gr.Textbox(label="Status", lines=2, interactive=False)

                        # Step 2: Basic Settings
                        gr.Markdown("### 2️⃣ Basic Settings")
                        with gr.Row():
                            page_width = gr.Number(label="Page Width", value=1846)
                            page_height = gr.Number(label="Page Height", value=1500)
                        update_page_btn = gr.Button("Update Page Dimensions", size="sm")

                        with gr.Row():
                            bubble_width = gr.Number(label="Default Bubble Width", value=40)
                            bubble_height = gr.Number(label="Default Bubble Height", value=40)
                        update_bubble_btn = gr.Button("Update Bubble Dimensions", size="sm")

                        dimension_status = gr.Textbox(label="Dimension Status", lines=1, interactive=False)

                    with gr.Column(scale=2):
                        # Image display with click coordinates
                        gr.Markdown("### 📍 Click on Image to Get Coordinates")
                        ref_image_display = gr.Image(
                            label="Reference Image (Click to select coordinates)",
                            interactive=False,
                        )
                        click_coords_output = gr.Textbox(
                            label="Selected Coordinates",
                            value="Click on image to select coordinates",
                            interactive=False,
                        )
                        with gr.Row():
                            selected_x = gr.Number(label="X Coordinate", value=0)
                            selected_y = gr.Number(label="Y Coordinate", value=0)

                # Step 3: Add Field Blocks
                with gr.Accordion("3️⃣ Add Field Blocks", open=True):
                    with gr.Row():
                        with gr.Column():
                            block_name_input = gr.Textbox(label="Block Name", placeholder="e.g., MCQ_Block_Q1")

                            with gr.Row():
                                origin_x_input = gr.Number(label="Origin X", value=100)
                                origin_y_input = gr.Number(label="Origin Y", value=100)

                            use_selected_coords_btn = gr.Button("📍 Use Selected Coordinates", size="sm")

                            field_type_input = gr.Dropdown(
                                label="Field Type",
                                choices=["QTYPE_INT", "QTYPE_INT_FROM_1", "QTYPE_MCQ4", "QTYPE_MCQ5", "CUSTOM"],
                                value="QTYPE_MCQ4",
                            )

                            custom_bubble_values_input = gr.Textbox(
                                label="Custom Bubble Values (comma-separated, for CUSTOM type)",
                                placeholder="e.g., A,B,C,D",
                                visible=False,
                            )

                        with gr.Column():
                            field_labels_input = gr.Textbox(
                                label="Field Labels (comma-separated)",
                                placeholder="e.g., q1,q2,q3 or q1..10",
                            )

                            direction_input = gr.Radio(
                                label="Direction",
                                choices=["horizontal", "vertical"],
                                value="horizontal",
                            )

                            with gr.Row():
                                bubbles_gap_input = gr.Number(label="Bubbles Gap", value=50)
                                labels_gap_input = gr.Number(label="Labels Gap", value=50)

                            with gr.Row():
                                custom_bubble_w = gr.Number(label="Custom Bubble Width (optional)", value=None)
                                custom_bubble_h = gr.Number(label="Custom Bubble Height (optional)", value=None)

                    with gr.Row():
                        add_block_btn = gr.Button("➕ Add Field Block", variant="primary")
                        remove_block_name = gr.Textbox(label="Block Name to Remove", placeholder="Enter block name")
                        remove_block_btn = gr.Button("🗑️ Remove Field Block", variant="stop")

                    field_blocks_display = gr.Textbox(
                        label="Current Field Blocks",
                        lines=10,
                        value="No field blocks added yet",
                        interactive=False,
                    )

                # Step 4: Custom Labels (Optional)
                with gr.Accordion("4️⃣ Custom Labels (Optional)", open=False):
                    with gr.Row():
                        custom_label_name = gr.Textbox(label="Label Name", placeholder="e.g., Roll")
                        custom_label_fields = gr.Textbox(
                            label="Field List (comma-separated)",
                            placeholder="e.g., Medium,roll1..9",
                        )

                    with gr.Row():
                        add_custom_label_btn = gr.Button("➕ Add Custom Label", variant="primary")
                        remove_custom_label_name = gr.Textbox(label="Label Name to Remove")
                        remove_custom_label_btn = gr.Button("🗑️ Remove Custom Label", variant="stop")

                    custom_labels_display = gr.Textbox(
                        label="Current Custom Labels",
                        lines=5,
                        value="No custom labels added yet",
                        interactive=False,
                    )

                # Step 5: Preprocessors (Optional)
                with gr.Accordion("5️⃣ Preprocessors (Optional)", open=False):
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
            with gr.Tab("📄 Generate Blank Sheet"):
                gr.Markdown(
                    """
                ### Automatically Generate Blank OMR Sheet

                Simply specify your requirements, and the system will generate:
                1. 📄 A blank OMR answer sheet image (ready to print)
                2. 📋 The corresponding template.json file

                **Perfect for quickly creating custom OMR sheets!**
                """
                )

                with gr.Row():
                    with gr.Column(scale=1):
                        gr.Markdown("### ⚙️ Sheet Configuration")

                        # Basic settings
                        with gr.Group():
                            gr.Markdown("#### Questions Setup")
                            gen_num_questions = gr.Number(
                                label="Number of Questions",
                                value=20,
                                minimum=1,
                                maximum=200,
                                step=1,
                            )

                            gen_question_type = gr.Dropdown(
                                label="Question Type",
                                choices=["QTYPE_MCQ4", "QTYPE_MCQ5", "QTYPE_INT", "QTYPE_INT_FROM_1"],
                                value="QTYPE_MCQ4",
                                info="MCQ4=A/B/C/D, MCQ5=A/B/C/D/E, INT=0-9 digits",
                            )

                            gen_num_columns = gr.Number(
                                label="Number of Columns (Horizontal)",
                                value=4,
                                minimum=1,
                                maximum=10,
                                step=1,
                                info="How many questions to place horizontally (X-axis, left to right)",
                            )

                        # Roll number settings
                        with gr.Group():
                            gr.Markdown("#### Roll Number (Optional)")
                            gen_include_roll = gr.Checkbox(
                                label="Include Roll Number Field",
                                value=True,
                            )

                            gen_roll_digits = gr.Number(
                                label="Number of Digits",
                                value=9,
                                minimum=1,
                                maximum=20,
                                step=1,
                                visible=True,
                            )

                        # Alignment markers
                        with gr.Group():
                            gr.Markdown("#### Alignment Markers")
                            gen_include_markers = gr.Checkbox(
                                label="Include Alignment Markers",
                                value=True,
                                info="✓ Recommended for print & scan workflow. Corrects rotation/skew when photographed.",
                            )

                        # Page settings
                        with gr.Accordion("Advanced Settings", open=False):
                            with gr.Row():
                                gen_page_width = gr.Number(
                                    label="Page Width (pixels)",
                                    value=2100,
                                    minimum=800,
                                    maximum=4000,
                                )
                                gen_page_height = gr.Number(
                                    label="Page Height (pixels)",
                                    value=2970,
                                    minimum=800,
                                    maximum=5000,
                                )

                            gen_bubble_size = gr.Number(
                                label="Bubble Size (pixels)",
                                value=40,
                                minimum=20,
                                maximum=100,
                            )

                        # Generate button
                        gen_generate_btn = gr.Button(
                            "✨ Generate Blank Sheet",
                            variant="primary",
                            size="lg",
                        )

                    with gr.Column(scale=2):
                        gr.Markdown("### 📊 Generated Output")

                        gen_status = gr.Textbox(
                            label="Generation Status",
                            lines=8,
                            interactive=False,
                        )

                        gen_sheet_image = gr.Image(
                            label="Generated Blank Sheet (Preview)",
                            type="filepath",
                        )

                        with gr.Row():
                            gen_sheet_file = gr.File(
                                label="Download Blank Sheet Image",
                            )
                            gen_template_file = gr.File(
                                label="Download Template JSON",
                            )

                        gr.Markdown(
                            """
                        ### 💡 Next Steps

                        1. **Download both files** (sheet image and template)
                        2. **Print the blank sheet** or use it digitally
                        3. Fill in answers on the sheet (or simulate filled answers)
                        4. Use the "Process OMR Sheets" tab with:
                           - Your filled OMR images
                           - The generated template.json
                        """
                        )

                # === Event Handlers for Sheet Generator ===

                # Toggle roll digits visibility based on checkbox
                def toggle_roll_digits(include_roll):
                    return gr.update(visible=include_roll)

                gen_include_roll.change(
                    fn=toggle_roll_digits,
                    inputs=[gen_include_roll],
                    outputs=[gen_roll_digits],
                )

                # Generate sheet button click
                def generate_sheet_wrapper(
                    num_q, q_type, num_cols, inc_roll, roll_dig, inc_mark, pw, ph, bs
                ):
                    sheet_path, template_path, msg = sheet_generator.generate_sheet(
                        num_questions=int(num_q),
                        question_type=q_type,
                        num_columns=int(num_cols),
                        include_roll_number=inc_roll,
                        roll_digits=int(roll_dig) if inc_roll else 0,
                        include_markers=inc_mark,
                        page_width=int(pw),
                        page_height=int(ph),
                        bubble_size=int(bs),
                    )
                    return sheet_path, sheet_path, template_path, msg

                gen_generate_btn.click(
                    fn=generate_sheet_wrapper,
                    inputs=[
                        gen_num_questions,
                        gen_question_type,
                        gen_num_columns,
                        gen_include_roll,
                        gen_roll_digits,
                        gen_include_markers,
                        gen_page_width,
                        gen_page_height,
                        gen_bubble_size,
                    ],
                    outputs=[
                        gen_sheet_image,
                        gen_sheet_file,
                        gen_template_file,
                        gen_status,
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
        server_name="0.0.0.0",
        server_port=7860,
        share=False,
        show_error=True,
    )
