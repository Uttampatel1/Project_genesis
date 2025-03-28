from typing import Tuple, Optional, List, Any
from simulation.agents.needs import NeedsManager
from simulation.agents.attributes import AttributesManager
from simulation.agents.inventory import Inventory
from simulation.agents.skills import SkillManager
from simulation.agents.memory import Memory
from simulation.ai.decision_maker import DecisionMakerInterface
from simulation.world.environment import Environment # For context

GridPoint = Tuple[int, int]

class Agent:
    def __init__(self, agent_id: int, position: GridPoint, config: dict, ai_logic: DecisionMakerInterface, template: Optional[dict] = None):
        """Initializes an agent instance.

        Args:
            agent_id (int): A unique identifier for the agent.
            position (GridPoint): Initial position (x, y).
            config (dict): General simulation configuration.
            ai_logic (DecisionMakerInterface): The AI implementation for this agent.
            template (Optional[dict], optional): Template defining base stats/traits. Defaults to None.
        """
        self.id: int = agent_id
        self.position: GridPoint = position
        self.attributes: AttributesManager = AttributesManager(template)
        self.needs: NeedsManager = NeedsManager(template)
        self.inventory: Inventory = Inventory()
        self.skills: SkillManager = SkillManager(template)
        self.memory: Memory = Memory()
        self.ai: DecisionMakerInterface = ai_logic
        self.current_action: Optional[Any] = None # Current action being executed
        self.action_progress: float = 0.0
        self.path: Optional[List[GridPoint]] = None # Current path for movement
        self.is_alive: bool = True
        # ... potentially add relationship manager, knowledge base etc. here or manage globally

    def update(self, dt: float, environment: Environment) -> None:
        """Main update logic for the agent for one simulation tick.

        Args:
            dt (float): Time elapsed since the last update.
            environment (Environment): The current state of the world environment.
        """
        if not self.is_alive:
            return

        # 1. Update internal state
        self.attributes.update(dt) # Aging etc.
        self.needs.update(dt, self.attributes) # Needs decay, apply penalties
        self.skills.update(dt) # Skill rustiness
        self.memory.update(dt) # Memory decay

        # 2. Check for death
        if self.attributes.health <= 0:
            self.die()
            return

        # 3. Execute current action / Choose new action
        if self.current_action:
            completed = self._execute_action_step(dt, environment)
            if completed:
                self.current_action = None
                self.action_progress = 0.0
        else:
            # 4. AI Decision Making
            chosen_action = self.ai.choose_action(self, environment)
            self.set_action(chosen_action)
            # Immediately start executing if possible/needed
            if self.current_action:
                 self._execute_action_step(dt, environment) # Execute fraction of new action

    def _execute_action_step(self, dt: float, environment: Environment) -> bool:
        """Executes a portion of the current action based on dt.

        Args:
            dt (float): Time elapsed.
            environment (Environment): World context.

        Returns:
            bool: True if the action is completed this step, False otherwise.
        """
        # Calls the appropriate action function (movement, gathering, crafting)
        # Increments self.action_progress
        # Returns True when progress >= action duration
        pass

    def set_action(self, action: Any) -> None:
        """Sets the agent's next action.

        Args:
            action (Any): The action object or identifier returned by the AI.
        """
        # Cancels previous path/action if necessary
        self.current_action = action
        self.action_progress = 0.0
        # May immediately trigger pathfinding if it's a move action

    def die(self) -> None:
        """Handles the agent's death."""
        self.is_alive = False
        # Log death event, drop items?, remove from simulation? (handled by SimLoop)
        print(f"Agent {self.id} died.")

    # --- Getters for AI context ---
    def get_position(self) -> GridPoint: return self.position
    def get_health(self) -> float: return self.attributes.health
    def get_needs_levels(self) -> dict[str, float]: return self.needs.get_levels()
    # ... etc ...