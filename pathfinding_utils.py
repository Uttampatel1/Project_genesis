# pathfinding_utils.py
import numpy as np
from pathfinding.core.diagonal_movement import DiagonalMovement
from pathfinding.core.grid import Grid
from pathfinding.finder.a_star import AStarFinder
import time # For debug

import config as cfg

def find_path(world_grid_data, start_pos, end_pos):
    """
    Uses A* algorithm to find a path on the world grid.

    Args:
        world_grid_data (numpy.ndarray): 2D array representing walkability (1=walkable, 0=obstacle).
        start_pos (tuple): (x, y) starting coordinates.
        end_pos (tuple): (x, y) target coordinates.

    Returns:
        list: A list of pathfinding.core.node.GridNode objects representing the path,
              or empty list if no path found. Includes the start_pos, excludes the end_pos for movement iteration.
              Returns None if start/end invalid.
    """
    start_time = time.time() # Perf check
    try:
        grid = Grid(matrix=world_grid_data)

        # Check if start and end nodes are valid within the grid dimensions
        if not grid.node(*start_pos).walkable:
            # print(f"Pathfinding Error: Start node {start_pos} is not walkable.")
            return None # Cannot start path from unwalkable node
        if not grid.node(*end_pos).walkable:
             # Caller should handle this by finding adjacent, but double check
             # print(f"Pathfinding Warning: End node {end_pos} is not walkable (A* might still find path TO adjacent).")
             pass # Let A* try, it might find a path to an adjacent node anyway

        start = grid.node(start_pos[0], start_pos[1])
        end = grid.node(end_pos[0], end_pos[1])

        # Limit iterations for performance
        finder = AStarFinder(diagonal_movement=DiagonalMovement.always, weight=1) # weight=1 standard cost
                                # time_limit=0.05, max_runs=cfg.MAX_PATHFINDING_ITERATIONS) # pathfinding lib parameters may vary

        path, runs = finder.find_path(start, end, grid)

        duration = time.time() - start_time
        # if duration > 0.01: # Log slow paths
        #      print(f"Pathfinding took {duration:.4f}s for {start_pos}->{end_pos} ({runs} runs). Path length: {len(path)}")

        # path[0] is the start node. Return path excluding the start node.
        return path[1:] if path else []

    except IndexError:
         # print(f"Pathfinding Error: Start {start_pos} or End {end_pos} outside grid bounds.")
         return None # Indicate error state
    except Exception as e:
        # Handle other potential pathfinding errors
        # print(f"Pathfinding unexpected error: {e} from {start_pos} to {end_pos}")
        return None # Indicate error state

def create_walkability_matrix(world_terrain_map, world_resource_map):
    """ Creates a matrix where 1 is walkable, 0 is not, considering terrain and blocking resources. """
    height, width = world_terrain_map.shape
    walkability_matrix = np.ones((height, width), dtype=int)

    for y in range(height):
        for x in range(width):
            terrain = world_terrain_map[y, x]
            resource = world_resource_map[y, x]

            # Non-walkable terrain types
            if terrain == cfg.TERRAIN_WATER or terrain == cfg.TERRAIN_OBSTACLE:
                 walkability_matrix[y, x] = 0

            # Non-walkable resources (even if terrain is ground)
            if resource and resource.blocks_walk:
                 walkability_matrix[y, x] = 0

    return walkability_matrix