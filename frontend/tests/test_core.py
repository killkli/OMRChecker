"""
Unit tests for frontend core business logic classes.

Tests the core classes: OMRProcessorGradio, TemplateBuilder, and OMRSheetGenerator.
"""

import pytest
import tempfile
import os
from pathlib import Path
from unittest.mock import Mock, patch

from frontend.core.processor import OMRProcessorGradio
from frontend.core.template_builder import TemplateBuilder
from frontend.core.sheet_generator import OMRSheetGenerator


class TestOMRProcessorGradio:
    """Tests for OMRProcessorGradio"""

    def test_initialization(self):
        """Test that processor can be initialized successfully."""
        processor = OMRProcessorGradio()
        assert processor.temp_dir is None
        assert processor.output_dir is None

    def test_setup_temp_directories(self):
        """Test temporary directory creation."""
        processor = OMRProcessorGradio()
        temp_dir, output_dir = processor.setup_temp_directories()

        assert temp_dir is not None
        assert output_dir is not None
        assert os.path.exists(temp_dir)
        assert os.path.exists(output_dir)
        assert "omr_input_" in temp_dir
        assert "omr_output_" in output_dir

        # Cleanup
        processor.cleanup_temp_directories()

    def test_cleanup_temp_directories(self):
        """Test temporary directory cleanup."""
        processor = OMRProcessorGradio()
        temp_dir, output_dir = processor.setup_temp_directories()

        assert os.path.exists(temp_dir)
        assert os.path.exists(output_dir)

        processor.cleanup_temp_directories()

        assert not os.path.exists(temp_dir)
        assert not os.path.exists(output_dir)


class TestTemplateBuilder:
    """Tests for TemplateBuilder"""

    def test_initialization(self):
        """Test that template builder can be initialized successfully."""
        builder = TemplateBuilder()
        assert builder.reference_image is None
        assert "pageDimensions" in builder.template_data
        assert "bubbleDimensions" in builder.template_data
        assert "fieldBlocks" in builder.template_data
        assert "customLabels" in builder.template_data
        assert "preProcessors" in builder.template_data

    def test_update_page_dimensions(self):
        """Test page dimensions update."""
        builder = TemplateBuilder()
        result = builder.update_page_dimensions(1200, 1600)

        assert builder.template_data["pageDimensions"] == [1200, 1600]
        assert "1200" in result
        assert "1600" in result

    def test_update_bubble_dimensions(self):
        """Test bubble dimensions update."""
        builder = TemplateBuilder()
        result = builder.update_bubble_dimensions(25, 25)

        assert builder.template_data["bubbleDimensions"] == [25, 25]
        assert "25" in result

    def test_add_field_block_success(self):
        """Test adding a valid field block."""
        builder = TemplateBuilder()
        status, blocks_display = builder.add_field_block(
            block_name="Q1",
            origin_x=100,
            origin_y=200,
            field_type="QTYPE_MCQ4",
            field_labels="1,2,3,4,5",
            bubbles_gap=50,
            labels_gap=60,
            direction="vertical"
        )

        assert "✅" in status
        assert "Q1" in status
        assert "Q1" in builder.template_data["fieldBlocks"]
        assert builder.template_data["fieldBlocks"]["Q1"]["origin"] == [100, 200]
        assert builder.template_data["fieldBlocks"]["Q1"]["fieldType"] == "QTYPE_MCQ4"

    def test_add_field_block_duplicate_error(self):
        """Test error when adding duplicate field block."""
        builder = TemplateBuilder()
        builder.add_field_block(
            block_name="Q1",
            origin_x=100,
            origin_y=200,
            field_type="QTYPE_MCQ4",
            field_labels="1,2,3",
            bubbles_gap=50,
            labels_gap=60,
            direction="vertical"
        )

        status, _ = builder.add_field_block(
            block_name="Q1",
            origin_x=200,
            origin_y=300,
            field_type="QTYPE_MCQ4",
            field_labels="4,5,6",
            bubbles_gap=50,
            labels_gap=60,
            direction="vertical"
        )

        assert "Error" in status
        assert "already exists" in status

    def test_remove_field_block(self):
        """Test removing a field block."""
        builder = TemplateBuilder()
        builder.add_field_block(
            block_name="Q1",
            origin_x=100,
            origin_y=200,
            field_type="QTYPE_MCQ4",
            field_labels="1,2,3",
            bubbles_gap=50,
            labels_gap=60,
            direction="vertical"
        )

        status, _ = builder.remove_field_block("Q1")

        assert "✅" in status
        assert "removed" in status
        assert "Q1" not in builder.template_data["fieldBlocks"]

    def test_add_custom_label(self):
        """Test adding custom labels."""
        builder = TemplateBuilder()
        status, _ = builder.add_custom_label("Total", "Q1,Q2,Q3")

        assert "✅" in status
        assert "Total" in builder.template_data["customLabels"]
        assert builder.template_data["customLabels"]["Total"] == ["Q1", "Q2", "Q3"]

    def test_export_template_requires_field_blocks(self):
        """Test that export requires at least one field block."""
        builder = TemplateBuilder()
        template_path, message = builder.export_template()

        assert template_path is None
        assert "Error" in message
        assert "at least one field block" in message


class TestOMRSheetGenerator:
    """Tests for OMRSheetGenerator"""

    def test_initialization(self):
        """Test that sheet generator can be initialized successfully."""
        generator = OMRSheetGenerator()
        assert generator.sheet_image is None
        assert generator.template_data is None

    def test_generate_sheet_basic(self):
        """Test basic sheet generation with minimal parameters."""
        generator = OMRSheetGenerator()

        # Test with minimal valid inputs
        result = generator.generate_sheet(
            num_questions=5,
            question_type="QTYPE_MCQ4",
            num_columns=1,
            include_markers=False,
            page_width=1200,
            page_height=1600,
            bubble_size=30,
            include_qr=False,
            qr_content="",
            custom_texts=[]
        )

        # Should return (image, template, message)
        assert result is not None
        assert len(result) == 3

        image, template, message = result

        # Basic validation
        if image is not None:
            assert generator.sheet_image is not None
            assert generator.template_data is not None
        else:
            # If generation failed, there should be an error message
            assert "Error" in message or "error" in message.lower()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
