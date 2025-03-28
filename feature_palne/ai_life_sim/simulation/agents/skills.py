from collections import defaultdict
import math

# Example: Load skill config from YAML/JSON elsewhere
SKILL_XP_PER_LEVEL = [100, 250, 500, 1000] # XP needed to REACH level 1, 2, 3, 4...

class SkillManager:
    def __init__(self, template: Optional[dict] = None):
        """Initializes the agent's skills.

        Args:
            template (Optional[dict], optional): Defines starting skills/XP.
        """
        self.skills: defaultdict[str, float] = defaultdict(float) # skill_name: xp_value
        self.rustiness_timer: defaultdict[str, float] = defaultdict(float) # Time since last use
        # Load starting skills/xp from template

    def update(self, dt: float) -> None:
        """Updates skills, applying rustiness if configured.

        Args:
            dt (float): Time elapsed.
        """
        RUST_THRESHOLD = 3600 # Example: 1 hour in simulation seconds
        RUST_AMOUNT = 0.1 # Example: Lose 0.1 XP per second if rusty
        for skill_name in list(self.skills.keys()):
            self.rustiness_timer[skill_name] += dt
            if self.rustiness_timer[skill_name] > RUST_THRESHOLD:
                # Apply rustiness - decrease XP slightly, but not below level minimum?
                current_level = self.get_skill_level(skill_name)
                min_xp_for_level = self._get_xp_for_level(current_level)
                self.skills[skill_name] = max(min_xp_for_level, self.skills[skill_name] - RUST_AMOUNT * dt)


    def add_xp(self, skill_name: str, xp_amount: float) -> None:
        """Adds experience points to a skill and resets rustiness timer.

        Args:
            skill_name (str): The name of the skill to gain XP in.
            xp_amount (float): The amount of XP to add (non-negative).
        """
        if xp_amount > 0:
            # Check prerequisites if implementing a skill tree
            self.skills[skill_name] += xp_amount
            self.rustiness_timer[skill_name] = 0.0 # Reset timer on use/gain

    def get_skill_xp(self, skill_name: str) -> float:
        """Gets the current total XP for a skill."""
        return self.skills[skill_name]

    def get_skill_level(self, skill_name: str) -> int:
        """Calculates the current level for a skill based on its XP.

        Args:
            skill_name (str): The name of the skill.

        Returns:
            int: The calculated skill level (0 if no XP).
        """
        xp = self.skills[skill_name]
        current_level = 0
        xp_required_cumulative = 0
        for level_xp in SKILL_XP_PER_LEVEL:
            xp_required_cumulative += level_xp
            if xp >= xp_required_cumulative:
                current_level += 1
            else:
                break
        return current_level

    def _get_xp_for_level(self, level: int) -> float:
        """Calculates the minimum total XP required to reach a given level."""
        if level <= 0:
            return 0.0
        return sum(SKILL_XP_PER_LEVEL[:level])

    def has_skill_level(self, skill_name: str, required_level: int) -> bool:
        """Checks if the agent meets a required skill level.

        Args:
            skill_name (str): The name of the skill.
            required_level (int): The minimum level required.

        Returns:
            bool: True if the agent's level meets or exceeds the requirement.
        """
        return self.get_skill_level(skill_name) >= required_level