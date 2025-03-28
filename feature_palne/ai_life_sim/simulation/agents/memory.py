from collections import deque
from typing import Tuple, Any, Optional

GridPoint = Tuple[int, int]
MemoryEntry = Tuple[GridPoint, str, float, Any] # E.g., (location, type, timestamp, details)

class Memory:
    def __init__(self, capacity: int = 50, decay_time: float = 86400): # Example: 1 day decay
        """Initializes the agent's memory system.

        Args:
            capacity (int, optional): Maximum number of memory entries. Defaults to 50.
            decay_time (float, optional): Time in seconds after which memories are forgotten. Defaults to 86400.
        """
        self.memory: deque[MemoryEntry] = deque(maxlen=capacity)
        self.capacity: int = capacity
        self.decay_time: float = decay_time
        self.current_time: float = 0.0 # Needs to be updated from TimeManager

    def update(self, dt: float, current_time: float) -> None:
        """Updates memory, removing decayed entries.

        Args:
            dt (float): Time elapsed (unused in simple decay, but good practice).
            current_time (float): The current simulation time.
        """
        self.current_time = current_time
        # Simple time-based decay
        while self.memory and (self.current_time - self.memory[0][2]) > self.decay_time:
            self.memory.popleft() # Remove oldest entry if expired

    def add_memory(self, location: GridPoint, entry_type: str, details: Any = None) -> None:
        """Adds a new memory entry.

        Args:
            location (GridPoint): The location associated with the memory.
            entry_type (str): The type of memory (e.g., "resource_wood", "hazard_lava", "agent_seen").
            details (Any, optional): Additional details (e.g., resource quality, agent ID). Defaults to None.
        """
        timestamp = self.current_time
        entry: MemoryEntry = (location, entry_type, timestamp, details)
        # Avoid duplicates? Or update timestamp if existing? Simple append for now:
        self.memory.append(entry)

    def recall_memories(self, query_type: Optional[str] = None, location: Optional[GridPoint] = None, radius: Optional[float] = None) -> list[MemoryEntry]:
        """Retrieves memories matching specific criteria.

        Args:
            query_type (Optional[str], optional): Filter by memory type. Defaults to None.
            location (Optional[GridPoint], optional): If specified with radius, filter by proximity. Defaults to None.
            radius (Optional[float], optional): Search radius around location. Defaults to None.

        Returns:
            list[MemoryEntry]: A list of matching memory entries, possibly ordered by recency.
        """
        results = []
        for entry in reversed(self.memory): # Iterate newest first
            match_type = (query_type is None or entry[1] == query_type)
            match_location = True
            if location is not None and radius is not None:
                 # Calculate distance between entry[0] and location
                 dist_sq = (entry[0][0] - location[0])**2 + (entry[0][1] - location[1])**2
                 match_location = dist_sq <= radius**2

            if match_type and match_location:
                results.append(entry)
        return results