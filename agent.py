# agent.py
import random
import math
import config as cfg
from pathfinding_utils import find_path
from knowledge import KnowledgeSystem
# Note: GridNode is used internally by pathfinding, no need to import explicitly usually

_agent_id_counter = 0

class Agent:
    def __init__(self, x, y, world):
        global _agent_id_counter
        self.id = _agent_id_counter
        _agent_id_counter += 1

        self.x = x
        self.y = y
        self.world = world # Reference to the world object

        # Core Attributes
        self.health = cfg.MAX_HEALTH
        self.energy = cfg.MAX_ENERGY
        self.hunger = 0 # Starts not hungry
        self.thirst = 0 # Starts not thirsty

        # State & Action
        self.current_action = None # e.g., "Moving", "Eating", "Resting"
        self.action_target = None # Dict containing target info: {'type': 'location'/'agent', 'goal': (x,y)/id, 'stand':(x,y)}
        self.current_path = [] # List of GridNode objects for movement from pathfinding library
        self.action_timer = 0.0 # Time spent on current action segment (e.g., gathering)

        # --- Phase 1 Additions ---
        # Simple memory replaced by knowledge system
        # self.last_known_water_pos = None
        # self.last_known_food_pos = None

        # --- Phase 2 Additions ---
        self.inventory = {} # item_name: count
        self.skills = { # skill_name: level (0-100)
            'GatherWood': cfg.INITIAL_SKILL_LEVEL,
            'GatherStone': cfg.INITIAL_SKILL_LEVEL,
            'BasicCrafting': cfg.INITIAL_SKILL_LEVEL,
            # Add more skills (e.g., specific crafting, social skills)
        }

        # --- Phase 3 Additions ---
        self.knowledge = KnowledgeSystem(self.id) # More structured knowledge
        # Add attributes like Curiosity, Intelligence? (Could influence invention chance/utility)

        # --- Phase 4 Additions ---
        self.sociability = random.uniform(0.1, 0.9) # Example personality trait
        self.pending_signal = None # Store the latest signal received: (sender_id, signal_type, position)

    def update(self, dt_real_seconds, agents, social_manager):
        dt_sim_seconds = dt_real_seconds * cfg.SIMULATION_SPEED_FACTOR

        # 1. Update Needs & Health
        self._update_needs(dt_sim_seconds)

        # 2. Handle Death
        if self.health <= 0:
            self._handle_death()
            return # Agent is dead, no further updates

        # 3. Process Environment Signals (Phase 4+)
        self._process_signals() # Handle any signal received last tick

        # 4. Execute Current Action or Choose New One
        if self.current_action:
            action_complete = self._perform_action(dt_sim_seconds, agents, social_manager)
            if action_complete:
                self._complete_action() # Cleanup and allow choosing new action next tick
        else:
            # Choose a new action if idle
            self._choose_action(agents, social_manager)


    def _update_needs(self, dt_sim_seconds):
        # Decay needs over time
        self.hunger = min(cfg.MAX_HUNGER, self.hunger + cfg.HUNGER_INCREASE_RATE * dt_sim_seconds)
        self.thirst = min(cfg.MAX_THIRST, self.thirst + cfg.THIRST_INCREASE_RATE * dt_sim_seconds)

        if self.current_action != "Rest": # Check against base action name
            self.energy = max(0, self.energy - cfg.ENERGY_DECAY_RATE * dt_sim_seconds)
        else:
            # Resting restores energy and potentially health slowly
            self.energy = min(cfg.MAX_ENERGY, self.energy + cfg.ENERGY_REGEN_RATE * dt_sim_seconds)
            # Only regen health if somewhat rested and not starving/dehydrated
            if self.energy > cfg.MAX_ENERGY * 0.5 and self.hunger < cfg.MAX_HUNGER * 0.8 and self.thirst < cfg.MAX_THIRST * 0.8:
                self.health = min(cfg.MAX_HEALTH, self.health + cfg.HEALTH_REGEN_RATE * dt_sim_seconds)

        # Health drain if needs critical or no energy
        health_drain = 0
        if self.hunger >= cfg.MAX_HUNGER * 0.95: health_drain += 0.8
        if self.thirst >= cfg.MAX_THIRST * 0.95: health_drain += 1.0 # Thirst more critical
        if self.energy <= 0: health_drain += 0.5
        self.health -= health_drain * dt_sim_seconds

        # Clamp health
        self.health = max(0, self.health)


    def _choose_action(self, agents, social_manager):
        """ Basic Utility AI Decision Making """
        utilities = {}

        # --- Calculate Utility for Basic Needs ---
        # Use a curve to make needs more urgent as they approach maximum
        utilities['SatisfyThirst'] = (self.thirst / cfg.MAX_THIRST)**2 # Squared makes it grow faster near max
        utilities['SatisfyHunger'] = (self.hunger / cfg.MAX_HUNGER)**2
        # Utility to rest increases as energy decreases, but only consider if below threshold
        energy_deficit = (cfg.MAX_ENERGY - self.energy) / cfg.MAX_ENERGY
        utilities['Rest'] = energy_deficit**2 if self.energy < cfg.MAX_ENERGY * 0.7 else 0

        # --- Phase 2+: Resource Gathering ---
        # Utility based on how much is needed vs a goal amount
        has_axe = self.inventory.get('CrudeAxe', 0) > 0
        wood_goal = 10
        wood_need_factor = max(0, 1 - (self.inventory.get('Wood', 0) / wood_goal))
        utilities['GatherWood'] = wood_need_factor * 0.3 * (1.5 if has_axe else 0.5) # Base utility 0.3, scaled by need and tool

        stone_goal = 5
        stone_need_factor = max(0, 1 - (self.inventory.get('Stone', 0) / stone_goal))
        utilities['GatherStone'] = stone_need_factor * 0.3

        # --- Phase 2+: Crafting ---
        # Check known recipes, ingredients, skills
        best_craft_utility = 0
        best_craft_recipe = None
        for recipe_name in self.knowledge.known_recipes:
            details = cfg.RECIPES.get(recipe_name)
            if details and self._has_ingredients(details['ingredients']) and self._has_skill_for(details):
                # Base utility for being able to craft something potentially useful
                utility = 0.2
                # Specific goal-based boosts:
                if recipe_name == 'CrudeAxe' and not has_axe:
                    utility = 0.7 # High desire for first tool
                # Add more boosts (e.g., need shelter materials -> craft shelter components)

                if utility > best_craft_utility:
                    best_craft_utility = utility
                    best_craft_recipe = recipe_name
        if best_craft_recipe:
            utilities['Craft:' + best_craft_recipe] = best_craft_utility # Unique key per recipe

        # --- Phase 3+: Invention ---
        # Utility: Consider if needs are met (low need urgency) and have items to combine
        needs_met_factor = max(0, 1 - max(utilities.get('SatisfyThirst',0), utilities.get('SatisfyHunger',0), utilities.get('Rest',0)))
        can_invent = len(self.inventory) >= 2 # Simplistic check
        # Phase 3: Add workbench requirement check here if needed
        if can_invent:
            # Base utility low, increases if not busy with basic needs, plus randomness/curiosity
            utilities['Invent'] = 0.1 * needs_met_factor * random.uniform(0.8, 1.2)

        # --- Phase 4+: Social Actions ---
        # Utility for Helping: Find someone nearby who needs help
        target_to_help = self._find_agent_to_help(agents)
        if target_to_help:
             # Utility depends on target's need severity, agent's sociability, and relationship
             relationship_mod = (1 + self.knowledge.get_relationship(target_to_help.id)) / 2 # Scale 0 to 1
             help_need = max(target_to_help.hunger, target_to_help.thirst) # Example: help most urgent need
             help_utility = 0.6 * self.sociability * relationship_mod * (help_need / cfg.MAX_HUNGER) # Base 0.6
             utilities['Help:'+str(target_to_help.id)] = help_utility

        # Placeholder: Utility for Teaching/Learning - requires finding partners/checking skills

        # --- Default/Fallback Action ---
        utilities['Wander'] = 0.05 # Very low base utility, chosen if nothing else is pressing

        # --- Select Best Action ---
        best_action = None
        max_utility = -1 # Find the absolute highest utility

        if not utilities: # Should not happen with Wander included
             self.current_action = "Idle"
             print(f"Agent {self.id} has no utilities, becoming Idle.")
             return

        # Sort actions by utility, highest first
        sorted_utilities = sorted(utilities.items(), key=lambda item: item[1], reverse=True)
        # print(f"Agent {self.id} Utilities: {[(a, f'{u:.2f}') for a, u in sorted_utilities]}") # Debug

        # Iterate through sorted actions and pick the first one that is feasible
        for action, utility in sorted_utilities:
            # Only consider actions with positive utility, meeting a minimum threshold can also be added here
            if utility <= 0: # or utility < cfg.UTILITY_THRESHOLD:
                continue

            feasible = self._check_action_feasibility(action, agents) # Pass agents if needed for checks
            if feasible:
                best_action = action
                max_utility = utility
                break # Found the highest priority feasible action

        # If no action is feasible (e.g., trapped, no resources anywhere), check Wander or become Idle
        if not best_action:
            if self._check_action_feasibility('Wander', agents): # Check if wandering is possible
                best_action = 'Wander'
                max_utility = utilities.get('Wander', 0.05)
                print(f"Agent {self.id}: No primary action feasible, choosing Wander.")
            else:
                # Truly stuck or nothing to do
                best_action = "Idle"
                max_utility = 0
                print(f"Agent {self.id} becoming Idle (no feasible action, including Wander). Needs(H,T,E): ({self.hunger:.0f},{self.thirst:.0f},{self.energy:.0f})")


        # --- Initiate Action ---
        if self.current_action == best_action and best_action == "Idle": return # Don't restart idle

        self.current_action = best_action
        self.action_target = None # Reset target
        self.current_path = [] # Reset path
        self.action_timer = 0.0 # Reset action timer

        if best_action == "Idle": return # No further setup for Idle

        print(f"Agent {self.id} choosing action: {best_action} (Utility: {max_utility:.2f}) Needs(H,T,E): ({self.hunger:.0f},{self.thirst:.0f},{self.energy:.0f})")

        # Set target and plan path based on action
        target_setup_success = False
        try:
            if best_action == 'SatisfyThirst':
                # Find water tile (goal) and adjacent land tile (stand)
                target_pos, stand_pos, dist = self.world.find_nearest_resource(self.x, self.y, cfg.RESOURCE_WATER)
                if stand_pos: # Check if a standing position was found
                    self.action_target = {'type': 'location', 'goal': target_pos, 'stand': stand_pos}
                    self.current_path = self._plan_path(stand_pos)
                    target_setup_success = bool(self.current_path or (self.x, self.y) == stand_pos) # Success if path found or already there
            elif best_action == 'SatisfyHunger':
                target_pos, stand_pos, dist = self.world.find_nearest_resource(self.x, self.y, cfg.RESOURCE_FOOD)
                if stand_pos:
                    self.action_target = {'type': 'location', 'goal': target_pos, 'stand': stand_pos}
                    self.current_path = self._plan_path(stand_pos)
                    self.knowledge.add_resource_location(cfg.RESOURCE_FOOD, target_pos[0], target_pos[1]) # Remember location
                    target_setup_success = bool(self.current_path or (self.x, self.y) == stand_pos)
            elif best_action == 'GatherWood':
                 target_pos, stand_pos, dist = self.world.find_nearest_resource(self.x, self.y, cfg.RESOURCE_WOOD)
                 if stand_pos:
                     self.action_target = {'type': 'location', 'goal': target_pos, 'stand': stand_pos}
                     self.current_path = self._plan_path(stand_pos)
                     self.knowledge.add_resource_location(cfg.RESOURCE_WOOD, target_pos[0], target_pos[1])
                     target_setup_success = bool(self.current_path or (self.x, self.y) == stand_pos)
            elif best_action == 'GatherStone':
                 target_pos, stand_pos, dist = self.world.find_nearest_resource(self.x, self.y, cfg.RESOURCE_STONE)
                 if stand_pos:
                     self.action_target = {'type': 'location', 'goal': target_pos, 'stand': stand_pos}
                     self.current_path = self._plan_path(stand_pos)
                     self.knowledge.add_resource_location(cfg.RESOURCE_STONE, target_pos[0], target_pos[1])
                     target_setup_success = bool(self.current_path or (self.x, self.y) == stand_pos)
            elif best_action.startswith('Craft:'):
                 # Assumes crafting happens at current location for now
                 self.action_target = {'type': 'craft', 'recipe': best_action.split(':')[1]}
                 # Phase 3: If recipe requires workbench, find nearest and path to it here.
                 target_setup_success = True # No movement needed initially
            elif best_action == 'Invent':
                 # Assumes inventing happens at current location for now
                 self.action_target = {'type': 'invent'}
                 # Phase 3: If requires workbench, find nearest and path to it here.
                 target_setup_success = True # No movement needed initially
            elif best_action.startswith('Help:'):
                target_id = int(best_action.split(':')[1])
                target_agent = next((a for a in agents if a.id == target_id), None)
                if target_agent:
                    # Path to a nearby tile to the target agent
                    stand_pos = self._find_adjacent_walkable(target_agent.x, target_agent.y)
                    if stand_pos:
                        self.action_target = {'type': 'agent', 'goal': target_agent.id, 'stand': stand_pos}
                        self.current_path = self._plan_path(stand_pos)
                        target_setup_success = bool(self.current_path or (self.x, self.y) == stand_pos)
                    else: print(f"Agent {self.id}: Cannot find spot near target agent {target_id} for Help.")
            elif best_action == 'Rest':
                 self.action_target = {'type': 'rest'}
                 target_setup_success = True # No movement needed
            elif best_action == 'Wander':
                wander_target = None
                for _ in range(10): # Try finding a random walkable target nearby
                     wx = self.x + random.randint(-cfg.WANDER_RADIUS, cfg.WANDER_RADIUS)
                     wy = self.y + random.randint(-cfg.WANDER_RADIUS, cfg.WANDER_RADIUS)
                     # Ensure within bounds and walkable
                     if 0 <= wx < self.world.width and 0 <= wy < self.world.height and self.world.walkability_matrix[wy, wx] == 1:
                          wander_target = (wx, wy)
                          break
                if wander_target:
                    self.action_target = {'type': 'wander', 'stand': wander_target}
                    self.current_path = self._plan_path(wander_target)
                    # Success if path found or already at target (unlikely for wander)
                    target_setup_success = bool(self.current_path or (self.x, self.y) == wander_target)
                else:
                    print(f"Agent {self.id}: Could not find a wander target nearby.")
                    target_setup_success = False # Failed to find target

        except Exception as e:
             print(f"Error during action setup for {best_action}: {e}")
             target_setup_success = False


        # If setting up the target/path failed, clear the action -> Idle or re-evaluate next tick
        if not target_setup_success:
             print(f"Agent {self.id}: Failed to initiate action {best_action}. Clearing action.")
             self.current_action = "Idle" # Revert to Idle state
             self.action_target = None
             self.current_path = []


    def _check_action_feasibility(self, action_name, agents):
        """ Checks if resources/targets exist and path might be possible """
        # Note: This is a preliminary check. Pathfinding might still fail later.
        if action_name == 'SatisfyThirst':
            _, stand_pos, _ = self.world.find_nearest_resource(self.x, self.y, cfg.RESOURCE_WATER)
            return stand_pos is not None
        elif action_name == 'SatisfyHunger':
            _, stand_pos, _ = self.world.find_nearest_resource(self.x, self.y, cfg.RESOURCE_FOOD)
            return stand_pos is not None
        elif action_name == 'GatherWood':
             _, stand_pos, _ = self.world.find_nearest_resource(self.x, self.y, cfg.RESOURCE_WOOD)
             return stand_pos is not None
        elif action_name == 'GatherStone':
             _, stand_pos, _ = self.world.find_nearest_resource(self.x, self.y, cfg.RESOURCE_STONE)
             return stand_pos is not None
        elif action_name.startswith('Craft:'):
             recipe_name = action_name.split(':')[1]
             details = cfg.RECIPES.get(recipe_name)
             # Phase 3+: Add check for workbench nearby if details['workbench'] is True
             return details and self.knowledge.knows_recipe(recipe_name) and self._has_ingredients(details['ingredients']) and self._has_skill_for(details)
        elif action_name == 'Invent':
             # Phase 3+: Add check for workbench nearby?
             return len(self.inventory) >= 2
        elif action_name.startswith('Help:'):
             # Feasibility (target exists and needs help) checked during utility calculation.
             # Check if we have the means (e.g., food)
             target_id = int(action_name.split(':')[1])
             target_agent = next((a for a in agents if a.id == target_id), None)
             if not target_agent: return False # Target doesn't exist anymore
             if target_agent.hunger > cfg.MAX_HUNGER * 0.7 and self.inventory.get('Food', 0) > 0: return True
             # Add checks for other types of help (water, etc.)
             return False # Cannot help this target currently
        elif action_name == 'Wander':
             # Check if *any* adjacent tile is walkable? Crude check for being trapped.
             for dx, dy in [(0,1), (0,-1), (1,0), (-1,0)]:
                  nx, ny = self.x + dx, self.y + dy
                  if 0 <= nx < self.world.width and 0 <= ny < self.world.height and self.world.walkability_matrix[ny, nx] == 1:
                      return True
             return False # Trapped
        elif action_name == "Idle":
             return True # Idle is always feasible
        elif action_name == "Rest":
             return True # Rest is always feasible (can rest anywhere for now)
        # Unknown action
        return False


    def _plan_path(self, target_pos):
        """ Finds a path using A*, returns list of GridNode objects """
        start_pos = (self.x, self.y)
        if not target_pos or start_pos == target_pos:
            return [] # Already there or no target

        # Ensure target is within bounds
        tx, ty = target_pos
        if not (0 <= tx < self.world.width and 0 <= ty < self.world.height):
            print(f"Agent {self.id}: Target {target_pos} is out of bounds.")
            return []

        # Check walkability before calling pathfinder
        if self.world.walkability_matrix[ty, tx] == 0:
            # Target itself is not walkable, try finding adjacent walkable instead
            adj_target = self._find_adjacent_walkable(tx, ty)
            if not adj_target:
                 print(f"Agent {self.id}: Target {target_pos} is unwalkable and no adjacent walkable found.")
                 return []
            # print(f"Agent {self.id}: Target {target_pos} unwalkable, rerouting to {adj_target}")
            target_pos = adj_target

        # If start pos is somehow unwalkable (shouldn't happen if agent moves correctly)
        if self.world.walkability_matrix[start_pos[1], start_pos[0]] == 0:
             print(f"Agent {self.id}: Starting position {start_pos} is unwalkable!")
             # Try finding adjacent walkable to start from? Complex recovery. For now, fail path.
             return []


        path_nodes = find_path(self.world.walkability_matrix, start_pos, target_pos)

        # Debug path output
        # path_coords = [ (n.x, n.y) for n in path_nodes] if path_nodes else "None"
        # print(f"Agent {self.id} Path from {start_pos} to {target_pos}: {path_coords}")

        return path_nodes


    def _perform_action(self, dt_sim_seconds, agents, social_manager):
        """ Executes the current action step, returns True if completed """
        if not self.current_action or self.current_action == "Idle":
             return True # Idle completes immediately (or action was cleared)

        action_type = self.current_action.split(':')[0] # Get base action type

        # --- 1. Movement Phase (if path exists) ---
        if self.current_path:
            target_node = self.current_path[0]
            # --- CORRECTED ACCESS to GridNode attributes ---
            target_x = target_node.x
            target_y = target_node.y

            # Simple grid movement: Move one cell per update tick towards the target node
            move_dist = 1 # Assume moved one cell

            # Update position (teleport to next cell in path)
            self.x = target_x
            self.y = target_y
            self.energy -= cfg.MOVE_ENERGY_COST * move_dist # Apply energy cost

            # Remove the reached node from the path
            self.current_path.pop(0)
            # --- END CORRECTION ---

            # Action is not complete yet, still moving (unless path is now empty)
            return False

        # --- 2. Action Execution Phase (at target location, path is empty) ---
        self.action_timer += dt_sim_seconds
        base_action_duration = 1.0 # Base seconds per action unit (can be modified by skill)

        try:
            # Check if action target is valid (e.g., resource still exists) before acting
            if self.action_target and 'goal' in self.action_target:
                 if self.action_target['type'] == 'location':
                     goal_x, goal_y = self.action_target['goal']
                     stand_x, stand_y = self.action_target['stand']
                     # Ensure agent is at the standing position
                     if self.x != stand_x or self.y != stand_y:
                         print(f"Agent {self.id}: Misaligned for action {self.current_action} at ({self.x},{self.y}), expected stand at ({stand_x},{stand_y}). Completing action.")
                         return True # Path ended but not at correct spot, fail action

                 elif self.action_target['type'] == 'agent':
                      target_id = self.action_target['goal']
                      target_agent = next((a for a in agents if a.id == target_id and a.health > 0), None)
                      if not target_agent:
                           print(f"Agent {self.id}: Target agent {target_id} for action {self.current_action} not found. Completing action.")
                           return True # Target agent gone

            # --- Phase 1 Actions ---
            if self.current_action == 'SatisfyThirst':
                target_x, target_y = self.action_target['goal'] # Water tile coords
                # Perform drink (fast action)
                action_duration = base_action_duration * 0.5
                if self.action_timer >= action_duration:
                    self.thirst = max(0, self.thirst - cfg.DRINK_THIRST_REDUCTION)
                    print(f"Agent {self.id} drank. Thirst: {self.thirst:.0f}")
                    return True # Drink action complete
                else: return False # Still drinking

            elif self.current_action == 'SatisfyHunger':
                target_x, target_y = self.action_target['goal'] # Food resource coords
                resource = self.world.get_resource(target_x, target_y)
                if resource and resource.type == cfg.RESOURCE_FOOD and not resource.is_depleted():
                    action_duration = base_action_duration * 0.5
                    if self.action_timer >= action_duration:
                        amount = self.world.consume_resource_at(target_x, target_y, 1)
                        if amount > 0:
                            self.hunger = max(0, self.hunger - cfg.EAT_HUNGER_REDUCTION)
                            print(f"Agent {self.id} ate. Hunger: {self.hunger:.0f}")
                        return True # Eating complete (even if resource depleted just now)
                    else: return False # Still eating
                else: # Resource disappeared or depleted before eating
                    print(f"Agent {self.id} failed to eat at {(target_x, target_y)} - resource gone.")
                    if cfg.RESOURCE_FOOD in self.knowledge.known_resource_locations: # Forget location
                         if (target_x, target_y) in self.knowledge.known_resource_locations[cfg.RESOURCE_FOOD]:
                             self.knowledge.known_resource_locations[cfg.RESOURCE_FOOD].remove((target_x, target_y))
                    return True # Action failed/complete

            elif self.current_action == 'Rest':
                # Resting continues until energy is full OR a critical need arises
                high_thirst = self.thirst > cfg.MAX_THIRST * 0.9
                high_hunger = self.hunger > cfg.MAX_HUNGER * 0.9
                if self.energy >= cfg.MAX_ENERGY or high_thirst or high_hunger:
                    print(f"Agent {self.id} finished resting. Energy: {self.energy:.0f}")
                    return True # Stop resting
                # Continue resting (energy gain happens in _update_needs)
                return False

            elif self.current_action == 'Wander':
                # Wander completes once destination is reached (which means path is empty here)
                return True

            # --- Phase 2 Actions ---
            elif self.current_action == 'GatherWood':
                 target_x, target_y = self.action_target['goal']
                 resource = self.world.get_resource(target_x, target_y)
                 if resource and resource.type == cfg.RESOURCE_WOOD and not resource.is_depleted():
                     action_duration = base_action_duration / self._get_skill_multiplier('GatherWood')
                     if self.action_timer >= action_duration:
                         amount = self.world.consume_resource_at(target_x, target_y, 1)
                         if amount > 0:
                             self.inventory['Wood'] = self.inventory.get('Wood', 0) + amount
                             self.energy -= cfg.GATHER_ENERGY_COST
                             self.learn_skill('GatherWood')
                             print(f"Agent {self.id} gathered Wood. Total: {self.inventory.get('Wood', 0)}. Skill: {self.skills.get('GatherWood',0):.1f}")
                             self.action_timer = 0 # Reset timer for next unit
                             # Check stopping conditions
                             inventory_full = sum(self.inventory.values()) >= 20 # Example limit
                             if self.inventory.get('Wood', 0) >= 10 or inventory_full or self.energy < cfg.GATHER_ENERGY_COST * 2:
                                  return True # Stop gathering
                             else:
                                  return False # Continue gathering from this source
                         else: # Resource depleted during attempt
                              print(f"Agent {self.id} failed to gather wood (depleted during attempt).")
                              return True
                     else: return False # Still gathering this unit
                 else: # Resource gone/depleted before starting
                     print(f"Agent {self.id} failed to gather wood at {(target_x, target_y)} - resource gone.")
                     if cfg.RESOURCE_WOOD in self.knowledge.known_resource_locations: # Forget location
                         if (target_x, target_y) in self.knowledge.known_resource_locations[cfg.RESOURCE_WOOD]:
                              self.knowledge.known_resource_locations[cfg.RESOURCE_WOOD].remove((target_x, target_y))
                     return True

            elif self.current_action == 'GatherStone':
                 target_x, target_y = self.action_target['goal']
                 resource = self.world.get_resource(target_x, target_y)
                 if resource and resource.type == cfg.RESOURCE_STONE and not resource.is_depleted():
                     action_duration = base_action_duration / self._get_skill_multiplier('GatherStone')
                     if self.action_timer >= action_duration:
                         amount = self.world.consume_resource_at(target_x, target_y, 1)
                         if amount > 0:
                             self.inventory['Stone'] = self.inventory.get('Stone', 0) + amount
                             self.energy -= cfg.GATHER_ENERGY_COST
                             self.learn_skill('GatherStone')
                             print(f"Agent {self.id} gathered Stone. Total: {self.inventory.get('Stone',0)}. Skill: {self.skills.get('GatherStone',0):.1f}")
                             self.action_timer = 0
                             inventory_full = sum(self.inventory.values()) >= 20
                             if self.inventory.get('Stone', 0) >= 5 or inventory_full or self.energy < cfg.GATHER_ENERGY_COST * 2: return True
                             else: return False
                         else:
                             print(f"Agent {self.id} failed to gather stone (depleted during attempt).")
                             return True
                     else: return False
                 else:
                     print(f"Agent {self.id} failed to gather stone at {(target_x, target_y)} - resource gone.")
                     if cfg.RESOURCE_STONE in self.knowledge.known_resource_locations: # Forget location
                         if (target_x, target_y) in self.knowledge.known_resource_locations[cfg.RESOURCE_STONE]:
                              self.knowledge.known_resource_locations[cfg.RESOURCE_STONE].remove((target_x, target_y))
                     return True

            elif action_type == 'Craft':
                 # Assumes crafting at current location
                 recipe_name = self.action_target['recipe']
                 details = cfg.RECIPES[recipe_name]
                 action_duration = base_action_duration * 2 / self._get_skill_multiplier(details['skill'])
                 if self.action_timer >= action_duration:
                     if not self._has_ingredients(details['ingredients']): # Double-check ingredients
                         print(f"Agent {self.id} cannot craft {recipe_name} - missing ingredients now.")
                         return True # Action failed
                     # Consume ingredients
                     for item, count in details['ingredients'].items():
                         self.inventory[item] = self.inventory.get(item, 0) - count
                         if self.inventory[item] <= 0: del self.inventory[item]
                     # Add result item
                     self.inventory[recipe_name] = self.inventory.get(recipe_name, 0) + 1
                     self.energy -= cfg.CRAFT_ENERGY_COST
                     self.learn_skill(details['skill'])
                     print(f"Agent {self.id} crafted {recipe_name}. Skill: {self.skills.get(details['skill'],0):.1f}")
                     social_manager.broadcast_signal(self, f"Crafted:{recipe_name}", (self.x, self.y)) # Announce crafting
                     return True # Crafting complete
                 else: return False # Still crafting

            # --- Phase 3 Actions ---
            elif self.current_action == 'Invent':
                 action_duration = base_action_duration * 3 # Invention takes time
                 if self.action_timer >= action_duration:
                     discovered_recipe = self.knowledge.attempt_invention(self.inventory)
                     self.energy -= cfg.CRAFT_ENERGY_COST # Invention costs energy
                     if discovered_recipe:
                         # Note: attempt_invention should add recipe to knowledge if successful
                         print(f"Agent {self.id} *** INVENTED *** {discovered_recipe}!")
                         social_manager.broadcast_signal(self, f"Invented:{discovered_recipe}", (self.x, self.y))
                     # else: # Failed invention attempt (optional print)
                     #    print(f"Agent {self.id} invention attempt yielded nothing.")
                     return True # Invention attempt complete (success or fail)
                 else: return False # Still thinking...

            # --- Phase 4 Actions ---
            elif action_type == 'Help':
                # Assumed agent is at 'stand' position near target
                target_id = self.action_target['goal']
                target_agent = next((a for a in agents if a.id == target_id and a.health > 0), None)
                if target_agent:
                     distance = abs(self.x - target_agent.x) + abs(self.y - target_agent.y)
                     if distance <= 2: # Check proximity again
                          # Attempt the actual help action via SocialManager (e.g., transfer item)
                          # This involves interaction logic (transfer food/water) inside attempt_helping
                          help_successful = social_manager.attempt_helping(self, target_agent)
                          if help_successful: print(f"Agent {self.id} successfully helped Agent {target_id}.")
                          # else: print(f"Agent {self.id} help attempt towards {target_id} failed (conditions not met?).")
                     else: print(f"Agent {self.id} too far from target {target_id} to help.")
                # else: print(f"Agent {self.id} cannot help target {target_id} (target gone).") # Already checked earlier

                return True # Help attempt is complete (success or fail in SocialManager)

            # --- Fallback ---
            else:
                print(f"Agent {self.id}: Unknown action {self.current_action} in perform_action step")
                return True # Unknown action, stop doing it

        except Exception as e:
            print(f"Error performing action {self.current_action} for agent {self.id}: {e}")
            import traceback
            traceback.print_exc()
            return True # Treat error as action completion/failure


    def _complete_action(self):
        """ Cleanup after an action is finished or failed """
        # print(f"Agent {self.id} completed action: {self.current_action}")
        self.current_action = None
        self.action_target = None
        self.current_path = []
        self.action_timer = 0.0

    def _handle_death(self):
        # This is called when health <= 0.
        # The main loop handles removing the agent from the active list.
        print(f"Agent {self.id} has died at ({self.x}, {self.y}).")
        # Future: Could drop items, leave a corpse object in the world, etc.

    # --- Phase 2: Skills & Crafting Helpers ---
    def learn_skill(self, skill_name, amount=cfg.SKILL_INCREASE_RATE):
        """ Increases skill level, learning by doing. Returns True if level increased. """
        # Allow learning base skills and skills implicitly defined by recipes
        is_known_skill_base = skill_name in self.skills
        is_recipe_skill = any(details.get('skill') == skill_name for details in cfg.RECIPES.values())

        if is_known_skill_base or is_recipe_skill:
            current_level = self.skills.get(skill_name, cfg.INITIAL_SKILL_LEVEL)
            if current_level < cfg.MAX_SKILL_LEVEL:
                # Diminishing returns: Learn faster at lower levels
                increase = amount * (1.0 - (current_level / (cfg.MAX_SKILL_LEVEL + 1)))
                new_level = min(cfg.MAX_SKILL_LEVEL, current_level + increase)
                # Only update if there's a noticeable increase (prevent float comparison issues)
                if new_level > current_level + 0.01:
                    self.skills[skill_name] = new_level
                    return True
        # Handle learning a completely new skill (e.g., via teaching, not tied to crafting)
        elif not is_known_skill_base:
             self.skills[skill_name] = min(cfg.MAX_SKILL_LEVEL, cfg.INITIAL_SKILL_LEVEL + amount)
             print(f"Agent {self.id} learned NEW base skill: {skill_name}")
             return True
        return False


    def _get_skill_multiplier(self, skill_name):
        """ Returns a multiplier based on skill level (e.g., for speed/efficiency) """
        level = self.skills.get(skill_name, 0)
        # Example: 1.0 at level 0, up to ~2.5 at max level (non-linear)
        multiplier = 1.0 + 1.5 * (level / cfg.MAX_SKILL_LEVEL)**0.75
        return max(0.1, multiplier) # Ensure multiplier doesn't go to zero or negative

    def _has_ingredients(self, ingredients):
        """ Check inventory for required crafting ingredients """
        if not ingredients: return True # No ingredients needed
        for item, required_count in ingredients.items():
            if self.inventory.get(item, 0) < required_count:
                return False
        return True

    def _has_skill_for(self, recipe_details):
        """ Check if agent has required skill level for recipe """
        skill_name = recipe_details.get('skill')
        min_level = recipe_details.get('min_level', 0)
        if not skill_name: return True # No skill required
        return self.skills.get(skill_name, 0) >= min_level

    # --- Phase 4: Social Helpers ---
    def perceive_signal(self, sender_id, signal_type, position):
        """ Stores the latest received signal for processing next update """
        self.pending_signal = (sender_id, signal_type, position)

    def _process_signals(self):
        """ Handle the latest received signal, potentially interrupting current action """
        if not self.pending_signal:
            return

        sender_id, signal_type, position = self.pending_signal
        self.pending_signal = None # Consume the signal

        # print(f"Agent {self.id} processing signal '{signal_type}' from {sender_id}") # Debug

        # Decide whether to react based on signal type, sender, agent's state
        relationship = self.knowledge.get_relationship(sender_id)
        current_action_util = self._get_current_action_utility()

        # Example Reactions:
        if signal_type == 'Danger':
            # High priority reaction, flee if utility is higher than current action
            flee_utility = 0.95 # Very high importance
            if flee_utility > current_action_util:
                 print(f"Agent {self.id} reacts to DANGER signal from {sender_id}! Fleeing.")
                 self._complete_action() # Interrupt current action forcefully
                 # Set a temporary 'Flee' state or just trigger Wander?
                 # Forcing Wander might make it wander towards danger, need specific flee logic.
                 # Simple immediate reaction: try to move directly away
                 dx = self.x - position[0]
                 dy = self.y - position[1]
                 norm = math.sqrt(dx*dx + dy*dy)
                 if norm > 0:
                     flee_x = int(self.x + dx / norm * cfg.WANDER_RADIUS) # Move further away
                     flee_y = int(self.y + dy / norm * cfg.WANDER_RADIUS)
                     flee_x = max(0, min(self.world.width - 1, flee_x))
                     flee_y = max(0, min(self.world.height - 1, flee_y))
                     # Find nearest walkable to the flee target
                     flee_target = self._find_walkable_near(flee_x, flee_y)
                     if flee_target:
                          self.current_action = 'Wander' # Use wander mechanism to move
                          self.action_target = {'type': 'wander', 'stand': flee_target}
                          self.current_path = self._plan_path(flee_target)
                     else: # Trapped or error
                          self.current_action = 'Idle' # Cannot flee

        elif signal_type == 'FoundFood':
            # React if hungry and trust sender enough, and if finding food is more important now
            food_signal_utility = (self.hunger / cfg.MAX_HUNGER)**2 * (1.0 + max(0, relationship)) # Use squared hunger, factor in trust
            if food_signal_utility > current_action_util and self.hunger > cfg.MAX_HUNGER * 0.3: # React even if only moderately hungry
                 print(f"Agent {self.id} reacting to food signal from {sender_id}")
                 self._complete_action() # Interrupt current action
                 # Set goal to investigate food source location
                 stand_pos = self._find_adjacent_walkable(position[0], position[1])
                 if stand_pos:
                      # Tentatively set action, _choose_action might override if thirst is critical
                      self.current_action = 'SatisfyHunger'
                      self.action_target = {'type': 'location_signal', 'goal': position, 'stand': stand_pos}
                      self.current_path = self._plan_path(stand_pos)
                      if not self.current_path and (self.x, self.y) != stand_pos: # Path failed?
                           self.current_action = None # Allow re-evaluation

        elif signal_type.startswith("Crafted:") or signal_type.startswith("Invented:"):
             # Passive learning: Learn recipe if close and relationship is okay
             item_name = signal_type.split(':')[1]
             if item_name in cfg.RECIPES and not self.knowledge.knows_recipe(item_name):
                  dist_sq = (self.x - position[0])**2 + (self.y - position[1])**2
                  learn_proximity_sq = 7**2 # Moderately close to hear/see?
                  if dist_sq < learn_proximity_sq and relationship >= -0.1: # Learn from non-hostile/neutral
                      # Add intelligence/curiosity check? Chance based?
                      if random.random() < 0.8: # 80% chance to learn from signal
                          self.knowledge.add_recipe(item_name)
                          print(f"Agent {self.id} learned recipe '{item_name}' from {sender_id}'s signal.")


    def decide_to_learn(self, teacher_id, skill_name):
        """ AI decides if it wants to accept teaching (called by SocialManager) """
        # Prioritize critical needs over learning
        if self.thirst > cfg.MAX_THIRST * 0.85 or self.hunger > cfg.MAX_HUNGER * 0.85:
            return False

        # Don't interrupt important actions like gathering critical resource?
        # if self.current_action and self._get_current_action_utility() > 0.7: return False

        # Check relationship with teacher
        relationship = self.knowledge.get_relationship(teacher_id)
        if relationship < 0.0: # Only learn from neutral or friendly?
            return False

        # Simple acceptance criteria
        print(f"Agent {self.id} accepts learning '{skill_name}' from {teacher_id}")
        # Could set a state 'BeingTaught' to pause other actions briefly
        # self._complete_action() # Interrupt current action to learn
        # self.current_action = "BeingTaught" # Example state
        return True

    def _find_agent_to_help(self, agents):
         """ Finds nearby agent in critical need that this agent *can* help """
         best_target = None
         max_weighted_need = 0 # Combine need level and relationship

         for other in agents:
              if other != self and other.health > 0: # Check living agents only
                   dist = abs(self.x - other.x) + abs(self.y - other.y)
                   if dist < 7: # Check within reasonable interaction range
                       need_level = 0
                       can_help_flag = False

                       # Check Hunger Need
                       if other.hunger > cfg.MAX_HUNGER * 0.75 and self.inventory.get('Food', 0) > 0:
                           need_level = max(need_level, (other.hunger / cfg.MAX_HUNGER)**2) # Squared need
                           can_help_flag = True

                       # Check Thirst Need (if agent can carry/give water)
                       # if other.thirst > cfg.MAX_THIRST * 0.75 and self.inventory.get('Waterskin', 0) > 0:
                       #    need_level = max(need_level, (other.thirst / cfg.MAX_THIRST)**2 * 1.1) # Thirst slightly more urgent
                       #    can_help_flag = True

                       if can_help_flag:
                           relationship = self.knowledge.get_relationship(other.id)
                           # Consider helping only if relationship is not too negative
                           if relationship > -0.3:
                               # Weight need by relationship (help friends more readily)
                               weighted_need = need_level * (1 + relationship) * self.sociability
                               if weighted_need > max_weighted_need:
                                   max_weighted_need = weighted_need
                                   best_target = other
         return best_target

    def _get_current_action_utility(self):
         """ Estimate utility of the current action (rough approximation) """
         if not self.current_action or self.current_action == 'Idle': return 0
         # Match utility calculations (using squared urgency for needs)
         if self.current_action == 'SatisfyThirst': return (self.thirst / cfg.MAX_THIRST)**2
         if self.current_action == 'SatisfyHunger': return (self.hunger / cfg.MAX_HUNGER)**2
         if self.current_action == 'Rest': return ((cfg.MAX_ENERGY - self.energy) / cfg.MAX_ENERGY)**2 if self.energy < cfg.MAX_ENERGY else 0

         # Assign rough estimates for other actions (can be refined)
         if self.current_action.startswith('Gather'): return 0.3
         if self.current_action.startswith('Craft'): return 0.4 # Crafting useful things has decent utility
         if self.current_action == ('Invent'): return 0.2
         if self.current_action.startswith('Help'): return 0.6 # Helping is considered important
         if self.current_action == ('Wander'): return 0.05

         return 0.1 # Default low utility for actions not explicitly estimated


    def _find_adjacent_walkable(self, x, y):
        """ Finds a walkable tile adjacent to (x, y), prioritizing cardinal directions """
        # Check cardinal directions first
        for dx, dy in [(0,1), (0,-1), (1,0), (-1,0)]:
            nx, ny = x + dx, y + dy
            if 0 <= nx < self.world.width and 0 <= ny < self.world.height:
                if self.world.walkability_matrix[ny, nx] == 1:
                    return (nx, ny)
        # Check diagonal directions if no cardinal found
        for dx, dy in [(1,1), (1,-1), (-1,1), (-1,-1)]:
            nx, ny = x + dx, y + dy
            if 0 <= nx < self.world.width and 0 <= ny < self.world.height:
                if self.world.walkability_matrix[ny, nx] == 1:
                    return (nx, ny)
        return None # No adjacent walkable found


    def _find_walkable_near(self, x, y):
         """ Finds the nearest walkable tile to x,y using BFS, limited search """
         if 0 <= x < self.world.width and 0 <= y < self.world.height and self.world.walkability_matrix[y, x] == 1:
             return (x, y) # Target itself is walkable

         q = [(x, y, 0)] # x, y, distance
         visited = set([(x,y)])
         max_search_dist = 5 # Limit search radius

         while q:
             curr_x, curr_y, dist = q.pop(0)
             if dist >= max_search_dist: continue

             for dx, dy in [(0,1), (0,-1), (1,0), (-1,0), (1,1), (1,-1), (-1,1), (-1,-1)]:
                 nx, ny = curr_x + dx, curr_y + dy
                 if 0 <= nx < self.world.width and 0 <= ny < self.world.height and (nx, ny) not in visited:
                     if self.world.walkability_matrix[ny, nx] == 1:
                         return (nx, ny) # Found nearest walkable
                     visited.add((nx, ny))
                     q.append((nx, ny, dist + 1))
         return None # No walkable tile found nearby