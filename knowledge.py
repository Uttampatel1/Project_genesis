import random
import config as cfg

class KnowledgeSystem:
    def __init__(self, agent_id):
        self.agent_id = agent_id
        # Known locations: type -> set of (x,y) tuples for quick lookup
        self.known_resource_locations = {
            cfg.RESOURCE_FOOD: set(),
            cfg.RESOURCE_WATER: set(),
            cfg.RESOURCE_WOOD: set(),  # Phase 2
            cfg.RESOURCE_STONE: set(), # Phase 2
            cfg.RESOURCE_WORKBENCH: set(), # Phase 3+
        }

        self.known_recipes = set() # set of recipe names (e.g., 'CrudeAxe') - Phase 2+
        self.relationships = {} # other_agent_id: relationship_score (-1.0 to 1.0) - Phase 4+

    def add_resource_location(self, resource_type, x, y):
        """ Adds a resource location to the agent's memory. """
        if resource_type in self.known_resource_locations:
             if (x, y) not in self.known_resource_locations[resource_type]:
                 self.known_resource_locations[resource_type].add((x, y))
                 if cfg.DEBUG_KNOWLEDGE: print(f"Agent {self.agent_id} learned location of {cfg.RESOURCE_INFO.get(resource_type,{}).get('name','?')} at ({x},{y})")
                 # Optional: Limit memory size (e.g., prune oldest or farthest if set gets too large)

    def remove_resource_location(self, resource_type, x, y):
         """ Removes a resource location (e.g., if found depleted). """
         if resource_type in self.known_resource_locations:
              if (x, y) in self.known_resource_locations[resource_type]:
                   self.known_resource_locations[resource_type].discard((x, y))
                   if cfg.DEBUG_KNOWLEDGE: print(f"Agent {self.agent_id} forgot location of {cfg.RESOURCE_INFO.get(resource_type,{}).get('name','?')} at ({x},{y})")

    def get_known_locations(self, resource_type):
        """ Returns a list of known locations for a given resource type. """
        return list(self.known_resource_locations.get(resource_type, set()))

    def add_recipe(self, recipe_name):
        """ Adds a learned recipe to the agent's knowledge. Returns True if newly learned."""
        if recipe_name in cfg.RECIPES and recipe_name not in self.known_recipes:
            self.known_recipes.add(recipe_name)
            if cfg.DEBUG_KNOWLEDGE: print(f"Agent {self.agent_id} learned recipe: {recipe_name}")
            return True
        return False

    def knows_recipe(self, recipe_name):
        """ Checks if the agent knows a specific recipe. """
        return recipe_name in self.known_recipes

    # --- Phase 3: Invention ---
    def attempt_invention(self, inventory):
        """
        Tries combining items from inventory to discover unknown recipes.
        (Placeholder for Phase 3 - current logic is basic random combo).
        Returns discovered recipe name or None.
        """
        if not inventory or len(inventory) < 2: return None # Need at least two item types

        # Simple random combination attempt
        item1_name = random.choice(list(inventory.keys()))
        item2_name = random.choice(list(inventory.keys()))

        # Check against unknown recipes
        for recipe_name, details in cfg.RECIPES.items():
             if self.knows_recipe(recipe_name): continue # Skip known

             ingredients = details.get('ingredients', {})
             # Very basic check: does the recipe use roughly the items we picked?
             # This needs significant improvement for a real invention system.
             if item1_name in ingredients and item2_name in ingredients:
                  # Check if we actually have enough
                  has_enough = True
                  for item, count in ingredients.items():
                      if inventory.get(item, 0) < count:
                          has_enough = False; break
                  if has_enough:
                      # Found a potential match!
                      if self.add_recipe(recipe_name): # Try adding, returns True if new
                          return recipe_name # Return the name of the discovered recipe

        return None # No new recipe discovered this attempt


    # --- Phase 4: Social Knowledge ---
    def update_relationship(self, other_agent_id, change):
        if other_agent_id == self.agent_id: return # Cannot have relationship with self
        current = self.relationships.get(other_agent_id, 0)
        self.relationships[other_agent_id] = max(-1.0, min(1.0, current + change))

    def get_relationship(self, other_agent_id):
        if other_agent_id == self.agent_id: return 0.0 # Relationship with self is neutral/irrelevant
        return self.relationships.get(other_agent_id, 0) # Default neutral (0)