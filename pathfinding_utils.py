# pathfinding_utils.py
import numpy as np
from pathfinding.core.diagonal_movement import DiagonalMovement
from pathfinding.core.grid import Grid
from pathfinding.finder.a_star import AStarFinder

import config as cfg

def find_path(world_grid_data, start_pos, end_pos):
    """
    Uses A* algorithm to find a path on the world grid.

    Args:
        world_grid_data (numpy.ndarray): 2D array representing walkability (1=walkable, 0=obstacle).
        start_pos (tuple): (x, y) starting coordinates.
        end_pos (tuple): (x, y) target coordinates.

    Returns:
        list: A list of (x, y) tuples representing the path, or empty list if no path found.
              Includes the start_pos, excludes the end_pos for movement iteration.
    """
    try:
        grid = Grid(matrix=world_grid_data)
        start = grid.node(start_pos[0], start_pos[1])
        end = grid.node(end_pos[0], end_pos[1])

        finder = AStarFinder(diagonal_movement=DiagonalMovement.always)
        path, runs = finder.find_path(start, end, grid)

        # print(f"Path found: {path} in {runs} runs") # Debugging
        # Remove the start node itself, path[0] is start
        return path[1:] if path else []

    except Exception as e:
        # Handle cases where start/end might be outside grid or on non-walkable nodes
        # print(f"Pathfinding error: {e} from {start_pos} to {end_pos}") # Debugging
        return [] # Return empty path on error

def create_walkability_matrix(world_map):
    """ Creates a matrix where 1 is walkable, 0 is not. """
    height, width = world_map.shape
    walkability_matrix = np.ones((height, width), dtype=int)

    for y in range(height):
        for x in range(width):
            terrain = world_map[y, x]
            # Define non-walkable terrain types
            if terrain == cfg.TERRAIN_WATER or terrain == cfg.TERRAIN_OBSTACLE:
                 # Check resource layer too? Maybe some resources block path?
                walkability_matrix[y, x] = 0

    return walkability_matrix