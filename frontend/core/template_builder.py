import json
import os
import tempfile
from pathlib import Path
from typing import Any, Tuple

import cv2
import gradio as gr

from src.constants import FIELD_TYPES
from src.logger import logger
from frontend.config.constants import config


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

    def get_coordinates_from_click(self, evt: gr.SelectData) -> Tuple[int, int, str]:
        """Get coordinates from image click event.

        Args:
            evt: Gradio SelectData event containing click coordinates

        Returns:
            Tuple of (x, y, status_message)
        """
        x, y = evt.index[0], evt.index[1]
        return x, y, f"Selected coordinates: ({x}, {y})"
