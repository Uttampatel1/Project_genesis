# agent.py
import random
import math
import config as cfg
from pathfinding_utils import find_path
from knowledge import KnowledgeSystem
from world import Resource # For type checking and placing workbenches
import traceback

# Global counter for agent IDs
_agent_id_counter = 0

class Agent:
    """
    Represents an agent in the simulation with needs, skills, knowledge,
    and the ability to perceive, decide, and act within the world.
    Phase 3: Includes knowledge, invention, and workbench interaction.
    """

    def __init__(self, x, y, world):
        """ Initializes an agent at a given position in the world. """
        global _agent_id_counter
        self.id = _agent_id_counter; _agent_id_counter += 1
        self.x = x; self.y = y          # Current grid coordinates
        self.world = world              # Reference to the world object

        # Basic Needs and State
        self.health = cfg.MAX_HEALTH
        self.energy = cfg.MAX_ENERGY
        self.hunger = 0                 # 0 = Not hungry, cfg.MAX_HUNGER = Starving
        self.thirst = 0                 # 0 = Not thirsty, cfg.MAX_THIRST = Dehydrated

        # Action State
        self.current_action = None      # String identifier (e.g., "GatherWood", "Craft:CrudeAxe")
        self.action_target = None       # Dictionary holding target info (goal, stand, recipe, etc.)
        self.current_path = []          # List of (x, y) tuples for movement
        self.action_timer = 0.0         # Timer for timed actions (gathering, crafting)

        # Inventory & Skills
        self.inventory = {}             # item_name: count
        self.skills = {
            'GatherWood': cfg.INITIAL_SKILL_LEVEL,
            'GatherStone': cfg.INITIAL_SKILL_LEVEL,
            'BasicCrafting': 1.0,       # Start with skill level 1 to enable axe crafting
        }

        # Phase 3: Knowledge & Attributes
        self.knowledge = KnowledgeSystem(self.id) # Agent's memory and beliefs
        self.intelligence = random.uniform(0.3, 0.8) # Factor influencing invention speed

        # --- Initial Knowledge (Bootstrap Recipes) ---
        self.knowledge.add_recipe('CrudeAxe')
        self.knowledge.add_recipe('Workbench')

        # Phase 4+ Placeholders
        self.sociability = random.uniform(0.1, 0.9)
        self.pending_signal = None


    def update(self, dt_real_seconds, agents, social_manager):
        """ Main update loop called each simulation tick. """
        dt_sim_seconds = dt_real_seconds * cfg.SIMULATION_SPEED_FACTOR

        # 1. Update Needs & Check Health
        self._update_needs(dt_sim_seconds)
        if self.health <= 0:
            self._handle_death()
            return # Agent is dead

        # 2. Process Social Signals (Phase 4+)
        # self._process_signals(agents, social_manager)

        # 3. Decide and Perform Action
        action_just_chosen = False
        if not self.current_action:
            self._choose_action(agents, social_manager)
            action_just_chosen = True # Don't execute immediately

        if self.current_action and not action_just_chosen:
            try:
                action_complete = self._perform_action(dt_sim_seconds, agents, social_manager)
                if action_complete:
                    self._complete_action()
            except Exception as e:
                print(f"!!! Agent {self.id} CRASH during perform_action {self.current_action}: {e}")
                traceback.print_exc()
                self._complete_action() # Reset state


    def _update_needs(self, dt_sim_seconds):
        """ Updates agent's health, energy, hunger, and thirst over time. """
        self.hunger = min(cfg.MAX_HUNGER, self.hunger + cfg.HUNGER_INCREASE_RATE * dt_sim_seconds)
        self.thirst = min(cfg.MAX_THIRST, self.thirst + cfg.THIRST_INCREASE_RATE * dt_sim_seconds)

        if self.current_action != "Rest":
            self.energy = max(0, self.energy - cfg.ENERGY_DECAY_RATE * dt_sim_seconds)
        else: # Resting
            self.energy = min(cfg.MAX_ENERGY, self.energy + cfg.ENERGY_REGEN_RATE * dt_sim_seconds)
            # Regenerate health only while resting and needs mostly met
            if self.energy > cfg.MAX_ENERGY * 0.5 and self.hunger < cfg.MAX_HUNGER * 0.8 and self.thirst < cfg.MAX_THIRST * 0.8:
                self.health = min(cfg.MAX_HEALTH, self.health + cfg.HEALTH_REGEN_RATE * dt_sim_seconds)

        # Health drain from critical needs
        health_drain = 0
        if self.hunger >= cfg.MAX_HUNGER * 0.95: health_drain += 0.8
        if self.thirst >= cfg.MAX_THIRST * 0.95: health_drain += 1.0
        if self.energy <= 0 and self.current_action != "Rest": health_drain += 0.5 # Exhaustion penalty
        self.health = max(0, self.health - health_drain * dt_sim_seconds)


    def _choose_action(self, agents, social_manager):
        """ Determines the best action to take based on utility scores. Phase 3 logic. """
        utilities = {}

        # --- Calculate Utility Scores ---
        # 1. Basic Needs Utilities
        utilities['SatisfyThirst'] = (self.thirst / cfg.MAX_THIRST)**2 * 1.1
        utilities['SatisfyHunger'] = (self.hunger / cfg.MAX_HUNGER)**2 * 1.1
        energy_deficit = (cfg.MAX_ENERGY - self.energy) / cfg.MAX_ENERGY
        needs_rest = (self.energy < cfg.MAX_ENERGY * 0.7 or
                      (self.health < cfg.MAX_HEALTH * 0.9 and self.hunger < cfg.MAX_HUNGER * 0.8 and self.thirst < cfg.MAX_THIRST * 0.8))
        utilities['Rest'] = energy_deficit**2 if needs_rest else 0

        # 2. Resource, Crafting, Invention Utilities
        has_axe = self.inventory.get('CrudeAxe', 0) > 0
        has_pick = self.inventory.get('StonePick', 0) > 0
        current_wood = self.inventory.get('Wood', 0)
        current_stone = self.inventory.get('Stone', 0)
        inventory_full = sum(self.inventory.values()) >= cfg.INVENTORY_CAPACITY
        # Factor representing how well basic needs are met (1 = fully met, 0 = critical)
        needs_met_factor = max(0, 1 - max(utilities.get('SatisfyThirst',0), utilities.get('SatisfyHunger',0), utilities.get('Rest',0)))
        is_at_workbench = self._is_at_workbench()

        # Calculate resource needs for known, desired recipes
        wood_needed_for_crafts = 0
        stone_needed_for_crafts = 0
        workbench_required_by_known_craft = False
        can_make_something_at_workbench = False # If know WB recipe, have mats+skill

        for recipe_name in self.knowledge.known_recipes:
            details = cfg.RECIPES.get(recipe_name)
            if not details or not self._has_skill_for(details): continue

            # Determine if agent 'wants' this item
            want_item = False
            if recipe_name == 'Workbench' and not self._has_workbench_knowledge():
                 want_item = True # Always want first workbench if location unknown
            elif recipe_name in ['CrudeAxe', 'StonePick'] and self.inventory.get(recipe_name, 0) == 0:
                 want_item = True # Want tools if none possessed
            # Add logic for other wanted items (e.g., shelter parts)

            if want_item:
                ingredients = details.get('ingredients', {})
                wood_needed_for_crafts = max(wood_needed_for_crafts, ingredients.get('Wood', 0) - current_wood)
                stone_needed_for_crafts = max(stone_needed_for_crafts, ingredients.get('Stone', 0) - current_stone)
                # Check if this desired item requires a workbench
                if details.get('workbench', False):
                     workbench_required_by_known_craft = True
                     # Check if we have ingredients *for this specific item*
                     if self._has_ingredients(ingredients):
                          can_make_something_at_workbench = True

        # Add stockpile goals (lower priority)
        stockpile_wood_goal = 5
        stockpile_stone_goal = 3
        # Total need = max(crafting_need, stockpile_need * needs_met_factor)
        total_wood_need = max(wood_needed_for_crafts, stockpile_wood_goal if needs_met_factor > 0.6 else 0)
        total_stone_need = max(stone_needed_for_crafts, stockpile_stone_goal if needs_met_factor > 0.6 else 0)

        # Gathering Utilities
        if not inventory_full and total_wood_need > current_wood:
            wood_need_norm = min(1, (total_wood_need - current_wood) / total_wood_need if total_wood_need > 0 else 0)
            tool_mult_wood = cfg.TOOL_EFFICIENCY['CrudeAxe'] if has_axe else 1.0
            utility = wood_need_norm * 0.4 * self._get_skill_multiplier('GatherWood') * tool_mult_wood * needs_met_factor
            utilities['GatherWood'] = utility

        if not inventory_full and total_stone_need > current_stone:
            stone_need_norm = min(1, (total_stone_need - current_stone) / total_stone_need if total_stone_need > 0 else 0)
            tool_mult_stone = cfg.TOOL_EFFICIENCY.get('StonePick', 1.0) if has_pick else 1.0
            utility = stone_need_norm * 0.35 * self._get_skill_multiplier('GatherStone') * tool_mult_stone * needs_met_factor
            utilities['GatherStone'] = utility

        # Crafting Utility (Only for KNOWN recipes feasible NOW)
        best_craft_utility = 0; best_craft_recipe = None
        for recipe_name in self.knowledge.known_recipes:
            details = cfg.RECIPES.get(recipe_name)
            if not details: continue

            # Check ingredients, skill, AND location feasibility
            can_craft_now = False
            if self._has_ingredients(details['ingredients']) and self._has_skill_for(details):
                if details.get('workbench', False): # Requires workbench
                    if is_at_workbench: can_craft_now = True
                else: # No workbench needed
                    can_craft_now = True

            if can_craft_now:
                utility = 0.0
                skill_mult = self._get_skill_multiplier(details['skill'])
                utility += 0.3 * needs_met_factor * skill_mult # Base utility

                # Boost utility for critical items
                if recipe_name == 'CrudeAxe' and not has_axe: utility = 0.75
                if recipe_name == 'StonePick' and not has_pick: utility = 0.70
                if recipe_name == 'Workbench' and not self._has_workbench_knowledge(): utility = 0.80

                if utility > best_craft_utility:
                    best_craft_utility = utility; best_craft_recipe = recipe_name

        if best_craft_recipe:
            utilities['Craft:' + best_craft_recipe] = best_craft_utility

        # GoToWorkbench Utility
        reason_for_workbench = None
        if can_make_something_at_workbench: # Check if known WB recipe has ingredients/skill
             reason_for_workbench = "Craft"
        # Consider Invention as another reason
        can_invent = (needs_met_factor > 0.7 and
                      len(self.inventory) >= cfg.INVENTION_ITEM_TYPES_THRESHOLD and
                      not inventory_full)
        if can_invent and not reason_for_workbench:
             reason_for_workbench = "Invent"

        if reason_for_workbench and not is_at_workbench:
             if self._has_workbench_knowledge(): # Only if we know where one is
                  utility = 0.65 if reason_for_workbench == "Craft" else 0.45
                  utilities['GoToWorkbench:' + reason_for_workbench] = utility * needs_met_factor
             # else: Cannot go if location unknown (might choose Craft:Workbench instead)

        # Invention Utility (Only if AT workbench and other conditions met)
        if is_at_workbench and can_invent:
             utility = 0.35 * self.intelligence * needs_met_factor
             if self.current_action and self.current_action.startswith("Craft"): utility *= 0.5 # Lower if busy
             utilities['Invent'] = utility

        # 3. Default Action Utility (Wander)
        utilities['Wander'] = 0.05 * needs_met_factor * (1.0 - self.intelligence * 0.5)

        # --- Selection Process ---
        best_action = None; max_utility = -1; self.action_target = None
        # Add slight randomness to break ties
        sorted_utilities = sorted(utilities.items(), key=lambda item: item[1] + random.uniform(-0.01, 0.01), reverse=True)

        if cfg.DEBUG_AGENT_AI: print(f"Agent {self.id} Utilities: {[(a, f'{u:.2f}') for a, u in sorted_utilities]}")

        # Find the highest utility feasible action
        for action, utility in sorted_utilities:
            if utility <= cfg.UTILITY_THRESHOLD and action != 'Wander': continue

            feasible, target_data = self._check_action_feasibility(action, agents)
            if feasible:
                best_action = action; max_utility = utility; self.action_target = target_data
                if cfg.DEBUG_AGENT_CHOICE: print(f"Agent {self.id} PRE-SELECTED: {best_action} (Util: {max_utility:.2f}) Target: {target_data}")
                break

        # Fallback to Wander/Idle
        if not best_action:
            feasible, target_data = self._check_action_feasibility('Wander', agents)
            if feasible:
                best_action = 'Wander'; max_utility = utilities.get('Wander', 0.05); self.action_target = target_data
            else:
                best_action = "Idle"; max_utility = 0; self.action_target = None

        # --- Log Chosen Action and Initiate ---
        if cfg.DEBUG_AGENT_CHOICE:
            inv_sum = sum(self.inventory.values())
            known_recipes_count = len(self.knowledge.known_recipes)
            skills_str = {k: f"{v:.1f}" for k, v in self.skills.items()}
            print(f"Agent {self.id} choosing action: {best_action} (Utility: {max_utility:.2f}) Needs(H,T,E): ({self.hunger:.0f},{self.thirst:.0f},{self.energy:.0f}) Inv: {inv_sum}/{cfg.INVENTORY_CAPACITY} Known Recipes: {known_recipes_count} Skills: {skills_str}")

        self.current_action = best_action
        self.current_path = []
        self.action_timer = 0.0
        if best_action == "Idle":
            self.action_target = None; return

        # --- Path Planning for the Chosen Action ---
        self._plan_path_for_action(agents)


    def _plan_path_for_action(self, agents):
        """ Plans the path required for the chosen action. Sets self.current_path or reverts to Idle on failure. """
        target_setup_success = False
        best_action = self.current_action

        try:
            stand_pos = self.action_target.get('stand') if self.action_target else None
            current_pos = (self.x, self.y)

            if stand_pos: # Action requires movement
                if current_pos == stand_pos: # Already there
                    target_setup_success = True; self.current_path = []
                else: # Need path
                    self.current_path = self._plan_path(stand_pos, agents)
                    if self.current_path is not None: # Path planning succeeded (list or empty list)
                        target_setup_success = True
                        if not self.current_path and current_pos != stand_pos: # Logic error check
                             if cfg.DEBUG_PATHFINDING: print(f"Agent {self.id}: Path to {stand_pos} for {best_action} empty but not at target. Failing.")
                             target_setup_success = False
                    else: # Path planning failed (returned None)
                         if cfg.DEBUG_PATHFINDING: print(f"Agent {self.id}: Path to {stand_pos} for {best_action} failed (pathfinder error).")
                         target_setup_success = False
            else: # Action happens locally
                action_type = best_action.split(':')[0]
                # Check if stand_pos *should* have existed based on action type
                needs_stand_pos = action_type in ['GatherWood', 'GatherStone', 'SatisfyHunger', 'SatisfyThirst', 'GoToWorkbench'] \
                                  or (action_type == 'Craft' and self.action_target and self.action_target.get('requires_workbench'))
                if needs_stand_pos: # Error: Local action chosen but needed a target location
                    print(f"Agent {self.id}: Critical error - Action {best_action} requires 'stand' pos but none found in target data: {self.action_target}")
                    target_setup_success = False
                else: # Action correctly identified as local (Rest, Invent@WB, Craft non-WB)
                    target_setup_success = True; self.current_path = []

        except Exception as e:
             print(f"!!! Error during action path planning setup for Agent {self.id}, Action: {best_action}: {e}"); traceback.print_exc()
             target_setup_success = False

        # Handle setup failure: Revert to Idle
        if not target_setup_success:
             if cfg.DEBUG_AGENT_CHOICE or cfg.DEBUG_PATHFINDING: print(f"Agent {self.id}: Failed to initiate action {best_action} (pathing/target setup failed). Reverting to Idle.")
             self.current_action = "Idle"; self.action_target = None; self.current_path = []


    def _check_action_feasibility(self, action_name, agents):
        """ Checks if an action is possible *right now*. Returns (bool feasible, dict target_data). """
        target_data = {'type': action_name.split(':')[0]}
        goal_pos, stand_pos, dist = None, None, float('inf')

        # Needs
        if action_name == 'SatisfyThirst':
            goal_pos, stand_pos, dist = self._find_best_resource_location(cfg.RESOURCE_WATER)
            if stand_pos: target_data.update({'goal': goal_pos, 'stand': stand_pos}); return True, target_data
        elif action_name == 'SatisfyHunger':
            goal_pos, stand_pos, dist = self._find_best_resource_location(cfg.RESOURCE_FOOD)
            if stand_pos: target_data.update({'goal': goal_pos, 'stand': stand_pos}); return True, target_data

        # Gathering
        elif action_name == 'GatherWood':
            if sum(self.inventory.values()) >= cfg.INVENTORY_CAPACITY: return False, None
            goal_pos, stand_pos, dist = self._find_best_resource_location(cfg.RESOURCE_WOOD)
            if stand_pos: target_data.update({'goal': goal_pos, 'stand': stand_pos}); return True, target_data
        elif action_name == 'GatherStone':
            if sum(self.inventory.values()) >= cfg.INVENTORY_CAPACITY: return False, None
            goal_pos, stand_pos, dist = self._find_best_resource_location(cfg.RESOURCE_STONE)
            if stand_pos: target_data.update({'goal': goal_pos, 'stand': stand_pos}); return True, target_data

        # Crafting
        elif action_name.startswith('Craft:'):
             recipe_name = action_name.split(':')[1]; details = cfg.RECIPES.get(recipe_name)
             if not details: return False, None
             if not self.knowledge.knows_recipe(recipe_name): return False, None
             if not self._has_ingredients(details['ingredients']): return False, None
             if not self._has_skill_for(details): return False, None

             req_wb = details.get('workbench', False)
             target_data.update({'recipe': recipe_name, 'requires_workbench': req_wb})

             if req_wb: # Requires workbench
                 if self._is_at_workbench(): # Must be AT workbench NOW
                     wb_pos = self._get_nearby_workbench_pos()
                     if wb_pos: goal_pos = wb_pos; stand_pos = (self.x, self.y)
                     else: return False, None # Error state
                 else: return False, None # Not at WB, cannot craft now
             else: # No workbench needed
                 stand_pos = (self.x, self.y); goal_pos = (self.x, self.y)

             target_data.update({'goal': goal_pos, 'stand': stand_pos}); return True, target_data

        # GoToWorkbench
        elif action_name.startswith('GoToWorkbench:'):
             purpose = action_name.split(':')[1]
             if self._is_at_workbench(): return False, None # Already there
             goal_pos, stand_pos, dist = self._find_best_resource_location(cfg.RESOURCE_WORKBENCH)
             if stand_pos: target_data.update({'goal': goal_pos, 'stand': stand_pos, 'purpose': purpose}); return True, target_data
             else: return False, None # No WB known/found

        # Invent
        elif action_name == 'Invent':
             if not self._is_at_workbench(): return False, None
             if len(self.inventory) < cfg.INVENTION_ITEM_TYPES_THRESHOLD: return False, None
             if sum(self.inventory.values()) >= cfg.INVENTORY_CAPACITY: return False, None
             wb_pos = self._get_nearby_workbench_pos()
             if wb_pos: target_data.update({'goal': wb_pos, 'stand': (self.x, self.y)}); return True, target_data
             else: return False, None # Error state

        # Standard Actions
        elif action_name == 'Wander':
             for _ in range(10): # Find random walkable ground nearby
                  wx = max(0, min(self.world.width - 1, self.x + random.randint(-cfg.WANDER_RADIUS, cfg.WANDER_RADIUS)))
                  wy = max(0, min(self.world.height - 1, self.y + random.randint(-cfg.WANDER_RADIUS, cfg.WANDER_RADIUS)))
                  if self.world.walkability_matrix[wy, wx] == 1 and self.world.terrain_map[wy,wx] == cfg.TERRAIN_GROUND:
                       stand_pos = (wx, wy); break
             else: stand_pos = self._find_adjacent_walkable(self.x, self.y, self.world.walkability_matrix) # Fallback: move 1 step
             if stand_pos: target_data['stand'] = stand_pos; target_data['goal'] = stand_pos; return True, target_data
             else: return False, None # Can't even move 1 step

        elif action_name == "Idle": return True, {'type': 'Idle'}
        elif action_name == "Rest":
            if self.hunger < cfg.MAX_HUNGER * 0.95 and self.thirst < cfg.MAX_THIRST * 0.95:
                 target_data['stand'] = (self.x, self.y); return True, target_data
            else: return False, None # Too hungry/thirsty to rest safely

        return False, None # Default: action not feasible


    def _perform_action(self, dt_sim_seconds, agents, social_manager):
        """ Executes the current action step, returns True if completed. """
        if not self.current_action or self.current_action == "Idle": return True

        # --- 1. Movement Phase ---
        if self.current_path:
            next_pos = self.current_path[0]; nx, ny = next_pos
            if self.world.walkability_matrix[ny,nx] == 0: # Check static obstacles
                 print(f"Agent {self.id}: Path leads to static obstacle {next_pos}! Failing {self.current_action}.")
                 return True
            occupied_by = next((a.id for a in agents if a != self and a.health > 0 and a.x == nx and a.y == ny), None)
            if occupied_by is not None: # Check dynamic obstacles (agents)
                stand_pos = self.action_target.get('stand')
                if stand_pos: # Try to replan
                     if cfg.DEBUG_PATHFINDING: print(f"Agent {self.id}: Path blocked by Agent {occupied_by} at {next_pos}. Re-planning to {stand_pos}.")
                     new_path = self._plan_path(stand_pos, agents)
                     if new_path is not None: self.current_path = new_path; return False # Continue next tick
                     else: print(f"Agent {self.id}: Failed replan around block. Failing {self.current_action}."); return True
                else: print(f"Agent {self.id}: Path blocked, no stand_pos to replan. Failing {self.current_action}."); return True
            else: # Move is clear
                self.x = nx; self.y = ny
                self.energy -= cfg.MOVE_ENERGY_COST
                self.current_path.pop(0)
                if self.current_path: return False # Still moving
                # else: Movement finished, proceed to action execution below

        # --- 2. Action Execution Phase ---
        action_type = self.current_action.split(':')[0]
        if not self._verify_position_for_action(action_type): return True # Fail if not positioned correctly

        self.action_timer += dt_sim_seconds # Increment timer for timed actions

        # --- Action Logic ---
        try:
            if action_type == 'SatisfyThirst':
                drink_duration = cfg.DRINK_THIRST_REDUCTION / 20
                if self.action_timer >= drink_duration:
                    self.thirst = max(0, self.thirst - cfg.DRINK_THIRST_REDUCTION)
                    self.energy -= cfg.MOVE_ENERGY_COST * 0.1
                    if cfg.DEBUG_AGENT_ACTIONS: print(f"Agent {self.id} drank. Thirst: {self.thirst:.1f}")
                    goal_pos = self.action_target.get('goal')
                    if goal_pos: # Confirm water location knowledge
                        self.knowledge.add_resource_location(cfg.RESOURCE_WATER, goal_pos[0], goal_pos[1])
                        if cfg.DEBUG_KNOWLEDGE: print(f"Agent {self.id} confirmed water location at {goal_pos}")
                    return True
                else: return False

            elif action_type == 'SatisfyHunger':
                goal_pos = self.action_target['goal']; resource = self.world.get_resource(goal_pos[0], goal_pos[1])
                eat_duration = cfg.EAT_HUNGER_REDUCTION / 25
                if not resource or resource.is_depleted():
                     self.knowledge.remove_resource_location(cfg.RESOURCE_FOOD, goal_pos[0], goal_pos[1])
                     if cfg.DEBUG_AGENT_ACTIONS: print(f"Agent {self.id}: Food at {goal_pos} gone before eating.")
                     return True
                if self.action_timer >= eat_duration:
                    amount_eaten = self.world.consume_resource_at(goal_pos[0], goal_pos[1], 1)
                    if amount_eaten > 0:
                        self.hunger = max(0, self.hunger - cfg.EAT_HUNGER_REDUCTION); self.energy -= cfg.MOVE_ENERGY_COST * 0.1
                        if cfg.DEBUG_AGENT_ACTIONS: print(f"Agent {self.id} ate. Hunger: {self.hunger:.1f}")
                        self.knowledge.add_resource_location(cfg.RESOURCE_FOOD, goal_pos[0], goal_pos[1]) # Confirm knowledge
                        if resource.is_depleted(): self.knowledge.remove_resource_location(cfg.RESOURCE_FOOD, goal_pos[0], goal_pos[1])
                    else: self.knowledge.remove_resource_location(cfg.RESOURCE_FOOD, goal_pos[0], goal_pos[1])
                    return True
                else: return False

            elif action_type == 'Rest':
                if self.energy >= cfg.MAX_ENERGY or self.thirst > cfg.MAX_THIRST * 0.9 or self.hunger > cfg.MAX_HUNGER * 0.9:
                    if cfg.DEBUG_AGENT_ACTIONS: print(f"Agent {self.id} finished resting.")
                    return True
                return False # Continue resting

            elif action_type == 'Wander': return True # Completes instantly upon arrival

            elif action_type == 'GatherWood' or action_type == 'GatherStone':
                 is_wood = action_type == 'GatherWood'
                 resource_type = cfg.RESOURCE_WOOD if is_wood else cfg.RESOURCE_STONE
                 skill_name = 'GatherWood' if is_wood else 'GatherStone'
                 tool_name = 'CrudeAxe' if is_wood else 'StonePick'
                 res_name_str = 'Wood' if is_wood else 'Stone'
                 goal_pos = self.action_target['goal']; resource = self.world.get_resource(goal_pos[0], goal_pos[1])

                 if not resource or resource.is_depleted() or resource.type != resource_type: # Re-check resource validity
                      self.knowledge.remove_resource_location(resource_type, goal_pos[0], goal_pos[1])
                      if cfg.DEBUG_AGENT_ACTIONS: print(f"Agent {self.id}: {res_name_str} at {goal_pos} gone/invalid before gathering.")
                      return True

                 tool_mult = cfg.TOOL_EFFICIENCY.get(tool_name, 1.0) if self.inventory.get(tool_name, 0) > 0 else 1.0
                 skill_mult = self._get_skill_multiplier(skill_name)
                 action_duration = cfg.GATHER_BASE_DURATION / (skill_mult * tool_mult)

                 if self.action_timer >= action_duration: # Time to gather one unit
                     amount = self.world.consume_resource_at(goal_pos[0], goal_pos[1], 1)
                     if amount > 0:
                         self.inventory[res_name_str] = self.inventory.get(res_name_str, 0) + amount
                         self.energy -= cfg.GATHER_ENERGY_COST / tool_mult
                         learned = self.learn_skill(skill_name)
                         if cfg.DEBUG_AGENT_ACTIONS: print(f"Agent {self.id} gathered {amount} {res_name_str} (Skill:{self.skills[skill_name]:.1f} {'+' if learned else ''}). Total: {self.inventory.get(res_name_str, 0)}")
                         self.action_timer = 0 # Reset timer for next unit
                         self.knowledge.add_resource_location(resource_type, goal_pos[0], goal_pos[1]) # Re-confirm knowledge

                         # Check stopping conditions
                         inv_full = sum(self.inventory.values()) >= cfg.INVENTORY_CAPACITY
                         low_energy = self.energy < cfg.GATHER_ENERGY_COST * 1.5
                         resource_gone = resource.is_depleted()
                         if inv_full or low_energy or resource_gone:
                              if resource_gone: self.knowledge.remove_resource_location(resource_type, goal_pos[0], goal_pos[1])
                              if cfg.DEBUG_AGENT_ACTIONS: print(f"Agent {self.id} finished gathering {res_name_str} session (Full:{inv_full}, LowE:{low_energy}, Gone:{resource_gone}).")
                              return True # Stop gathering session
                         else: return False # Continue gathering
                     else: # Failed to consume
                         self.knowledge.remove_resource_location(resource_type, goal_pos[0], goal_pos[1])
                         if cfg.DEBUG_AGENT_ACTIONS: print(f"Agent {self.id}: {res_name_str} at {goal_pos} depleted during gathering attempt.")
                         return True
                 else: return False # Still gathering this unit

            elif action_type == 'Craft':
                 recipe_name = self.action_target['recipe']; details = cfg.RECIPES[recipe_name]
                 skill_req = details.get('skill')
                 skill_mult = self._get_skill_multiplier(skill_req)
                 action_duration = cfg.CRAFT_BASE_DURATION / skill_mult

                 if self.action_timer >= action_duration: # Crafting time elapsed
                     # Final checks
                     if not self._has_ingredients(details['ingredients']):
                         if cfg.DEBUG_AGENT_ACTIONS: print(f"Agent {self.id} cannot craft {recipe_name} - Missing ingredients finally.")
                         return True
                     if not self._has_skill_for(details):
                          if cfg.DEBUG_AGENT_ACTIONS: print(f"Agent {self.id} cannot craft {recipe_name} - Skill {skill_req} too low finally.")
                          return True

                     # Consume ingredients
                     for item, count in details['ingredients'].items():
                         self.inventory[item] = self.inventory.get(item, 0) - count
                         if self.inventory[item] <= 0: del self.inventory[item]

                     # Add result
                     if recipe_name == 'Workbench': # Special case: Place Workbench
                          wb_obj = Resource(cfg.RESOURCE_WORKBENCH, self.x, self.y)
                          if self.world.add_world_object(wb_obj, self.x, self.y):
                               self.knowledge.add_resource_location(cfg.RESOURCE_WORKBENCH, self.x, self.y)
                               if cfg.DEBUG_AGENT_ACTIONS or cfg.DEBUG_KNOWLEDGE: print(f"Agent {self.id} crafted and placed a Workbench at ({self.x}, {self.y}).")
                          else:
                               if cfg.DEBUG_AGENT_ACTIONS: print(f"Agent {self.id} crafted Workbench but FAILED TO PLACE at ({self.x}, {self.y}). Ingredients lost!")
                               # TODO: Refund ingredients?
                     else: # Add regular item to inventory
                          self.inventory[recipe_name] = self.inventory.get(recipe_name, 0) + 1
                          if cfg.DEBUG_AGENT_ACTIONS: print(f"Agent {self.id} crafted {recipe_name}. Inventory: {self.inventory.get(recipe_name)}")

                     # Costs and Learning
                     self.energy -= cfg.CRAFT_ENERGY_COST
                     learned = self.learn_skill(skill_req)
                     if cfg.DEBUG_AGENT_ACTIONS and skill_req: print(f"  -> Skill '{skill_req}': {self.skills.get(skill_req, 0):.1f} {'+' if learned else ''}")
                     self.knowledge.add_recipe(recipe_name) # Ensure known

                     return True # Crafting complete
                 else: return False # Still crafting

            elif action_type == 'GoToWorkbench': # Completes on arrival
                 if self._is_at_workbench():
                     if cfg.DEBUG_AGENT_ACTIONS: print(f"Agent {self.id} arrived at Workbench {self.action_target.get('goal')} for purpose: {self.action_target.get('purpose', 'N/A')}")
                     wb_pos = self._get_nearby_workbench_pos()
                     if wb_pos: self.knowledge.add_resource_location(cfg.RESOURCE_WORKBENCH, wb_pos[0], wb_pos[1])
                     return True
                 else: # Arrived but check fails?
                     print(f"Agent {self.id} finished path for GoToWorkbench but is not at a workbench ({self.x},{self.y}). Target was {self.action_target.get('goal')}. Failing.")
                     goal_pos = self.action_target.get('goal')
                     if goal_pos: self.knowledge.remove_resource_location(cfg.RESOURCE_WORKBENCH, goal_pos[0], goal_pos[1])
                     return True

            elif action_type == 'Invent':
                 action_duration = cfg.INVENT_BASE_DURATION / self.intelligence
                 if self.action_timer >= action_duration:
                     if cfg.DEBUG_INVENTION: print(f"Agent {self.id} finishing invention cycle.")
                     discovered_recipe = self.knowledge.attempt_invention(self.inventory, self.skills)
                     self.energy -= cfg.INVENT_ENERGY_COST
                     if discovered_recipe:
                          if cfg.DEBUG_AGENT_ACTIONS or cfg.DEBUG_INVENTION: print(f"Agent {self.id} successfully invented: {discovered_recipe}!")
                     else:
                          if cfg.DEBUG_AGENT_ACTIONS or cfg.DEBUG_INVENTION: print(f"Agent {self.id} tried to invent but discovered nothing.")
                     return True # Attempt complete
                 else: return False # Still inventing

            else: # Fallback for unknown action types
                print(f"Agent {self.id}: Unknown action execution: {self.current_action}")
                return True

        except Exception as e: # General error handling during action logic
            print(f"!!! Error performing action logic {self.current_action} for agent {self.id}: {e}"); traceback.print_exc()
            return True # Fail action to prevent loops


    def _verify_position_for_action(self, action_type):
        """ Checks if the agent is in the correct location to start/continue the action. """
        expected_stand_pos = self.action_target.get('stand') if self.action_target else None
        current_pos = (self.x, self.y)

        # 1. Actions needing specific 'stand' position
        if expected_stand_pos:
            if current_pos == expected_stand_pos: return True # Exactly at stand pos
            # Allow adjacency for resource interaction
            adjacent_allowed_actions = {'GatherWood', 'GatherStone', 'SatisfyHunger', 'SatisfyThirst'}
            if action_type in adjacent_allowed_actions:
                 goal_pos = self.action_target.get('goal')
                 if goal_pos:
                      goal_dist = max(abs(self.x - goal_pos[0]), abs(self.y - goal_pos[1]))
                      # Allow if standing adjacent (dist=1) to the actual resource goal tile
                      if goal_dist <= 1: return True
            # If not exact match or allowed adjacency failed
            if cfg.DEBUG_AGENT_ACTIONS: print(f"Agent {self.id}: Position error - Not at expected stand pos {expected_stand_pos} OR not adjacent to goal {self.action_target.get('goal')} for {self.current_action}. Current: {current_pos}")
            return False

        # 2. Actions needing workbench proximity
        workbench_actions = ['Invent']
        if action_type == 'Craft' and self.action_target and self.action_target.get('requires_workbench'):
             workbench_actions.append('Craft')
        if action_type in workbench_actions:
             if not self._is_at_workbench():
                  if cfg.DEBUG_AGENT_ACTIONS: print(f"Agent {self.id}: Position error - Not at workbench for {self.current_action}. Current: {current_pos}")
                  return False

        # 3. Actions valid anywhere (Rest, Wander, non-WB Crafts) pass implicitly
        return True


    def _complete_action(self):
        """ Resets action state when an action finishes or fails. """
        self.current_action = None; self.action_target = None
        self.current_path = []; self.action_timer = 0.0


    def _handle_death(self):
        """ Handles agent death (logging). """
        if cfg.DEBUG_AGENT_CHOICE:
            print(f"Agent {self.id} has died at ({self.x}, {self.y}). Needs(H,T,E): ({self.health:.0f},{self.hunger:.0f},{self.thirst:.0f},{self.energy:.0f})")
        # TODO: Implement item dropping, corpse object


    # --- Skill & Crafting Helpers ---
    def learn_skill(self, skill_name, boost=1.0):
        """ Increases skill level based on usage, returns True if skill increased noticeably. """
        if not skill_name or skill_name not in self.skills: return False
        current_level = self.skills.get(skill_name, 0)
        if current_level >= cfg.MAX_SKILL_LEVEL: return False
        gain_factor = max(0.05, (1.0 - (current_level / (cfg.MAX_SKILL_LEVEL + 1)))**1.2)
        increase = cfg.SKILL_INCREASE_RATE * boost * gain_factor
        increase = max(0.01, increase) # Minimum gain
        new_level = min(cfg.MAX_SKILL_LEVEL, current_level + increase)
        if new_level > current_level + 0.001: # Check for meaningful increase
            self.skills[skill_name] = new_level
            return True
        return False

    def _get_skill_multiplier(self, skill_name):
        """ Returns a multiplier based on skill level (e.g., for action speed). """
        if not skill_name or skill_name not in self.skills: return 1.0
        level = self.skills.get(skill_name, 0)
        max_bonus = 1.5; exponent = 0.7
        multiplier = 1.0 + max_bonus * (level / cfg.MAX_SKILL_LEVEL)**exponent
        return max(0.1, multiplier) # Ensure minimum effect

    def _has_ingredients(self, ingredients):
        """ Checks if agent has required items in inventory. """
        if not ingredients: return True
        return all(self.inventory.get(item, 0) >= req for item, req in ingredients.items())

    def _has_skill_for(self, recipe_details):
        """ Checks if agent meets skill requirement for a recipe. """
        skill = recipe_details.get('skill')
        min_level = recipe_details.get('min_level', 0)
        return not skill or self.skills.get(skill, 0) >= min_level


    # --- Location & Knowledge Helpers ---
    def _find_best_resource_location(self, resource_type, max_search_dist=cfg.AGENT_VIEW_RADIUS):
        """ Finds the best known or nearby resource location. Returns (goal_pos, stand_pos, distance). """
        best_pos, best_stand_pos, min_dist_sq = None, None, float('inf')
        resource_name = cfg.RESOURCE_INFO.get(resource_type, {}).get('name','?')
        display_name = "Water" if resource_type == cfg.RESOURCE_WATER else resource_name

        # 1. Check known locations
        known_locations = self.knowledge.get_known_locations(resource_type)
        locations_to_remove = []
        if cfg.DEBUG_KNOWLEDGE and known_locations: print(f"Agent {self.id} checking known {display_name} locations: {known_locations}")
        for rx, ry in known_locations:
            is_valid = False
            if resource_type == cfg.RESOURCE_WATER:
                 if self.world.get_terrain(rx, ry) == cfg.TERRAIN_WATER: is_valid = True
            else:
                 res = self.world.get_resource(rx, ry)
                 if res and res.type == resource_type and not res.is_depleted(): is_valid = True
            if is_valid:
                stand_pos = self._find_stand_pos_for_resource(rx, ry)
                if stand_pos:
                    dist_sq = (self.x - stand_pos[0])**2 + (self.y - stand_pos[1])**2
                    if dist_sq < min_dist_sq:
                        min_dist_sq = dist_sq; best_pos = (rx, ry); best_stand_pos = stand_pos
            else: locations_to_remove.append((rx, ry))
        for rx, ry in locations_to_remove: self.knowledge.remove_resource_location(resource_type, rx, ry)
        if best_stand_pos and cfg.DEBUG_KNOWLEDGE: print(f"Agent {self.id} best KNOWN {display_name} at {best_pos}, stand {best_stand_pos}, dist^2 {min_dist_sq:.1f}")

        # 2. Search world if needed
        search_threshold_sq = (max_search_dist * 0.7)**2
        should_search_world = (not best_stand_pos or min_dist_sq > search_threshold_sq)
        if should_search_world:
            if cfg.DEBUG_KNOWLEDGE: print(f"Agent {self.id} searching world for {display_name} (Known dist^2: {min_dist_sq:.1f}, Threshold^2: {search_threshold_sq:.1f})")
            g_pos, s_pos, bfs_dist = self.world.find_nearest_resource(self.x, self.y, resource_type, max_dist=max_search_dist)
            if s_pos: # Found via BFS
                 if resource_type != cfg.RESOURCE_WATER: self.knowledge.add_resource_location(resource_type, g_pos[0], g_pos[1])
                 dist_sq_bfs = (self.x - s_pos[0])**2 + (self.y - s_pos[1])**2
                 if dist_sq_bfs < min_dist_sq: # BFS result is better
                      min_dist_sq = dist_sq_bfs; best_pos = g_pos; best_stand_pos = s_pos
                      if cfg.DEBUG_KNOWLEDGE: print(f"Agent {self.id} found closer {display_name} via world search at {best_pos}, stand {best_stand_pos}, dist^2 {dist_sq_bfs:.1f}")

        final_dist = math.sqrt(min_dist_sq) if best_stand_pos else float('inf')
        return best_pos, best_stand_pos, final_dist

    def _find_stand_pos_for_resource(self, res_x, res_y):
        """ Determines standing position to interact with a resource/water tile. """
        if self.world.get_terrain(res_x, res_y) == cfg.TERRAIN_WATER:
             return self._find_adjacent_walkable(res_x, res_y, self.world.walkability_matrix)
        resource = self.world.get_resource(res_x, res_y)
        if not resource: return None
        if self.world.walkability_matrix[res_y, res_x] == 1: return (res_x, res_y) # Stand on it if walkable (Workbench)
        else: return self._find_adjacent_walkable(res_x, res_y, self.world.walkability_matrix) # Stand adjacent if blocking (Tree, Rock)

    def _is_at_workbench(self):
        """ Checks if standing within interaction radius of a workbench tile. """
        distance = cfg.WORKBENCH_INTERACTION_RADIUS
        min_x=max(0, self.x-distance); max_x=min(self.world.width-1, self.x+distance)
        min_y=max(0, self.y-distance); max_y=min(self.world.height-1, self.y+distance)
        for y in range(min_y, max_y+1):
             for x in range(min_x, max_x+1):
                 res = self.world.get_resource(x, y)
                 if res and res.type == cfg.RESOURCE_WORKBENCH: return True
        return False

    def _get_nearby_workbench_pos(self):
        """ Returns the (x,y) of the nearest workbench within interaction radius, or None. """
        distance = cfg.WORKBENCH_INTERACTION_RADIUS
        min_x=max(0, self.x-distance); max_x=min(self.world.width-1, self.x+distance)
        min_y=max(0, self.y-distance); max_y=min(self.world.height-1, self.y+distance)
        for y in range(min_y, max_y+1):
             for x in range(min_x, max_x+1):
                 res = self.world.get_resource(x, y)
                 if res and res.type == cfg.RESOURCE_WORKBENCH: return (x, y)
        return None

    def _has_workbench_knowledge(self):
         """ Checks if the agent knows the location of ANY workbench. """
         return len(self.knowledge.get_known_locations(cfg.RESOURCE_WORKBENCH)) > 0


    # --- Pathfinding Helpers ---
    def _plan_path(self, target_pos, agents):
        """ Plans a path from current position to target_pos using A*. Returns list of (x,y) or None. """
        start_pos = (self.x, self.y)
        if not target_pos or start_pos == target_pos: return []
        tx, ty = target_pos
        if not (0 <= tx < self.world.width and 0 <= ty < self.world.height):
            if cfg.DEBUG_PATHFINDING: print(f"Agent {self.id}: Path target {target_pos} out of bounds.")
            return None

        other_agent_positions = [(a.x, a.y) for a in agents if a != self and a.health > 0]
        temp_walkability = self.world.update_walkability(agent_positions=other_agent_positions)

        final_start = start_pos
        if temp_walkability[start_pos[1], start_pos[0]] == 0: # Start blocked
            adj_start = self._find_adjacent_walkable(start_pos[0], start_pos[1], temp_walkability)
            if adj_start: final_start = adj_start
            else: 
                if cfg.DEBUG_PATHFINDING: print(f"Agent {self.id}: Start {start_pos} blocked, no adjacent walkable. Path fail."); return None

        final_target = target_pos
        if temp_walkability[ty, tx] == 0: # Target blocked
            adj_target = self._find_adjacent_walkable(tx, ty, temp_walkability)
            if adj_target: final_target = adj_target
            else: 
                if cfg.DEBUG_PATHFINDING: print(f"Agent {self.id}: Target {target_pos} blocked, no adjacent walkable. Path fail."); return None

        path_nodes = find_path(temp_walkability, final_start, final_target) # Call A*

        if path_nodes is None: # Pathfinding error
            if cfg.DEBUG_PATHFINDING: print(f"Agent {self.id}: find_path returned None for {final_start}->{final_target}.")
            return None
        elif not path_nodes and final_start != final_target: # No path found
             if cfg.DEBUG_PATHFINDING: print(f"Agent {self.id}: find_path returned empty list (no path) for {final_start}->{final_target}.")
             return None
        else: # Path found (or start == target)
            path_coords = [(node.x, node.y) for node in path_nodes]
            # Prepend original start if we adjusted it and path is non-empty
            if final_start != start_pos and path_coords: path_coords.insert(0, start_pos)
            if cfg.DEBUG_PATHFINDING and path_coords: print(f"Agent {self.id}: Path found from {start_pos} (adj:{final_start}) to {target_pos} (adj:{final_target}) (len {len(path_coords)}): {path_coords[:5]}...")
            return path_coords

    def _find_adjacent_walkable(self, x, y, walkability_matrix):
        """ Finds a walkable tile adjacent (including diagonals) to (x, y). """
        neighbors = [(0,-1), (0,1), (1,0), (-1,0), (1,-1), (1,1), (-1,1), (-1,-1)]
        for dx, dy in neighbors:
            nx, ny = x + dx, y + dy
            if 0 <= nx < self.world.width and 0 <= ny < self.world.height and walkability_matrix[ny, nx] == 1:
                return (nx, ny)
        return None

    # --- Phase 4+ Social Placeholders ---
    def perceive_signal(self, sender_id, signal_type, position): pass
    def _process_signals(self, agents, social_manager): pass
    def decide_to_learn(self, teacher_id, skill_name): return False
    def _find_agent_to_help(self, agents): return None
    def _get_current_action_utility(self): return 0.1 # Placeholder if needed later