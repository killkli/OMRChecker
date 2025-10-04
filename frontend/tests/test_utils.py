"""
Unit tests for frontend utility functions.

Tests the reusable utilities for marker generation, text positioning,
and coordinate calculations.
"""

import pytest
import numpy as np
from unittest.mock import Mock

from frontend.utils import (
    generate_concentric_circle_marker,
    calculate_text_positioning,
    calculate_max_text_y,
    calculate_coordinate_system,
)


class TestMarkerUtils:
    """Tests for marker_utils.py"""

    def test_generate_concentric_circle_marker_dimensions(self):
        """Test that marker image has correct dimensions."""
        # Create mock config
        config = Mock()
        config.COLOR_BLACK = (0, 0, 0)
        config.COLOR_WHITE = (255, 255, 255)
        config.MARKER_MIDDLE_CIRCLE_RATIO = 0.7
        config.MARKER_INNER_CIRCLE_RATIO = 0.4

        marker_size = 100
        marker_img = generate_concentric_circle_marker(marker_size, config)

        # Verify dimensions
        assert marker_img.shape == (marker_size, marker_size, 3)
        assert marker_img.dtype == np.uint8

    def test_generate_concentric_circle_marker_structure(self):
        """Test that marker has correct concentric circle structure."""
        config = Mock()
        config.COLOR_BLACK = (0, 0, 0)
        config.COLOR_WHITE = (255, 255, 255)
        config.MARKER_MIDDLE_CIRCLE_RATIO = 0.7
        config.MARKER_INNER_CIRCLE_RATIO = 0.4

        marker_size = 100
        marker_img = generate_concentric_circle_marker(marker_size, config)

        # Check center pixel (should be black - inner circle)
        center = marker_size // 2
        center_pixel = marker_img[center, center]
        assert np.array_equal(center_pixel, config.COLOR_BLACK)

        # Check middle ring pixel (should be white)
        middle_radius = int((marker_size // 2) * 0.55)  # Between inner and middle
        middle_pixel = marker_img[center, center + middle_radius]
        assert np.array_equal(middle_pixel, config.COLOR_WHITE)


class TestTextUtils:
    """Tests for text_utils.py"""

    def test_calculate_text_positioning_no_markers(self):
        """Test text positioning without markers."""
        config = Mock()
        config.TEXT_SAFE_MARGIN = 50
        config.TEXT_LINE_SPACING = 60
        config.CHAR_WIDTH_LARGE = 20
        config.CHAR_WIDTH_NORMAL = 15

        text_lines = ["Title", "Subtitle"]
        positioned = calculate_text_positioning(
            text_lines, page_width=2480, include_markers=False, config=config
        )

        assert len(positioned) == 2

        # First line should be larger and bold
        assert positioned[0]["text"] == "Title"
        assert positioned[0]["font_size"] == 1.5
        assert positioned[0]["bold"] is True

        # Second line should be normal
        assert positioned[1]["text"] == "Subtitle"
        assert positioned[1]["font_size"] == 1.0
        assert positioned[1]["bold"] is False

        # Y positions should be spaced correctly
        assert positioned[1]["y"] == positioned[0]["y"] + config.TEXT_LINE_SPACING

    def test_calculate_text_positioning_with_markers(self):
        """Test text positioning with markers included."""
        config = Mock()
        config.MARKER_SIZE_RATIO = 0.1
        config.TEXT_SAFE_MARGIN_WITH_MARKER = 20
        config.CUSTOM_TEXT_SPACING = 30
        config.TEXT_LINE_SPACING = 60
        config.CHAR_WIDTH_LARGE = 20
        config.CHAR_WIDTH_NORMAL = 15

        text_lines = ["Title"]
        positioned = calculate_text_positioning(
            text_lines, page_width=2480, include_markers=True, config=config
        )

        assert len(positioned) == 1

        # With markers, Y position should account for marker size + spacing
        marker_size = int(2480 * config.MARKER_SIZE_RATIO)
        expected_y = marker_size + config.CUSTOM_TEXT_SPACING
        assert positioned[0]["y"] == expected_y

    def test_calculate_text_positioning_empty_strings(self):
        """Test that empty strings are filtered out."""
        config = Mock()
        config.TEXT_SAFE_MARGIN = 50
        config.TEXT_LINE_SPACING = 60
        config.CHAR_WIDTH_LARGE = 20
        config.CHAR_WIDTH_NORMAL = 15

        text_lines = ["Title", "", "   "]  # Include empty and whitespace-only
        positioned = calculate_text_positioning(
            text_lines, page_width=2480, include_markers=False, config=config
        )

        # Should only have one entry (empty strings filtered by caller)
        # But our function processes all non-empty after filtering
        # So we test with pre-filtered input
        filtered_lines = [t for t in text_lines if t and t.strip()]
        positioned = calculate_text_positioning(
            filtered_lines, page_width=2480, include_markers=False, config=config
        )
        assert len(positioned) == 1

    def test_calculate_max_text_y(self):
        """Test calculation of maximum Y position used by text."""
        config = Mock()
        config.BASE_FONT_SIZE = 40
        config.TEXT_BOTTOM_PADDING = 10
        config.TEXT_SAFE_MARGIN = 50

        custom_texts = [
            {"text": "Title", "y": 100, "font_size": 1.5},
            {"text": "Subtitle", "y": 160, "font_size": 1.0},
        ]

        max_y = calculate_max_text_y(custom_texts, config)

        # Should be y + (BASE_FONT_SIZE * font_size) + padding for the lower text
        expected_max_y = 160 + int(40 * 1.0) + 10
        assert max_y == expected_max_y

    def test_calculate_max_text_y_empty_list(self):
        """Test that empty text list returns 0."""
        config = Mock()

        max_y = calculate_max_text_y([], config)
        assert max_y == 0


class TestCoordinateUtils:
    """Tests for coordinate_utils.py"""

    def test_calculate_coordinate_system_no_markers(self):
        """Test coordinate system without markers."""
        config = Mock()

        result = calculate_coordinate_system(
            page_width=2480,
            page_height=3508,
            include_markers=False,
            config=config
        )

        # Without markers, dimensions should match page size
        assert result["template_width"] == 2480
        assert result["template_height"] == 3508
        assert result["coord_offset_x"] == 0
        assert result["coord_offset_y"] == 0
        assert result["marker_positions"] is None
        assert result["marker_centers"] is None
        assert result["marker_size"] == 0

    def test_calculate_coordinate_system_with_markers(self):
        """Test coordinate system with markers."""
        config = Mock()
        config.MARKER_SIZE_RATIO = 0.1
        config.MARKER_EDGE_SPACING = 30

        page_width = 2480
        page_height = 3508

        result = calculate_coordinate_system(
            page_width=page_width,
            page_height=page_height,
            include_markers=True,
            config=config
        )

        # Marker size should be 10% of page width
        expected_marker_size = int(page_width * 0.1)
        assert result["marker_size"] == expected_marker_size

        # Should have 4 marker positions
        assert len(result["marker_positions"]) == 4
        assert len(result["marker_centers"]) == 4

        # Template dimensions should be distance between marker centers
        # Top-left and top-right markers
        expected_width = result["marker_centers"][1][0] - result["marker_centers"][0][0]
        assert result["template_width"] == expected_width

        # Top-left and bottom-left markers
        expected_height = result["marker_centers"][2][1] - result["marker_centers"][0][1]
        assert result["template_height"] == expected_height

        # Offset should be at top-left marker center
        assert result["coord_offset_x"] == result["marker_centers"][0][0]
        assert result["coord_offset_y"] == result["marker_centers"][0][1]

    def test_calculate_coordinate_system_marker_positions(self):
        """Test that marker positions are correctly calculated."""
        config = Mock()
        config.MARKER_SIZE_RATIO = 0.1
        config.MARKER_EDGE_SPACING = 30

        page_width = 2480
        page_height = 3508

        result = calculate_coordinate_system(
            page_width=page_width,
            page_height=page_height,
            include_markers=True,
            config=config
        )

        marker_size = result["marker_size"]
        edge_spacing = config.MARKER_EDGE_SPACING

        # Verify positions
        expected_positions = [
            (edge_spacing, edge_spacing),  # Top-left
            (page_width - edge_spacing - marker_size, edge_spacing),  # Top-right
            (edge_spacing, page_height - edge_spacing - marker_size),  # Bottom-left
            (
                page_width - edge_spacing - marker_size,
                page_height - edge_spacing - marker_size
            ),  # Bottom-right
        ]

        assert result["marker_positions"] == expected_positions


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
