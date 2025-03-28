# agent.py
import random
import math
import config as cfg
from pathfinding_utils import find_path
from knowledge import KnowledgeSystem
from world import Resource # Phase 3 check for workbench instance

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
        self.current_action = None # e.g., "Moving", "Eating", "Resting", "Craft:CrudeAxe"
        self.action_target = None # Dict containing target info: {'type': 'location'/'agent'/'craft', 'goal': (x,y)/id/recipe, 'stand':(x,y), 'requires_workbench': bool}
        self.current_path = [] # List of GridNode objects for movement
        self.action_timer = 0.0 # Time spent on current action segment (e.g., gathering)

        # --- Phase 2 Additions ---
        self.inventory = {} # item_name: count
        self.skills = { # skill_name: level (0-100)
            'GatherWood': cfg.INITIAL_SKILL_LEVEL,
            'GatherStone': cfg.INITIAL_SKILL_LEVEL,
            'BasicCrafting': cfg.INITIAL_SKILL_LEVEL,
        }

        # --- Phase 3 Additions ---
        self.knowledge = KnowledgeSystem(self.id) # More structured knowledge

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
        self._process_signals(agents, social_manager) # Pass args if needed by reactions

        # If a signal reaction changed the action, skip action execution this tick
        if self.pending_signal: # Check if signal processing set a new action that needs setup next tick
             pass # Let the new action start next update loop

        # 4. Execute Current Action or Choose New One
        elif self.current_action:
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
        if self.energy <= 0 and self.current_action != "Rest": health_drain += 0.5 # Drain health if out of energy AND not resting
        self.health -= health_drain * dt_sim_seconds

        # Clamp health
        self.health = max(0, self.health)


    def _choose_action(self, agents, social_manager):
        """ Utility AI Decision Making - Expanded for Phases 2, 3, 4 """
        utilities = {}

        # --- Calculate Utility for Basic Needs ---
        utilities['SatisfyThirst'] = (self.thirst / cfg.MAX_THIRST)**2
        utilities['SatisfyHunger'] = (self.hunger / cfg.MAX_HUNGER)**2
        energy_deficit = (cfg.MAX_ENERGY - self.energy) / cfg.MAX_ENERGY
        utilities['Rest'] = energy_deficit**2 if self.energy < cfg.MAX_ENERGY * 0.7 else 0

        # --- Phase 2+: Resource Gathering ---
        has_axe = self.inventory.get('CrudeAxe', 0) > 0
        has_pick = self.inventory.get('StonePick', 0) > 0
        current_wood = self.inventory.get('Wood', 0)
        current_stone = self.inventory.get('Stone', 0)
        inventory_full = sum(self.inventory.values()) >= cfg.INVENTORY_CAPACITY

        # Gather Wood Utility: Higher if low on wood, boosted by axe, zero if inventory full
        if not inventory_full or current_wood < 5: # Allow gathering if specifically low on wood
            wood_goal = 10
            wood_need_factor = max(0, min(1, (wood_goal - current_wood) / wood_goal)) # Need decreases as goal reached
            wood_gather_utility = wood_need_factor * 0.4 # Base utility
            if has_axe: wood_gather_utility *= 1.8 # Axe helps a lot
            if inventory_full: wood_gather_utility *= 0.1 # Much lower priority if generally full
            utilities['GatherWood'] = wood_gather_utility

        # Gather Stone Utility: Similar logic, boosted by pickaxe
        if not inventory_full or current_stone < 5:
            stone_goal = 5
            stone_need_factor = max(0, min(1, (stone_goal - current_stone) / stone_goal))
            stone_gather_utility = stone_need_factor * 0.35
            if has_pick: stone_gather_utility *= 1.8
            if inventory_full: stone_gather_utility *= 0.1
            utilities['GatherStone'] = stone_gather_utility

        # --- Phase 2+/3+: Crafting ---
        best_craft_utility = 0
        best_craft_recipe = None
        for recipe_name in cfg.RECIPES.keys(): # Check all potential recipes
            details = cfg.RECIPES[recipe_name]
            # Feasibility checks: Have ingredients? Have skill? Recipe Requires Workbench? Workbench available?
            has_ings = self._has_ingredients(details['ingredients'])
            has_skill = self._has_skill_for(details)
            requires_wb = details.get('workbench', False)

            # Preliminary check - can we even craft this?
            if not (has_ings and has_skill):
                 continue

            # Check workbench proximity IF required (more detailed check in _check_action_feasibility)
            needs_wb_check = requires_wb # Only check if recipe needs it
            if needs_wb_check:
                 _, wb_stand_pos, _ = self.world.find_nearest_resource(self.x, self.y, cfg.RESOURCE_WORKBENCH, max_dist=5) # Quick check nearby
                 if wb_stand_pos is None: # No WB nearby -> cannot craft this now
                     continue

            # Calculate utility IF feasible
            utility = 0.0
            knows_recipe = self.knowledge.knows_recipe(recipe_name)

            # Base utility: Higher if recipe is known, lower if just potentially craftable
            utility += 0.1 if knows_recipe else 0.01

            # Goal-based boosts:
            if recipe_name == 'CrudeAxe' and not has_axe: utility = 0.7 # High desire for first tool
            elif recipe_name == 'StonePick' and not has_pick and current_stone < stone_goal: utility = 0.65 # High desire for pick if needed
            elif recipe_name == 'Workbench' and current_wood >= 4 and current_stone >= 2 and not self._is_workbench_nearby(distance=5):
                 # Utility to build a workbench if none is nearby and have materials
                 utility = 0.6
            elif recipe_name == 'SmallShelter' and self.inventory.get('SmallShelter', 0) == 0:
                 # Utility to build shelter (maybe higher at night?)
                 utility = 0.5

            # Only consider recipes agent KNOWS unless trying to invent
            if knows_recipe and utility > best_craft_utility:
                best_craft_utility = utility
                best_craft_recipe = recipe_name

        if best_craft_recipe:
            utilities['Craft:' + best_craft_recipe] = best_craft_utility

        # --- Phase 3+: Invention ---
        # Utility: Consider if needs are met, have items, and AT a workbench
        needs_met_factor = max(0, 1 - max(utilities.get('SatisfyThirst',0), utilities.get('SatisfyHunger',0), utilities.get('Rest',0)))
        can_invent = len(self.inventory) >= 2 # Simplistic check: has at least 2 item types/counts
        is_at_workbench = self._is_at_workbench() # Check if currently at a workbench

        if can_invent and is_at_workbench: # Invention requires workbench
            # Base utility low, increases if not busy with basic needs, plus randomness/curiosity
            # Reduce utility slightly if already know many recipes
            known_recipe_count = len(self.knowledge.known_recipes)
            invention_utility = 0.15 * needs_met_factor * random.uniform(0.8, 1.2) * max(0.1, 1 - known_recipe_count / len(cfg.RECIPES))
            utilities['Invent'] = invention_utility
        elif can_invent and not is_at_workbench:
             # Add utility to GO TO a workbench to invent
             _, wb_stand_pos, _ = self.world.find_nearest_resource(self.x, self.y, cfg.RESOURCE_WORKBENCH)
             if wb_stand_pos: # If a workbench exists somewhere
                  goto_wb_utility = 0.1 * needs_met_factor # Low utility just to move there
                  # Action name distinguishes it from crafting AT workbench
                  utilities['GoToWorkbench:Invent'] = goto_wb_utility


        # --- Phase 4+: Social Actions ---
        target_to_help = self._find_agent_to_help(agents)
        if target_to_help:
             relationship_mod = (1 + self.knowledge.get_relationship(target_to_help.id)) / 2 # Scale 0 to 1
             # Determine primary need of target agent
             help_need = 0
             if target_to_help.hunger > target_to_help.thirst and target_to_help.hunger > cfg.MAX_HUNGER * 0.7:
                 help_need = (target_to_help.hunger / cfg.MAX_HUNGER)**2
             elif target_to_help.thirst > cfg.MAX_THIRST * 0.7:
                 help_need = (target_to_help.thirst / cfg.MAX_THIRST)**2

             if help_need > 0:
                 help_utility = 0.6 * self.sociability * relationship_mod * help_need # Base 0.6
                 utilities['Help:'+str(target_to_help.id)] = help_utility

        # TODO: Add utility for Teaching (find agent who needs skill, check relationship etc.)

        # --- Default/Fallback Action ---
        utilities['Wander'] = 0.05 # Very low base utility

        # --- Select Best Action ---
        best_action = None
        max_utility = -1

        if not utilities:
             self.current_action = "Idle"
             print(f"Agent {self.id} has no utilities, becoming Idle.")
             return

        sorted_utilities = sorted(utilities.items(), key=lambda item: item[1], reverse=True)
        # print(f"Agent {self.id} Utilities: {[(a, f'{u:.2f}') for a, u in sorted_utilities]}") # Debug spammy

        for action, utility in sorted_utilities:
            if utility <= cfg.UTILITY_THRESHOLD and action != 'Wander': # Allow Wander even below threshold if nothing else works
                continue

            feasible, target_data = self._check_action_feasibility(action, agents) # Get feasibility AND target data
            if feasible:
                best_action = action
                max_utility = utility
                # Store target data gathered during feasibility check
                self.action_target = target_data
                break

        if not best_action:
            feasible, target_data = self._check_action_feasibility('Wander', agents)
            if feasible:
                best_action = 'Wander'
                max_utility = utilities.get('Wander', 0.05)
                self.action_target = target_data
                # print(f"Agent {self.id}: No primary action feasible/above threshold, choosing Wander.")
            else:
                best_action = "Idle"
                max_utility = 0
                self.action_target = None # Ensure target is clear for Idle
                print(f"Agent {self.id} becoming Idle (no feasible action, including Wander). Needs(H,T,E): ({self.hunger:.0f},{self.thirst:.0f},{self.energy:.0f})")


        # --- Initiate Action ---
        if self.current_action == best_action and best_action == "Idle": return

        print(f"Agent {self.id} choosing action: {best_action} (Utility: {max_utility:.2f}) Needs(H,T,E): ({self.hunger:.0f},{self.thirst:.0f},{self.energy:.0f}) Inv: {sum(self.inventory.values())}")

        self.current_action = best_action
        self.current_path = [] # Reset path
        self.action_timer = 0.0 # Reset action timer

        if best_action == "Idle":
             self.action_target = None # Explicitly clear target for Idle
             return

        # --- Path Planning based on action_target ---
        target_setup_success = False
        try:
            stand_pos = self.action_target.get('stand')

            if stand_pos:
                # Check if already at the stand position
                if (self.x, self.y) == stand_pos:
                    target_setup_success = True # No path needed
                    self.current_path = []
                else:
                    # Plan path to the stand position, avoiding other agents
                    self.current_path = self._plan_path(stand_pos, agents)
                    if self.current_path is not None: # Check if pathfinding returned a list (even empty) vs None (error)
                         if not self.current_path and (self.x, self.y) != stand_pos:
                              # Pathfinding returned empty list but not at target -> unreachable?
                              target_setup_success = False
                              print(f"Agent {self.id}: Path to {stand_pos} for {best_action} failed (empty path, not at target).")
                         else:
                              target_setup_success = True # Path found or already there
                    else:
                         # Pathfinding failed (returned None)
                         target_setup_success = False
                         print(f"Agent {self.id}: Path to {stand_pos} for {best_action} failed (pathfinder error).")

            elif best_action == 'Rest' or best_action == 'Invent': # Actions at current location initially
                # Invent might require moving to workbench later if GoToWorkbench chosen
                 target_setup_success = True
            else:
                 # Action doesn't have a 'stand' position defined in feasibility check? Error state.
                 print(f"Agent {self.id}: Action {best_action} selected but no 'stand' position in target data.")
                 target_setup_success = False


        except Exception as e:
             print(f"Error during action path planning for {best_action}: {e}")
             import traceback
             traceback.print_exc()
             target_setup_success = False


        # If setting up the target/path failed, revert to Idle
        if not target_setup_success:
             print(f"Agent {self.id}: Failed to initiate action {best_action}. Reverting to Idle.")
             self.current_action = "Idle"
             self.action_target = None
             self.current_path = []


    def _check_action_feasibility(self, action_name, agents):
        """
        Checks if an action is possible and returns (bool feasible, dict target_data).
        Target data includes 'type', 'goal', 'stand', etc. needed to execute action.
        """
        target_data = {'type': action_name.split(':')[0]} # Base type

        if action_name == 'SatisfyThirst':
            goal_pos, stand_pos, dist = self.world.find_nearest_resource(self.x, self.y, cfg.RESOURCE_WATER)
            if stand_pos:
                target_data.update({'goal': goal_pos, 'stand': stand_pos})
                return True, target_data
            return False, None

        elif action_name == 'SatisfyHunger':
            goal_pos, stand_pos, dist = self.world.find_nearest_resource(self.x, self.y, cfg.RESOURCE_FOOD)
            if stand_pos:
                target_data.update({'goal': goal_pos, 'stand': stand_pos})
                self.knowledge.add_resource_location(cfg.RESOURCE_FOOD, goal_pos[0], goal_pos[1]) # Remember location
                return True, target_data
            return False, None

        elif action_name == 'GatherWood':
             goal_pos, stand_pos, dist = self.world.find_nearest_resource(self.x, self.y, cfg.RESOURCE_WOOD)
             if stand_pos:
                 target_data.update({'goal': goal_pos, 'stand': stand_pos})
                 self.knowledge.add_resource_location(cfg.RESOURCE_WOOD, goal_pos[0], goal_pos[1])
                 return True, target_data
             return False, None

        elif action_name == 'GatherStone':
             goal_pos, stand_pos, dist = self.world.find_nearest_resource(self.x, self.y, cfg.RESOURCE_STONE)
             if stand_pos:
                 target_data.update({'goal': goal_pos, 'stand': stand_pos})
                 self.knowledge.add_resource_location(cfg.RESOURCE_STONE, goal_pos[0], goal_pos[1])
                 return True, target_data
             return False, None

        elif action_name.startswith('Craft:'):
             recipe_name = action_name.split(':')[1]
             details = cfg.RECIPES.get(recipe_name)
             if not details: return False, None

             requires_wb = details.get('workbench', False)
             target_data.update({'recipe': recipe_name, 'requires_workbench': requires_wb})

             # Check ingredients, skill, knowledge
             if not (self.knowledge.knows_recipe(recipe_name) and
                     self._has_ingredients(details['ingredients']) and
                     self._has_skill_for(details)):
                 return False, None

             # Check workbench requirement
             if requires_wb:
                 # Is agent already at a workbench?
                 if self._is_at_workbench():
                      target_data['stand'] = (self.x, self.y) # Stand at current location (workbench)
                      target_data['goal'] = (self.x, self.y) # Goal is also workbench location
                      return True, target_data
                 else:
                      # Find nearest workbench and set stand/goal to go there
                      wb_goal_pos, wb_stand_pos, dist = self.world.find_nearest_resource(self.x, self.y, cfg.RESOURCE_WORKBENCH)
                      if wb_stand_pos:
                          target_data['goal'] = wb_goal_pos # The workbench itself
                          target_data['stand'] = wb_stand_pos # Where to stand to use it
                          # Action becomes moving TO the workbench first
                          return True, target_data
                      else:
                          return False, None # No workbench available
             else: # No workbench needed, craft at current location
                 target_data['stand'] = (self.x, self.y)
                 target_data['goal'] = (self.x, self.y)
                 return True, target_data

        elif action_name == 'Invent':
             # Requires being AT a workbench
             target_data['requires_workbench'] = True
             if len(self.inventory) >= 2 and self._is_at_workbench():
                 target_data['stand'] = (self.x, self.y)
                 target_data['goal'] = (self.x, self.y)
                 return True, target_data
             return False, None

        elif action_name == 'GoToWorkbench:Invent':
             # Feasibility: Inventory has items, and a workbench exists somewhere
             if len(self.inventory) >= 2:
                  wb_goal_pos, wb_stand_pos, dist = self.world.find_nearest_resource(self.x, self.y, cfg.RESOURCE_WORKBENCH)
                  if wb_stand_pos:
                      target_data['goal'] = wb_goal_pos
                      target_data['stand'] = wb_stand_pos
                      return True, target_data
             return False, None


        elif action_name.startswith('Help:'):
             target_id = int(action_name.split(':')[1])
             target_agent = next((a for a in agents if a.id == target_id and a.health > 0), None)
             if not target_agent: return False, None # Target gone

             # Check if CAN help (e.g., have food if target is hungry)
             can_help = False
             if target_agent.hunger > cfg.MAX_HUNGER * 0.75 and self.inventory.get('Food', 0) >= 1:
                 can_help = True
             # Add check for water if carrying mechanism exists

             if not can_help: return False, None

             # Find a spot near the target to stand
             stand_pos = self._find_adjacent_walkable(target_agent.x, target_agent.y)
             if stand_pos:
                  target_data.update({'goal': target_id, 'stand': stand_pos})
                  return True, target_data
             return False, None # Cannot find spot near target

        elif action_name == 'Wander':
             # Find a random walkable target nearby
             wander_target = None
             for _ in range(10):
                  wx = self.x + random.randint(-cfg.WANDER_RADIUS, cfg.WANDER_RADIUS)
                  wy = self.y + random.randint(-cfg.WANDER_RADIUS, cfg.WANDER_RADIUS)
                  if 0 <= wx < self.world.width and 0 <= wy < self.world.height and self.world.walkability_matrix[wy, wx] == 1:
                       # Ensure not wandering into water/obstacle inadvertently
                       if self.world.terrain_map[wy,wx] == cfg.TERRAIN_GROUND:
                            wander_target = (wx, wy)
                            break
             if wander_target:
                 target_data['stand'] = wander_target # For wander, stand=goal
                 target_data['goal'] = wander_target
                 return True, target_data
             else:
                 # Check if *any* adjacent tile is walkable as a last resort (check if trapped)
                 if self._find_adjacent_walkable(self.x, self.y):
                      # Can move, but couldn't find random spot? Try wandering to adjacent.
                      adj = self._find_adjacent_walkable(self.x, self.y)
                      target_data['stand'] = adj
                      target_data['goal'] = adj
                      return True, target_data # Can at least move one step
                 else:
                      return False, None # Truly trapped

        elif action_name == "Idle":
             return True, {'type': 'Idle'} # Idle is always feasible

        elif action_name == "Rest":
             target_data['stand'] = (self.x, self.y) # Rest at current location
             return True, target_data

        # Unknown action
        print(f"Warning: Feasibility check for unknown action '{action_name}'")
        return False, None

    def _is_workbench_nearby(self, distance=1):
        """ Checks if the agent is within `distance` cells of a workbench. """
        for dx in range(-distance, distance + 1):
             for dy in range(-distance, distance + 1):
                 if dx == 0 and dy == 0: continue # Skip self
                 nx, ny = self.x + dx, self.y + dy
                 resource = self.world.get_resource(nx, ny)
                 if resource and resource.type == cfg.RESOURCE_WORKBENCH:
                     return True
        return False

    def _is_at_workbench(self):
         """ Checks if the agent is standing ON or directly adjacent to a workbench resource tile """
         # Check current tile (shouldn't happen if WB blocks walk, but check anyway)
         res_here = self.world.get_resource(self.x, self.y)
         if res_here and res_here.type == cfg.RESOURCE_WORKBENCH:
              return True
         # Check adjacent tiles
         for dx, dy in [(0,1), (0,-1), (1,0), (-1,0)]:
             nx, ny = self.x + dx, self.y + dy
             res_adj = self.world.get_resource(nx, ny)
             if res_adj and res_adj.type == cfg.RESOURCE_WORKBENCH:
                 return True
         return False


    def _plan_path(self, target_pos, agents):
        """ Finds path using A*, avoiding other agents. Returns list of GridNode or None. """
        start_pos = (self.x, self.y)
        if not target_pos or start_pos == target_pos:
            return [] # Already there or no target

        tx, ty = target_pos
        if not (0 <= tx < self.world.width and 0 <= ty < self.world.height):
            print(f"Agent {self.id}: Target {target_pos} is out of bounds.")
            return None # Indicate error

        # Get temporary walkability matrix with other agents marked as obstacles
        other_agent_positions = [(a.x, a.y) for a in agents if a != self]
        temp_walkability = self.world.update_walkability(agent_positions=other_agent_positions)

        # Check walkability of start/end on the temporary grid
        if temp_walkability[start_pos[1], start_pos[0]] == 0:
             print(f"Agent {self.id}: Starting position {start_pos} is blocked (possibly by another agent)!")
             # Try finding adjacent walkable to start from? Complex. Fail for now.
             return None
        if temp_walkability[ty, tx] == 0:
            adj_target = self._find_adjacent_walkable(tx, ty, temp_walkability) # Use temp matrix for check
            if not adj_target:
                 print(f"Agent {self.id}: Target {target_pos} is unwalkable/blocked and no adjacent found.")
                 return None # Indicate error
            # print(f"Agent {self.id}: Target {target_pos} unwalkable/blocked, rerouting to adjacent {adj_target}")
            target_pos = adj_target # Update target to the adjacent walkable spot

        # Call pathfinder with the temporary matrix
        path_nodes = find_path(temp_walkability, start_pos, target_pos)

        return path_nodes # Returns list of nodes, empty list if not found, None on error


    def _perform_action(self, dt_sim_seconds, agents, social_manager):
        """ Executes the current action step, returns True if completed """
        if not self.current_action or self.current_action == "Idle":
             return True

        # --- 1. Movement Phase (if path exists) ---
        if self.current_path:
            # Check if path is still valid (e.g., next step isn't blocked by another agent NOW)
            # More robust check needed here if dynamic obstacles are critical.
            # For now, assume path remains valid unless explicitly recalculated.

            target_node = self.current_path[0]
            target_x, target_y = target_node.x, target_node.y

            # Check if next step is occupied *right now* by another agent
            is_occupied = False
            for agent in agents:
                 if agent != self and agent.health > 0 and agent.x == target_x and agent.y == target_y:
                      is_occupied = True
                      break

            if is_occupied:
                # print(f"Agent {self.id}: Next step ({target_x},{target_y}) blocked by Agent {agent.id}. Recalculating path...")
                # Path is blocked, try recalculating path to the original stand position
                stand_pos = self.action_target.get('stand')
                if stand_pos:
                     new_path = self._plan_path(stand_pos, agents)
                     if new_path is not None and new_path: # Successfully recalculated
                          self.current_path = new_path
                          # Proceed with the first step of the *new* path next tick
                          return False
                     else: # Recalculation failed or yielded empty path immediately
                          print(f"Agent {self.id}: Failed to recalculate path around obstacle. Completing action.")
                          self._complete_action() # Give up on the action
                          return True
                else: # No stand_pos? Should not happen if action was set up correctly
                     print(f"Agent {self.id}: Path blocked, but no stand_pos to replan to. Completing action.")
                     self._complete_action()
                     return True

            # --- If next step is clear, move ---
            move_dist = 1 # Simple grid movement
            self.x = target_x
            self.y = target_y
            self.energy -= cfg.MOVE_ENERGY_COST * move_dist

            self.current_path.pop(0)
            return False # Still moving (or just finished moving this tick)

        # --- 2. Action Execution Phase (at target location, path is empty) ---
        # Ensure agent is actually at the required standing position
        expected_stand_pos = self.action_target.get('stand')
        if expected_stand_pos and (self.x, self.y) != expected_stand_pos:
            # Arrived somewhere, but not the intended spot (path might have been short-circuited or target moved?)
            print(f"Agent {self.id}: Arrived at ({self.x},{self.y}) but expected stand {expected_stand_pos} for {self.current_action}. Action failed.")
            return True # Fail the action

        self.action_timer += dt_sim_seconds
        base_action_duration = 1.0 # Base seconds per action unit

        try:
            action_type = self.current_action.split(':')[0] # Get base action type like 'Craft', 'Gather'

            # --- Phase 1 Actions ---
            if self.current_action == 'SatisfyThirst':
                # Water is infinite at the goal tile (water terrain)
                action_duration = base_action_duration * 0.5
                if self.action_timer >= action_duration:
                    self.thirst = max(0, self.thirst - cfg.DRINK_THIRST_REDUCTION)
                    self.energy -= cfg.MOVE_ENERGY_COST * 0.1 # Small energy cost to drink
                    # print(f"Agent {self.id} drank. Thirst: {self.thirst:.0f}")
                    return True # Drink action complete
                else: return False # Still drinking

            elif self.current_action == 'SatisfyHunger':
                goal_pos = self.action_target['goal']
                resource = self.world.get_resource(goal_pos[0], goal_pos[1])
                if resource and resource.type == cfg.RESOURCE_FOOD and not resource.is_depleted():
                    action_duration = base_action_duration * 0.5
                    if self.action_timer >= action_duration:
                        amount = self.world.consume_resource_at(goal_pos[0], goal_pos[1], 1)
                        if amount > 0:
                            self.hunger = max(0, self.hunger - cfg.EAT_HUNGER_REDUCTION)
                            self.energy -= cfg.MOVE_ENERGY_COST * 0.1 # Small energy cost to eat
                            # print(f"Agent {self.id} ate. Hunger: {self.hunger:.0f}")
                            # Food item disappears after eating? Or reduces quantity? Consume handles quantity.
                        else: # Failed to consume (e.g., depleted exactly now)
                            self.knowledge.remove_resource_location(cfg.RESOURCE_FOOD, goal_pos[0], goal_pos[1])
                        return True # Eating attempt complete
                    else: return False # Still eating
                else: # Resource disappeared or depleted before eating
                    print(f"Agent {self.id} failed to eat at {goal_pos} - resource gone.")
                    self.knowledge.remove_resource_location(cfg.RESOURCE_FOOD, goal_pos[0], goal_pos[1])
                    return True # Action failed/complete

            elif self.current_action == 'Rest':
                high_thirst = self.thirst > cfg.MAX_THIRST * 0.9
                high_hunger = self.hunger > cfg.MAX_HUNGER * 0.9
                if self.energy >= cfg.MAX_ENERGY or high_thirst or high_hunger:
                    # print(f"Agent {self.id} finished resting. Energy: {self.energy:.0f}")
                    return True # Stop resting
                return False # Continue resting (energy gain in _update_needs)

            elif self.current_action == 'Wander':
                # Wander completes once destination ('stand' pos) is reached (path is empty here)
                return True

            # --- Phase 2 Actions ---
            elif self.current_action == 'GatherWood':
                 goal_pos = self.action_target['goal']
                 resource = self.world.get_resource(goal_pos[0], goal_pos[1])
                 if resource and resource.type == cfg.RESOURCE_WOOD and not resource.is_depleted():
                     tool_multiplier = 1.5 if self.inventory.get('CrudeAxe', 0) > 0 else 1.0
                     action_duration = base_action_duration / (self._get_skill_multiplier('GatherWood') * tool_multiplier)
                     if self.action_timer >= action_duration:
                         amount = self.world.consume_resource_at(goal_pos[0], goal_pos[1], 1)
                         if amount > 0:
                             self.inventory['Wood'] = self.inventory.get('Wood', 0) + amount
                             self.energy -= cfg.GATHER_ENERGY_COST
                             self.learn_skill('GatherWood')
                             # print(f"Agent {self.id} gathered Wood. Total: {self.inventory.get('Wood', 0)}. Skill: {self.skills.get('GatherWood',0):.1f}")
                             self.action_timer = 0 # Reset timer for next unit

                             inventory_full = sum(self.inventory.values()) >= cfg.INVENTORY_CAPACITY
                             wood_goal = 10 # Local goal for this gathering session
                             if self.inventory.get('Wood', 0) >= wood_goal or inventory_full or self.energy < cfg.GATHER_ENERGY_COST * 2 or resource.is_depleted():
                                  if resource.is_depleted(): self.knowledge.remove_resource_location(cfg.RESOURCE_WOOD, goal_pos[0], goal_pos[1])
                                  return True # Stop gathering
                             else:
                                  return False # Continue gathering from this source
                         else: # Resource depleted during attempt
                              print(f"Agent {self.id} failed to gather wood (depleted during attempt).")
                              self.knowledge.remove_resource_location(cfg.RESOURCE_WOOD, goal_pos[0], goal_pos[1])
                              return True
                     else: return False # Still gathering this unit
                 else: # Resource gone/depleted before starting
                     print(f"Agent {self.id} failed to gather wood at {goal_pos} - resource gone.")
                     self.knowledge.remove_resource_location(cfg.RESOURCE_WOOD, goal_pos[0], goal_pos[1])
                     return True

            elif self.current_action == 'GatherStone':
                 goal_pos = self.action_target['goal']
                 resource = self.world.get_resource(goal_pos[0], goal_pos[1])
                 if resource and resource.type == cfg.RESOURCE_STONE and not resource.is_depleted():
                     tool_multiplier = 1.5 if self.inventory.get('StonePick', 0) > 0 else 1.0
                     action_duration = base_action_duration / (self._get_skill_multiplier('GatherStone') * tool_multiplier)
                     if self.action_timer >= action_duration:
                         amount = self.world.consume_resource_at(goal_pos[0], goal_pos[1], 1)
                         if amount > 0:
                             self.inventory['Stone'] = self.inventory.get('Stone', 0) + amount
                             self.energy -= cfg.GATHER_ENERGY_COST
                             self.learn_skill('GatherStone')
                             # print(f"Agent {self.id} gathered Stone. Total: {self.inventory.get('Stone',0)}. Skill: {self.skills.get('GatherStone',0):.1f}")
                             self.action_timer = 0

                             inventory_full = sum(self.inventory.values()) >= cfg.INVENTORY_CAPACITY
                             stone_goal = 5
                             if self.inventory.get('Stone', 0) >= stone_goal or inventory_full or self.energy < cfg.GATHER_ENERGY_COST * 2 or resource.is_depleted():
                                 if resource.is_depleted(): self.knowledge.remove_resource_location(cfg.RESOURCE_STONE, goal_pos[0], goal_pos[1])
                                 return True
                             else: return False
                         else:
                             print(f"Agent {self.id} failed to gather stone (depleted during attempt).")
                             self.knowledge.remove_resource_location(cfg.RESOURCE_STONE, goal_pos[0], goal_pos[1])
                             return True
                     else: return False
                 else:
                     print(f"Agent {self.id} failed to gather stone at {goal_pos} - resource gone.")
                     self.knowledge.remove_resource_location(cfg.RESOURCE_STONE, goal_pos[0], goal_pos[1])
                     return True

            elif action_type == 'Craft':
                 # Check if workbench is required and if agent is at one
                 requires_wb = self.action_target.get('requires_workbench', False)
                 if requires_wb and not self._is_at_workbench():
                      print(f"Agent {self.id} cannot craft {self.action_target['recipe']} - not at workbench.")
                      # Maybe should have pathfound to workbench first? Logic error somewhere?
                      # For now, just fail the action.
                      return True

                 # Perform crafting
                 recipe_name = self.action_target['recipe']
                 details = cfg.RECIPES[recipe_name]
                 action_duration = base_action_duration * 2.5 / self._get_skill_multiplier(details['skill']) # Crafting takes longer
                 if self.action_timer >= action_duration:
                     if not self._has_ingredients(details['ingredients']): # Double-check ingredients
                         print(f"Agent {self.id} cannot craft {recipe_name} - missing ingredients now.")
                         return True # Action failed

                     # Consume ingredients
                     for item, count in details['ingredients'].items():
                         self.inventory[item] = self.inventory.get(item, 0) - count
                         if self.inventory[item] <= 0: del self.inventory[item]

                     # Add result item OR place object in world
                     if recipe_name == 'Workbench': # Special case: Place workbench
                          # Find placeable spot nearby? For now, place at current agent location if possible
                          if self.world.add_world_object(Resource(cfg.RESOURCE_WORKBENCH, self.x, self.y, quantity=1, max_quantity=1), self.x, self.y):
                               print(f"Agent {self.id} crafted and placed a Workbench at ({self.x},{self.y}).")
                               social_manager.broadcast_signal(self, f"Crafted:{recipe_name}", (self.x, self.y))
                          else:
                               print(f"Agent {self.id} crafted Workbench but failed to place it at ({self.x},{self.y}). Items lost?")
                               # TODO: Handle failed placement (drop items? Refund?) For now, items are lost.
                     elif recipe_name == 'SmallShelter': # Special case: Place shelter
                          # For now, just add to inventory, placement would be another action
                          self.inventory[recipe_name] = self.inventory.get(recipe_name, 0) + 1
                          print(f"Agent {self.id} crafted {recipe_name}. Stored in inventory.")
                          social_manager.broadcast_signal(self, f"Crafted:{recipe_name}", (self.x, self.y)) # Announce crafting
                     else: # Default: Add to inventory
                          self.inventory[recipe_name] = self.inventory.get(recipe_name, 0) + 1
                          print(f"Agent {self.id} crafted {recipe_name}. Skill: {self.skills.get(details['skill'],0):.1f}")
                          social_manager.broadcast_signal(self, f"Crafted:{recipe_name}", (self.x, self.y)) # Announce crafting

                     self.energy -= cfg.CRAFT_ENERGY_COST
                     self.learn_skill(details['skill'])
                     return True # Crafting complete
                 else: return False # Still crafting

            # --- Phase 3 Actions ---
            elif self.current_action == 'Invent':
                 # Requires being AT a workbench
                 if not self._is_at_workbench():
                     print(f"Agent {self.id} cannot Invent - not at workbench.")
                     return True # Fail action

                 action_duration = base_action_duration * 4 # Invention takes significant time
                 if self.action_timer >= action_duration:
                     discovered_recipe = self.knowledge.attempt_invention(self.inventory)
                     self.energy -= cfg.INVENT_ENERGY_COST
                     if discovered_recipe:
                         print(f"Agent {self.id} *** INVENTED *** {discovered_recipe}!")
                         social_manager.broadcast_signal(self, f"Invented:{discovered_recipe}", (self.x, self.y))
                     # else: print(f"Agent {self.id} invention attempt yielded nothing.")
                     return True # Invention attempt complete (success or fail)
                 else: return False # Still thinking...

            elif self.current_action == 'GoToWorkbench:Invent':
                 # Action completes when workbench is reached (path is empty, agent is at stand pos)
                 # Now, the agent should choose the 'Invent' action in the next tick.
                 print(f"Agent {self.id} arrived at workbench. Will attempt to Invent next.")
                 return True # Arrived, action complete. Let AI choose 'Invent' next.


            # --- Phase 4 Actions ---
            elif action_type == 'Help':
                target_id = self.action_target['goal']
                target_agent = next((a for a in agents if a.id == target_id and a.health > 0), None)

                if target_agent:
                     distance = abs(self.x - target_agent.x) + abs(self.y - target_agent.y)
                     if distance <= 2: # Check proximity again
                          # Attempt the actual help action via SocialManager
                          help_successful = social_manager.attempt_helping(self, target_agent)
                          if help_successful:
                               print(f"Agent {self.id} successfully helped Agent {target_id}.")
                               self.energy -= cfg.GATHER_ENERGY_COST * 0.2 # Small energy cost for helping
                          # else: print(f"Agent {self.id} help attempt towards {target_id} failed (conditions not met?).")
                     else: print(f"Agent {self.id} too far from target {target_id} ({distance} units) to help.")
                # else: Already checked agent existence in feasibility

                return True # Help attempt is complete (success or fail handled in SocialManager)

            # --- Fallback ---
            else:
                print(f"Agent {self.id}: Unknown action {self.current_action} in perform_action step")
                return True # Unknown action, stop doing it

        except Exception as e:
            print(f"!!! Error performing action {self.current_action} for agent {self.id}: {e}")
            import traceback
            traceback.print_exc()
            return True # Treat error as action completion/failure


    def _complete_action(self):
        """ Cleanup after an action is finished or failed """
        if self.current_action and self.current_action != "Idle":
            # print(f"Agent {self.id} completed action: {self.current_action}")
            pass # Reduce log spam
        self.current_action = None
        self.action_target = None
        self.current_path = []
        self.action_timer = 0.0

    def _handle_death(self):
        print(f"Agent {self.id} has died at ({self.x}, {self.y}). Needs(H,T,E): ({self.hunger:.0f},{self.thirst:.0f},{self.energy:.0f})")
        # Optional: Drop some inventory items
        # for item, count in self.inventory.items():
        #     if random.random() < 0.3: # 30% chance to drop each item type
        #         # Need a mechanism to place items on the ground (e.g., Item resource type)
        #         print(f"  (Agent {self.id} dropped {item})")
        pass

    # --- Phase 2: Skills & Crafting Helpers ---
    def learn_skill(self, skill_name, boost=1.0):
        """ Increases skill level, learning by doing. Returns True if level increased. """
        if not skill_name: return False # Ignore if no skill associated

        is_known_skill_base = skill_name in self.skills
        # Check if it's a skill used by any recipe (even if not explicitly in self.skills yet)
        is_recipe_skill = any(details.get('skill') == skill_name for details in cfg.RECIPES.values())

        if is_known_skill_base or is_recipe_skill:
            current_level = self.skills.get(skill_name, cfg.INITIAL_SKILL_LEVEL) # Start at 0 if learning new recipe skill
            if current_level < cfg.MAX_SKILL_LEVEL:
                # Diminishing returns + boost factor
                increase = cfg.SKILL_INCREASE_RATE * boost * (1.0 - (current_level / (cfg.MAX_SKILL_LEVEL + 1)))
                new_level = min(cfg.MAX_SKILL_LEVEL, current_level + increase)
                # Update skill if increase is significant enough
                if new_level > current_level + 0.01:
                    self.skills[skill_name] = new_level
                    # print(f"Agent {self.id} skill {skill_name} increased to {new_level:.2f}") # Debug
                    return True
        else:
             # Maybe learning a skill not tied to recipes (e.g. 'Social', 'Combat' later)
             # print(f"Agent {self.id} attempted to learn unknown skill category: {skill_name}")
             pass
        return False


    def _get_skill_multiplier(self, skill_name):
        """ Returns a multiplier based on skill level (e.g., for speed/efficiency) """
        if not skill_name: return 1.0
        level = self.skills.get(skill_name, 0)
        # More impactful curve: starts at 1x, reaches ~3x at max skill
        multiplier = 1.0 + 2.0 * (level / cfg.MAX_SKILL_LEVEL)**0.8
        return max(0.1, multiplier) # Ensure non-zero

    def _has_ingredients(self, ingredients):
        """ Check inventory for required crafting ingredients """
        if not ingredients: return True
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
        # TODO: Maybe queue signals instead of just keeping latest? For now, latest is simpler.
        self.pending_signal = (sender_id, signal_type, position)

    def _process_signals(self, agents, social_manager):
        """ Handle the latest received signal, potentially interrupting current action """
        if not self.pending_signal:
            return

        sender_id, signal_type, signal_pos = self.pending_signal
        self.pending_signal = None # Consume the signal

        # print(f"Agent {self.id} processing signal '{signal_type}' from {sender_id}") # Debug

        relationship = self.knowledge.get_relationship(sender_id)
        current_action_util = self._get_current_action_utility()

        # Example Reactions:
        if signal_type == 'Danger': # TODO: Need a source of 'Danger' signals
            flee_utility = 0.95
            if flee_utility > current_action_util:
                 print(f"Agent {self.id} reacts to DANGER signal from {sender_id}! Fleeing.")
                 self._complete_action() # Interrupt current action forcefully
                 # Flee logic: move away from signal position
                 dx = self.x - signal_pos[0]
                 dy = self.y - signal_pos[1]
                 norm = math.hypot(dx, dy)
                 if norm > 0:
                     flee_x = int(self.x + dx / norm * cfg.WANDER_RADIUS)
                     flee_y = int(self.y + dy / norm * cfg.WANDER_RADIUS)
                     flee_x = max(0, min(self.world.width - 1, flee_x))
                     flee_y = max(0, min(self.world.height - 1, flee_y))
                     flee_target = self._find_walkable_near(flee_x, flee_y)
                     if flee_target:
                          # Use Wander action to flee to the target spot
                          self.current_action = 'Wander'
                          self.action_target = {'type': 'Wander', 'stand': flee_target, 'goal': flee_target}
                          self.current_path = self._plan_path(flee_target, agents)
                          if self.current_path is None: # Pathing failed
                              self.current_action = 'Idle' # Cannot flee path
                     else:
                          self.current_action = 'Idle' # Cannot find flee spot
                 else: # Danger signal originated from agent's own location? Strange. Idle.
                      self.current_action = 'Idle'
                 # Mark action as changed so execution waits until next tick
                 self.pending_signal = True # Use pending_signal flag hackily


        elif signal_type == 'FoundFood' and self.hunger > cfg.MAX_HUNGER * 0.3: # React if hungry
            # Utility based on hunger and relationship
            food_signal_utility = (self.hunger / cfg.MAX_HUNGER)**1.5 * (0.8 + relationship * 0.4) # Trust influences utility
            if food_signal_utility > current_action_util:
                 print(f"Agent {self.id} reacting to food signal from {sender_id} at {signal_pos}")
                 self._complete_action() # Interrupt current action
                 # Set goal to investigate food source location
                 stand_pos = self._find_adjacent_walkable(signal_pos[0], signal_pos[1])
                 if stand_pos:
                      self.current_action = 'SatisfyHunger' # Tentative action
                      self.action_target = {'type': 'SatisfyHunger', 'goal': signal_pos, 'stand': stand_pos, 'from_signal': True} # Mark as from signal
                      self.current_path = self._plan_path(stand_pos, agents)
                      if self.current_path is None or (not self.current_path and (self.x, self.y) != stand_pos):
                           print(f"Agent {self.id}: Failed to path to food signal location.")
                           self.current_action = None # Allow re-evaluation next tick
                      else:
                           self.pending_signal = True # Mark action changed
                 else:
                      print(f"Agent {self.id}: Cannot find walkable spot near food signal at {signal_pos}.")
                      self.current_action = None # Re-evaluate

        elif signal_type.startswith("Crafted:") or signal_type.startswith("Invented:"):
             item_name = signal_type.split(':')[1]
             # Learn recipe passively if requirements met
             if item_name in cfg.RECIPES and not self.knowledge.knows_recipe(item_name):
                  dist_sq = (self.x - signal_pos[0])**2 + (self.y - signal_pos[1])**2
                  learn_proximity_sq = (cfg.SIGNAL_RANGE * 0.7)**2 # Need to be relatively close
                  # Learn more easily from friends, less likely from disliked agents
                  learn_chance = cfg.PASSIVE_LEARN_CHANCE * (0.7 + relationship * 0.6)
                  if dist_sq < learn_proximity_sq and relationship >= cfg.LEARNING_RELATIONSHIP_THRESHOLD and random.random() < learn_chance:
                      self.knowledge.add_recipe(item_name)
                      # print(f"Agent {self.id} learned recipe '{item_name}' from {sender_id}'s signal.") # Debug


    def decide_to_learn(self, teacher_id, skill_name):
        """ AI decides if it wants to accept teaching. """
        # Prioritize critical needs
        if self.thirst > cfg.MAX_THIRST * 0.9 or self.hunger > cfg.MAX_HUNGER * 0.9 or self.health < cfg.MAX_HEALTH * 0.4:
            # print(f"Agent {self.id} refuses teaching '{skill_name}' from {teacher_id} due to critical needs.")
            return False

        # Don't interrupt very high utility actions?
        current_util = self._get_current_action_utility()
        if current_util > 0.8 and self.current_action not in ['Idle', 'Wander', 'Rest']:
             # print(f"Agent {self.id} refuses teaching '{skill_name}' from {teacher_id} due to important action '{self.current_action}'.")
             return False

        # Check relationship with teacher
        relationship = self.knowledge.get_relationship(teacher_id)
        if relationship < cfg.LEARNING_RELATIONSHIP_THRESHOLD:
            # print(f"Agent {self.id} refuses teaching '{skill_name}' from {teacher_id} due to low relationship ({relationship:.2f}).")
            return False

        # Check if already proficient
        if self.skills.get(skill_name, 0) > cfg.MAX_SKILL_LEVEL * 0.8:
             # print(f"Agent {self.id} refuses teaching '{skill_name}' from {teacher_id} - already skilled.")
             return False

        print(f"Agent {self.id} accepts learning '{skill_name}' from {teacher_id}")
        # Interrupt current action to learn
        self._complete_action()
        # Set a temporary state? Or just allow learn_skill to happen directly?
        # Direct learning is simpler for now. The cost/time is handled by the teacher.
        self.energy -= cfg.LEARN_ENERGY_COST # Cost energy to learn
        return True

    def _find_agent_to_help(self, agents):
         """ Finds nearby agent in critical need that this agent *can* help and has decent relationship with. """
         best_target = None
         max_weighted_need = 0 # Combined need level, relationship, sociability

         potential_targets = []
         for other in agents:
              if other.id != self.id and other.health > 0: # Check living agents only
                   dist = abs(self.x - other.x) + abs(self.y - other.y)
                   if dist < cfg.AGENT_VIEW_RADIUS * 0.7: # Check within interaction range
                       potential_targets.append(other)

         if not potential_targets: return None

         # Evaluate potential targets
         for other in potential_targets:
            need_level = 0
            can_help_flag = False

            # Check Hunger Need
            if other.hunger > cfg.MAX_HUNGER * 0.7 and self.inventory.get('Food', 0) >= 1:
                need_level = max(need_level, (other.hunger / cfg.MAX_HUNGER)**2)
                can_help_flag = True

            # Check Thirst Need (Requires carrying water mechanism)
            # if other.thirst > cfg.MAX_THIRST * 0.7 and self.inventory.get('WaterskinFull', 0) >= 1:
            #    need_level = max(need_level, (other.thirst / cfg.MAX_THIRST)**2 * 1.1) # Thirst slightly more urgent
            #    can_help_flag = True

            if can_help_flag:
                relationship = self.knowledge.get_relationship(other.id)
                # Consider helping only if relationship is not too negative
                if relationship >= cfg.HELPING_RELATIONSHIP_THRESHOLD:
                    # Weight need by relationship and sociability
                    weighted_need = need_level * (0.5 + relationship + self.sociability) # Combined factor
                    if weighted_need > max_weighted_need:
                        max_weighted_need = weighted_need
                        best_target = other
         return best_target

    def _get_current_action_utility(self):
         """ Estimate utility of the current action for interruption checks. """
         if not self.current_action or self.current_action == 'Idle': return 0.0

         action_base = self.current_action.split(':')[0]

         # Needs have squared utility based on urgency
         if action_base == 'SatisfyThirst': return (self.thirst / cfg.MAX_THIRST)**2
         if action_base == 'SatisfyHunger': return (self.hunger / cfg.MAX_HUNGER)**2
         if action_base == 'Rest': return ((cfg.MAX_ENERGY - self.energy) / cfg.MAX_ENERGY)**2 if self.energy < cfg.MAX_ENERGY else 0.0

         # Rough estimates for others (can be refined based on goals)
         if action_base == 'GatherWood': return 0.4 * (1.5 if self.inventory.get('CrudeAxe',0)>0 else 1.0) # Value depends on tool
         if action_base == 'GatherStone': return 0.35 * (1.5 if self.inventory.get('StonePick',0)>0 else 1.0)
         if action_base == 'Craft':
              recipe_name = self.action_target.get('recipe', '')
              if recipe_name == 'CrudeAxe' and self.inventory.get('CrudeAxe', 0) == 0: return 0.7
              if recipe_name == 'StonePick' and self.inventory.get('StonePick', 0) == 0: return 0.65
              if recipe_name == 'Workbench' and not self._is_workbench_nearby(5): return 0.6
              return 0.5 # General crafting is quite important
         if action_base == 'Invent' or action_base == 'GoToWorkbench': return 0.2 # Lower base utility
         if action_base == 'Help': return 0.65 # Helping is important
         if action_base == 'Wander': return 0.05

         return 0.1 # Default low utility


    def _find_adjacent_walkable(self, x, y, walkability_matrix=None):
        """ Finds a walkable tile adjacent to (x, y), using world matrix if none provided. """
        matrix = walkability_matrix if walkability_matrix is not None else self.world.walkability_matrix
        # Prioritize cardinal directions
        for dx, dy in [(0,1), (0,-1), (1,0), (-1,0)]:
            nx, ny = x + dx, y + dy
            if 0 <= nx < self.world.width and 0 <= ny < self.world.height:
                if matrix[ny, nx] == 1:
                    return (nx, ny)
        # Check diagonal directions if no cardinal found
        for dx, dy in [(1,1), (1,-1), (-1,1), (-1,-1)]:
            nx, ny = x + dx, y + dy
            if 0 <= nx < self.world.width and 0 <= ny < self.world.height:
                if matrix[ny, nx] == 1:
                    return (nx, ny)
        return None


    def _find_walkable_near(self, x, y, max_search_dist=5):
         """ Finds the nearest walkable tile to x,y using BFS, limited search. """
         if 0 <= x < self.world.width and 0 <= y < self.world.height and self.world.walkability_matrix[y, x] == 1:
             return (x, y) # Target itself is walkable

         q = [(x, y, 0)] # x, y, distance
         visited = set([(x,y)])

         while q:
             curr_x, curr_y, dist = q.pop(0)
             if dist >= max_search_dist: continue

             # Check neighbors in order: Cardinal first, then Diagonal
             neighbors = [(0,1), (0,-1), (1,0), (-1,0), (1,1), (1,-1), (-1,1), (-1,-1)]
             for dx, dy in neighbors:
                 nx, ny = curr_x + dx, curr_y + dy
                 if 0 <= nx < self.world.width and 0 <= ny < self.world.height and (nx, ny) not in visited:
                     if self.world.walkability_matrix[ny, nx] == 1:
                         return (nx, ny) # Found nearest walkable
                     visited.add((nx, ny))
                     # Only add valid grid points to queue (even if unwalkable) to explore from them
                     q.append((nx, ny, dist + 1))

         return None # No walkable tile found nearby