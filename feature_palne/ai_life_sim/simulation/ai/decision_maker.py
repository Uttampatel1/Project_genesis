from abc import ABC, abstractmethod
from typing import Any
# Forward references if needed, or import carefully
# from simulation.agents.agent import Agent
# from simulation.world.environment import Environment

class DecisionMakerInterface(ABC):
    @abstractmethod
    def choose_action(self, agent: 'Agent', environment: 'Environment') -> Any:
        """Selects the best action for the agent in the current context.

        Args:
            agent (Agent): The agent making the decision.
            environment (Environment): The current state of the world.

        Returns:
            Any: An object or identifier representing the chosen action
                 (e.g., a tuple ('move', target_pos), a function reference,
                  a custom Action object). Returns None if no action is chosen.
        """
        pass