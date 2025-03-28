# pathfinding_utils.py
import numpy as np
from pathfinding.core.diagonal_movement import DiagonalMovement
from pathfinding.core.grid import Grid
from pathfinding.finder.a_star import AStarFinder
import time # For debug
import config as cfg # Import config

def find_path(world_grid_data, start_pos, end_pos):
    """
    Uses A* algorithm to find a path on the world grid.

    Args:
        world_grid_data (numpy.ndarray): 2D array representing walkability (1=walkable, 0=obstacle).
        start_pos (tuple): (x, y) starting coordinates.
        end_pos (tuple): (x, y) target coordinates.

    Returns:
        list: A list of pathfinding.core.node.GridNode objects representing the path,
              excluding the start node. Returns empty list if start==end or no path found.
              Returns None if start/end invalid or internal error.
    """
    start_time = time.time()
    try:
        # Ensure integer coordinates
        start_pos = (int(start_pos[0]), int(start_pos[1]))
        end_pos = (int(end_pos[0]), int(end_pos[1]))

        grid_height, grid_width = world_grid_data.shape
        # Basic bounds check
        if not (0 <= start_pos[0] < grid_width and 0 <= start_pos[1] < grid_height):
            if cfg.DEBUG_PATHFINDING: print(f"Pathfinding Error: Start node {start_pos} out of bounds.")
            return None
        if not (0 <= end_pos[0] < grid_width and 0 <= end_pos[1] < grid_height):
             if cfg.DEBUG_PATHFINDING: print(f"Pathfinding Error: End node {end_pos} out of bounds.")
             return None

        # Create grid object AFTER bounds check
        grid = Grid(matrix=world_grid_data)
        start = grid.node(start_pos[0], start_pos[1])
        end = grid.node(end_pos[0], end_pos[1])

        # Check walkability using the grid object, which handles node creation
        if not start.walkable:
            # This should ideally be handled by the caller (e.g., find adjacent start)
            if cfg.DEBUG_PATHFINDING: print(f"Pathfinding Error: Start node {start_pos} is not walkable.")
            return None # Cannot start path from unwalkable node
        if not end.walkable:
             # Caller should handle this (e.g., find adjacent target), but log warning.
             if cfg.DEBUG_PATHFINDING: print(f"Pathfinding Warning: End node {end_pos} is not walkable (A* target adjusted by caller).")
             # Pathfinding might still work if caller provided an adjacent walkable end_pos

        finder = AStarFinder(diagonal_movement=DiagonalMovement.always, weight=1)

        # Use the library's find_path method
        path, runs = finder.find_path(start, end, grid)

        duration = time.time() - start_time
        if cfg.DEBUG_PATHFINDING and duration > 0.01: # Log slow paths
             print(f"Pathfinding took {duration:.4f}s for {start_pos}->{end_pos} ({runs} runs). Path length: {len(path)}")

        # path[0] is the start node. Return path excluding the start node.
        return path[1:] if path else []

    except Exception as e:
        # Catch potential errors from the pathfinding library or unexpected issues
        print(f"!!! Pathfinding unexpected error for {start_pos} -> {end_pos}: {e}")
        import traceback
        traceback.print_exc()
        return None # Indicate error state

def create_walkability_matrix(world_terrain_map, world_resource_map):
    """ Creates a matrix where 1 is walkable, 0 is not, considering terrain and blocking resources. """
    height, width = world_terrain_map.shape
    # Start with all ground walkable
    walkability_matrix = (world_terrain_map == cfg.TERRAIN_GROUND).astype(int)

    # Mark non-walkable resources as 0
    for y in range(height):
        for x in range(width):
            resource = world_resource_map[y, x]
            # Check if resource exists and has the 'blocks_walk' attribute/property set to True
            if resource and getattr(resource, 'blocks_walk', False):
                 walkability_matrix[y, x] = 0

    return walkability_matrix