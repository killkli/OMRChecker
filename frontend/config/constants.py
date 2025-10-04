"""
Frontend Configuration Constants

Centralized configuration for all frontend hardcoded values including
page dimensions, bubble sizes, margins, spacing, fonts, and marker settings.

Author: Generated with Claude Code
"""
from pathlib import Path
from typing import List, Tuple


class FrontendConfig:
    """Centralized configuration for OMR frontend application."""

    # ==================== Page Dimensions ====================
    # Default page dimensions for template builder
    DEFAULT_PAGE_WIDTH: int = 1846
    DEFAULT_PAGE_HEIGHT: int = 1500

    # Default page dimensions for sheet generator (A4 size at ~300 DPI)
    GENERATOR_PAGE_WIDTH: int = 2100
    GENERATOR_PAGE_HEIGHT: int = 2970

    # ==================== Bubble Dimensions ====================
    # Default bubble dimensions for template builder
    DEFAULT_BUBBLE_WIDTH: int = 40
    DEFAULT_BUBBLE_HEIGHT: int = 40

    # Default bubble size for sheet generator
    GENERATOR_BUBBLE_SIZE: int = 60

    # Alternative small bubble size
    SMALL_BUBBLE_SIZE: int = 40

    # ==================== Margins and Spacing ====================
    # Margins for sheet layout
    DEFAULT_MARGIN: int = 80
    MARKER_EXTRA_SPACING: int = 30  # Extra spacing when markers are present

    # Header height (space reserved for title/text at top)
    DEFAULT_HEADER_HEIGHT: int = 120
    MARKER_HEADER_HEIGHT: int = 40  # Additional height when markers present

    # Bubble gaps
    DEFAULT_BUBBLE_GAP: int = 8  # Gap between bubbles
    SMALL_BUBBLE_GAP: int = 50  # Gap for template builder

    # Row and column spacing
    ROW_GAP_HORIZONTAL: int = 30  # Row gap for horizontal bubble layout
    COLUMN_GAP_MIN: int = 20  # Minimum gap between columns
    COLUMN_GAP_MAX: int = 50  # Maximum gap between columns

    # Custom text spacing
    CUSTOM_TEXT_SPACING: int = 60  # Spacing below custom text before questions start
    TEXT_LINE_SPACING: int = 50  # Spacing between text lines

    # ==================== Marker Settings ====================
    # Marker size calculation
    MARKER_SIZE_RATIO: float = 0.1  # Marker size as ratio of page width (10%)

    # Marker positioning
    MARKER_EDGE_SPACING: int = 20  # Distance from page edge to marker

    # Marker rescale settings (for CropOnMarkers preprocessor)
    MARKER_RESCALE_RANGE_MIN: int = 60  # Minimum rescale percentage
    MARKER_RESCALE_RANGE_MAX: int = 130  # Maximum rescale percentage
    MARKER_RESCALE_STEPS: int = 15  # Number of rescale steps
    MARKER_MIN_MATCHING_THRESHOLD: float = 0.2  # Minimum matching threshold
    MARKER_MAX_MATCHING_VARIATION: float = 0.5  # Maximum matching variation

    # Concentric circle marker ratios
    MARKER_MIDDLE_CIRCLE_RATIO: float = 0.7  # Middle circle size ratio
    MARKER_INNER_CIRCLE_RATIO: float = 0.4  # Inner circle size ratio

    # ==================== QR Code Settings ====================
    QR_SIZE_MIN: int = 200  # Minimum QR code size in pixels
    QR_SIZE_BUBBLE_MULTIPLIER: int = 5  # QR size = bubble_size * multiplier

    # QR Code technical parameters
    QR_VERSION: int = 1  # QR code version
    QR_BOX_SIZE: int = 10  # Size of each box in the QR grid
    QR_BORDER_SIZE: int = 4  # Border size in boxes

    # ==================== Font Settings ====================
    # Base font size for custom text
    BASE_FONT_SIZE: int = 30  # Base size in pixels

    # Font paths (in order of preference)
    @staticmethod
    def get_font_paths() -> List[str]:
        """
        Get list of font paths in order of preference.

        Returns:
            List of font file paths to try
        """
        project_root = Path(__file__).parent.parent.parent
        project_font = project_root / "fonts" / "TW-Kai.ttf"

        return [
            str(project_font),  # Project bundled font (TW Kai - 台灣標楷體)
            "/Users/johnchen/Library/Fonts/edukai-4.0.ttf",  # 標楷體
            "/System/Library/Fonts/Supplemental/Songti.ttc",  # 宋體
            "/System/Library/Fonts/STHeiti Medium.ttc",  # 黑體
            "/System/Library/Fonts/Supplemental/Arial.ttf",  # Arial (fallback)
        ]

    # ==================== Text Rendering Settings ====================
    # Text width estimation (approximate characters width in pixels)
    CHAR_WIDTH_LARGE: int = 18  # For large/header text
    CHAR_WIDTH_NORMAL: int = 15  # For normal text

    # Bold text offset for simulated bold effect
    BOLD_OFFSET_X: int = 1
    BOLD_OFFSET_Y: int = 1

    # Text positioning margins
    TEXT_SAFE_MARGIN: int = 50  # Safe margin for text positioning (when no markers)
    TEXT_SAFE_MARGIN_WITH_MARKER: int = 50  # Additional margin beyond marker
    TEXT_BOTTOM_PADDING: int = 10  # Padding below text for height calculation

    # ==================== Question Label Settings ====================
    # Question number positioning offsets
    QUESTION_LABEL_OFFSET_X: int = -35  # X offset for "Q1", "Q2" labels
    QUESTION_LABEL_OFFSET_Y: int = 5  # Y offset for question labels

    # Bubble value label offsets
    BUBBLE_LABEL_OFFSET_X_HORIZONTAL: int = -8  # X offset for horizontal bubbles
    BUBBLE_LABEL_OFFSET_Y_HORIZONTAL: int = -10  # Y offset for horizontal bubbles
    BUBBLE_LABEL_OFFSET_X_VERTICAL: int = 10  # X offset for vertical bubbles
    BUBBLE_LABEL_OFFSET_Y_VERTICAL: int = 5  # Y offset for vertical bubbles

    # ==================== OpenCV Settings ====================
    # Font face for OpenCV text rendering
    CV2_FONT_FACE: int = 0  # cv2.FONT_HERSHEY_SIMPLEX = 0

    # Font scales
    CV2_QUESTION_FONT_SCALE: float = 0.55
    CV2_BUBBLE_LABEL_FONT_SCALE: float = 0.5
    CV2_BLOCK_NAME_FONT_SCALE: float = 0.6

    # Font thickness
    CV2_QUESTION_FONT_THICKNESS: int = 2
    CV2_BUBBLE_LABEL_FONT_THICKNESS: int = 1
    CV2_BLOCK_NAME_FONT_THICKNESS: int = 2

    # Bubble border thickness
    CV2_BUBBLE_BORDER_THICKNESS: int = 2

    # Colors (BGR format for OpenCV)
    COLOR_BLACK: Tuple[int, int, int] = (0, 0, 0)
    COLOR_WHITE: Tuple[int, int, int] = (255, 255, 255)
    COLOR_GREEN: Tuple[int, int, int] = (0, 255, 0)  # For visualization
    COLOR_RED: Tuple[int, int, int] = (255, 0, 0)  # For labels

    # ==================== Generator Settings ====================
    # Question block width calculation
    QUESTION_BLOCK_PADDING_HORIZONTAL: int = 40  # Padding for horizontal bubbles
    QUESTION_BLOCK_PADDING_VERTICAL: int = 60  # Padding for vertical bubbles

    # Row gap calculation
    ROW_GAP_VERTICAL: int = 40  # Additional gap for vertical bubble rows

    # ==================== Gradio UI Settings ====================
    # Server settings
    GRADIO_SERVER_NAME: str = "0.0.0.0"
    GRADIO_SERVER_PORT: int = 7860
    GRADIO_SHARE: bool = False
    GRADIO_SHOW_ERROR: bool = True

    # UI default values
    DEFAULT_NUM_QUESTIONS: int = 20  # Default number of questions in generator
    DEFAULT_LOG_LINES: int = 10  # Default number of lines in log output
    DEFAULT_FIELD_BLOCKS_LINES: int = 10  # Default lines for field blocks display
    DEFAULT_STATUS_LINES: int = 12  # Default lines for status output
    DEFAULT_BUBBLE_GAP_UI: int = 50  # Default bubble gap in template builder UI
    DEFAULT_ORIGIN_X: int = 100  # Default X coordinate for field block origin
    DEFAULT_ORIGIN_Y: int = 100  # Default Y coordinate for field block origin

    # ==================== File Settings ====================
    # Temporary file prefixes
    TEMP_PREFIX_INPUT: str = "omr_input_"
    TEMP_PREFIX_OUTPUT: str = "omr_output_"
    TEMP_PREFIX_BATCH: str = "batch_omr_"

    # File extensions
    MARKER_FILE_EXTENSION: str = ".jpg"
    SHEET_FILE_EXTENSION: str = ".png"
    TEMPLATE_FILE_EXTENSION: str = ".json"

    # Marker filename
    MARKER_FILENAME: str = "omr_marker.jpg"

    # ==================== Advanced Settings ====================
    # Page width range for UI
    PAGE_WIDTH_MIN: int = 800
    PAGE_WIDTH_MAX: int = 4000
    PAGE_HEIGHT_MIN: int = 800
    PAGE_HEIGHT_MAX: int = 5000

    # Bubble size range for UI
    BUBBLE_SIZE_MIN: int = 20
    BUBBLE_SIZE_MAX: int = 100

    # Question limits
    NUM_QUESTIONS_MIN: int = 1
    NUM_QUESTIONS_MAX: int = 200

    # Column limits
    NUM_COLUMNS_MIN: int = 1
    NUM_COLUMNS_MAX: int = 10


# Create a singleton instance for easy access
config = FrontendConfig()
