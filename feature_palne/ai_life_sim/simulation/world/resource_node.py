from typing import Tuple

GridPoint = Tuple[int, int]

class ResourceNode:
    def __init__(self, node_type: str, position: GridPoint, quantity: float, quality: float = 1.0, regeneration_rate: float = 0.0):
        """Initializes a resource node.

        Args:
            node_type (str): Type of resource (e.g., "Tree", "Rock", "BerryBush").
            position (GridPoint): The (x, y) coordinates on the grid.
            quantity (float): Initial amount of the resource available.
            quality (float, optional): Quality modifier (e.g., affects yield). Defaults to 1.0.
            regeneration_rate (float, optional): Amount regenerated per second. Defaults to 0.0.
        """
        self.node_type: str = node_type
        self.position: GridPoint = position
        self.quantity: float = quantity
        self.quality: float = quality
        self.regeneration_rate: float = regeneration_rate

    def update(self, dt: float) -> None:
        """Updates the resource node's state (e.g., regeneration).

        Args:
            dt (float): Time elapsed since the last update.
        """
        if self.regeneration_rate > 0:
            self.quantity += self.regeneration_rate * dt
            # Add max quantity cap if applicable

    def harvest(self, amount: float) -> float:
        """Reduces the quantity of the resource.

        Args:
            amount (float): The amount attempted to be harvested.

        Returns:
            float: The actual amount harvested (cannot exceed available quantity).
        """
        harvested = min(self.quantity, amount)
        self.quantity -= harvested
        return harvested

    def is_depleted(self) -> bool:
        """Checks if the resource node is empty."""
        return self.quantity <= 0