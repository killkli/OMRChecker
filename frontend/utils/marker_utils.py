"""
Marker generation utilities for OMR sheets.

This module provides functions to generate alignment markers (concentric circles)
used for automatic sheet alignment and cropping.
"""

import cv2
import numpy as np
from typing import Any


def generate_concentric_circle_marker(marker_size: int, config: Any) -> np.ndarray:
    """
    Generate a concentric circle marker image (black-white-black circles).

    This marker is used for automatic alignment and cropping of OMR sheets.
    The marker consists of three concentric circles:
    - Outer circle (black, 100% of marker radius)
    - Middle circle (white, 70% of marker radius by default)
    - Inner circle (black, 40% of marker radius by default)

    Args:
        marker_size: Size of the marker in pixels (width and height)
        config: Configuration object containing marker ratios and colors

    Returns:
        np.ndarray: BGR image array of shape (marker_size, marker_size, 3)

    Example:
        >>> marker_img = generate_concentric_circle_marker(100, config)
        >>> cv2.imwrite('marker.jpg', marker_img)
    """
    # Create white background image
    marker_img = np.ones((marker_size, marker_size, 3), dtype=np.uint8) * 255

    # Calculate center point
    center = marker_size // 2

    # Draw outer circle (black)
    cv2.circle(
        marker_img,
        (center, center),
        marker_size // 2,
        config.COLOR_BLACK,
        -1  # filled
    )

    # Draw middle circle (white)
    cv2.circle(
        marker_img,
        (center, center),
        int(marker_size // 2 * config.MARKER_MIDDLE_CIRCLE_RATIO),
        config.COLOR_WHITE,
        -1  # filled
    )

    # Draw inner circle (black)
    cv2.circle(
        marker_img,
        (center, center),
        int(marker_size // 2 * config.MARKER_INNER_CIRCLE_RATIO),
        config.COLOR_BLACK,
        -1  # filled
    )

    return marker_img
