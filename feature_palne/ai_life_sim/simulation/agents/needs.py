class NeedsManager:
    def __init__(self, template: Optional[dict] = None):
        """Initializes agent needs.

        Args:
            template (Optional[dict], optional): Base needs levels and decay rates.
        """
        self.needs: dict[str, float] = {"hunger": 100.0, "thirst": 100.0, "energy": 100.0}
        self.decay_rates: dict[str, float] = {"hunger": 0.1, "thirst": 0.15, "energy": 0.05} # Per second
        # Load initial values/rates from template if provided

    def update(self, dt: float, attributes: 'AttributesManager') -> None:
        """Updates need levels based on decay and applies penalties.

        Args:
            dt (float): Time elapsed.
            attributes (AttributesManager): Agent's attributes for applying penalties (e.g., health loss).
        """
        for need, level in self.needs.items():
            decay = self.decay_rates.get(need, 0.0)
            self.needs[need] = max(0.0, level - decay * dt)
            # Apply penalties if need is critical (e.g., hunger < 10)
            if self.needs[need] < 10.0: # Example threshold
                 attributes.apply_damage(0.1 * dt) # Example penalty

    def get_levels(self) -> dict[str, float]:
        """Returns the current levels of all needs."""
        return self.needs.copy()

    def get_level(self, need_name: str) -> float:
        """Gets the level of a specific need."""
        return self.needs.get(need_name, 0.0)

    def satisfy(self, need_name: str, amount: float) -> None:
        """Increases the level of a specific need.

        Args:
            need_name (str): The name of the need (e.g., "hunger").
            amount (float): The amount to increase the need by.
        """
        if need_name in self.needs:
            self.needs[need_name] = min(100.0, self.needs[need_name] + amount) # Assume 100 max