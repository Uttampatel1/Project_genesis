class RecipeManager:
    def __init__(self, recipe_filepath: str):
        """Loads and manages crafting recipes.

        Args:
            recipe_filepath (str): Path to the JSON/YAML file with recipe definitions.
        """
        self.recipes: dict[str, dict] = self._load_recipes(recipe_filepath)

    def _load_recipes(self, filepath: str) -> dict[str, dict]:
        """Loads recipe definitions from a file.

        Args:
            filepath (str): Path to the recipe file.

        Returns:
            dict[str, dict]: A dictionary mapping recipe_id to recipe details
                             (inputs, outputs, skill_req, time, workbench_req).
        """
        # Use json.load or yaml.safe_load
        pass # Returns the loaded dictionary

    def get_recipe(self, recipe_id: str) -> Optional[dict]:
        """Retrieves the details for a specific recipe.

        Args:
            recipe_id (str): The ID of the recipe.

        Returns:
            Optional[dict]: The recipe details dictionary, or None if not found.
        """
        return self.recipes.get(recipe_id)

    def check_crafting_requirements(self, agent: 'Agent', recipe_id: str, environment: 'Environment') -> bool:
        """Checks if an agent meets all requirements to craft a recipe.

        Args:
            agent (Agent): The agent attempting to craft.
            recipe_id (str): The ID of the recipe.
            environment (Environment): World context to check for workbenches.

        Returns:
            bool: True if all requirements (items, skills, workbench) are met, False otherwise.
        """
        recipe = self.get_recipe(recipe_id)
        if not recipe: return False

        # Check items
        for item_id, quantity in recipe.get('inputs', {}).items():
            if not agent.inventory.has_item(item_id, quantity): return False

        # Check skills
        for skill_name, level in recipe.get('skill_req', {}).items():
            if not agent.skills.has_skill_level(skill_name, level): return False

        # Check workbench
        required_workbench = recipe.get('workbench_req')
        if required_workbench:
             structure = environment.get_structure_at(agent.position)
             if not structure or structure.structure_type != required_workbench:
                 # Or check nearby structures? Depends on interaction range.
                 return False

        return True