from collections import defaultdict

class Inventory:
    def __init__(self, capacity: Optional[int] = None):
        """Initializes the agent's inventory.

        Args:
            capacity (Optional[int], optional): Maximum number of item stacks or total weight. Defaults to None (unlimited).
        """
        self.items: defaultdict[str, int] = defaultdict(int) # item_id: quantity
        self.capacity: Optional[int] = capacity

    def add_item(self, item_id: str, quantity: int = 1) -> bool:
        """Adds items to the inventory.

        Args:
            item_id (str): The identifier of the item to add.
            quantity (int, optional): The number of items to add. Defaults to 1.

        Returns:
            bool: True if the item(s) were successfully added, False if inventory is full.
        """
        # Check capacity if applicable
        if self.capacity is not None and len(self.items) >= self.capacity and item_id not in self.items:
             return False # Simple stack-based capacity example
        self.items[item_id] += quantity
        return True

    def remove_item(self, item_id: str, quantity: int = 1) -> bool:
        """Removes items from the inventory.

        Args:
            item_id (str): The identifier of the item to remove.
            quantity (int, optional): The number of items to remove. Defaults to 1.

        Returns:
            bool: True if the item(s) were successfully removed, False if not enough items were present.
        """
        if self.items[item_id] >= quantity:
            self.items[item_id] -= quantity
            if self.items[item_id] == 0:
                del self.items[item_id] # Remove entry if quantity is zero
            return True
        return False

    def has_item(self, item_id: str, quantity: int = 1) -> bool:
        """Checks if the inventory contains a sufficient quantity of an item.

        Args:
            item_id (str): The identifier of the item to check.
            quantity (int, optional): The minimum quantity required. Defaults to 1.

        Returns:
            bool: True if the required quantity is present, False otherwise.
        """
        return self.items[item_id] >= quantity

    def get_item_count(self, item_id: str) -> int:
        """Gets the quantity of a specific item in the inventory.

        Args:
            item_id (str): The identifier of the item.

        Returns:
            int: The quantity of the item present (0 if none).
        """
        return self.items[item_id]

    def get_all_items(self) -> dict[str, int]:
        """Returns a copy of the entire inventory contents."""
        return self.items.copy()