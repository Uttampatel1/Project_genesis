# knowledge.py
# Represents what an agent knows. Can be simple or complex (knowledge graph).

class KnowledgeSystem:
    def __init__(self, agent_id):
        self.agent_id = agent_id
        self.known_resource_locations = {} # type: [(x, y), (x, y), ...]
        self.known_recipes = set() # set of recipe names (e.g., 'CrudeAxe')
        # Phase 4+: Learned facts, social knowledge (trust levels, relationships)
        self.relationships = {} # agent_id: relationship_score (-1 to 1)

    def add_resource_location(self, resource_type, x, y):
        if resource_type not in self.known_resource_locations:
            self.known_resource_locations[resource_type] = []
        if (x, y) not in self.known_resource_locations[resource_type]:
            self.known_resource_locations[resource_type].append((x, y))
            # Limit memory size? Forget old locations?

    def get_known_locations(self, resource_type):
        return self.known_resource_locations.get(resource_type, [])

    def add_recipe(self, recipe_name):
        self.known_recipes.add(recipe_name)
        print(f"Agent {self.agent_id} learned recipe: {recipe_name}")

    def knows_recipe(self, recipe_name):
        return recipe_name in self.known_recipes

    # --- Phase 3: Invention ---
    def attempt_invention(self, inventory):
        # Simple Combinatorial Exploration Placeholder
        # Needs access to agent's inventory and maybe world state (workbench nearby?)
        # This is extremely simplified. Real invention needs more structure.
        import random
        import config as cfg

        if len(inventory) < 2: return None # Need at least 2 items to combine

        # Try combining 2 random items
        item1_name = random.choice(list(inventory.keys()))
        item2_name = random.choice(list(inventory.keys()))
        if item1_name == item2_name and inventory[item1_name] < 2: return None # Need 2 if same item

        # Check against predefined (but unknown to agent) recipes
        for recipe_name, details in cfg.RECIPES.items():
            ingredients = details['ingredients']
            # Simple check for 2 ingredients only for this example
            if len(ingredients) == 2:
                 # Check both orders
                 match1 = (item1_name in ingredients and item2_name in ingredients[item1_name] and
                           item2_name in ingredients and item1_name in ingredients[item2_name]) # Needs better check for counts
                 # This logic needs refinement based on RECIPES structure and counts
                 # For now, just check if the two items ARE the ingredients
                 items_in_recipe = list(ingredients.keys())
                 if (item1_name == items_in_recipe[0] and item2_name == items_in_recipe[1]) or \
                    (item1_name == items_in_recipe[1] and item2_name == items_in_recipe[0]):
                     if not self.knows_recipe(recipe_name):
                         # DISCOVERY!
                         return recipe_name # Return the name of the discovered recipe
        return None

    # --- Phase 4: Social Knowledge ---
    def update_relationship(self, other_agent_id, change):
        current = self.relationships.get(other_agent_id, 0)
        self.relationships[other_agent_id] = max(-1.0, min(1.0, current + change))

    def get_relationship(self, other_agent_id):
        return self.relationships.get(other_agent_id, 0) # Default neutral