# Contents of knowledge.py
# knowledge.py
import random
import config as cfg
import traceback # For debugging invention

class KnowledgeSystem:
    """
    Manages an agent's knowledge about the world, including resource locations,
    crafting recipes, and social relationships. Phase 4: Includes relationships.
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

        # --- Phase 4: Social Knowledge ---
        # other_agent_id -> relationship_score (-1.0 to 1.0)
        self.relationships = {}

    def add_resource_location(self, resource_type, x, y):
        """ Adds a resource location to the agent's memory. """
        if resource_type in self.known_resource_locations:
             if (x, y) not in self.known_resource_locations[resource_type]:
                 self.known_resource_locations[resource_type].add((x, y))
                 # Optional: Add debug log (kept false by default in config now)
                 # if cfg.DEBUG_KNOWLEDGE: ...

    def remove_resource_location(self, resource_type, x, y):
         """ Removes a resource location (e.g., if found depleted or destroyed). """
         if resource_type in self.known_resource_locations:
              if (x,y) in self.known_resource_locations[resource_type]:
                   self.known_resource_locations[resource_type].discard((x, y))
                   # Optional: Add debug log
                   # if cfg.DEBUG_KNOWLEDGE: ...

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
        if not inventory or len(inventory) < cfg.INVENTION_ITEM_TYPES_THRESHOLD: return None
        if cfg.DEBUG_INVENTION: print(f"Agent {self.agent_id} attempting invention with inventory: {inventory}")

        available_items = list(inventory.keys())
        discovered_recipe = None
        invention_attempts = 3

        for _ in range(invention_attempts):
            num_items_to_combine = random.randint(2, min(3, len(available_items)))
            items_to_try = set(random.sample(available_items, num_items_to_combine))
            if cfg.DEBUG_INVENTION: print(f"  Trying combination: {items_to_try}")

            for recipe_name, details in cfg.RECIPES.items():
                if self.knows_recipe(recipe_name): continue
                try:
                    ingredients = details.get('ingredients', {})
                    if not ingredients: continue
                    ingredient_items = set(ingredients.keys())
                    if items_to_try != ingredient_items: continue

                    has_enough = all(inventory.get(item, 0) >= count for item, count in ingredients.items())
                    if not has_enough: continue

                    skill_req = details.get('skill'); min_level = details.get('min_level', 0)
                    if skill_req and skills.get(skill_req, 0) < min_level:
                         if cfg.DEBUG_INVENTION: print(f"    -> Potential {recipe_name}, but skill '{skill_req}' too low ({skills.get(skill_req, 0):.1f} < {min_level})")
                         continue

                    if self.add_recipe(recipe_name):
                        if cfg.DEBUG_INVENTION: print(f"  >>> Agent {self.agent_id} DISCOVERED recipe: {recipe_name}!")
                        discovered_recipe = recipe_name; break
                except Exception as e:
                     print(f"!!! Error checking recipe {recipe_name} during invention for agent {self.agent_id}: {e}"); traceback.print_exc(); continue
            if discovered_recipe: break

        if not discovered_recipe and cfg.DEBUG_INVENTION: print(f"  Agent {self.agent_id} failed to invent anything this time.")
        return discovered_recipe

    # --- Phase 4: Social Knowledge Methods ---
    def update_relationship(self, other_agent_id, change):
        """ Updates the relationship score with another agent, clamping between -1.0 and 1.0. """
        if other_agent_id == self.agent_id: return # Cannot have relationship with self
        current = self.relationships.get(other_agent_id, 0.0)
        new_score = max(-1.0, min(1.0, current + change))
        if abs(new_score - current) > 0.01: # Only update if change is significant
             self.relationships[other_agent_id] = new_score
             if cfg.DEBUG_SOCIAL: print(f"Agent {self.agent_id} relationship with Agent {other_agent_id}: {current:.2f} -> {new_score:.2f} (Change: {change:.2f})")

    def get_relationship(self, other_agent_id):
        """ Gets the relationship score with another agent (default 0). """
        if other_agent_id == self.agent_id: return 0.0 # Relationship with self is neutral
        return self.relationships.get(other_agent_id, 0.0)

    def decay_relationships(self, dt_sim_seconds):
        """ Slowly moves all relationships towards 0. """
        decay_amount = cfg.RELATIONSHIP_DECAY_RATE * dt_sim_seconds
        if decay_amount == 0: return # No decay if rate is zero or dt is zero

        # Iterate over a copy of keys in case relationship is removed (e.g., goes exactly to 0)
        for other_id in list(self.relationships.keys()):
             current_score = self.relationships[other_id]
             if current_score > 0:
                 new_score = max(0.0, current_score - decay_amount)
             elif current_score < 0:
                 new_score = min(0.0, current_score + decay_amount)
             else: # Already neutral
                 continue

             if abs(new_score) < 0.01: # Remove if very close to zero
                  del self.relationships[other_id]
                  # Optional debug log for removal due to decay
                  # if cfg.DEBUG_SOCIAL: print(f"Agent {self.agent_id} relationship with {other_id} decayed to neutral.")
             elif abs(new_score - current_score) > 0.001 : # Update only if changed noticeably
                  self.relationships[other_id] = new_score
                  # Optional debug log for decay step
                  # if cfg.DEBUG_SOCIAL: print(f"Agent {self.agent_id} relationship with {other_id} decayed: {current_score:.2f} -> {new_score:.2f}")