# agent.py
import random
import math
import config as cfg
from pathfinding_utils import find_path
from knowledge import KnowledgeSystem
from world import Resource # For type checking workbench
import traceback # For error logging

_agent_id_counter = 0

class Agent:
    def __init__(self, x, y, world):
        global _agent_id_counter
        self.id = _agent_id_counter; _agent_id_counter += 1
        self.x = x; self.y = y
        self.world = world
        self.health = cfg.MAX_HEALTH; self.energy = cfg.MAX_ENERGY
        self.hunger = 0; self.thirst = 0
        self.current_action = None; self.action_target = None
        self.current_path = []; self.action_timer = 0.0
        self.inventory = {}; self.skills = {
            'GatherWood': cfg.INITIAL_SKILL_LEVEL,
            'GatherStone': cfg.INITIAL_SKILL_LEVEL,
            'BasicCrafting': cfg.INITIAL_SKILL_LEVEL,
        }
        self.knowledge = KnowledgeSystem(self.id)
        self.sociability = random.uniform(0.1, 0.9)
        self.pending_signal = None

    def update(self, dt_real_seconds, agents, social_manager):
        dt_sim_seconds = dt_real_seconds * cfg.SIMULATION_SPEED_FACTOR
        self._update_needs(dt_sim_seconds)
        if self.health <= 0: self._handle_death(); return
        self._process_signals(agents, social_manager)

        action_just_chosen = False # Flag to prevent executing newly chosen action immediately
        if not self.current_action:
            self._choose_action(agents, social_manager)
            action_just_chosen = True # Don't execute this tick, path needs planning/checking

        # Only execute if an action exists and wasn't *just* chosen
        if self.current_action and not action_just_chosen:
            action_complete = self._perform_action(dt_sim_seconds, agents, social_manager)
            if action_complete:
                self._complete_action()

    def _update_needs(self, dt_sim_seconds):
        self.hunger = min(cfg.MAX_HUNGER, self.hunger + cfg.HUNGER_INCREASE_RATE * dt_sim_seconds)
        self.thirst = min(cfg.MAX_THIRST, self.thirst + cfg.THIRST_INCREASE_RATE * dt_sim_seconds)

        if self.current_action != "Rest":
            self.energy = max(0, self.energy - cfg.ENERGY_DECAY_RATE * dt_sim_seconds)
        else:
            self.energy = min(cfg.MAX_ENERGY, self.energy + cfg.ENERGY_REGEN_RATE * dt_sim_seconds)
            # Regenerate health only while resting and not critically hungry/thirsty
            if self.energy > cfg.MAX_ENERGY * 0.5 and self.hunger < cfg.MAX_HUNGER * 0.8 and self.thirst < cfg.MAX_THIRST * 0.8:
                self.health = min(cfg.MAX_HEALTH, self.health + cfg.HEALTH_REGEN_RATE * dt_sim_seconds)

        health_drain = 0
        if self.hunger >= cfg.MAX_HUNGER * 0.95: health_drain += 0.8
        if self.thirst >= cfg.MAX_THIRST * 0.95: health_drain += 1.0
        if self.energy <= 0 and self.current_action != "Rest": health_drain += 0.5
        self.health = max(0, self.health - health_drain * dt_sim_seconds)

    def _choose_action(self, agents, social_manager):
        """ Utility AI Decision Making """
        utilities = {}
        # Basic Needs
        utilities['SatisfyThirst'] = (self.thirst / cfg.MAX_THIRST)**2
        utilities['SatisfyHunger'] = (self.hunger / cfg.MAX_HUNGER)**2
        energy_deficit = (cfg.MAX_ENERGY - self.energy) / cfg.MAX_ENERGY
        # Only consider resting if energy is below 70% or health is low while not critically hungry/thirsty
        needs_rest = (self.energy < cfg.MAX_ENERGY * 0.7 or
                      (self.health < cfg.MAX_HEALTH * 0.9 and self.hunger < cfg.MAX_HUNGER * 0.8 and self.thirst < cfg.MAX_THIRST * 0.8))
        utilities['Rest'] = energy_deficit**2 if needs_rest else 0

        # Resource Gathering
        has_axe = self.inventory.get('CrudeAxe', 0) > 0
        has_pick = self.inventory.get('StonePick', 0) > 0
        current_wood = self.inventory.get('Wood', 0); current_stone = self.inventory.get('Stone', 0)
        inventory_full = sum(self.inventory.values()) >= cfg.INVENTORY_CAPACITY

        if not inventory_full or current_wood < 10: # Goal of 10 wood
            wood_need = max(0, min(1, (10 - current_wood) / 10))
            utility = wood_need * 0.4 * (1.8 if has_axe else 1.0) * (0.1 if inventory_full else 1.0)
            utilities['GatherWood'] = utility
        if not inventory_full or current_stone < 5: # Goal of 5 stone
            stone_need = max(0, min(1, (5 - current_stone) / 5))
            utility = stone_need * 0.35 * (1.8 if has_pick else 1.0) * (0.1 if inventory_full else 1.0)
            utilities['GatherStone'] = utility

        # Crafting
        best_craft_utility = 0; best_craft_recipe = None
        for recipe_name, details in cfg.RECIPES.items():
            # Check resources, skill, and if near workbench if required
            if not (self._has_ingredients(details['ingredients']) and self._has_skill_for(details)): continue
            if details.get('workbench', False) and not self._is_workbench_nearby(distance=cfg.WORKBENCH_INTERACTION_RADIUS): continue # Check if near workbench if needed

            utility = 0.0; knows = self.knowledge.knows_recipe(recipe_name)
            if knows: utility += 0.1 # Small boost for known recipes

            # Specific item needs boosting utility
            if recipe_name == 'CrudeAxe' and not has_axe: utility = 0.7
            elif recipe_name == 'StonePick' and not has_pick: utility = 0.65 # No dependency on stone amount here
            elif recipe_name == 'Workbench' and not self._is_workbench_nearby(distance=10): utility = 0.6 # Increased desire if none around
            elif recipe_name == 'SmallShelter' and self.inventory.get('SmallShelter', 0) == 0: utility = 0.5 # Desire for shelter

            if knows and utility > best_craft_utility:
                best_craft_utility = utility; best_craft_recipe = recipe_name
        if best_craft_recipe: utilities['Craft:' + best_craft_recipe] = best_craft_utility

        # Invention / GoToWorkbench
        needs_met_factor = max(0, 1 - max(utilities.get('SatisfyThirst',0), utilities.get('SatisfyHunger',0), utilities.get('Rest',0)))
        can_invent_items = len(self.inventory) >= 2 # Basic check, knowledge checks details
        is_at_wb = self._is_at_workbench()

        if can_invent_items:
            # Invent if at workbench
            if is_at_wb:
                 known_recipe_count = len(self.knowledge.known_recipes)
                 # Higher utility if fewer recipes are known
                 utility = 0.15 * needs_met_factor * random.uniform(0.8, 1.2) * max(0.1, 1 - known_recipe_count / len(cfg.RECIPES))
                 utilities['Invent'] = utility
            # Consider going to workbench to invent if not there
            else:
                 _, wb_stand_pos, _ = self.world.find_nearest_resource(self.x, self.y, cfg.RESOURCE_WORKBENCH)
                 if wb_stand_pos:
                     utilities['GoToWorkbench:Invent'] = 0.1 * needs_met_factor # Lower utility, just for travel

        # Social: Help
        target_to_help = self._find_agent_to_help(agents)
        if target_to_help:
             rel_mod = (1 + self.knowledge.get_relationship(target_to_help.id)) / 2 # Scale relationship [-1,1] to [0,1]
             help_need = 0
             # Consider urgency of need
             if target_to_help.hunger > cfg.MAX_HUNGER * 0.7: help_need = max(help_need, (target_to_help.hunger / cfg.MAX_HUNGER)**2)
             if target_to_help.thirst > cfg.MAX_THIRST * 0.7: help_need = max(help_need, (target_to_help.thirst / cfg.MAX_THIRST)**2)
             # Maybe add help for low health? Requires different mechanism (e.g., carrying?)

             if help_need > 0:
                 # Utility depends on need, relationship, and agent's sociability
                 utilities['Help:'+str(target_to_help.id)] = 0.6 * self.sociability * rel_mod * help_need

        # Default Exploration / Idleness
        utilities['Wander'] = 0.05 * needs_met_factor # Wander less if very needy

        # --- Selection ---
        best_action = None; max_utility = -1; self.action_target = None
        sorted_utilities = sorted(utilities.items(), key=lambda item: item[1], reverse=True)
        if cfg.DEBUG_AGENT_AI: print(f"Agent {self.id} Utilities: {[(a, f'{u:.2f}') for a, u in sorted_utilities]}") # DEBUG

        for action, utility in sorted_utilities:
            # Check utility threshold (unless it's the fallback Wander)
            if utility <= cfg.UTILITY_THRESHOLD and action != 'Wander': continue

            feasible, target_data = self._check_action_feasibility(action, agents)
            if feasible:
                best_action = action; max_utility = utility; self.action_target = target_data
                break # Found the highest feasible utility action

        # If no action met threshold or was feasible, fall back to Wander or Idle
        if not best_action:
            feasible, target_data = self._check_action_feasibility('Wander', agents)
            if feasible:
                best_action = 'Wander'; max_utility = utilities.get('Wander', 0.05); self.action_target = target_data
            else: # If even Wander isn't feasible (e.g., completely boxed in), Idle.
                best_action = "Idle"; max_utility = 0; self.action_target = None

        # --- Initiate Action ---
        # Avoid restarting the same non-idle action if nothing changed significantly
        # (Simple check for now, could be more sophisticated)
        # if self.current_action == best_action and best_action != "Idle": return

        if cfg.DEBUG_AGENT_CHOICE: print(f"Agent {self.id} choosing action: {best_action} (Utility: {max_utility:.2f}) Needs(H,T,E): ({self.hunger:.0f},{self.thirst:.0f},{self.energy:.0f}) Inv: {sum(self.inventory.values())}")

        self.current_action = best_action; self.current_path = []; self.action_timer = 0.0
        if best_action == "Idle": self.action_target = None; return

        # --- Path Planning for actions requiring movement ---
        target_setup_success = False
        try:
            stand_pos = self.action_target.get('stand') if self.action_target else None

            # Actions that inherently require a destination
            if stand_pos:
                current_pos = (self.x, self.y)
                if current_pos == stand_pos:
                    # Already at the destination
                    target_setup_success = True; self.current_path = []
                else:
                    # Need to plan path
                    self.current_path = self._plan_path(stand_pos, agents)
                    if self.current_path is not None: # Pathing succeeded (could be empty list if adjacent)
                        target_setup_success = True
                        if not self.current_path and current_pos != stand_pos:
                             if cfg.DEBUG_PATHFINDING: print(f"Agent {self.id}: Path to {stand_pos} for {best_action} resulted in empty list, but not at target. Failing.")
                             target_setup_success = False # Treat as failure if path is empty but not already there
                    else: # Pathing returned None (error)
                         if cfg.DEBUG_PATHFINDING: print(f"Agent {self.id}: Path to {stand_pos} for {best_action} failed (pathfinder error).")
                         target_setup_success = False

            # Actions that happen at the current location (don't require pathfinding)
            elif best_action in ['Rest', 'Craft', 'Invent']:
                # Craft/Invent might require being *near* a workbench, but the action itself happens here.
                # Feasibility check should have handled workbench proximity already.
                target_setup_success = True
                self.current_path = []

            else:
                # Action might not need movement OR target data is missing 'stand'
                if cfg.DEBUG_AGENT_AI: print(f"Agent {self.id}: Action {best_action} doesn't have explicit 'stand' target. Assuming action happens at current location or target data is incomplete: {self.action_target}")
                # Assume success if no stand_pos was expected (like Idle, handled above)
                # If a stand_pos *was* expected but missing, this is an error caught here.
                if 'stand' not in (self.action_target or {}):
                     target_setup_success = True # Assume it's okay if no stand pos was defined for this action type
                     self.current_path = []
                else:
                     target_setup_success = False # Stand pos was expected but is None/missing

        except Exception as e:
             print(f"!!! Error during action path planning setup for Agent {self.id}, Action: {best_action}: {e}"); traceback.print_exc()
             target_setup_success = False

        if not target_setup_success: # Revert to Idle on failure
             print(f"Agent {self.id}: Failed to initiate action {best_action} (pathing or target setup failed). Reverting to Idle.")
             self.current_action = "Idle"; self.action_target = None; self.current_path = []

    def _check_action_feasibility(self, action_name, agents):
        """ Checks if action is possible, returns (bool feasible, dict target_data). """
        target_data = {'type': action_name.split(':')[0]}; goal_pos, stand_pos, dist = None, None, float('inf')

        if action_name == 'SatisfyThirst':
            # Look for known water first
            known_waters = self.knowledge.get_known_locations(cfg.RESOURCE_WATER)
            best_known_dist = float('inf')
            for wx, wy in known_waters:
                # Need adjacent walkable spot to drink
                adj = self._find_adjacent_walkable(wx, wy)
                if adj:
                    d = abs(self.x - adj[0]) + abs(self.y - adj[1]) # Manhattan dist for rough check
                    if d < best_known_dist: best_known_dist = d; goal_pos = (wx, wy); stand_pos = adj
            # If no known water is close enough, search the world
            if not stand_pos or best_known_dist > 5: # Search wider if known is far
                g_pos, s_pos, d = self.world.find_nearest_resource(self.x, self.y, cfg.RESOURCE_WATER)
                if s_pos: # Found potentially closer water
                     # Update knowledge only if found via world search
                     self.knowledge.add_resource_location(cfg.RESOURCE_WATER, g_pos[0], g_pos[1])
                     goal_pos, stand_pos, dist = g_pos, s_pos, d
            if stand_pos: target_data.update({'goal': goal_pos, 'stand': stand_pos}); return True, target_data

        elif action_name == 'SatisfyHunger':
            # Prioritize known food, then search
            goal_pos, stand_pos, dist = self._find_best_resource_location(cfg.RESOURCE_FOOD)
            if stand_pos: target_data.update({'goal': goal_pos, 'stand': stand_pos}); return True, target_data

        elif action_name == 'GatherWood':
            if sum(self.inventory.values()) >= cfg.INVENTORY_CAPACITY: return False, None # Skip if full
            goal_pos, stand_pos, dist = self._find_best_resource_location(cfg.RESOURCE_WOOD)
            if stand_pos: target_data.update({'goal': goal_pos, 'stand': stand_pos}); return True, target_data

        elif action_name == 'GatherStone':
            if sum(self.inventory.values()) >= cfg.INVENTORY_CAPACITY: return False, None # Skip if full
            goal_pos, stand_pos, dist = self._find_best_resource_location(cfg.RESOURCE_STONE)
            if stand_pos: target_data.update({'goal': goal_pos, 'stand': stand_pos}); return True, target_data

        elif action_name.startswith('Craft:'):
             recipe_name = action_name.split(':')[1]; details = cfg.RECIPES.get(recipe_name)
             if not details: return False, None # Invalid recipe name

             # Check knowledge, ingredients, skill BEFORE checking workbench location
             if not (self.knowledge.knows_recipe(recipe_name) and
                     self._has_ingredients(details['ingredients']) and
                     self._has_skill_for(details)):
                 return False, None

             req_wb = details.get('workbench', False)
             target_data.update({'recipe': recipe_name, 'requires_workbench': req_wb})

             if req_wb:
                 # If workbench required, must be at/near one, or find one to go to
                 if self._is_at_workbench():
                     # Already at workbench, craft here
                     stand_pos = (self.x, self.y); goal_pos = (self.x, self.y) # Goal is irrelevant here
                 else:
                     # Not at workbench, find nearest one to travel to
                     goal_pos, stand_pos, dist = self._find_best_resource_location(cfg.RESOURCE_WORKBENCH)
                     if not stand_pos: return False, None # No known/nearby workbench available
             else:
                 # No workbench required, craft at current location
                 stand_pos = (self.x, self.y); goal_pos = (self.x, self.y)

             target_data.update({'goal': goal_pos, 'stand': stand_pos}); return True, target_data

        elif action_name == 'Invent':
             target_data['requires_workbench'] = True
             # Must have items and be AT workbench
             if len(self.inventory) >= 2 and self._is_at_workbench():
                 target_data['stand'] = (self.x, self.y); target_data['goal'] = (self.x, self.y) # Action happens here
                 return True, target_data

        elif action_name == 'GoToWorkbench:Invent':
             # Must have items, action is feasible if a workbench exists to path to
             if len(self.inventory) >= 2:
                  goal_pos, stand_pos, dist = self._find_best_resource_location(cfg.RESOURCE_WORKBENCH)
                  if stand_pos:
                      target_data.update({'goal': goal_pos, 'stand': stand_pos})
                      target_data['type'] = 'GoToWorkbench' # Set type correctly for action execution
                      return True, target_data

        elif action_name.startswith('Help:'):
             target_id = int(action_name.split(':')[1]); target_agent = next((a for a in agents if a.id == target_id and a.health > 0), None)
             if not target_agent: return False, None # Target agent doesn't exist or is dead

             # Check if help is actually needed and possible
             can_help = False
             if target_agent.hunger > cfg.MAX_HUNGER * 0.7 and self.inventory.get('Food', 0) >= 1 and self.hunger < cfg.MAX_HUNGER * 0.85:
                 can_help = True
             # Add other help types here (e.g., water)
             # elif target_agent.thirst > cfg.MAX_THIRST * 0.7 and self.inventory.get('WaterskinFull', 0) >= 1 and self.thirst < cfg.MAX_THIRST * 0.85:
             #     can_help = True

             if not can_help: return False, None

             # Find a reachable spot adjacent to the target agent
             stand_pos = self._find_adjacent_walkable(target_agent.x, target_agent.y)
             if stand_pos:
                 target_data.update({'goal': target_id, 'stand': stand_pos}) # Goal is agent ID, stand is position
                 return True, target_data

        elif action_name == 'Wander':
             # Try finding a random walkable ground tile within radius
             for _ in range(10): # Try a few times
                  wx = self.x + random.randint(-cfg.WANDER_RADIUS, cfg.WANDER_RADIUS);
                  wy = self.y + random.randint(-cfg.WANDER_RADIUS, cfg.WANDER_RADIUS)
                  # Clamp to world bounds
                  wx = max(0, min(self.world.width - 1, wx))
                  wy = max(0, min(self.world.height - 1, wy))

                  if self.world.walkability_matrix[wy, wx] == 1 and self.world.terrain_map[wy,wx] == cfg.TERRAIN_GROUND:
                       stand_pos = (wx, wy); break
             else: # If no suitable random spot found, try moving just one step
                 stand_pos = self._find_adjacent_walkable(self.x, self.y)

             if stand_pos:
                 target_data['stand'] = stand_pos; target_data['goal'] = stand_pos # Goal and stand are the same for wander
                 return True, target_data
             # If even adjacent is blocked, Wander is not feasible

        elif action_name == "Idle":
            return True, {'type': 'Idle'} # Always feasible

        elif action_name == "Rest":
            # Rest is feasible if basic needs aren't critical (prevents resting to death)
            # This check is arguably better placed in utility calculation, but double-check here.
            if self.hunger < cfg.MAX_HUNGER * 0.95 and self.thirst < cfg.MAX_THIRST * 0.95:
                 target_data['stand'] = (self.x, self.y) # Rest at current location
                 return True, target_data

        # Default: Action not recognized or conditions not met
        return False, None

    def _find_best_resource_location(self, resource_type, max_search_dist=cfg.AGENT_VIEW_RADIUS):
        """Finds the best known or nearby resource location."""
        best_pos = None; best_stand_pos = None; min_dist = float('inf')

        # 1. Check known locations
        known_locations = self.knowledge.get_known_locations(resource_type)
        valid_known = []
        for rx, ry in known_locations:
            res = self.world.get_resource(rx, ry)
            # Check if resource still exists and has quantity
            if res and res.type == resource_type and not res.is_depleted():
                valid_known.append((rx, ry))
                stand_pos = self._find_stand_pos_for_resource(rx, ry)
                if stand_pos:
                    # Use pathfinding distance for accuracy? Simpler: Manhattan distance
                    dist = abs(self.x - stand_pos[0]) + abs(self.y - stand_pos[1])
                    if dist < min_dist:
                        min_dist = dist
                        best_pos = (rx, ry)
                        best_stand_pos = stand_pos
            else:
                # Remove knowledge of depleted/missing resource
                self.knowledge.remove_resource_location(resource_type, rx, ry)

        # Update knowledge with only valid known locations
        # self.knowledge.known_resource_locations[resource_type] = set(valid_known) # Might be slow if large

        # 2. If no known resource is close enough, search the nearby world
        # Search if no known resource found, or nearest known is further than a threshold
        search_threshold = max_search_dist / 2
        if not best_stand_pos or min_dist > search_threshold:
            g_pos, s_pos, dist = self.world.find_nearest_resource(self.x, self.y, resource_type, max_dist=max_search_dist)
            if s_pos and dist < min_dist: # Found a closer one via search
                 min_dist = dist
                 best_pos = g_pos
                 best_stand_pos = s_pos
                 # Add newly found resource to knowledge
                 self.knowledge.add_resource_location(resource_type, g_pos[0], g_pos[1])

        return best_pos, best_stand_pos, min_dist

    def _find_stand_pos_for_resource(self, res_x, res_y):
        """Determines the appropriate standing position to interact with a resource."""
        resource = self.world.get_resource(res_x, res_y)
        if not resource: return None # Resource doesn't exist

        # If the resource tile itself is walkable (e.g., workbench), stand on it
        if self.world.walkability_matrix[res_y, res_x] == 1:
            return (res_x, res_y)
        else:
            # If resource blocks walking (e.g., tree, rock), find adjacent walkable
            return self._find_adjacent_walkable(res_x, res_y)


    def _is_workbench_nearby(self, distance=cfg.WORKBENCH_INTERACTION_RADIUS):
        """ Checks if a workbench resource exists within the specified Chebyshev distance. """
        for dx in range(-distance, distance + 1):
             for dy in range(-distance, distance + 1):
                 # No need to check (0,0) explicitly if interaction doesn't require adjacent
                 check_x, check_y = self.x + dx, self.y + dy
                 if 0 <= check_x < self.world.width and 0 <= check_y < self.world.height:
                     res = self.world.get_resource(check_x, check_y)
                     if res and res.type == cfg.RESOURCE_WORKBENCH:
                         return True
        return False

    def _is_at_workbench(self):
        """ Checks if standing directly on or immediately adjacent (radius 1) to a workbench tile. """
        return self._is_workbench_nearby(distance=1)


    def _plan_path(self, target_pos, agents):
        """
        Finds path using A*, avoiding other agents. Returns list of (x, y) tuples or None on failure.
        Handles cases where the target tile itself is blocked.
        """
        start_pos = (self.x, self.y)
        if not target_pos or start_pos == target_pos:
            return [] # Already at target or no target specified

        tx, ty = target_pos
        if not (0 <= tx < self.world.width and 0 <= ty < self.world.height):
            if cfg.DEBUG_PATHFINDING: print(f"Agent {self.id}: Path target {target_pos} out of bounds.")
            return None # Target is outside the world

        # Create a temporary walkability grid, marking other agents' positions as blocked
        other_agent_positions = [(a.x, a.y) for a in agents if a != self and a.health > 0]
        temp_walkability = self.world.update_walkability(agent_positions=other_agent_positions)

        # Check if the start position is valid in the temporary grid (should usually be true)
        if temp_walkability[start_pos[1], start_pos[0]] == 0:
            if cfg.DEBUG_PATHFINDING: print(f"Agent {self.id}: Start position {start_pos} is blocked in temp grid! Cannot plan path.")
            # This might happen if another agent moved exactly onto the start tile in the same tick? Rare.
            # Could try finding an adjacent start, but for now, fail the path planning.
            return None

        final_target = target_pos
        # Check if the target position is walkable in the temporary grid
        if temp_walkability[ty, tx] == 0:
            # Target is blocked (e.g., by another agent, or it's a blocking resource like a tree)
            # Find the nearest walkable adjacent tile to the original target.
            adj_target = self._find_adjacent_walkable(tx, ty, temp_walkability)
            if not adj_target:
                # Cannot find any walkable tile next to the blocked target. Path is impossible.
                if cfg.DEBUG_PATHFINDING: print(f"Agent {self.id}: Target {target_pos} is blocked, and no adjacent walkable tile found.")
                return None # Indicate pathfinding failure
            else:
                # Use the adjacent walkable tile as the new target for A*
                final_target = adj_target
                if cfg.DEBUG_PATHFINDING: print(f"Agent {self.id}: Original target {target_pos} blocked, using adjacent {final_target}.")


        # --- Call the A* pathfinding function ---
        path_nodes = find_path(temp_walkability, start_pos, final_target)
        # ----------------------------------------

        if path_nodes is None:
            # find_path returns None on internal errors (e.g., invalid start/end for the library)
            if cfg.DEBUG_PATHFINDING: print(f"Agent {self.id}: find_path returned None (error) for {start_pos}->{final_target}.")
            return None
        elif not path_nodes and start_pos != final_target:
            # find_path returns [] if no path exists between start and end
            if cfg.DEBUG_PATHFINDING: print(f"Agent {self.id}: find_path returned empty list (no path found) for {start_pos}->{final_target}.")
            # Treat no path found as a failure (return None)
            return None
        else:
            # Path found (potentially empty list if start == final_target)
            # Convert GridNode objects to simple (x, y) tuples for easier use
            path_coords = [(node.x, node.y) for node in path_nodes]
            if cfg.DEBUG_PATHFINDING and path_coords: print(f"Agent {self.id}: Path found from {start_pos} to {final_target} (length {len(path_coords)}): {path_coords[:5]}...")
            elif cfg.DEBUG_PATHFINDING: print(f"Agent {self.id}: Path found from {start_pos} to {final_target} (length 0 - already adjacent or at target)")
            return path_coords


    def _perform_action(self, dt_sim_seconds, agents, social_manager):
        """ Executes the current action step, returns True if completed """
        if not self.current_action or self.current_action == "Idle":
            return True # Idle action is always "complete"

        # --- 1. Movement Phase ---
        if self.current_path:
            next_pos = self.current_path[0]; nx, ny = next_pos
            # Check if the next step is occupied *now*
            occupied = any(a.x == nx and a.y == ny for a in agents if a != self and a.health > 0)

            if occupied:
                # Path is blocked by another agent. Try to replan.
                stand_pos = self.action_target.get('stand') if self.action_target else None
                if stand_pos:
                     if cfg.DEBUG_PATHFINDING: print(f"Agent {self.id}: Path blocked at {next_pos} by another agent. Re-planning to {stand_pos} for action {self.current_action}.")
                     new_path = self._plan_path(stand_pos, agents)
                     if new_path is not None: # Replan succeeded (might be empty if already close)
                         self.current_path = new_path
                         # If the new path is also empty, we might be stuck, but try again next tick
                         return False # Continue action next tick with the new path
                     else:
                         # Replan failed. Give up on the current action.
                         print(f"Agent {self.id}: Failed to recalculate path around block at {next_pos}. Failing action {self.current_action}.")
                         return True # Action failed, complete it.
                else:
                    # No standing position defined? This shouldn't happen if path exists.
                    print(f"Agent {self.id}: Path blocked at {next_pos}, but no 'stand' position in target data? Failing action {self.current_action}.")
                    return True # Action failed

            else:
                # Move to the next position
                self.x = nx; self.y = ny
                self.energy -= cfg.MOVE_ENERGY_COST
                self.current_path.pop(0)
                # If path is now empty, movement is done, proceed to action execution *this tick*.
                # Otherwise, movement continues next tick.
                if self.current_path:
                    return False # Still moving
                # else: path is empty, fall through to action execution

        # --- 2. Action Execution Phase (Reached destination or no movement needed) ---
        # Verify if agent is correctly positioned for the action, if a position matters.
        expected_stand_pos = self.action_target.get('stand') if self.action_target else None
        is_correctly_positioned = False
        action_type = self.current_action.split(':')[0] # Get base action type

        if expected_stand_pos:
            current_pos = (self.x, self.y)
            # Check if at the exact standing position OR adjacent is allowed for certain actions
            chebyshev_dist = max(abs(self.x - expected_stand_pos[0]), abs(self.y - expected_stand_pos[1]))

            # Define actions where adjacency (dist=1) is sufficient
            adjacent_allowed_actions = {'GatherWood', 'GatherStone', 'SatisfyHunger', 'SatisfyThirst', 'Help'}
            # Crafting/Inventing usually requires being *at* the workbench tile or adjacent? Let's use is_at_workbench check later.

            if current_pos == expected_stand_pos:
                is_correctly_positioned = True
            elif chebyshev_dist <= 1 and action_type in adjacent_allowed_actions:
                is_correctly_positioned = True
                # Optional Debug: Only print if it was NOT exact match but adjacent
                # if cfg.DEBUG_AGENT_AI: print(f"Agent {self.id}: Arrived adjacent ({current_pos}) to expected {expected_stand_pos} for {self.current_action}. Allowing action.")
            elif action_type in ['Craft', 'Invent', 'GoToWorkbench'] and self._is_at_workbench():
                 # Special check for workbench actions - being near is enough
                 is_correctly_positioned = True

            # If not positioned correctly AND a stand position was expected, fail the action.
            if not is_correctly_positioned:
                print(f"Agent {self.id}: Arrived at ({self.x},{self.y}) but not correctly positioned relative to {expected_stand_pos} for {self.current_action}. Action failed.")
                # Possible reasons: Path led somewhere unexpected, target moved, stand_pos logic error.
                # Try to replan maybe? For now, just fail.
                return True # Fail the action

        else:
            # No specific standing position expected (e.g., Rest, Wander, some Crafts)
            is_correctly_positioned = True # Assume okay

        # --- If correctly positioned, proceed with action timer etc. ---
        self.action_timer += dt_sim_seconds
        base_action_duration = 1.0 # Base time units for actions

        try:
            # --- Basic Needs Actions ---
            if self.current_action == 'SatisfyThirst':
                # Assumes agent is adjacent to water tile (verified by positioning check)
                drink_duration = base_action_duration * 0.5
                if self.action_timer >= drink_duration:
                    self.thirst = max(0, self.thirst - cfg.DRINK_THIRST_REDUCTION)
                    self.energy -= cfg.MOVE_ENERGY_COST * 0.1 # Small energy cost for drinking
                    if cfg.DEBUG_AGENT_ACTIONS: print(f"Agent {self.id} drank. Thirst: {self.thirst:.1f}")
                    return True # Action complete
                else: return False # Still drinking

            elif self.current_action == 'SatisfyHunger':
                # Assumes agent is at/adjacent to food resource
                goal_pos = self.action_target['goal']; resource = self.world.get_resource(goal_pos[0], goal_pos[1])
                eat_duration = base_action_duration * 0.6

                if not resource or resource.is_depleted():
                     self.knowledge.remove_resource_location(cfg.RESOURCE_FOOD, goal_pos[0], goal_pos[1])
                     if cfg.DEBUG_AGENT_ACTIONS: print(f"Agent {self.id}: Food at {goal_pos} is gone. Cannot eat.")
                     return True # Action failed/complete

                if self.action_timer >= eat_duration:
                    amount_eaten = self.world.consume_resource_at(goal_pos[0], goal_pos[1], 1)
                    if amount_eaten > 0:
                        self.hunger = max(0, self.hunger - cfg.EAT_HUNGER_REDUCTION)
                        self.energy -= cfg.MOVE_ENERGY_COST * 0.1 # Small energy cost for eating
                        if cfg.DEBUG_AGENT_ACTIONS: print(f"Agent {self.id} ate. Hunger: {self.hunger:.1f}")
                        if resource.is_depleted(): # Check if depleted after eating
                            self.knowledge.remove_resource_location(cfg.RESOURCE_FOOD, goal_pos[0], goal_pos[1])
                    else:
                        # Resource became depleted just before consumption?
                        self.knowledge.remove_resource_location(cfg.RESOURCE_FOOD, goal_pos[0], goal_pos[1])
                        if cfg.DEBUG_AGENT_ACTIONS: print(f"Agent {self.id}: Failed to eat, food at {goal_pos} depleted.")
                    return True # Attempt complete
                else: return False # Still eating

            elif self.current_action == 'Rest':
                # Continue resting until energy full OR needs become too high
                if self.energy >= cfg.MAX_ENERGY or self.thirst > cfg.MAX_THIRST * 0.9 or self.hunger > cfg.MAX_HUNGER * 0.9:
                    if cfg.DEBUG_AGENT_ACTIONS: print(f"Agent {self.id} finished resting.")
                    return True # Stop resting
                return False # Continue resting

            elif self.current_action == 'Wander':
                # Action is complete upon reaching the wander destination
                return True

            # --- Resource Gathering Actions ---
            elif self.current_action == 'GatherWood':
                 goal_pos = self.action_target['goal']; resource = self.world.get_resource(goal_pos[0], goal_pos[1])
                 if not resource or resource.is_depleted() or resource.type != cfg.RESOURCE_WOOD:
                      self.knowledge.remove_resource_location(cfg.RESOURCE_WOOD, goal_pos[0], goal_pos[1])
                      if cfg.DEBUG_AGENT_ACTIONS: print(f"Agent {self.id}: Wood at {goal_pos} gone/invalid.")
                      return True # Cannot gather

                 tool_mult = cfg.TOOL_EFFICIENCY.get('CrudeAxe', 1.0) if self.inventory.get('CrudeAxe', 0) > 0 else 1.0
                 skill_mult = self._get_skill_multiplier('GatherWood')
                 action_duration = cfg.GATHER_BASE_DURATION / (skill_mult * tool_mult)

                 if self.action_timer >= action_duration:
                     amount = self.world.consume_resource_at(goal_pos[0], goal_pos[1], 1)
                     if amount > 0:
                         self.inventory['Wood'] = self.inventory.get('Wood', 0) + amount
                         self.energy -= cfg.GATHER_ENERGY_COST / tool_mult # Less energy cost with tool?
                         self.learn_skill('GatherWood')
                         if cfg.DEBUG_AGENT_ACTIONS: print(f"Agent {self.id} gathered {amount} Wood. Total: {self.inventory.get('Wood', 0)}")
                         self.action_timer = 0 # Reset timer for next unit

                         # Check stopping conditions
                         inv_full = sum(self.inventory.values()) >= cfg.INVENTORY_CAPACITY
                         gathered_enough = self.inventory.get('Wood', 0) >= 10 # Gather session goal
                         low_energy = self.energy < cfg.GATHER_ENERGY_COST * 2
                         resource_gone = resource.is_depleted()

                         if inv_full or gathered_enough or low_energy or resource_gone:
                              if resource_gone: self.knowledge.remove_resource_location(cfg.RESOURCE_WOOD, goal_pos[0], goal_pos[1])
                              if cfg.DEBUG_AGENT_ACTIONS: print(f"Agent {self.id} finished gathering wood session.")
                              return True # Stop gathering session
                         else: return False # Continue gathering
                     else:
                         # Resource depleted during attempt
                         self.knowledge.remove_resource_location(cfg.RESOURCE_WOOD, goal_pos[0], goal_pos[1])
                         if cfg.DEBUG_AGENT_ACTIONS: print(f"Agent {self.id}: Wood at {goal_pos} depleted during gathering attempt.")
                         return True # Stop
                 else: return False # Still gathering this unit

            elif self.current_action == 'GatherStone':
                 goal_pos = self.action_target['goal']; resource = self.world.get_resource(goal_pos[0], goal_pos[1])
                 if not resource or resource.is_depleted() or resource.type != cfg.RESOURCE_STONE:
                     self.knowledge.remove_resource_location(cfg.RESOURCE_STONE, goal_pos[0], goal_pos[1])
                     if cfg.DEBUG_AGENT_ACTIONS: print(f"Agent {self.id}: Stone at {goal_pos} gone/invalid.")
                     return True

                 tool_mult = cfg.TOOL_EFFICIENCY.get('StonePick', 1.0) if self.inventory.get('StonePick', 0) > 0 else 1.0
                 skill_mult = self._get_skill_multiplier('GatherStone')
                 action_duration = cfg.GATHER_BASE_DURATION / (skill_mult * tool_mult)

                 if self.action_timer >= action_duration:
                     amount = self.world.consume_resource_at(goal_pos[0], goal_pos[1], 1)
                     if amount > 0:
                         self.inventory['Stone'] = self.inventory.get('Stone', 0) + amount
                         self.energy -= cfg.GATHER_ENERGY_COST / tool_mult
                         self.learn_skill('GatherStone')
                         if cfg.DEBUG_AGENT_ACTIONS: print(f"Agent {self.id} gathered {amount} Stone. Total: {self.inventory.get('Stone', 0)}")
                         self.action_timer = 0

                         # Check stopping conditions
                         inv_full = sum(self.inventory.values()) >= cfg.INVENTORY_CAPACITY
                         gathered_enough = self.inventory.get('Stone', 0) >= 5 # Gather session goal
                         low_energy = self.energy < cfg.GATHER_ENERGY_COST * 2
                         resource_gone = resource.is_depleted()

                         if inv_full or gathered_enough or low_energy or resource_gone:
                             if resource_gone: self.knowledge.remove_resource_location(cfg.RESOURCE_STONE, goal_pos[0], goal_pos[1])
                             if cfg.DEBUG_AGENT_ACTIONS: print(f"Agent {self.id} finished gathering stone session.")
                             return True
                         else: return False
                     else:
                         self.knowledge.remove_resource_location(cfg.RESOURCE_STONE, goal_pos[0], goal_pos[1])
                         if cfg.DEBUG_AGENT_ACTIONS: print(f"Agent {self.id}: Stone at {goal_pos} depleted during gathering attempt.")
                         return True
                 else: return False

            # --- Crafting & Invention ---
            elif action_type == 'Craft':
                 recipe_name = self.action_target['recipe']; details = cfg.RECIPES[recipe_name]
                 req_wb = self.action_target.get('requires_workbench', False)

                 # Verify workbench proximity again just before crafting
                 if req_wb and not self._is_at_workbench():
                     print(f"Agent {self.id} cannot craft {recipe_name} - Not at workbench (or moved away).")
                     return True # Fail action

                 skill_mult = self._get_skill_multiplier(details['skill'])
                 action_duration = cfg.CRAFT_BASE_DURATION / skill_mult

                 if self.action_timer >= action_duration:
                     # Final check for ingredients before consuming
                     if not self._has_ingredients(details['ingredients']):
                         print(f"Agent {self.id} cannot craft {recipe_name} - Missing ingredients at final moment.")
                         return True # Fail action

                     # Consume ingredients
                     for item, count in details['ingredients'].items():
                         self.inventory[item] = self.inventory.get(item, 0) - count
                         if self.inventory[item] <= 0: del self.inventory[item]

                     # Add result item OR place object in world
                     if recipe_name == 'Workbench':
                          # Try placing at current location
                          if self.world.add_world_object(Resource(cfg.RESOURCE_WORKBENCH, self.x, self.y, q=1, max_q=1, regen=0), self.x, self.y):
                              print(f"Agent {self.id} Crafted & Placed Workbench at ({self.x},{self.y}).")
                              self.knowledge.add_resource_location(cfg.RESOURCE_WORKBENCH, self.x, self.y) # Know where it is
                              social_manager.broadcast_signal(self, f"Crafted:{recipe_name}", (self.x, self.y))
                          else:
                              print(f"Agent {self.id} crafted Workbench but failed to place it at ({self.x},{self.y}). Item lost.")
                              # Maybe try placing adjacent? For now, just lost.
                     elif recipe_name == 'SmallShelter':
                          # Shelters might be placable items later, for now just inventory
                          self.inventory[recipe_name] = self.inventory.get(recipe_name, 0) + 1
                          print(f"Agent {self.id} crafted {recipe_name}. (Inventory)")
                          social_manager.broadcast_signal(self, f"Crafted:{recipe_name}", (self.x, self.y))
                     else: # Default: Add crafted item to inventory
                          self.inventory[recipe_name] = self.inventory.get(recipe_name, 0) + 1
                          print(f"Agent {self.id} crafted {recipe_name}.")
                          social_manager.broadcast_signal(self, f"Crafted:{recipe_name}", (self.x, self.y))

                     self.energy -= cfg.CRAFT_ENERGY_COST; self.learn_skill(details['skill'])
                     return True # Crafting complete
                 else:
                     return False # Still crafting

            elif self.current_action == 'Invent':
                 # Verify workbench proximity
                 if not self._is_at_workbench():
                     print(f"Agent {self.id} cannot Invent - Not at workbench.")
                     return True # Fail

                 action_duration = cfg.INVENT_BASE_DURATION
                 if self.action_timer >= action_duration:
                     discovered_recipe = self.knowledge.attempt_invention(self.inventory)
                     self.energy -= cfg.INVENT_ENERGY_COST
                     if discovered_recipe:
                         print(f"Agent {self.id} *** INVENTED *** {discovered_recipe}!")
                         social_manager.broadcast_signal(self, f"Invented:{discovered_recipe}", (self.x, self.y))
                     else:
                         if cfg.DEBUG_AGENT_ACTIONS: print(f"Agent {self.id} attempted invention, no discovery.")
                     return True # Invention attempt complete (whether successful or not)
                 else:
                     return False # Still inventing

            elif self.current_action == 'GoToWorkbench:Invent':
                 # This action's purpose is just to reach the workbench.
                 # If we are here, it means the path (if any) is finished.
                 # We should be at/near the workbench now.
                 if self._is_at_workbench():
                      # Successfully reached. The AI will likely choose 'Invent' next tick.
                      if cfg.DEBUG_AGENT_ACTIONS: print(f"Agent {self.id} arrived at workbench for invention.")
                      return True # Complete the 'GoTo' action.
                 else:
                      # Arrived somewhere, but not actually at a workbench? Pathing issue or WB destroyed?
                      print(f"Agent {self.id} finished 'GoToWorkbench' path but is not at a workbench ({self.x},{self.y}). Failing.")
                      # Try finding another workbench? For now, fail.
                      return True

            # --- Social Actions ---
            elif action_type == 'Help':
                target_id = self.action_target['goal']
                target_agent = self.world.get_agent_by_id(target_id) # Assuming world has a way to get agent by ID efficiently

                if not target_agent or target_agent.health <= 0:
                    if cfg.DEBUG_AGENT_ACTIONS: print(f"Agent {self.id}: Target agent {target_id} for help is gone.")
                    return True # Target gone, action complete/failed

                # Check proximity again (target might have moved)
                # Use Chebyshev distance (grid adjacency)
                dist = max(abs(self.x - target_agent.x), abs(self.y - target_agent.y))
                if dist <= cfg.HELPING_INTERACTION_RADIUS:
                     # Attempt the help action via SocialManager
                     success = social_manager.attempt_helping(self, target_agent)
                     if success:
                         if cfg.DEBUG_AGENT_ACTIONS: print(f"Agent {self.id} successfully helped Agent {target_id}.")
                         self.energy -= cfg.HELP_ENERGY_COST # Apply energy cost only on success
                     # else: # SocialManager handles failure case logging/relationship impact
                     #     if cfg.DEBUG_AGENT_ACTIONS: print(f"Agent {self.id}: Help attempt towards {target_id} failed (handled by SocialManager).")
                else:
                     if cfg.DEBUG_AGENT_ACTIONS: print(f"Agent {self.id}: Too far ({dist}) to help {target_id} at interaction time.")
                     # Didn't get close enough, or target moved away.

                return True # Help attempt is complete (whether successful or not)

            # --- Fallback for Unknown Actions ---
            else:
                print(f"Agent {self.id}: Encountered unknown action '{self.current_action}' during execution phase.")
                return True # Complete unknown action to avoid getting stuck

        except Exception as e:
            print(f"!!! Runtime Error performing action {self.current_action} for agent {self.id}: {e}")
            traceback.print_exc()
            return True # Complete the action on error to prevent agent lock-up


    def _complete_action(self):
        """ Resets action state after an action finishes or fails. """
        if cfg.DEBUG_AGENT_ACTIONS and self.current_action: print(f"Agent {self.id} completing action: {self.current_action}")
        self.current_action = None; self.action_target = None
        self.current_path = []; self.action_timer = 0.0

    def _handle_death(self):
        """ Actions to perform when agent's health reaches zero. """
        # Drop inventory? Create corpse object? For now, just print.
        print(f"Agent {self.id} has died at ({self.x}, {self.y}). Final Needs(H,T,E): ({self.health:.0f},{self.hunger:.0f},{self.thirst:.0f},{self.energy:.0f})")
        # Agent object will be removed from the main list in main.py

    # --- Skill & Crafting Helpers ---
    def learn_skill(self, skill_name, boost=1.0):
        """ Increases skill level based on usage, returns True if skill increased noticeably. """
        if not skill_name or skill_name not in self.skills: return False # Only learn defined skills

        current_level = self.skills.get(skill_name, cfg.INITIAL_SKILL_LEVEL)
        if current_level >= cfg.MAX_SKILL_LEVEL: return False # Already maxed

        # Increase rate diminishes as skill approaches max level
        gain_factor = (1.0 - (current_level / (cfg.MAX_SKILL_LEVEL + 1)))**1.5 # Steeper curve
        increase = cfg.SKILL_INCREASE_RATE * boost * gain_factor

        # Ensure some minimum gain if not maxed
        increase = max(0.01, increase)

        new_level = min(cfg.MAX_SKILL_LEVEL, current_level + increase)

        # Only update if the change is significant enough (avoids tiny float changes)
        if new_level > current_level + 0.001:
            self.skills[skill_name] = new_level
            # if cfg.DEBUG_AGENT_SKILLS: print(f"Agent {self.id} skill '{skill_name}' increased to {new_level:.2f}")
            return True
        return False

    def _get_skill_multiplier(self, skill_name):
        """ Returns a multiplier based on skill level (e.g., for action speed/success). """
        if not skill_name or skill_name not in self.skills: return 1.0 # No skill effect

        level = self.skills.get(skill_name, 0)
        # Non-linear scaling: starts slow, increases, then slightly tapers near max
        # Example: 1.0 + MaxBonus * (level / MaxLevel)^Exponent
        max_bonus = 1.5 # e.g., max skill gives 1.0 + 1.5 = 2.5x speed/efficiency
        exponent = 0.8
        multiplier = 1.0 + max_bonus * (level / cfg.MAX_SKILL_LEVEL)**exponent
        return max(0.1, multiplier) # Ensure multiplier is at least slightly positive

    def _has_ingredients(self, ingredients):
        """ Checks if agent has required items in inventory. """
        if not ingredients: return True # No ingredients required
        return all(self.inventory.get(item, 0) >= req for item, req in ingredients.items())

    def _has_skill_for(self, recipe_details):
        """ Checks if agent meets skill requirement for a recipe. """
        skill = recipe_details.get('skill')
        min_level = recipe_details.get('min_level', 0)
        # If no skill is required, or if the agent has the skill at or above the minimum level
        return not skill or self.skills.get(skill, 0) >= min_level

    # --- Social & Perception Helpers ---
    def perceive_signal(self, sender_id, signal_type, position):
        """ Stores a perceived signal to be processed later. Allows one signal per update. """
        # Simple model: Agent only remembers the last signal heard.
        # Could be extended to a queue or list if needed.
        self.pending_signal = (sender_id, signal_type, position)
        if cfg.DEBUG_SOCIAL: print(f"Agent {self.id} perceived signal '{signal_type}' from {sender_id} at {position}")

    def _process_signals(self, agents, social_manager):
        """ Reacts to the stored pending signal based on current state and priorities. """
        if not self.pending_signal: return

        sender_id, signal_type, signal_pos = self.pending_signal
        self.pending_signal = None # Consume the signal

        # Ignore signals from self? (Shouldn't happen with broadcast logic, but check)
        if sender_id == self.id: return

        # --- Signal Reaction Logic ---
        rel = self.knowledge.get_relationship(sender_id);
        current_util = self._get_current_action_utility() # Estimate priority of current task

        # Example: Reacting to 'FoundFood' signal
        if signal_type == 'FoundFood' and self.hunger > cfg.MAX_HUNGER * 0.4: # React if moderately hungry
            # Utility of going for signaled food: depends on hunger, relationship, distance?
            dist_sq = (self.x - signal_pos[0])**2 + (self.y - signal_pos[1])**2
            # Closer food is more attractive. Relationship makes signal more trustworthy/appealing.
            food_sig_util = (self.hunger / cfg.MAX_HUNGER)**1.5 * (0.7 + rel * 0.5) / (1 + math.sqrt(dist_sq)/10)

            if food_sig_util > current_util and food_sig_util > cfg.UTILITY_THRESHOLD:
                 if cfg.DEBUG_SOCIAL: print(f"Agent {self.id} reacting to food signal from {sender_id} (Util: {food_sig_util:.2f} vs Current: {current_util:.2f})")
                 self._complete_action() # Interrupt current action

                 # Set target to the signaled food location
                 stand_pos = self._find_stand_pos_for_resource(signal_pos[0], signal_pos[1])
                 # Need to handle case where resource is gone by the time agent gets there
                 if stand_pos:
                      self.current_action = 'SatisfyHunger'
                      self.action_target = {'type': 'SatisfyHunger', 'goal': signal_pos, 'stand': stand_pos}
                      # Path planning will happen in the next _choose_action or immediately if forced
                      new_path = self._plan_path(stand_pos, agents)
                      if new_path is not None:
                           self.current_path = new_path
                           # Action is now set, path (possibly empty) is planned
                      else:
                           # Path failed, revert to choosing action normally
                           self.current_action = None
                           self.action_target = None
                 else:
                      # Cannot stand near the signaled food (e.g., blocked, invalid)
                      self.current_action = None # Re-evaluate actions

        # Example: Reacting to 'Crafted' or 'Invented' signals (Passive Learning)
        elif signal_type.startswith("Crafted:") or signal_type.startswith("Invented:"):
             item_name = signal_type.split(':')[1]
             if item_name in cfg.RECIPES and not self.knowledge.knows_recipe(item_name):
                  # Check proximity and relationship for learning chance
                  dist_sq = (self.x - signal_pos[0])**2 + (self.y - signal_pos[1])**2
                  learn_prox_sq = (cfg.SIGNAL_RANGE * 0.5)**2 # Learn only if relatively close

                  # Chance depends on proximity, relationship, base chance
                  learn_chance = 0
                  if dist_sq < learn_prox_sq and rel >= cfg.LEARNING_RELATIONSHIP_THRESHOLD:
                       proximity_factor = 1.0 - (math.sqrt(dist_sq) / (cfg.SIGNAL_RANGE * 0.5)) # Closer = higher chance
                       relationship_factor = (1 + rel) / 2 # Scale rel [-1,1] to [0,1]
                       learn_chance = cfg.PASSIVE_LEARN_CHANCE * proximity_factor * relationship_factor

                  if random.random() < learn_chance:
                       if cfg.DEBUG_SOCIAL: print(f"Agent {self.id} passively learned recipe '{item_name}' from Agent {sender_id} (Chance: {learn_chance:.2f})")
                       self.knowledge.add_recipe(item_name)

        # Add more signal reactions here (e.g., Danger, CallForHelp)

    def decide_to_learn(self, teacher_id, skill_name):
        """ Agent's internal decision whether to accept a teaching offer. """
        # Conditions: Not in critical need, current action isn't vital, relationship okay, skill not too high.
        if self.thirst > cfg.MAX_THIRST*0.9 or self.hunger > cfg.MAX_HUNGER*0.9 or self.health < cfg.MAX_HEALTH*0.4:
            if cfg.DEBUG_SOCIAL: print(f"Agent {self.id} refuses learning '{skill_name}' from {teacher_id} (critical needs).")
            return False # Too busy with survival

        current_util = self._get_current_action_utility()
        # Don't interrupt high-priority actions unless learning utility is higher?
        # Simple check: Don't interrupt actions with utility > 0.5 unless learning offers more?
        # For now, interrupt only low-priority actions.
        if current_util > 0.5 and self.current_action not in ['Idle', 'Wander', 'Rest']:
            if cfg.DEBUG_SOCIAL: print(f"Agent {self.id} refuses learning '{skill_name}' from {teacher_id} (current action too important: {self.current_action} util {current_util:.2f}).")
            return False

        # Relationship threshold check
        if self.knowledge.get_relationship(teacher_id) < cfg.LEARNING_RELATIONSHIP_THRESHOLD:
            if cfg.DEBUG_SOCIAL: print(f"Agent {self.id} refuses learning '{skill_name}' from {teacher_id} (relationship too low: {self.knowledge.get_relationship(teacher_id):.2f}).")
            return False

        # Skill level check: Don't learn if already highly skilled
        current_skill = self.skills.get(skill_name, 0)
        if current_skill > cfg.MAX_SKILL_LEVEL * 0.9:
             if cfg.DEBUG_SOCIAL: print(f"Agent {self.id} refuses learning '{skill_name}' from {teacher_id} (skill already high: {current_skill:.1f}).")
             return False # Already very skilled

        # Seems like a good opportunity to learn
        if cfg.DEBUG_SOCIAL: print(f"Agent {self.id} accepts learning '{skill_name}' from Agent {teacher_id}.")
        self._complete_action() # Stop current low-priority action
        self.energy -= cfg.LEARN_ENERGY_COST # Energy cost for learning session
        # Set current action to 'Learning'? Or just let skill boost happen instantly?
        # For simplicity, assume learning effect is instant for now.
        return True

    def _find_agent_to_help(self, agents):
         """ Scans nearby agents and decides if any need help that this agent can provide. """
         best_target = None; max_weighted_need = 0

         # Limit how often help is considered? Or just rely on utility threshold?

         for other in agents:
              if other.id == self.id or other.health <= 0: continue # Skip self and dead agents

              # Check proximity
              dist = abs(self.x - other.x) + abs(self.y - other.y) # Manhattan distance
              if dist < cfg.AGENT_VIEW_RADIUS * 0.8: # Must be reasonably close to perceive need

                   need_level = 0; can_help_type = None

                   # Check for hunger need
                   if other.hunger > cfg.MAX_HUNGER * 0.7 and self.inventory.get('Food', 0) >= 1 and self.hunger < cfg.MAX_HUNGER * 0.85:
                       need_level = max(need_level, (other.hunger / cfg.MAX_HUNGER)**2)
                       can_help_type = 'Food'

                   # Check for thirst need (requires item like 'Waterskin')
                   # if other.thirst > cfg.MAX_THIRST * 0.7 and self.inventory.get('WaterskinFull', 0) >= 1 and self.thirst < cfg.MAX_THIRST * 0.85:
                   #     if (other.thirst / cfg.MAX_THIRST)**2 > need_level: # Prioritize higher need
                   #         need_level = (other.thirst / cfg.MAX_THIRST)**2
                   #         can_help_type = 'Water'

                   if can_help_type:
                       rel = self.knowledge.get_relationship(other.id)
                       # Consider helping only if relationship is not too negative
                       if rel >= cfg.HELPING_RELATIONSHIP_THRESHOLD:
                           # Weighted need considers the urgency, relationship, and agent's sociability
                           weighted_need = need_level * (0.5 + rel + self.sociability) / (1 + dist / 10) # Closer is slightly more prioritized

                           if weighted_need > max_weighted_need:
                               max_weighted_need = weighted_need; best_target = other

         return best_target # Return the agent object, or None

    def _get_current_action_utility(self):
         """ Estimates the utility score of the currently executing action. """
         if not self.current_action or self.current_action == 'Idle': return 0.0

         action_base = self.current_action.split(':')[0]

         # Map actions back to their likely driving needs/goals
         if action_base == 'SatisfyThirst': return (self.thirst / cfg.MAX_THIRST)**2
         if action_base == 'SatisfyHunger': return (self.hunger / cfg.MAX_HUNGER)**2
         if action_base == 'Rest': return ((cfg.MAX_ENERGY - self.energy)/cfg.MAX_ENERGY)**2 if self.energy < cfg.MAX_ENERGY else 0.0

         # Resource gathering utility is harder to pinpoint, use a base value adjusted by tool?
         if action_base == 'GatherWood': return 0.4 * (1.8 if self.inventory.get('CrudeAxe',0)>0 else 1.0)
         if action_base == 'GatherStone': return 0.35 * (1.8 if self.inventory.get('StonePick',0)>0 else 1.0)

         # Crafting utility depends on the item's perceived need
         if action_base == 'Craft':
              if self.action_target and 'recipe' in self.action_target:
                   recipe = self.action_target['recipe']
                   util = 0.5 # Base utility for crafting something
                   if recipe == 'CrudeAxe' and self.inventory.get('CrudeAxe', 0) == 0: util = 0.7
                   elif recipe == 'StonePick' and self.inventory.get('StonePick', 0) == 0: util = 0.65
                   elif recipe == 'Workbench' and not self._is_workbench_nearby(10): util = 0.6
                   elif recipe == 'SmallShelter' and self.inventory.get('SmallShelter', 0) == 0: util = 0.5
                   return util
              else: return 0.3 # Default if target data missing

         if action_base == 'Invent' or action_base == 'GoToWorkbench': return 0.2 # Utility of exploration/discovery

         if action_base == 'Help': return 0.65 # Helping is generally considered high utility if chosen

         if action_base == 'Wander': return 0.05 # Wandering is low utility

         # Default for unknown or less critical actions
         return 0.1

    def _find_adjacent_walkable(self, x, y, walkability_matrix=None):
        """ Finds a walkable tile adjacent (including diagonals) to (x, y). """
        matrix = walkability_matrix if walkability_matrix is not None else self.world.walkability_matrix
        # Prioritize orthogonal directions?
        for dx, dy in [(0,1), (0,-1), (1,0), (-1,0), (1,1), (1,-1), (-1,1), (-1,-1)]:
            nx, ny = x + dx, y + dy
            # Check bounds and walkability
            if 0 <= nx < self.world.width and 0 <= ny < self.world.height and matrix[ny, nx] == 1:
                return (nx, ny) # Return the first valid adjacent tile found
        return None # No walkable adjacent tile found

    def _find_walkable_near(self, x, y, max_search_dist=5, walkability_matrix=None):
         """ Performs a small BFS to find the nearest walkable tile to (x,y). """
         matrix = walkability_matrix if walkability_matrix is not None else self.world.walkability_matrix
         # Clamp initial target to bounds
         x = max(0, min(self.world.width - 1, x))
         y = max(0, min(self.world.height - 1, y))

         if matrix[y, x] == 1: return (x, y) # Target is already walkable

         q = [(x, y, 0)]; visited = set([(x,y)])
         while q:
             curr_x, curr_y, dist = q.pop(0)
             if dist >= max_search_dist: continue

             # Check neighbors (including diagonals)
             neighbors = [(0,1), (0,-1), (1,0), (-1,0), (1,1), (1,-1), (-1,1), (-1,-1)]
             # Shuffle neighbors to avoid bias? Optional. random.shuffle(neighbors)
             for dx, dy in neighbors:
                 nx, ny = curr_x + dx, curr_y + dy
                 # Check bounds and visited
                 if 0 <= nx < self.world.width and 0 <= ny < self.world.height and (nx, ny) not in visited:
                     if matrix[ny, nx] == 1: # Found a walkable tile
                         return (nx, ny)
                     visited.add((nx, ny))
                     q.append((nx, ny, dist + 1)) # Add non-walkable to queue to continue search from it

         return None # No walkable tile found within max_search_dist