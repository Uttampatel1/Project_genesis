import numpy as np
from typing import Tuple, Optional

GridPoint = Tuple[int, int]

class WorldGrid:
    def __init__(self, width: int, height: int):
        """Initializes the world grid.

        Args:
            width (int): Width of the grid.
            height (int): Height of the grid.
        """
        self.width: int = width
        self.height: int = height
        # Example using NumPy: terrain, elevation, hazards could be layers
        self.terrain: np.ndarray = np.zeros((height, width), dtype=int)
        self.hazards: np.ndarray = np.zeros((height, width), dtype=float) # Damage per tick

    def get_terrain(self, pos: GridPoint) -> int:
        """Gets the terrain type at a specific grid position.

        Args:
            pos (GridPoint): The (x, y) coordinates.

        Returns:
            int: The terrain type identifier. Returns a default/invalid type if out of bounds.
        """
        pass # Implementation handles bounds checking

    def get_hazard_damage(self, pos: GridPoint) -> float:
        """Gets the hazard damage per tick at a specific grid position.

        Args:
            pos (GridPoint): The (x, y) coordinates.

        Returns:
            float: Damage per tick. Returns 0 if out of bounds or no hazard.
        """
        pass # Implementation handles bounds checking

    def is_walkable(self, pos: GridPoint) -> bool:
        """Checks if a grid position is walkable (considering terrain, structures).

        Args:
            pos (GridPoint): The (x, y) coordinates.

        Returns:
            bool: True if the position is walkable, False otherwise.
        """
        # Checks terrain type, presence of blocking structures (needs access to them)
        pass

    def get_neighbors(self, pos: GridPoint) -> list[GridPoint]:
        """Gets valid neighbor coordinates for a given position.

        Args:
            pos (GridPoint): The (x, y) coordinates.

        Returns:
            list[GridPoint]: A list of valid (within bounds) neighbor coordinates.
        """
        pass # Implementation generates N, S, E, W (and optionally diagonal) neighbors
             # and filters out-of-bounds ones.