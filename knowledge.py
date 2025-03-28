# knowledge.py
import random
import config as cfg

class KnowledgeSystem:
    def __init__(self, agent_id):
        self.agent_id = agent_id
        # Known locations: type -> set of (x,y) tuples for quick lookup
        self.known_resource_locations = {res_type: set() for res_type in cfg.RESOURCE_INFO.keys()}
        self.known_resource_locations[cfg.RESOURCE_WATER] = set() # Add water explicitly if needed

        self.known_recipes = set() # set of recipe names (e.g., 'CrudeAxe')
        self.relationships = {} # other_agent_id: relationship_score (-1.0 to 1.0)

    def add_resource_location(self, resource_type, x, y):
        # Use sets for efficient add/check/remove
        if resource_type in self.known_resource_locations:
             self.known_resource_locations[resource_type].add((x, y))
             # Limit memory? Could prune oldest or farthest if set gets too large.

    def remove_resource_location(self, resource_type, x, y):
         if resource_type in self.known_resource_locations:
              self.known_resource_locations[resource_type].discard((x, y)) # discard doesn't raise error if not found

    def get_known_locations(self, resource_type):
        # Returns a list of known locations (convert from set)
        return list(self.known_resource_locations.get(resource_type, set()))

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
        Tries combining two items (types) from inventory and checks if they match
        an unknown recipe. Improved logic.
        """
        if not inventory: return None

        available_item_types = list(inventory.keys())
        if not available_item_types: return None

        # Choose first item type
        item1_name = random.choice(available_item_types)
        item1_count = inventory.get(item1_name, 0)

        # Choose second item type (can be same as first if count >= 2)
        possible_second_items = available_item_types[:]
        if item1_count < 2:
             if item1_name in possible_second_items:
                 possible_second_items.remove(item1_name) # Cannot pick same again

        if not possible_second_items: return None # No valid second item combination possible

        item2_name = random.choice(possible_second_items)
        item2_count = inventory.get(item2_name, 0)

        # Create the 'combination' signature (order doesn't matter)
        combination = tuple(sorted((item1_name, item2_name)))

        # Check against predefined (but potentially unknown) recipes
        for recipe_name, details in cfg.RECIPES.items():
             if self.knows_recipe(recipe_name): continue # Skip known recipes

             ingredients_needed = details.get('ingredients', {})
             # Check if this recipe uses exactly the two combined item types
             recipe_req_items = tuple(sorted(ingredients_needed.keys()))

             if combination == recipe_req_items:
                  # Check if the agent actually has enough quantity of both ingredients
                  req_item1_name = recipe_req_items[0]
                  req_item1_needed = ingredients_needed[req_item1_name]
                  has_enough_item1 = inventory.get(req_item1_name, 0) >= req_item1_needed

                  # Handle recipes with only one type of ingredient (e.g., 2 wood -> ?)
                  if len(recipe_req_items) == 1:
                      if has_enough_item1:
                          self.add_recipe(recipe_name)
                          return recipe_name
                  # Handle two different ingredient types
                  elif len(recipe_req_items) == 2:
                      req_item2_name = recipe_req_items[1]
                      req_item2_needed = ingredients_needed[req_item2_name]
                      has_enough_item2 = inventory.get(req_item2_name, 0) >= req_item2_needed

                      if has_enough_item1 and has_enough_item2:
                          self.add_recipe(recipe_name)
                          return recipe_name # Return the name of the discovered recipe

        return None # No new recipe discovered this attempt

    # --- Phase 4: Social Knowledge ---
    def update_relationship(self, other_agent_id, change):
        if other_agent_id == self.agent_id: return # Cannot have relationship with self
        current = self.relationships.get(other_agent_id, 0)
        self.relationships[other_agent_id] = max(-1.0, min(1.0, current + change))
        # print(f"Agent {self.agent_id} relationship with {other_agent_id}: {self.relationships[other_agent_id]:.2f}") # Debug

    def get_relationship(self, other_agent_id):
        if other_agent_id == self.agent_id: return 1.0 # Max relationship with self? Or 0? Let's use 0.
        return self.relationships.get(other_agent_id, 0) # Default neutral (0)