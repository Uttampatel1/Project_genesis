# knowledge.py
import random
import config as cfg
import traceback # For debugging invention

class KnowledgeSystem:
    """
    Manages an agent's knowledge about the world, including resource locations,
    crafting recipes, and social relationships.
    """
    def __init__(self, agent_id):
        """ Initializes the knowledge base for a specific agent. """
        self.agent_id = agent_id

        # Known locations: type -> set of (x,y) tuples for quick lookup
        self.known_resource_locations = {
            cfg.RESOURCE_FOOD: set(),
            cfg.RESOURCE_WATER: set(), # Stores specific water tiles interacted with
            cfg.RESOURCE_WOOD: set(),
            cfg.RESOURCE_STONE: set(),
            cfg.RESOURCE_WORKBENCH: set(), # Stores locations of known workbenches
        }

        # Known crafting recipes: set of recipe names (e.g., 'CrudeAxe')
        self.known_recipes = set()

        # Social relationships (Phase 4+): other_agent_id -> relationship_score (-1.0 to 1.0)
        self.relationships = {}

    def add_resource_location(self, resource_type, x, y):
        """ Adds a resource location to the agent's memory. """
        if resource_type in self.known_resource_locations:
             # Add only if not already known
             if (x, y) not in self.known_resource_locations[resource_type]:
                 self.known_resource_locations[resource_type].add((x, y))
                 if cfg.DEBUG_KNOWLEDGE:
                     res_name = cfg.RESOURCE_INFO.get(resource_type, {}).get('name')
                     # Handle water display name explicitly
                     display_name = "Water" if resource_type == cfg.RESOURCE_WATER else res_name if res_name else '?'
                     print(f"Agent {self.agent_id} learned location of {display_name} at ({x},{y})")
                 # Optional: Implement memory limits (e.g., prune oldest/farthest if set grows too large)

    def remove_resource_location(self, resource_type, x, y):
         """ Removes a resource location (e.g., if found depleted or destroyed). """
         if resource_type in self.known_resource_locations:
              # Use discard() which doesn't raise error if item not found
              if (x,y) in self.known_resource_locations[resource_type]:
                   self.known_resource_locations[resource_type].discard((x, y))
                   if cfg.DEBUG_KNOWLEDGE:
                        res_name = cfg.RESOURCE_INFO.get(resource_type, {}).get('name')
                        display_name = "Water" if resource_type == cfg.RESOURCE_WATER else res_name if res_name else '?'
                        print(f"Agent {self.agent_id} forgot location of {display_name} at ({x},{y})")

    def get_known_locations(self, resource_type):
        """ Returns a list of known (x, y) locations for a given resource type. """
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
    def attempt_invention(self, inventory, skills):
        """
        Simulates an invention attempt by combining items from inventory.
        Currently uses a simple random combination check against unknown recipes.
        Requires being at a workbench (location check handled by Agent).
        Returns discovered recipe name or None.
        """
        # Basic checks: Need inventory, enough different item types
        if not inventory or len(inventory) < cfg.INVENTION_ITEM_TYPES_THRESHOLD:
             return None

        if cfg.DEBUG_INVENTION:
             print(f"Agent {self.agent_id} attempting invention with inventory: {inventory}")

        available_items = list(inventory.keys())
        discovered_recipe = None
        invention_attempts = 3 # How many combinations to try per cycle

        for _ in range(invention_attempts):
            # Pick 2 or 3 different items available in inventory (adjust complexity here)
            num_items_to_combine = random.randint(2, min(3, len(available_items)))
            items_to_try = set(random.sample(available_items, num_items_to_combine))

            if cfg.DEBUG_INVENTION: print(f"  Trying combination: {items_to_try}")

            # Check this combination against all UNKNOWN recipes in the config
            for recipe_name, details in cfg.RECIPES.items():
                if self.knows_recipe(recipe_name): continue # Skip already known recipes

                try:
                    ingredients = details.get('ingredients', {})
                    if not ingredients: continue # Skip recipes with no ingredients

                    ingredient_items = set(ingredients.keys())

                    # --- Invention Logic (Simple Matching) ---
                    # 1. Do the items we tried EXACTLY match the required ingredient types?
                    #    (This is a strict check, could be loosened later)
                    if items_to_try != ingredient_items:
                        continue

                    # 2. Do we have ENOUGH quantity of each required ingredient?
                    has_enough = True
                    for item, count in ingredients.items():
                        if inventory.get(item, 0) < count:
                            has_enough = False
                            break
                    if not has_enough:
                        continue # Don't have enough quantity even if types match

                    # 3. Do we meet the minimum SKILL requirement to figure this out?
                    skill_req = details.get('skill')
                    min_level = details.get('min_level', 0)
                    if skill_req and skills.get(skill_req, 0) < min_level:
                         if cfg.DEBUG_INVENTION:
                              print(f"    -> Potential recipe {recipe_name} matches items, but skill '{skill_req}' too low ({skills.get(skill_req, 0):.1f} < {min_level})")
                         continue # Skill too low

                    # --- DISCOVERY! ---
                    # All checks passed: items match, enough quantity, sufficient skill
                    if self.add_recipe(recipe_name): # Try adding, returns True if newly learned
                        if cfg.DEBUG_INVENTION:
                            print(f"  >>> Agent {self.agent_id} DISCOVERED recipe: {recipe_name}!")
                        discovered_recipe = recipe_name
                        break # Stop checking other recipes for this combination attempt

                except Exception as e: # Catch errors during recipe checking
                     print(f"!!! Error checking recipe {recipe_name} during invention for agent {self.agent_id}: {e}")
                     traceback.print_exc()
                     continue # Skip to next recipe

            if discovered_recipe:
                break # Stop trying further combinations if one discovery was made

        if not discovered_recipe and cfg.DEBUG_INVENTION:
             print(f"  Agent {self.agent_id} failed to invent anything this time.")

        return discovered_recipe


    # --- Phase 4: Social Knowledge (Placeholder) ---
    def update_relationship(self, other_agent_id, change):
        """ Updates the relationship score with another agent. """
        if other_agent_id == self.agent_id: return # Cannot have relationship with self
        current = self.relationships.get(other_agent_id, 0)
        self.relationships[other_agent_id] = max(-1.0, min(1.0, current + change))
        # Optional: Add debug log for relationship changes

    def get_relationship(self, other_agent_id):
        """ Gets the relationship score with another agent (default 0). """
        if other_agent_id == self.agent_id: return 0.0 # Relationship with self is neutral
        return self.relationships.get(other_agent_id, 0)