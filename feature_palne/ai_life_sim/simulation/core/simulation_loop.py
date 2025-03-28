class SimulationLoop:
    def __init__(self, config: dict, renderer: RendererInterface, world: Environment, agents: list[Agent], time_manager: TimeManager):
        """Initializes the main simulation loop controller.

        Args:
            config (dict): Loaded simulation parameters.
            renderer (RendererInterface): The chosen visualization renderer.
            world (Environment): The simulation environment instance.
            agents (list[Agent]): The initial list of agents.
            time_manager (TimeManager): The simulation time manager.
        """
        pass # Implementation stores these references

    def run_simulation(self) -> None:
        """Starts and runs the main simulation loop until stopped.

        Handles time updates, agent updates, world updates, rendering,
        and input processing within the loop.
        """
        pass # Implementation contains the main while loop

    def _update_step(self, dt: float) -> None:
        """Performs a single simulation update step.

        Args:
            dt (float): The time elapsed since the last frame/tick in seconds.
        """
        # Calls time_manager.update(), agent.update() for all agents,
        # world.update(), handles agent births/deaths
        pass

    def _render_step(self) -> None:
        """Renders the current simulation state using the renderer."""
        # Calls self.renderer.render(self.world, self.agents, ...)
        pass

    def _handle_input(self) -> None:
        """Processes user input (if any) via the renderer."""
        # Calls self.renderer.handle_input()
        # Potentially triggers pause, save, load, exit
        pass

    def save_simulation(self, filepath: str) -> None:
        """Saves the current simulation state to a file.

        Args:
            filepath (str): The path to the save file.
        """
        # Collects state from world, agents, time_manager and serializes
        pass

    def load_simulation(self, filepath: str) -> None:
        """Loads simulation state from a file, replacing the current state.

        Args:
            filepath (str): The path to the save file.
        """
        # Deserializes state and updates world, agents, time_manager
        pass