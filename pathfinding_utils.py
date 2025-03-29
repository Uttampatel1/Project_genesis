# pathfinding_utils.py
import numpy as np
from pathfinding.core.diagonal_movement import DiagonalMovement
from pathfinding.core.grid import Grid
from pathfinding.finder.a_star import AStarFinder
import time # For debug timing
import config as cfg # Import config for debug flags and limits
import traceback # For error logging

def find_path(world_grid_data, start_pos, end_pos):
    """
    Uses A* algorithm to find a path on the world grid.

    Args:
        world_grid_data (numpy.ndarray): 2D array representing walkability (1=walkable, 0=obstacle).
        start_pos (tuple): (x, y) starting coordinates.
        end_pos (tuple): (x, y) target coordinates.

    Returns:
        list: A list of pathfinding.core.node.GridNode objects representing the path,
              excluding the start node. Returns empty list if start==end.
              Returns None if no path found, start/end invalid, or internal error.
    """
    start_time = time.time()
    try:
        # Ensure integer coordinates
        start_pos = (int(start_pos[0]), int(start_pos[1]))
        end_pos = (int(end_pos[0]), int(end_pos[1]))

        grid_height, grid_width = world_grid_data.shape

        # Basic bounds check for start and end positions
        if not (0 <= start_pos[0] < grid_width and 0 <= start_pos[1] < grid_height):
            if cfg.DEBUG_PATHFINDING: print(f"Pathfinding Error: Start node {start_pos} out of bounds.")
            return None # Invalid start
        if not (0 <= end_pos[0] < grid_width and 0 <= end_pos[1] < grid_height):
             if cfg.DEBUG_PATHFINDING: print(f"Pathfinding Error: End node {end_pos} out of bounds.")
             return None # Invalid end

        # Create grid object AFTER bounds check
        # The pathfinding library expects matrix dimensions as (width, height)
        # but numpy arrays are (height, width). Transpose is needed if library expects (w,h).
        # Let's assume the library handles numpy arrays correctly (row=y, col=x)
        grid = Grid(matrix=world_grid_data)
        start_node = grid.node(start_pos[0], start_pos[1])
        end_node = grid.node(end_pos[0], end_pos[1])

        # Check walkability using the grid object's nodes
        # The Agent logic should handle adjusting start/end if they are blocked,
        # but we add checks here for robustness. find_path requires walkable start/end.
        if not start_node.walkable:
            if cfg.DEBUG_PATHFINDING: print(f"Pathfinding Error: Start node {start_pos} is not walkable in the provided grid.")
            # Agent logic should have prevented this call or adjusted 'start_pos'
            return None
        if not end_node.walkable:
             if cfg.DEBUG_PATHFINDING: print(f"Pathfinding Warning: End node {end_pos} is not walkable in the provided grid (Caller should have adjusted).")
             # A* requires a walkable end node.
             return None

        # Configure A* finder: allow diagonal movement, default weight
        finder = AStarFinder(diagonal_movement=DiagonalMovement.always, weight=1)

        # Limit iterations to prevent runaway calculations on impossible paths
        finder.max_iterations = cfg.MAX_PATHFINDING_ITERATIONS

        # Find the path using the library
        path, runs = finder.find_path(start_node, end_node, grid)

        # Performance logging for slow paths
        duration = time.time() - start_time
        if cfg.DEBUG_PATHFINDING and duration > 0.01: # Log paths taking longer than 10ms
             path_len = len(path) if path else 0
             print(f"Pathfinding took {duration:.4f}s for {start_pos}->{end_pos} ({runs} runs). Path length: {path_len}")

        # Return path excluding the start node if found, otherwise None for no path
        if path:
            return path[1:] # Exclude the starting node itself
        else:
             # No path found between the (potentially adjusted) start and end nodes
             return None

    except Exception as e:
        # Catch potential errors from the pathfinding library or unexpected issues
        print(f"!!! Pathfinding unexpected error for {start_pos} -> {end_pos}: {e}")
        traceback.print_exc()
        return None # Indicate error state

def create_walkability_matrix(world_terrain_map, world_resource_map):
    """
    Creates a walkability matrix (1=walkable, 0=obstacle) based on terrain
    and resources that block movement.
    """
    height, width = world_terrain_map.shape
    # Start with ground tiles being walkable (1), others not (0)
    walkability_matrix = (world_terrain_map == cfg.TERRAIN_GROUND).astype(np.uint8) # Use uint8 for efficiency

    # Iterate through resources and mark tiles as non-walkable if resource blocks walk
    for y in range(height):
        for x in range(width):
            # Only need to check if tile is currently marked walkable
            if walkability_matrix[y, x] == 1:
                resource = world_resource_map[y, x]
                # Check if resource exists and its 'blocks_walk' attribute is True
                if resource and getattr(resource, 'blocks_walk', False):
                     walkability_matrix[y, x] = 0 # Mark as non-walkable

    return walkability_matrix