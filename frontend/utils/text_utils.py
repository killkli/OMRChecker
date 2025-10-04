from typing import List, Dict, Any, Tuple


def calculate_text_positioning(
    text_lines: List[str],
    page_width: int,
    include_markers: bool,
    config: Any
) -> List[Dict[str, Any]]:
    """
    Calculate safe positioning for custom text fields with center alignment.

    This function takes a list of text strings and calculates their positions
    to avoid overlapping with alignment markers while ensuring they are
    center-aligned on the page.

    Args:
        text_lines: List of text strings to position (max 3 lines typically)
        page_width: Width of the page in pixels
        include_markers: Whether alignment markers are included on the sheet
        config: Configuration object containing margins, spacing, and font sizes

    Returns:
        List of dictionaries with text positioning data:
        [
            {
                "text": str,
                "x": int,
                "y": int,
                "font_size": float,
                "bold": bool
            },
            ...
        ]
    """
    custom_texts = []

    # Calculate safe text positioning (avoid markers)
    marker_size = int(page_width * config.MARKER_SIZE_RATIO) if include_markers else 0
    safe_margin_left = (
        marker_size + config.TEXT_SAFE_MARGIN_WITH_MARKER
        if include_markers
        else config.TEXT_SAFE_MARGIN
    )
    safe_y_start = (
        marker_size + config.CUSTOM_TEXT_SPACING
        if include_markers
        else config.TEXT_SAFE_MARGIN
    )

    # Line spacing between text lines
    line_spacing = config.TEXT_LINE_SPACING

    # Process each text line
    for idx, text in enumerate(text_lines):
        if not text or not text.strip():
            continue

        # Determine font size and bold based on line index
        # First line is larger and bold (header)
        is_header = (idx == 0)
        font_size_scale = 1.5 if is_header else 1.0
        bold = is_header

        # Calculate approximate text width for center alignment
        char_width = config.CHAR_WIDTH_LARGE if is_header else config.CHAR_WIDTH_NORMAL
        text_width = len(text) * char_width

        # Calculate center-aligned X position (respecting safe margins)
        x_position = max(safe_margin_left, page_width // 2 - text_width // 2)

        # Calculate Y position (each line is offset by line_spacing)
        y_position = safe_y_start + (line_spacing * idx)

        custom_texts.append({
            "text": text,
            "x": x_position,
            "y": y_position,
            "font_size": font_size_scale,
            "bold": bold,
        })

    return custom_texts


def calculate_max_text_y(custom_texts: List[Dict[str, Any]], config: Any) -> int:
    """
    Calculate the maximum Y position used by custom text fields.

    This is useful for determining where question blocks should start
    to avoid overlapping with custom text.

    Args:
        custom_texts: List of positioned text dictionaries
        config: Configuration object containing font size constants

    Returns:
        int: Maximum Y coordinate occupied by text (including padding)
    """
    if not custom_texts:
        return 0

    max_y = 0
    for text_field in custom_texts:
        y = text_field.get("y", config.TEXT_SAFE_MARGIN)
        font_size_scale = text_field.get("font_size", 1.0)
        actual_font_size = int(config.BASE_FONT_SIZE * font_size_scale)

        # Approximate text height (font size + padding)
        text_bottom = y + actual_font_size + config.TEXT_BOTTOM_PADDING
        max_y = max(max_y, text_bottom)

    return max_y