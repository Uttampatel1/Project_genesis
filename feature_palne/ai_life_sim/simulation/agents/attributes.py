class AttributesManager:
    def __init__(self, template: Optional[dict] = None):
        """Initializes agent attributes."""
        self.health: float = 100.0
        self.max_health: float = 100.0
        self.stamina: float = 100.0
        self.max_stamina: float = 100.0
        self.age: float = 0.0 # In simulation seconds or days
        # ... other attributes like speed modifier, base damage, traits ...
        # Load initial values from template if provided

    def update(self, dt: float) -> None:
        """Updates attributes over time (e.g., aging).

        Args:
            dt (float): Time elapsed.
        """
        self.age += dt
        # Implement effects of aging if necessary

    def apply_damage(self, amount: float) -> None:
        """Reduces the agent's health.

        Args:
            amount (float): The amount of damage to apply (non-negative).
        """
        self.health = max(0.0, self.health - amount)

    def heal(self, amount: float) -> None:
        """Increases the agent's health.

        Args:
            amount (float): The amount to heal (non-negative).
        """
        self.health = min(self.max_health, self.health + amount)

    # ... methods for stamina usage/recovery ...