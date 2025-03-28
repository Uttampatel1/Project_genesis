from typing import Tuple, Optional, List, Dict
from simulation.world.grid import WorldGrid, GridPoint
from simulation.world.resource_node import ResourceNode
from simulation.world.structure import Structure

class Environment:
    def __init__(self, grid: WorldGrid, config: dict):
        """Initializes and manages the dynamic environment.

        Args:
            grid (WorldGrid): The static world grid.
            config (dict): Configuration for world generation, resource density, etc.
        """
        self.grid: WorldGrid = grid
        self.resources: Dict[GridPoint, ResourceNode] = {} # Resources by location
        self.structures: Dict[GridPoint, Structure] = {} # Structures by location
        # ... potentially weather state ...

    def update(self, dt: float) -> None:
        """Updates all dynamic elements in the environment.

        Updates resource regeneration, weather effects, etc.

        Args:
            dt (float): Time elapsed since the last update.
        """
        for resource in self.resources.values():
            resource.update(dt)
        # Handle resource respawning/spawning based on config/rules
        # Handle structure decay? Weather updates?

    def add_resource(self, resource: ResourceNode) -> None:
        """Adds a resource node to the environment.

        Args:
            resource (ResourceNode): The resource node to add.
        """
        self.resources[resource.position] = resource

    def remove_resource(self, position: GridPoint) -> Optional[ResourceNode]:
        """Removes a resource node from the environment.

        Args:
            position (GridPoint): The position of the resource to remove.

        Returns:
            Optional[ResourceNode]: The removed resource node, or None if not found.
        """
        return self.resources.pop(position, None)

    def get_resource_at(self, position: GridPoint) -> Optional[ResourceNode]:
        """Gets the resource node at a specific position.

        Args:
            position (GridPoint): The position to check.

        Returns:
            Optional[ResourceNode]: The ResourceNode if present, else None.
        """
        return self.resources.get(position)

    def add_structure(self, structure: Structure) -> None:
        """Adds a structure to the environment."""
        self.structures[structure.position] = structure
        # Potentially update grid walkability if structure blocks path

    def remove_structure(self, position: GridPoint) -> Optional[Structure]:
        """Removes a structure from the environment."""
        structure = self.structures.pop(position, None)
        # Potentially update grid walkability
        return structure

    def get_structure_at(self, position: GridPoint) -> Optional[Structure]:
        """Gets the structure at a specific position."""
        return self.structures.get(position)

    def find_nearby_resources(self, position: GridPoint, radius: float, resource_type: Optional[str] = None) -> List[ResourceNode]:
        """Finds resource nodes within a certain radius of a position.

        Args:
            position (GridPoint): The center position for the search.
            radius (float): The search radius.
            resource_type (Optional[str], optional): If specified, only return resources
                                                     of this type. Defaults to None (all types).

        Returns:
            List[ResourceNode]: A list of resource nodes found within the radius.
        """
        # Implementation uses spatial query or iterates through self.resources
        pass