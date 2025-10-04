from typing import Dict, List, Tuple, Any


def calculate_coordinate_system(
    page_width: int,
    page_height: int,
    include_markers: bool,
    config: Any
) -> Dict[str, Any]:
    """
    Calculate coordinate system dimensions and offsets for OMR template.

    When markers are included, the coordinate system is relative to the
    top-left marker center. When markers are not included, coordinates
    are relative to the page origin (0, 0).

    Args:
        page_width: Width of the page in pixels
        page_height: Height of the page in pixels
        include_markers: Whether alignment markers are included
        config: Configuration object containing marker settings

    Returns:
        Dictionary containing:
        {
            "template_width": int,        # Width of template coordinate space
            "template_height": int,       # Height of template coordinate space
            "coord_offset_x": int,        # X offset for absolute coordinates
            "coord_offset_y": int,        # Y offset for absolute coordinates
            "marker_positions": List[Tuple[int, int]] or None,  # Corner positions
            "marker_centers": List[Tuple[int, int]] or None,    # Center positions
            "marker_size": int            # Size of markers (0 if no markers)
        }
    """
    if include_markers:
        # Calculate marker size (1/10 of page width by default)
        marker_size = int(page_width * config.MARKER_SIZE_RATIO)

        # Markers are placed near page corners with fixed edge spacing
        edge_spacing = config.MARKER_EDGE_SPACING
        marker_positions = [
            (edge_spacing, edge_spacing),  # Top-left
            (page_width - edge_spacing - marker_size, edge_spacing),  # Top-right
            (edge_spacing, page_height - edge_spacing - marker_size),  # Bottom-left
            (
                page_width - edge_spacing - marker_size,
                page_height - edge_spacing - marker_size,
            ),  # Bottom-right
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

        return {
            "template_width": template_width,
            "template_height": template_height,
            "coord_offset_x": coord_offset_x,
            "coord_offset_y": coord_offset_y,
            "marker_positions": marker_positions,
            "marker_centers": marker_centers,
            "marker_size": marker_size,
        }
    else:
        # No markers: pageDimensions = full page size, no offset
        return {
            "template_width": page_width,
            "template_height": page_height,
            "coord_offset_x": 0,
            "coord_offset_y": 0,
            "marker_positions": None,
            "marker_centers": None,
            "marker_size": 0,
        }