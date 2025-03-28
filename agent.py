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

        # Phase 2: Inventory & Skills
        self.inventory = {} # item_name: count
        self.skills = {
            'GatherWood': cfg.INITIAL_SKILL_LEVEL,
            'GatherStone': cfg.INITIAL_SKILL_LEVEL,
            'BasicCrafting': cfg.INITIAL_SKILL_LEVEL,
            # Add more skills as needed (e.g., Cooking, AdvancedCrafting)
        }

        self.knowledge = KnowledgeSystem(self.id)
        self.sociability = random.uniform(0.1, 0.9) # Phase 4+
        self.pending_signal = None # Phase 4+

    def update(self, dt_real_seconds, agents, social_manager):
        dt_sim_seconds = dt_real_seconds * cfg.SIMULATION_SPEED_FACTOR
        self._update_needs(dt_sim_seconds)
        if self.health <= 0: self._handle_death(); return
        # self._process_signals(agents, social_manager) # Phase 4+

        action_just_chosen = False # Flag to prevent executing newly chosen action immediately
        if not self.current_action:
            self._choose_action(agents, social_manager)
            action_just_chosen = True # Don't execute this tick, path needs planning/checking

        # Only execute if an action exists and wasn't *just* chosen
        if self.current_action and not action_just_chosen:
            try:
                action_complete = self._perform_action(dt_sim_seconds, agents, social_manager)
                if action_complete:
                    self._complete_action()
            except Exception as e:
                print(f"!!! Agent {self.id} CRASH during perform_action {self.current_action}: {e}")
                traceback.print_exc()
                self._complete_action() # Try to reset state to avoid infinite crash loop


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
        """ Utility AI Decision Making - Phase 2 """
        utilities = {}
        # Basic Needs
        utilities['SatisfyThirst'] = (self.thirst / cfg.MAX_THIRST)**2
        utilities['SatisfyHunger'] = (self.hunger / cfg.MAX_HUNGER)**2
        energy_deficit = (cfg.MAX_ENERGY - self.energy) / cfg.MAX_ENERGY
        needs_rest = (self.energy < cfg.MAX_ENERGY * 0.7 or
                      (self.health < cfg.MAX_HEALTH * 0.9 and self.hunger < cfg.MAX_HUNGER * 0.8 and self.thirst < cfg.MAX_THIRST * 0.8))
        utilities['Rest'] = energy_deficit**2 if needs_rest else 0

        # Phase 2: Resource Gathering & Crafting Needs
        has_axe = self.inventory.get('CrudeAxe', 0) > 0
        has_pick = self.inventory.get('StonePick', 0) > 0 # Relevant for Phase 3+ usually
        current_wood = self.inventory.get('Wood', 0); current_stone = self.inventory.get('Stone', 0)
        inventory_full = sum(self.inventory.values()) >= cfg.INVENTORY_CAPACITY

        # Utility to gather resources needed for known/desired crafts, or just stockpile
        wood_needed_for_crafts = 0
        stone_needed_for_crafts = 0
        wants_axe = not has_axe
        # Crude Axe needs: 2 Wood, 1 Stone
        if wants_axe:
            wood_needed_for_crafts = max(wood_needed_for_crafts, 2 - current_wood)
            stone_needed_for_crafts = max(stone_needed_for_crafts, 1 - current_stone)

        # Simple stockpile goal if basic needs met
        needs_met_factor = max(0, 1 - max(utilities.get('SatisfyThirst',0), utilities.get('SatisfyHunger',0), utilities.get('Rest',0)))
        stockpile_wood_goal = 5
        stockpile_stone_goal = 3

        total_wood_need = max(wood_needed_for_crafts, stockpile_wood_goal if needs_met_factor > 0.5 else 0)
        total_stone_need = max(stone_needed_for_crafts, stockpile_stone_goal if needs_met_factor > 0.5 else 0)

        if not inventory_full and total_wood_need > 0:
            wood_need_norm = min(1, (total_wood_need - current_wood) / total_wood_need if total_wood_need > 0 else 0)
            utility = wood_need_norm * 0.4 * self._get_skill_multiplier('GatherWood') * (cfg.TOOL_EFFICIENCY['CrudeAxe'] if has_axe else 1.0) * needs_met_factor
            utilities['GatherWood'] = utility * (0.1 if inventory_full else 1.0) # Penalize if full

        if not inventory_full and total_stone_need > 0:
            stone_need_norm = min(1, (total_stone_need - current_stone) / total_stone_need if total_stone_need > 0 else 0)
            utility = stone_need_norm * 0.35 * self._get_skill_multiplier('GatherStone') * (cfg.TOOL_EFFICIENCY.get('StonePick', 1.0) if has_pick else 1.0) * needs_met_factor
            utilities['GatherStone'] = utility * (0.1 if inventory_full else 1.0) # Penalize if full

        # Crafting Utility
        best_craft_utility = 0; best_craft_recipe = None
        for recipe_name, details in cfg.RECIPES.items():
            # Check ingredients and skill first (workbench checked in feasibility)
            if not (self._has_ingredients(details['ingredients']) and self._has_skill_for(details)): continue
            # Workbench check needed here? No, feasibility handles location.

            utility = 0.0
            # Base utility: If I have the ingredients, maybe I should craft it?
            utility += 0.2 * needs_met_factor * self._get_skill_multiplier(details['skill'])

            # Specific item needs boosting utility
            if recipe_name == 'CrudeAxe' and not has_axe: utility = 0.7 # High desire for first axe
            # Add other specific craft desires here (e.g., StonePick, Workbench in Phase 3)

            # Consider if recipe is known (for Phase 3+ invention)
            # For Phase 2, assume all defined recipes are potentially known/knowable implicitly for now
            # knows = self.knowledge.knows_recipe(recipe_name)
            # if knows: utility *= 1.1 # Slightly prefer known recipes

            if utility > best_craft_utility:
                best_craft_utility = utility; best_craft_recipe = recipe_name

        if best_craft_recipe:
            utilities['Craft:' + best_craft_recipe] = best_craft_utility

        # Invention / GoToWorkbench (Placeholder for Phase 3)
        # ...

        # Social: Help (Placeholder for Phase 4)
        # ...

        # Default Exploration / Idleness
        utilities['Wander'] = 0.05 * needs_met_factor # Wander less if very needy

        # --- Selection ---
        best_action = None; max_utility = -1; self.action_target = None
        sorted_utilities = sorted(utilities.items(), key=lambda item: item[1], reverse=True)
        if cfg.DEBUG_AGENT_AI: print(f"Agent {self.id} Utilities: {[(a, f'{u:.2f}') for a, u in sorted_utilities]}") # DEBUG

        for action, utility in sorted_utilities:
            if utility <= cfg.UTILITY_THRESHOLD and action != 'Wander': continue

            feasible, target_data = self._check_action_feasibility(action, agents)
            if feasible:
                best_action = action; max_utility = utility; self.action_target = target_data
                break

        if not best_action:
            feasible, target_data = self._check_action_feasibility('Wander', agents)
            if feasible:
                best_action = 'Wander'; max_utility = utilities.get('Wander', 0.05); self.action_target = target_data
            else:
                best_action = "Idle"; max_utility = 0; self.action_target = None

        # --- Initiate Action ---
        if cfg.DEBUG_AGENT_CHOICE: print(f"Agent {self.id} choosing action: {best_action} (Utility: {max_utility:.2f}) Needs(H,T,E): ({self.hunger:.0f},{self.thirst:.0f},{self.energy:.0f}) Inv: {sum(self.inventory.values())}/{cfg.INVENTORY_CAPACITY} Skills:{ {k:f'{v:.1f}' for k,v in self.skills.items()} }")

        self.current_action = best_action; self.current_path = []; self.action_timer = 0.0
        if best_action == "Idle": self.action_target = None; return

        # --- Path Planning ---
        target_setup_success = False
        try:
            stand_pos = self.action_target.get('stand') if self.action_target else None
            current_pos = (self.x, self.y)

            if stand_pos: # Actions requiring movement to a specific spot
                if current_pos == stand_pos:
                    target_setup_success = True; self.current_path = []
                else:
                    self.current_path = self._plan_path(stand_pos, agents)
                    if self.current_path is not None:
                        target_setup_success = True
                        if not self.current_path and current_pos != stand_pos:
                             if cfg.DEBUG_PATHFINDING: print(f"Agent {self.id}: Path to {stand_pos} for {best_action} resulted in empty list, but not at target. Failing.")
                             target_setup_success = False
                    else:
                         if cfg.DEBUG_PATHFINDING: print(f"Agent {self.id}: Path to {stand_pos} for {best_action} failed (pathfinder error).")
                         target_setup_success = False

            elif best_action.startswith('Craft') and not cfg.RECIPES[best_action.split(':')[1]].get('workbench'):
                # Crafting non-workbench items happens at current location
                target_setup_success = True; self.current_path = []
            elif best_action == 'Rest':
                target_setup_success = True; self.current_path = []
            # Add other actions that don't require specific movement here

            else:
                # Action might not need movement OR target data is missing 'stand' when expected
                 if cfg.DEBUG_AGENT_AI: print(f"Agent {self.id}: Action {best_action} has no 'stand' target. Assuming it happens locally or data is incomplete: {self.action_target}")
                 # If stand_pos was expected based on action type but is None, it's an error
                 # Example: Gather action *always* needs a stand pos.
                 action_type = best_action.split(':')[0]
                 if action_type in ['GatherWood', 'GatherStone', 'SatisfyHunger', 'SatisfyThirst']: # Actions that MUST have a stand_pos
                     target_setup_success = False
                     print(f"Agent {self.id}: Critical error - Action {action_type} requires 'stand' position but none provided/found.")
                 else: # Assume okay for actions like Idle, Rest, some Crafts
                     target_setup_success = True
                     self.current_path = []


        except Exception as e:
             print(f"!!! Error during action path planning setup for Agent {self.id}, Action: {best_action}: {e}"); traceback.print_exc()
             target_setup_success = False

        if not target_setup_success: # Revert to Idle on failure
             print(f"Agent {self.id}: Failed to initiate action {best_action} (pathing or target setup failed). Reverting to Idle.")
             self.current_action = "Idle"; self.action_target = None; self.current_path = []

    def _check_action_feasibility(self, action_name, agents):
        """ Checks if action is possible, returns (bool feasible, dict target_data). Phase 2"""
        target_data = {'type': action_name.split(':')[0]}; goal_pos, stand_pos, dist = None, None, float('inf')

        # Basic Needs (Mostly unchanged, but use knowledge)
        if action_name == 'SatisfyThirst':
            goal_pos, stand_pos, dist = self._find_best_resource_location(cfg.RESOURCE_WATER)
            if stand_pos: target_data.update({'goal': goal_pos, 'stand': stand_pos}); return True, target_data
        elif action_name == 'SatisfyHunger':
            goal_pos, stand_pos, dist = self._find_best_resource_location(cfg.RESOURCE_FOOD)
            if stand_pos: target_data.update({'goal': goal_pos, 'stand': stand_pos}); return True, target_data

        # Phase 2: Gathering
        elif action_name == 'GatherWood':
            if sum(self.inventory.values()) >= cfg.INVENTORY_CAPACITY: return False, None # Skip if full
            goal_pos, stand_pos, dist = self._find_best_resource_location(cfg.RESOURCE_WOOD)
            if stand_pos: target_data.update({'goal': goal_pos, 'stand': stand_pos}); return True, target_data
        elif action_name == 'GatherStone':
            if sum(self.inventory.values()) >= cfg.INVENTORY_CAPACITY: return False, None # Skip if full
            goal_pos, stand_pos, dist = self._find_best_resource_location(cfg.RESOURCE_STONE)
            if stand_pos: target_data.update({'goal': goal_pos, 'stand': stand_pos}); return True, target_data

        # Phase 2: Crafting
        elif action_name.startswith('Craft:'):
             recipe_name = action_name.split(':')[1]; details = cfg.RECIPES.get(recipe_name)
             if not details: return False, None # Invalid recipe

             # Check ingredients & skill FIRST
             if not (self._has_ingredients(details['ingredients']) and self._has_skill_for(details)):
                 return False, None

             req_wb = details.get('workbench', False)
             target_data.update({'recipe': recipe_name, 'requires_workbench': req_wb})

             if req_wb: # Phase 3+ logic
                 # Must be at/near one, or find one to go to
                 if self._is_at_workbench():
                     stand_pos = (self.x, self.y); goal_pos = (self.x, self.y) # Craft here
                 else:
                     goal_pos, stand_pos, dist = self._find_best_resource_location(cfg.RESOURCE_WORKBENCH)
                     if not stand_pos: return False, None # No workbench available/reachable
             else:
                 # No workbench required, craft at current location
                 stand_pos = (self.x, self.y); goal_pos = (self.x, self.y)

             target_data.update({'goal': goal_pos, 'stand': stand_pos}); return True, target_data

        # Phase 3 Placeholders
        elif action_name == 'Invent': return False, None # Not implemented yet
        elif action_name == 'GoToWorkbench:Invent': return False, None # Not implemented yet

        # Phase 4 Placeholder
        elif action_name.startswith('Help:'): return False, None # Not implemented yet

        # Standard actions
        elif action_name == 'Wander':
             for _ in range(10):
                  wx = self.x + random.randint(-cfg.WANDER_RADIUS, cfg.WANDER_RADIUS); wy = self.y + random.randint(-cfg.WANDER_RADIUS, cfg.WANDER_RADIUS)
                  wx = max(0, min(self.world.width - 1, wx)); wy = max(0, min(self.world.height - 1, wy))
                  if self.world.walkability_matrix[wy, wx] == 1 and self.world.terrain_map[wy,wx] == cfg.TERRAIN_GROUND:
                       stand_pos = (wx, wy); break
             else: stand_pos = self._find_adjacent_walkable(self.x, self.y) # Try moving one step if stuck
             if stand_pos: target_data['stand'] = stand_pos; target_data['goal'] = stand_pos; return True, target_data
        elif action_name == "Idle": return True, {'type': 'Idle'}
        elif action_name == "Rest":
            if self.hunger < cfg.MAX_HUNGER * 0.95 and self.thirst < cfg.MAX_THIRST * 0.95:
                 target_data['stand'] = (self.x, self.y); return True, target_data

        return False, None # Default if no condition met


    def _find_best_resource_location(self, resource_type, max_search_dist=cfg.AGENT_VIEW_RADIUS):
        """Finds the best known or nearby resource location, updating knowledge. Phase 2"""
        best_pos = None; best_stand_pos = None; min_dist = float('inf')
        resource_name = cfg.RESOURCE_INFO.get(resource_type, {}).get('name','?')

        # 1. Check known locations
        known_locations = self.knowledge.get_known_locations(resource_type)
        locations_to_remove = [] # Keep track of locations to remove after iteration
        if cfg.DEBUG_KNOWLEDGE and known_locations: print(f"Agent {self.id} checking known {resource_name} locations: {known_locations}")

        for rx, ry in known_locations:
            res = self.world.get_resource(rx, ry)
            # Check if resource still exists and has quantity at the known location
            if res and res.type == resource_type and not res.is_depleted():
                stand_pos = self._find_stand_pos_for_resource(rx, ry)
                if stand_pos:
                    # Estimate distance (Manhattan for speed)
                    dist = abs(self.x - stand_pos[0]) + abs(self.y - stand_pos[1])
                    if dist < min_dist:
                        min_dist = dist
                        best_pos = (rx, ry)
                        best_stand_pos = stand_pos
                # else: Cannot reach known resource, maybe ignore for now?
            else:
                # Resource is gone or depleted, mark for removal from knowledge
                locations_to_remove.append((rx, ry))

        # Remove invalid locations from knowledge
        for rx, ry in locations_to_remove:
            self.knowledge.remove_resource_location(resource_type, rx, ry)

        if best_stand_pos:
             if cfg.DEBUG_KNOWLEDGE: print(f"Agent {self.id} best known {resource_name} at {best_pos}, stand {best_stand_pos}, dist {min_dist}")

        # 2. If no known resource is close enough, search the nearby world
        search_threshold = max_search_dist * 0.6 # Search if known is further than this, or none found
        should_search_world = (not best_stand_pos or min_dist > search_threshold)

        if should_search_world:
            if cfg.DEBUG_KNOWLEDGE: print(f"Agent {self.id} searching world for {resource_name} (Known dist: {min_dist}, Threshold: {search_threshold})")
            g_pos, s_pos, dist = self.world.find_nearest_resource(self.x, self.y, resource_type, max_dist=max_search_dist)

            if s_pos and dist < min_dist: # Found a closer one via search
                 min_dist = dist
                 best_pos = g_pos
                 best_stand_pos = s_pos
                 # Add newly found resource to knowledge
                 self.knowledge.add_resource_location(resource_type, g_pos[0], g_pos[1])
                 if cfg.DEBUG_KNOWLEDGE: print(f"Agent {self.id} found closer {resource_name} via world search at {best_pos}, stand {best_stand_pos}")

        return best_pos, best_stand_pos, min_dist


    def _find_stand_pos_for_resource(self, res_x, res_y):
        """Determines the appropriate standing position to interact with a resource."""
        resource = self.world.get_resource(res_x, res_y)
        if not resource: return None

        # If the resource tile itself is walkable (e.g., workbench), stand on it
        if self.world.walkability_matrix[res_y, res_x] == 1:
            return (res_x, res_y)
        else:
            # If resource blocks walking (e.g., tree, rock), find adjacent walkable
            return self._find_adjacent_walkable(res_x, res_y)

    # is_workbench_nearby and is_at_workbench remain the same (used in Phase 3+)
    def _is_workbench_nearby(self, distance=cfg.WORKBENCH_INTERACTION_RADIUS):
        """ Checks if a workbench resource exists within the specified Chebyshev distance. """
        # Correct implementation for Chebyshev distance:
        min_x, max_x = max(0, self.x - distance), min(self.world.width - 1, self.x + distance)
        min_y, max_y = max(0, self.y - distance), min(self.world.height - 1, self.y + distance)
        for check_y in range(min_y, max_y + 1):
             for check_x in range(min_x, max_x + 1):
                 # Skip self? No, check self tile too.
                 # if check_x == self.x and check_y == self.y: continue
                 res = self.world.get_resource(check_x, check_y)
                 if res and res.type == cfg.RESOURCE_WORKBENCH:
                     return True
        return False

    def _is_at_workbench(self):
        """ Checks if standing within interaction radius (usually 1) of a workbench tile. """
        return self._is_workbench_nearby(distance=cfg.WORKBENCH_INTERACTION_RADIUS)

    # _plan_path remains largely the same
    def _plan_path(self, target_pos, agents):
        start_pos = (self.x, self.y)
        if not target_pos or start_pos == target_pos: return []
        tx, ty = target_pos
        if not (0 <= tx < self.world.width and 0 <= ty < self.world.height):
            if cfg.DEBUG_PATHFINDING: print(f"Agent {self.id}: Path target {target_pos} out of bounds.")
            return None
        other_agent_positions = [(a.x, a.y) for a in agents if a != self and a.health > 0]
        temp_walkability = self.world.update_walkability(agent_positions=other_agent_positions)
        if temp_walkability[start_pos[1], start_pos[0]] == 0:
            if cfg.DEBUG_PATHFINDING: print(f"Agent {self.id}: Start position {start_pos} is blocked in temp grid! Cannot plan path.")
            adj_start = self._find_adjacent_walkable(start_pos[0], start_pos[1], temp_walkability)
            if adj_start: start_pos = adj_start; print(f"  -> Adjusted start to {start_pos}")
            else: return None # Truly stuck
        final_target = target_pos
        if temp_walkability[ty, tx] == 0:
            adj_target = self._find_adjacent_walkable(tx, ty, temp_walkability)
            if not adj_target:
                if cfg.DEBUG_PATHFINDING: print(f"Agent {self.id}: Target {target_pos} is blocked, and no adjacent walkable tile found.")
                return None
            else: final_target = adj_target
            if cfg.DEBUG_PATHFINDING: print(f"Agent {self.id}: Original target {target_pos} blocked, using adjacent {final_target}.")
        path_nodes = find_path(temp_walkability, start_pos, final_target)
        if path_nodes is None:
            if cfg.DEBUG_PATHFINDING: print(f"Agent {self.id}: find_path returned None (error) for {start_pos}->{final_target}.")
            return None
        elif not path_nodes and start_pos != final_target:
            if cfg.DEBUG_PATHFINDING: print(f"Agent {self.id}: find_path returned empty list (no path found) for {start_pos}->{final_target}.")
            return None # Treat no path found as failure
        else:
            path_coords = [(node.x, node.y) for node in path_nodes]
            if cfg.DEBUG_PATHFINDING and path_coords: print(f"Agent {self.id}: Path found from {start_pos} to {final_target} (len {len(path_coords)}): {path_coords[:5]}...")
            elif cfg.DEBUG_PATHFINDING: print(f"Agent {self.id}: Path from {start_pos} to {final_target} (len 0)")
            return path_coords


    def _perform_action(self, dt_sim_seconds, agents, social_manager):
        """ Executes the current action step, returns True if completed. Phase 2"""
        if not self.current_action or self.current_action == "Idle":
            return True

        # --- 1. Movement Phase ---
        if self.current_path:
            next_pos = self.current_path[0]; nx, ny = next_pos
            occupied = any(a.x == nx and a.y == ny for a in agents if a != self and a.health > 0)
            if occupied:
                stand_pos = self.action_target.get('stand') if self.action_target else None
                if stand_pos:
                     if cfg.DEBUG_PATHFINDING: print(f"Agent {self.id}: Path blocked at {next_pos}. Re-planning to {stand_pos} for {self.current_action}.")
                     new_path = self._plan_path(stand_pos, agents)
                     if new_path is not None: self.current_path = new_path; return False
                     else: print(f"Agent {self.id}: Failed recalculate path around block. Failing {self.current_action}."); return True
                else: print(f"Agent {self.id}: Path block, no stand_pos. Failing {self.current_action}."); return True
            else:
                self.x = nx; self.y = ny
                self.energy -= cfg.MOVE_ENERGY_COST
                self.current_path.pop(0)
                if self.current_path: return False # Still moving
                # else: movement finished, fall through to action execution

        # --- 2. Action Execution Phase ---
        expected_stand_pos = self.action_target.get('stand') if self.action_target else None
        is_correctly_positioned = False
        action_type = self.current_action.split(':')[0]

        if expected_stand_pos:
            current_pos = (self.x, self.y)
            chebyshev_dist = max(abs(self.x - expected_stand_pos[0]), abs(self.y - expected_stand_pos[1]))
            # Adjacency allowed for gathering/drinking/eating
            adjacent_allowed_actions = {'GatherWood', 'GatherStone', 'SatisfyHunger', 'SatisfyThirst'} # Help later
            if current_pos == expected_stand_pos or (chebyshev_dist <= 1 and action_type in adjacent_allowed_actions):
                is_correctly_positioned = True
            # Workbench check (Phase 3+)
            # elif action_type in ['Craft', 'Invent', 'GoToWorkbench'] and self._is_at_workbench():
            #      is_correctly_positioned = True
            elif action_type == 'Craft' and self.action_target.get('requires_workbench') and self._is_at_workbench():
                 is_correctly_positioned = True # Phase 3+ needs check
            elif action_type == 'Craft' and not self.action_target.get('requires_workbench'):
                 is_correctly_positioned = True # Craft anywhere if WB not required

            if not is_correctly_positioned:
                print(f"Agent {self.id}: Not correctly positioned at ({self.x},{self.y}) for {self.current_action} (expected near {expected_stand_pos}). Failing.")
                return True # Fail action
        else:
            # No specific stand pos needed (Rest, Wander, some Crafts)
            is_correctly_positioned = True

        # --- Proceed with action timer ---
        self.action_timer += dt_sim_seconds

        # --- Action Logic ---
        try:
            # Basic Needs (mostly unchanged)
            if self.current_action == 'SatisfyThirst':
                drink_duration = cfg.DRINK_THIRST_REDUCTION / 20 # Example duration scale
                if self.action_timer >= drink_duration:
                    self.thirst = max(0, self.thirst - cfg.DRINK_THIRST_REDUCTION); self.energy -= cfg.MOVE_ENERGY_COST * 0.1
                    if cfg.DEBUG_AGENT_ACTIONS: print(f"Agent {self.id} drank. Thirst: {self.thirst:.1f}")
                    return True
                else: return False
            elif self.current_action == 'SatisfyHunger':
                goal_pos = self.action_target['goal']; resource = self.world.get_resource(goal_pos[0], goal_pos[1])
                eat_duration = cfg.EAT_HUNGER_REDUCTION / 25 # Example duration scale
                if not resource or resource.is_depleted():
                     self.knowledge.remove_resource_location(cfg.RESOURCE_FOOD, goal_pos[0], goal_pos[1])
                     if cfg.DEBUG_AGENT_ACTIONS: print(f"Agent {self.id}: Food at {goal_pos} gone. Cannot eat.")
                     return True
                if self.action_timer >= eat_duration:
                    amount_eaten = self.world.consume_resource_at(goal_pos[0], goal_pos[1], 1)
                    if amount_eaten > 0:
                        self.hunger = max(0, self.hunger - cfg.EAT_HUNGER_REDUCTION); self.energy -= cfg.MOVE_ENERGY_COST * 0.1
                        if cfg.DEBUG_AGENT_ACTIONS: print(f"Agent {self.id} ate. Hunger: {self.hunger:.1f}")
                        self.knowledge.add_resource_location(cfg.RESOURCE_FOOD, goal_pos[0], goal_pos[1]) # Re-confirm location
                        if resource.is_depleted(): self.knowledge.remove_resource_location(cfg.RESOURCE_FOOD, goal_pos[0], goal_pos[1])
                    else: self.knowledge.remove_resource_location(cfg.RESOURCE_FOOD, goal_pos[0], goal_pos[1])
                    return True
                else: return False
            elif self.current_action == 'Rest':
                if self.energy >= cfg.MAX_ENERGY or self.thirst > cfg.MAX_THIRST * 0.9 or self.hunger > cfg.MAX_HUNGER * 0.9:
                    if cfg.DEBUG_AGENT_ACTIONS: print(f"Agent {self.id} finished resting.")
                    return True
                return False
            elif self.current_action == 'Wander': return True

            # --- Phase 2: Resource Gathering ---
            elif self.current_action == 'GatherWood':
                 goal_pos = self.action_target['goal']; resource = self.world.get_resource(goal_pos[0], goal_pos[1])
                 if not resource or resource.is_depleted() or resource.type != cfg.RESOURCE_WOOD:
                      self.knowledge.remove_resource_location(cfg.RESOURCE_WOOD, goal_pos[0], goal_pos[1])
                      if cfg.DEBUG_AGENT_ACTIONS: print(f"Agent {self.id}: Wood at {goal_pos} gone/invalid.")
                      return True

                 tool_name = 'CrudeAxe'
                 tool_mult = cfg.TOOL_EFFICIENCY.get(tool_name, 1.0) if self.inventory.get(tool_name, 0) > 0 else 1.0
                 skill_mult = self._get_skill_multiplier('GatherWood')
                 action_duration = cfg.GATHER_BASE_DURATION / (skill_mult * tool_mult)

                 if self.action_timer >= action_duration:
                     amount = self.world.consume_resource_at(goal_pos[0], goal_pos[1], 1)
                     if amount > 0:
                         self.inventory['Wood'] = self.inventory.get('Wood', 0) + amount
                         self.energy -= cfg.GATHER_ENERGY_COST / tool_mult # Less energy cost with tool
                         learned = self.learn_skill('GatherWood') # Learn by doing
                         if cfg.DEBUG_AGENT_ACTIONS: print(f"Agent {self.id} gathered {amount} Wood (Skill:{self.skills['GatherWood']:.1f} {'+' if learned else ''}). Total: {self.inventory.get('Wood', 0)}")
                         self.action_timer = 0 # Reset timer for next unit
                         self.knowledge.add_resource_location(cfg.RESOURCE_WOOD, goal_pos[0], goal_pos[1]) # Re-confirm

                         # Check stopping conditions for this gathering session
                         inv_full = sum(self.inventory.values()) >= cfg.INVENTORY_CAPACITY
                         # Stop if inventory full, energy low, or resource depleted
                         low_energy = self.energy < cfg.GATHER_ENERGY_COST * 1.5
                         resource_gone = resource.is_depleted()

                         if inv_full or low_energy or resource_gone:
                              if resource_gone: self.knowledge.remove_resource_location(cfg.RESOURCE_WOOD, goal_pos[0], goal_pos[1])
                              if cfg.DEBUG_AGENT_ACTIONS: print(f"Agent {self.id} finished gathering wood session (Full:{inv_full}, LowE:{low_energy}, Gone:{resource_gone}).")
                              return True # Stop gathering session
                         else: return False # Continue gathering
                     else:
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

                 tool_name = 'StonePick' # Relevant later
                 tool_mult = cfg.TOOL_EFFICIENCY.get(tool_name, 1.0) if self.inventory.get(tool_name, 0) > 0 else 1.0
                 skill_mult = self._get_skill_multiplier('GatherStone')
                 action_duration = cfg.GATHER_BASE_DURATION / (skill_mult * tool_mult) # Stone might be harder baseline?

                 if self.action_timer >= action_duration:
                     amount = self.world.consume_resource_at(goal_pos[0], goal_pos[1], 1)
                     if amount > 0:
                         self.inventory['Stone'] = self.inventory.get('Stone', 0) + amount
                         self.energy -= cfg.GATHER_ENERGY_COST / tool_mult
                         learned = self.learn_skill('GatherStone')
                         if cfg.DEBUG_AGENT_ACTIONS: print(f"Agent {self.id} gathered {amount} Stone (Skill:{self.skills['GatherStone']:.1f} {'+' if learned else ''}). Total: {self.inventory.get('Stone', 0)}")
                         self.action_timer = 0
                         self.knowledge.add_resource_location(cfg.RESOURCE_STONE, goal_pos[0], goal_pos[1])

                         inv_full = sum(self.inventory.values()) >= cfg.INVENTORY_CAPACITY
                         low_energy = self.energy < cfg.GATHER_ENERGY_COST * 1.5
                         resource_gone = resource.is_depleted()

                         if inv_full or low_energy or resource_gone:
                             if resource_gone: self.knowledge.remove_resource_location(cfg.RESOURCE_STONE, goal_pos[0], goal_pos[1])
                             if cfg.DEBUG_AGENT_ACTIONS: print(f"Agent {self.id} finished gathering stone session (Full:{inv_full}, LowE:{low_energy}, Gone:{resource_gone}).")
                             return True
                         else: return False
                     else:
                         self.knowledge.remove_resource_location(cfg.RESOURCE_STONE, goal_pos[0], goal_pos[1])
                         if cfg.DEBUG_AGENT_ACTIONS: print(f"Agent {self.id}: Stone at {goal_pos} depleted during gathering attempt.")
                         return True
                 else: return False

            # --- Phase 2: Crafting ---
            elif action_type == 'Craft':
                 recipe_name = self.action_target['recipe']; details = cfg.RECIPES[recipe_name]
                 req_wb = self.action_target.get('requires_workbench', False)

                 # Re-verify location if workbench required (Phase 3+)
                 # if req_wb and not self._is_at_workbench():
                 #     print(f"Agent {self.id} cannot craft {recipe_name} - Not at workbench.")
                 #     return True # Fail

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

                     # Add result item to inventory
                     self.inventory[recipe_name] = self.inventory.get(recipe_name, 0) + 1
                     print(f"Agent {self.id} crafted {recipe_name}.")
                     # Add knowledge of recipe implicitly here for Phase 2, or require Invention later
                     self.knowledge.add_recipe(recipe_name)

                     self.energy -= cfg.CRAFT_ENERGY_COST
                     learned = self.learn_skill(details['skill']) # Learn crafting skill
                     if cfg.DEBUG_AGENT_ACTIONS: print(f"  -> Skill '{details['skill']}': {self.skills[details['skill']]:.1f} {'+' if learned else ''}")
                     return True # Crafting complete
                 else:
                     return False # Still crafting

            # --- Fallback ---
            else: print(f"Agent {self.id}: Unknown action {self.current_action}"); return True

        except Exception as e:
            print(f"!!! Error performing action {self.current_action} for agent {self.id}: {e}"); traceback.print_exc(); return True

    def _complete_action(self):
        # if cfg.DEBUG_AGENT_ACTIONS and self.current_action: print(f"Agent {self.id} completing action: {self.current_action}")
        self.current_action = None; self.action_target = None
        self.current_path = []; self.action_timer = 0.0

    def _handle_death(self):
        print(f"Agent {self.id} has died at ({self.x}, {self.y}). Needs(H,T,E): ({self.health:.0f},{self.hunger:.0f},{self.thirst:.0f},{self.energy:.0f})")
        # TODO: Drop inventory on death? Create corpse object?

    # --- Phase 2: Skill & Crafting Helpers ---
    def learn_skill(self, skill_name, boost=1.0):
        """ Increases skill level based on usage, returns True if skill increased noticeably. """
        if not skill_name or skill_name not in self.skills: return False

        current_level = self.skills.get(skill_name, cfg.INITIAL_SKILL_LEVEL)
        if current_level >= cfg.MAX_SKILL_LEVEL: return False

        # Increase rate diminishes as skill approaches max level
        gain_factor = max(0.05, (1.0 - (current_level / (cfg.MAX_SKILL_LEVEL + 1)))**1.2) # Adjusted curve
        increase = cfg.SKILL_INCREASE_RATE * boost * gain_factor
        increase = max(0.01, increase) # Ensure minimum gain

        new_level = min(cfg.MAX_SKILL_LEVEL, current_level + increase)

        if new_level > current_level + 0.001: # Avoid tiny float noise
            self.skills[skill_name] = new_level
            return True
        return False

    def _get_skill_multiplier(self, skill_name):
        """ Returns a multiplier based on skill level (e.g., for action speed/success). """
        if not skill_name or skill_name not in self.skills: return 1.0

        level = self.skills.get(skill_name, 0)
        # Example scaling: 1.0 + MaxBonus * (level / MaxLevel)^Exponent
        max_bonus = 1.5 # Max skill gives 2.5x benefit (speed, yield etc.)
        exponent = 0.7
        multiplier = 1.0 + max_bonus * (level / cfg.MAX_SKILL_LEVEL)**exponent
        return max(0.1, multiplier) # Ensure reasonable minimum

    def _has_ingredients(self, ingredients):
        """ Checks if agent has required items in inventory. """
        if not ingredients: return True
        return all(self.inventory.get(item, 0) >= req for item, req in ingredients.items())

    def _has_skill_for(self, recipe_details):
        """ Checks if agent meets skill requirement for a recipe. """
        skill = recipe_details.get('skill')
        min_level = recipe_details.get('min_level', 0)
        return not skill or self.skills.get(skill, 0) >= min_level

    # --- Phase 4+ Social & Perception Helpers (Placeholders) ---
    def perceive_signal(self, sender_id, signal_type, position):
        self.pending_signal = (sender_id, signal_type, position)
        # if cfg.DEBUG_SOCIAL: print(f"Agent {self.id} perceived signal '{signal_type}' from {sender_id}")

    def _process_signals(self, agents, social_manager):
        if not self.pending_signal: return
        # ... (Keep Phase 4 logic here, but it won't be triggered much in Phase 2) ...
        sender_id, signal_type, signal_pos = self.pending_signal; self.pending_signal = None
        # ... rest of signal processing ...
        pass

    def decide_to_learn(self, teacher_id, skill_name): # Phase 4+
         return False # Cannot learn socially yet

    def _find_agent_to_help(self, agents): # Phase 4+
         return None # Cannot help yet

    def _get_current_action_utility(self):
         """ Estimates the utility score of the currently executing action. Phase 2 """
         if not self.current_action or self.current_action == 'Idle': return 0.0
         action_base = self.current_action.split(':')[0]

         if action_base == 'SatisfyThirst': return (self.thirst / cfg.MAX_THIRST)**2
         if action_base == 'SatisfyHunger': return (self.hunger / cfg.MAX_HUNGER)**2
         if action_base == 'Rest': return ((cfg.MAX_ENERGY - self.energy)/cfg.MAX_ENERGY)**2 if self.energy < cfg.MAX_ENERGY else 0.0

         # Estimate gathering utility based on need/skill/tool
         if action_base == 'GatherWood':
             tool_mult = cfg.TOOL_EFFICIENCY.get('CrudeAxe', 1.0) if self.inventory.get('CrudeAxe',0)>0 else 1.0
             return 0.4 * self._get_skill_multiplier('GatherWood') * tool_mult
         if action_base == 'GatherStone':
             tool_mult = cfg.TOOL_EFFICIENCY.get('StonePick', 1.0) if self.inventory.get('StonePick',0)>0 else 1.0
             return 0.35 * self._get_skill_multiplier('GatherStone') * tool_mult

         # Estimate crafting utility
         if action_base == 'Craft':
              util = 0.5 # Base utility
              if self.action_target and 'recipe' in self.action_target:
                   recipe = self.action_target['recipe']
                   if recipe == 'CrudeAxe' and self.inventory.get('CrudeAxe', 0) == 0: util = 0.7 # Higher if needed
                   # Add others later
              return util

         # Other actions
         if action_base == 'Wander': return 0.05
         return 0.1 # Default low utility for unknown/other

    # --- Pathfinding Helpers ---
    def _find_adjacent_walkable(self, x, y, walkability_matrix=None):
        """ Finds a walkable tile adjacent (including diagonals) to (x, y). """
        matrix = walkability_matrix if walkability_matrix is not None else self.world.walkability_matrix
        for dx, dy in [(0,1), (0,-1), (1,0), (-1,0), (1,1), (1,-1), (-1,1), (-1,-1)]:
            nx, ny = x + dx, y + dy
            if 0 <= nx < self.world.width and 0 <= ny < self.world.height and matrix[ny, nx] == 1:
                return (nx, ny)
        return None

    def _find_walkable_near(self, x, y, max_search_dist=5, walkability_matrix=None):
         """ Performs a small BFS to find the nearest walkable tile to (x,y). """
         matrix = walkability_matrix if walkability_matrix is not None else self.world.walkability_matrix
         x = max(0, min(self.world.width - 1, x)); y = max(0, min(self.world.height - 1, y))
         if matrix[y, x] == 1: return (x, y)
         q = [(x, y, 0)]; visited = set([(x,y)])
         while q:
             curr_x, curr_y, dist = q.pop(0)
             if dist >= max_search_dist: continue
             neighbors = [(0,1), (0,-1), (1,0), (-1,0), (1,1), (1,-1), (-1,1), (-1,-1)]
             for dx, dy in neighbors:
                 nx, ny = curr_x + dx, curr_y + dy
                 if 0 <= nx < self.world.width and 0 <= ny < self.world.height and (nx, ny) not in visited:
                     if matrix[ny, nx] == 1: return (nx, ny)
                     visited.add((nx, ny)); q.append((nx, ny, dist + 1))
         return None