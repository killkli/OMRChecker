"""
Frontend utility modules for OMR processing.

This package contains reusable utilities for marker generation, text positioning,
and coordinate calculations.
"""

from .marker_utils import generate_concentric_circle_marker
from .text_utils import calculate_text_positioning, calculate_max_text_y
from .coordinate_utils import calculate_coordinate_system

__all__ = [
    'generate_concentric_circle_marker',
    'calculate_text_positioning',
    'calculate_max_text_y',
    'calculate_coordinate_system',
]
