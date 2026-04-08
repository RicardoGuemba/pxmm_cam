"""Distance in pixels between two points (Euclidean)."""

from typing import Tuple


def distance_px(
    point_a: Tuple[float, float],
    point_b: Tuple[float, float],
) -> float:
    """Euclidean distance in pixels between (x1,y1) and (x2,y2)."""
    x1, y1 = point_a
    x2, y2 = point_b
    return ((x2 - x1) ** 2 + (y2 - y1) ** 2) ** 0.5
