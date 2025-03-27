# knowledge.py
import random
import config as cfg

class KnowledgeSystem:
    def __init__(self, agent_id):
        self.agent_id = agent_id
        self.known_resource_locations = {} # type: [(x, y), (x, y), ...]
        self.known_recipes = set() # set of recipe names (e.g., 'CrudeAxe')
        self.relationships = {} # other_agent_id: relationship_score (-1.0 to 1.0)

    def add_resource_location(self, resource_type, x, y):
        if resource_type not in self.known_resource_locations:
            self.known_resource_locations[resource_type] = []
        if (x, y) not in self.known_resource_locations[resource_type]:
            # Limit memory? For now, add all discovered.
            self.known_resource_locations[resource_type].append((x, y))

    def get_known_locations(self, resource_type):
        # Maybe return locations closer to agent first? Future optimization.
        return self.known_resource_locations.get(resource_type, [])

    def add_recipe(self, recipe_name):
        if recipe_name not in self.known_recipes:
            self.known_recipes.add(recipe_name)
            print(f"Agent {self.agent_id} learned recipe: {recipe_name}")
            return True
        return False

    def knows_recipe(self, recipe_name):
        return recipe_name in self.known_recipes

    # --- Phase 3: Invention ---
    def attempt_invention(self, inventory):
        """
        Simple Combinatorial Exploration Placeholder.
        Tries combining two random items from inventory and checks if they match
        an unknown 2-ingredient recipe for which the agent has enough materials.
        """
        if not inventory or len(inventory) < 2: # Need at least two distinct item types, or >= 2 of one type
            # Check if there's at least one item type with count >= 2
            can_combine_same = any(count >= 2 for count in inventory.values())
            # Check if there are at least two different item types
            can_combine_different = len(inventory) >= 2
            if not (can_combine_same or can_combine_different):
                 return None

        # --- Corrected Invention Logic ---
        try:
            # Select two items (can be the same type if count >= 2)
            available_items = list(inventory.keys())
            item1_name = random.choice(available_items)

            # Ensure we can pick a second item (either different, or same if count >= 2)
            second_item_options = available_items[:] # Copy list
            if inventory.get(item1_name, 0) < 2:
                if item1_name in second_item_options:
                     second_item_options.remove(item1_name) # Cannot pick same item again if only 1 exists

            if not second_item_options: return None # No valid second item to pick

            item2_name = random.choice(second_item_options)

            # Now check against predefined (but potentially unknown) recipes
            for recipe_name, details in cfg.RECIPES.items():
                # Only consider recipes with exactly two ingredient types for this simple mechanism
                ingredients_needed = details.get('ingredients', {})
                if len(ingredients_needed) == 2:
                    # Get the names and counts of the required ingredients
                    req_items = list(ingredients_needed.keys())
                    req_item1_name, req_item2_name = req_items[0], req_items[1]
                    req_item1_count = ingredients_needed[req_item1_name]
                    req_item2_count = ingredients_needed[req_item2_name]

                    # Check if the selected items match the required items (order doesn't matter)
                    match = (item1_name == req_item1_name and item2_name == req_item2_name) or \
                            (item1_name == req_item2_name and item2_name == req_item1_name)

                    if match:
                        # Check if the agent actually has enough quantity of both ingredients
                        has_enough_item1 = inventory.get(req_item1_name, 0) >= req_item1_count
                        has_enough_item2 = inventory.get(req_item2_name, 0) >= req_item2_count

                        # Check if recipe is already known
                        is_known = self.knows_recipe(recipe_name)

                        if has_enough_item1 and has_enough_item2 and not is_known:
                            # DISCOVERY! Add the recipe and return its name
                            self.add_recipe(recipe_name)
                            return recipe_name # Return the name of the discovered recipe

        except Exception as e:
            # Catch potential errors during random choice or dict access if inventory/recipes are weird
            print(f"Error during invention attempt for Agent {self.agent_id}: {e}")
            return None

        return None # No new 2-item recipe discovered this attempt


    # --- Phase 4: Social Knowledge ---
    def update_relationship(self, other_agent_id, change):
        current = self.relationships.get(other_agent_id, 0)
        self.relationships[other_agent_id] = max(-1.0, min(1.0, current + change))
        # print(f"Agent {self.agent_id} relationship with {other_agent_id}: {self.relationships[other_agent_id]:.2f}") # Debug

    def get_relationship(self, other_agent_id):
        return self.relationships.get(other_agent_id, 0) # Default neutral (0)