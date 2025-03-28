import math
from typing import Tuple

GridPoint = Tuple[int, int]

def calculate_distance_sq(pos1: GridPoint, pos2: GridPoint) -> float:
    """Calculates the squared Euclidean distance between two points.

    Faster than calculating the actual distance if only comparing distances.

    Args:
        pos1 (GridPoint): First point (x, y).
        pos2 (GridPoint): Second point (x, y).

    Returns:
        float: The squared Euclidean distance.
    """
    return (pos1[0] - pos2[0])**2 + (pos1[1] - pos2[1])**2

def calculate_distance(pos1: GridPoint, pos2: GridPoint) -> float:
    """Calculates the Euclidean distance between two points.

    Args:
        pos1 (GridPoint): First point (x, y).
        pos2 (GridPoint): Second point (x, y).

    Returns:
        float: The Euclidean distance.
    """
    return math.sqrt(calculate_distance_sq(pos1, pos2))

def clamp(value: float, min_value: float, max_value: float) -> float:
    """Clamps a value within a specified range.

    Args:
        value (float): The value to clamp.
        min_value (float): The minimum allowed value.
        max_value (float): The maximum allowed value.

    Returns:
        float: The clamped value.
    """
    return max(min_value, min(value, max_value))