# Contents of agent.py
# agent.py
import random
import math
import config as cfg
from pathfinding_utils import find_path
from knowledge import KnowledgeSystem
from world import Resource # For type checking and placing workbenches
from social import Signal # For type hinting perceive_signal
import traceback

# Global counter for agent IDs
_agent_id_counter = 0

class Agent:
    """
    Represents an agent in the simulation with needs, skills, knowledge,
    and the ability to perceive, decide, and act within the world.
    Phase 4: Includes social attributes, relationships, signaling, teaching, helping.
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
        self.current_action = None      # String identifier (e.g., "GatherWood", "Craft:CrudeAxe", "Help:12:Food")
        self.action_target = None       # Dictionary holding target info (goal, stand, recipe, agent_id, item, etc.)
        self.current_path = []          # List of (x, y) tuples for movement
        self.action_timer = 0.0         # Timer for timed actions (gathering, crafting, teaching, etc.)

        # Inventory & Skills
        self.inventory = {}             # item_name: count
        self.skills = {                 # skill_name: level
            'GatherWood': cfg.INITIAL_SKILL_LEVEL,
            'GatherStone': cfg.INITIAL_SKILL_LEVEL,
            'BasicCrafting': 1.0,       # Start with skill level 1 to enable axe crafting
        }

        # Knowledge & Attributes
        self.knowledge = KnowledgeSystem(self.id) # Agent's memory and beliefs
        self.intelligence = random.uniform(0.3, 0.8) # Factor influencing invention speed

        # --- Initial Knowledge (Bootstrap Recipes) ---
        self.knowledge.add_recipe('CrudeAxe')
        self.knowledge.add_recipe('Workbench')

        # --- Phase 4: Social Attributes & State ---
        self.sociability = random.uniform(0.1, 0.9) # How likely to engage in positive social actions
        self.pending_signal: Signal | None = None      # Last signal perceived this tick
        self.reacted_to_signal_type = None # Track if reacted to avoid spamming reactions
        self.last_passive_learn_check_time = 0.0 # Throttle passive learning checks


    def update(self, dt_real_seconds, agents, social_manager):
        """ Main update loop called each simulation tick. """
        dt_sim_seconds = dt_real_seconds * cfg.SIMULATION_SPEED_FACTOR

        # 1. Update Needs & Check Health
        self._update_needs(dt_sim_seconds)
        if self.health <= 0:
            self._handle_death()
            return # Agent is dead

        # 2. Process Social Signals (Phase 4)
        self._process_signals(agents, social_manager) # React to any perceived signal

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

        # 4. Passive Learning Check (Phase 4) - Throttled
        if self.world.simulation_time - self.last_passive_learn_check_time > 1.0: # Check roughly once per sim sec
             self._check_passive_learning(agents)
             self.last_passive_learn_check_time = self.world.simulation_time


    def _update_needs(self, dt_sim_seconds):
        """ Updates agent's health, energy, hunger, and thirst over time. """
        self.hunger = min(cfg.MAX_HUNGER, self.hunger + cfg.HUNGER_INCREASE_RATE * dt_sim_seconds) # Uses updated config rate
        self.thirst = min(cfg.MAX_THIRST, self.thirst + cfg.THIRST_INCREASE_RATE * dt_sim_seconds) # Uses updated config rate

        # Energy decay/regen based on action
        energy_change = 0
        if self.current_action == "Rest":
            energy_change = cfg.ENERGY_REGEN_RATE * dt_sim_seconds
        elif self.current_action is not None: # Any other active action decays energy
            energy_change = -cfg.ENERGY_DECAY_RATE * dt_sim_seconds
        # Apply base decay if not resting
        if self.current_action != "Rest":
             energy_change -= cfg.ENERGY_DECAY_RATE * dt_sim_seconds # Uses updated config rate

        self.energy = max(0, min(cfg.MAX_ENERGY, self.energy + energy_change))

        # Health regen only while resting and needs mostly met
        if self.current_action == "Rest" and self.energy > cfg.MAX_ENERGY * 0.5 and self.hunger < cfg.MAX_HUNGER * 0.8 and self.thirst < cfg.MAX_THIRST * 0.8:
            self.health = min(cfg.MAX_HEALTH, self.health + cfg.HEALTH_REGEN_RATE * dt_sim_seconds) # Uses updated config rate

        # Health drain from critical needs
        health_drain = 0
        if self.hunger >= cfg.MAX_HUNGER * 0.95: health_drain += 0.8
        if self.thirst >= cfg.MAX_THIRST * 0.95: health_drain += 1.0
        if self.energy <= 0 and self.current_action != "Rest": health_drain += 0.5 # Exhaustion penalty
        self.health = max(0, self.health - health_drain * dt_sim_seconds)


    def _choose_action(self, agents, social_manager):
        """ Determines the best action based on utility scores. Phase 4 includes social actions. """
        utilities = {}

        # --- Calculate Utility Scores ---
        # 1. Basic Needs Utilities
        # Use the explicit config weights
        utilities['SatisfyThirst'] = (self.thirst / cfg.MAX_THIRST)**2 * cfg.UTILITY_THIRST_WEIGHT
        utilities['SatisfyHunger'] = (self.hunger / cfg.MAX_HUNGER)**2 * cfg.UTILITY_HUNGER_WEIGHT
        energy_deficit = (cfg.MAX_ENERGY - self.energy) / cfg.MAX_ENERGY
        needs_rest = (self.energy < cfg.MAX_ENERGY * 0.3 or
                      (self.health < cfg.MAX_HEALTH * 0.8 and self.hunger < cfg.MAX_HUNGER * 0.8 and self.thirst < cfg.MAX_THIRST * 0.8))
        utilities['Rest'] = (energy_deficit**2) * 1.1 if needs_rest else 0

        # 2. Resource, Crafting, Invention Utilities
        has_axe = self.inventory.get('CrudeAxe', 0) > 0
        has_pick = self.inventory.get('StonePick', 0) > 0
        current_wood = self.inventory.get('Wood', 0)
        current_stone = self.inventory.get('Stone', 0)
        inventory_full = sum(self.inventory.values()) >= cfg.INVENTORY_CAPACITY
        needs_met_factor = max(0, 1 - max(utilities.get('SatisfyThirst',0), utilities.get('SatisfyHunger',0), utilities.get('Rest',0)))
        is_at_workbench = self._is_at_workbench()

        # Calculate resource needs
        wood_needed_for_crafts = 0; stone_needed_for_crafts = 0
        workbench_required_by_known_craft = False; can_make_something_at_workbench = False
        for recipe_name in self.knowledge.known_recipes:
            details = cfg.RECIPES.get(recipe_name)
            if not details or not self._has_skill_for(details): continue
            want_item = False
            if recipe_name == 'Workbench' and not self._has_workbench_knowledge(): want_item = True
            elif recipe_name == 'StonePick' and not has_pick: want_item = True
            elif recipe_name == 'CrudeAxe' and not has_axe: want_item = True
            elif recipe_name == 'CookedFood' and self.inventory.get('Food', 0) > 0 : want_item = True

            if want_item:
                ingredients = details.get('ingredients', {})
                wood_needed_for_crafts = max(wood_needed_for_crafts, ingredients.get('Wood', 0) - current_wood)
                stone_needed_for_crafts = max(stone_needed_for_crafts, ingredients.get('Stone', 0) - current_stone)
                if details.get('workbench', False):
                     workbench_required_by_known_craft = True
                     if self._has_ingredients(ingredients): can_make_something_at_workbench = True

        stockpile_wood_goal = 5; stockpile_stone_goal = 3
        total_wood_need = max(wood_needed_for_crafts, stockpile_wood_goal if needs_met_factor > 0.6 else 0)
        total_stone_need = max(stone_needed_for_crafts, stockpile_stone_goal if needs_met_factor > 0.6 else 0)

        # Gathering Utilities
        if not inventory_full and total_wood_need > current_wood:
            wood_need_norm = min(1, (total_wood_need - current_wood) / total_wood_need if total_wood_need > 0 else 0)
            tool_mult = cfg.TOOL_EFFICIENCY['CrudeAxe'] if has_axe else 1.0
            utilities['GatherWood'] = wood_need_norm * 0.4 * self._get_skill_multiplier('GatherWood') * tool_mult * needs_met_factor
        if not inventory_full and total_stone_need > current_stone:
            stone_need_norm = min(1, (total_stone_need - current_stone) / total_stone_need if total_stone_need > 0 else 0)
            tool_mult = cfg.TOOL_EFFICIENCY.get('StonePick', 1.0) if has_pick else 1.0
            utilities['GatherStone'] = stone_need_norm * 0.35 * self._get_skill_multiplier('GatherStone') * tool_mult * needs_met_factor

        # Crafting Utility
        best_craft_utility = 0; best_craft_recipe = None
        for recipe_name in self.knowledge.known_recipes:
            details = cfg.RECIPES.get(recipe_name); utility = 0.0
            if not details: continue
            can_craft_now = False
            if self._has_ingredients(details['ingredients']) and self._has_skill_for(details):
                if details.get('workbench', False): can_craft_now = is_at_workbench
                else: can_craft_now = True
            if can_craft_now:
                utility = 0.3 * needs_met_factor * self._get_skill_multiplier(details.get('skill')) # Base utility
                if recipe_name == 'CrudeAxe' and not has_axe: utility = 0.75
                if recipe_name == 'StonePick' and not has_pick: utility = 0.70
                if recipe_name == 'Workbench' and not self._has_workbench_knowledge(): utility = 0.80
                if recipe_name == 'CookedFood' and self.hunger > cfg.MAX_HUNGER * 0.5: utility = 0.65
                if utility > best_craft_utility:
                    best_craft_utility = utility; best_craft_recipe = recipe_name
        if best_craft_recipe: utilities['Craft:' + best_craft_recipe] = best_craft_utility

        # GoToWorkbench Utility
        reason_for_workbench = None
        if can_make_something_at_workbench: reason_for_workbench = "Craft"
        can_invent = (needs_met_factor > 0.7 and len(self.inventory) >= cfg.INVENTION_ITEM_TYPES_THRESHOLD and not inventory_full)
        if can_invent and not reason_for_workbench: reason_for_workbench = "Invent"
        if reason_for_workbench and not is_at_workbench:
             if self._has_workbench_knowledge():
                  utility = 0.65 if reason_for_workbench == "Craft" else 0.45
                  utilities['GoToWorkbench:' + reason_for_workbench] = utility * needs_met_factor

        # Invention Utility
        if is_at_workbench and can_invent:
             utility = 0.35 * self.intelligence * needs_met_factor
             if self.current_action and self.current_action.startswith("Craft"): utility *= 0.5
             utilities['Invent'] = utility

        # --- Phase 4: Social Action Utilities ---
        # 3. Signaling Utility
        best_signal_utility = 0; best_signal_type = None
        if self.hunger > cfg.MAX_HUNGER * cfg.HELPING_TARGET_NEED_THRESHOLD:
             utility = (self.hunger / cfg.MAX_HUNGER) * 0.8 * self.sociability
             if utility > best_signal_utility: best_signal_utility = utility; best_signal_type = cfg.SIGNAL_HELP_NEEDED_FOOD
        # Add other signal triggers here if desired

        if best_signal_type:
            # <<< Adjusted utility factor to rely less on perfect needs state >>>
            signal_utility_factor = max(0.1, 0.2 + needs_met_factor * 0.8)
            utilities[f"Signal:{best_signal_type}"] = best_signal_utility * signal_utility_factor

        # 4. Helping Utility
        best_help_utility = 0; best_help_target = None; best_help_item = None
        # Use the relaxed self-need threshold from config
        can_consider_helping = (self.hunger < cfg.MAX_HUNGER * cfg.HELPING_SELF_NEED_THRESHOLD and \
                                self.thirst < cfg.MAX_THIRST * cfg.HELPING_SELF_NEED_THRESHOLD and \
                                self.energy > cfg.MAX_ENERGY * 0.3)

        if can_consider_helping:
            available_help_items = [item for item in cfg.HELPABLE_ITEMS if self.inventory.get(item, 0) > 0]
            if available_help_items: # Only check agents if have items
                nearby_agents = self._find_nearby_agents(agents, cfg.HELPING_INTERACTION_RADIUS)
                for other in nearby_agents:
                     rel = self.knowledge.get_relationship(other.id)
                     if rel < cfg.HELPING_MIN_RELATIONSHIP: continue # Use updated config

                     needs_help = False; item_to_give = None; need_severity = 0
                     if other.hunger > cfg.MAX_HUNGER * cfg.HELPING_TARGET_NEED_THRESHOLD:
                          item_to_give = available_help_items[0]; needs_help = True
                          need_severity = (other.hunger / cfg.MAX_HUNGER)
                     # Add health check later

                     if needs_help and item_to_give:
                          # <<< Adjusted utility factor to be less penalized by own needs >>>
                          utility = need_severity * (rel + 1.1) * self.sociability * 0.75 # Increased base slightly more
                          help_utility_factor = max(0.2, 0.4 + needs_met_factor * 0.6) # Ensure minimum floor
                          final_utility = utility * help_utility_factor

                          if final_utility > best_help_utility:
                               best_help_utility = final_utility; best_help_target = other.id; best_help_item = item_to_give

                if best_help_target and best_help_item:
                     utilities[f"Help:{best_help_target}:{best_help_item}"] = best_help_utility

        # 5. Teaching Utility
        best_teach_utility = 0; best_teach_target = None; best_teach_skill = None
        can_consider_teaching = (self.hunger < cfg.MAX_HUNGER * 0.7 and \
                                 self.thirst < cfg.MAX_THIRST * 0.7 and \
                                 self.energy > cfg.MAX_ENERGY * 0.4)

        if can_consider_teaching:
             nearby_agents_teach = self._find_nearby_agents(agents, cfg.TEACHING_INTERACTION_RADIUS)
             for other in nearby_agents_teach:
                 rel = self.knowledge.get_relationship(other.id)
                 if rel < cfg.TEACHING_MIN_RELATIONSHIP: continue # Use updated config

                 for skill_name, my_level in self.skills.items():
                      other_level = other.skills.get(skill_name, 0)
                      # Use updated config skill advantage
                      if my_level > cfg.TEACHING_MIN_SKILL_ADVANTAGE and \
                         my_level > other_level + cfg.TEACHING_MIN_SKILL_ADVANTAGE and \
                         other_level < cfg.MAX_SKILL_LEVEL * 0.6:
                           skill_gap_factor = (my_level - other_level) / cfg.MAX_SKILL_LEVEL
                           # <<< Adjusted utility factor >>>
                           utility = skill_gap_factor * (rel + 1.1) * self.sociability * 0.50 # Increased base utility more
                           teach_utility_factor = max(0.25, 0.5 + needs_met_factor * 0.5) # Higher minimum floor
                           final_utility = utility * teach_utility_factor

                           if final_utility > best_teach_utility:
                                best_teach_utility = final_utility; best_teach_target = other.id; best_teach_skill = skill_name
                                break # Teach first suitable skill found for this agent

             if best_teach_target and best_teach_skill:
                  utilities[f"Teach:{best_teach_target}:{best_teach_skill}"] = best_teach_utility


        # --- Default Action Utility ---
        utilities['Wander'] = 0.05 * needs_met_factor * (1.0 - self.intelligence * 0.5)


        # --- Selection Process ---
        best_action = None; max_utility = -1; self.action_target = None
        sorted_utilities = sorted(utilities.items(), key=lambda item: item[1] + random.uniform(-0.01, 0.01), reverse=True)

        if cfg.DEBUG_AGENT_AI: print(f"Agent {self.id} Utilities: {[(a, f'{u:.2f}') for a, u in sorted_utilities if u > 0.01]}")

        for action, utility in sorted_utilities:
            if utility <= cfg.UTILITY_THRESHOLD and 'Wander' not in action: continue

            feasible, target_data = self._check_action_feasibility(action, agents)
            if feasible:
                best_action = action; max_utility = utility; self.action_target = target_data
                if cfg.DEBUG_AGENT_CHOICE: print(f"Agent {self.id} PRE-SELECTED: {best_action} (Util: {max_utility:.2f}) Target: {target_data}")
                break

        if not best_action:
            feasible, target_data = self._check_action_feasibility('Wander', agents)
            if feasible: best_action = 'Wander'; max_utility = utilities.get('Wander', 0.05); self.action_target = target_data
            else: best_action = "Idle"; max_utility = 0; self.action_target = None


        # --- Log Chosen Action and Initiate ---
        if cfg.DEBUG_AGENT_CHOICE:
            inv_sum = sum(self.inventory.values()); known_recipes_count = len(self.knowledge.known_recipes)
            skills_str = {k: f"{v:.1f}" for k, v in self.skills.items() if v > 0.1}
            rels_str = {id: f"{s:.1f}" for id, s in self.knowledge.relationships.items()}
            print(f"Agent {self.id} choosing: {best_action} (Util: {max_utility:.2f}) Needs(Hl,H,T,E): ({self.health:.0f},{self.hunger:.0f},{self.thirst:.0f},{self.energy:.0f}) Inv: {inv_sum} Recipes: {known_recipes_count} Soc:{self.sociability:.1f} Skills: {skills_str} Rels: {rels_str}")

        self.current_action = best_action
        self.current_path = []; self.action_timer = 0.0
        if best_action == "Idle": self.action_target = None; return

        self._plan_path_for_action(agents)


    def _plan_path_for_action(self, agents):
        """ Plans path for chosen action. Sets self.current_path or reverts to Idle. """
        target_setup_success = False; best_action = self.current_action
        if not self.action_target:
            print(f"Agent {self.id}: Critical Error - Action {best_action} chosen but action_target is None!")
            self.current_action = "Idle"; return

        try:
            stand_pos = self.action_target.get('stand')
            current_pos = (self.x, self.y)

            if stand_pos: # Action requires movement to a specific standing spot
                if current_pos == stand_pos: target_setup_success = True; self.current_path = []
                else:
                    self.current_path = self._plan_path(stand_pos, agents)
                    if self.current_path is not None: target_setup_success = True
                    else:
                         if cfg.DEBUG_PATHFINDING: print(f"Agent {self.id}: Path planning failed for {best_action} to {stand_pos}.")
                         target_setup_success = False
            else: # Action happens locally or target position is determined differently
                action_type = best_action.split(':')[0]
                needs_stand_pos = action_type in ['GatherWood', 'GatherStone', 'SatisfyHunger', 'SatisfyThirst', 'GoToWorkbench'] \
                                  or (action_type == 'Craft' and self.action_target.get('requires_workbench')) \
                                  or action_type in ['Help', 'Teach']

                if needs_stand_pos and not self.action_target.get('goal'):
                     print(f"Agent {self.id}: Warning - Action {best_action} might need stand pos, but none/no goal found in target: {self.action_target}")
                     target_setup_success = True; self.current_path = [] # Assume local ok if feasibility passed
                elif not needs_stand_pos: # Truly local actions
                     target_setup_success = True; self.current_path = []
                else:
                     print(f"Agent {self.id}: Critical error - Action {best_action} requires 'stand' pos but none found in target data: {self.action_target}")
                     target_setup_success = False

        except Exception as e:
             print(f"!!! Error during action path planning setup for Agent {self.id}, Action: {best_action}: {e}"); traceback.print_exc()
             target_setup_success = False

        if not target_setup_success:
             if cfg.DEBUG_AGENT_CHOICE or cfg.DEBUG_PATHFINDING: print(f"Agent {self.id}: Failed to initiate action {best_action} (pathing/target setup failed). Reverting to Idle.")
             self._complete_action()


    def _check_action_feasibility(self, action_name, agents):
        """ Checks if an action is possible *right now*. Returns (bool feasible, dict target_data). Phase 4 checks added. """
        target_data = {'type': action_name.split(':')[0]}
        goal_pos, stand_pos, dist = None, None, float('inf')

        # Needs, Gathering, Crafting, GoToWorkbench, Invent, Wander, Idle, Rest (Unchanged logic, relies on updated Config)
        if action_name == 'SatisfyThirst':
            goal_pos, stand_pos, dist = self._find_best_resource_location(cfg.RESOURCE_WATER)
            if stand_pos: target_data.update({'goal': goal_pos, 'stand': stand_pos}); return True, target_data
        elif action_name == 'SatisfyHunger':
            goal_pos, stand_pos, dist = self._find_best_resource_location(cfg.RESOURCE_FOOD)
            if stand_pos: target_data.update({'goal': goal_pos, 'stand': stand_pos}); return True, target_data
        elif action_name == 'GatherWood':
            if sum(self.inventory.values()) >= cfg.INVENTORY_CAPACITY: return False, None
            goal_pos, stand_pos, dist = self._find_best_resource_location(cfg.RESOURCE_WOOD)
            if stand_pos: target_data.update({'goal': goal_pos, 'stand': stand_pos}); return True, target_data
        elif action_name == 'GatherStone':
            if sum(self.inventory.values()) >= cfg.INVENTORY_CAPACITY: return False, None
            goal_pos, stand_pos, dist = self._find_best_resource_location(cfg.RESOURCE_STONE)
            if stand_pos: target_data.update({'goal': goal_pos, 'stand': stand_pos}); return True, target_data
        elif action_name.startswith('Craft:'):
             recipe_name = action_name.split(':')[1]; details = cfg.RECIPES.get(recipe_name)
             if not details or not self.knowledge.knows_recipe(recipe_name) or not self._has_ingredients(details['ingredients']) or not self._has_skill_for(details): return False, None
             req_wb = details.get('workbench', False)
             target_data.update({'recipe': recipe_name, 'requires_workbench': req_wb})
             if req_wb:
                 if not self._is_at_workbench(): return False, None
                 wb_pos = self._get_nearby_workbench_pos()
                 if not wb_pos: return False, None
                 goal_pos = wb_pos; stand_pos = (self.x, self.y)
             else: goal_pos = (self.x, self.y); stand_pos = (self.x, self.y)
             target_data.update({'goal': goal_pos, 'stand': stand_pos}); return True, target_data
        elif action_name.startswith('GoToWorkbench:'):
             purpose = action_name.split(':')[1]
             if self._is_at_workbench(): return False, None
             goal_pos, stand_pos, dist = self._find_best_resource_location(cfg.RESOURCE_WORKBENCH)
             if stand_pos: target_data.update({'goal': goal_pos, 'stand': stand_pos, 'purpose': purpose}); return True, target_data
        elif action_name == 'Invent':
             if not self._is_at_workbench(): return False, None
             if len(self.inventory) < cfg.INVENTION_ITEM_TYPES_THRESHOLD: return False, None
             if sum(self.inventory.values()) >= cfg.INVENTORY_CAPACITY: return False, None
             wb_pos = self._get_nearby_workbench_pos()
             if wb_pos: target_data.update({'goal': wb_pos, 'stand': (self.x, self.y)}); return True, target_data
             else: return False, None
        elif action_name == 'Wander':
             for _ in range(10):
                  wx = max(0, min(self.world.width - 1, self.x + random.randint(-cfg.WANDER_RADIUS, cfg.WANDER_RADIUS)))
                  wy = max(0, min(self.world.height - 1, self.y + random.randint(-cfg.WANDER_RADIUS, cfg.WANDER_RADIUS)))
                  if self.world.walkability_matrix[wy, wx] == 1 and self.world.terrain_map[wy,wx] == cfg.TERRAIN_GROUND:
                       stand_pos = (wx, wy); break
             else: stand_pos = self._find_adjacent_walkable(self.x, self.y, self.world.walkability_matrix)
             if stand_pos: target_data.update({'goal': stand_pos, 'stand': stand_pos}); return True, target_data
        elif action_name == "Idle": return True, {'type': 'Idle'}
        elif action_name == "Rest":
            if self.hunger < cfg.MAX_HUNGER * 0.95 and self.thirst < cfg.MAX_THIRST * 0.95:
                 target_data['stand'] = (self.x, self.y); return True, target_data


        # --- Phase 4: Social Action Feasibility ---
        elif action_name.startswith('Signal:'):
             signal_type = action_name.split(':')[1]
             known_signals = [cfg.SIGNAL_HELP_NEEDED_FOOD, cfg.SIGNAL_HELP_NEEDED_HEALTH, cfg.SIGNAL_FOUND_FOOD, cfg.SIGNAL_FOUND_WATER, cfg.SIGNAL_DANGER_NEAR]
             if signal_type in known_signals:
                 target_data['signal_type'] = signal_type
                 target_data['stand'] = (self.x, self.y); target_data['goal'] = (self.x, self.y)
                 return True, target_data

        elif action_name.startswith('Help:'):
             parts = action_name.split(':');
             if len(parts) != 3: return False, None
             _, target_id_str, item_name = parts
             try: target_id = int(target_id_str)
             except ValueError: return False, None
             target_agent = self.world.get_agent_by_id(target_id)
             if not target_agent or target_agent.health <= 0: return False, None

             # Check conditions using updated config values
             if self.inventory.get(item_name, 0) <= 0: return False, None
             if item_name not in cfg.HELPABLE_ITEMS: return False, None
             dist_sq = (self.x - target_agent.x)**2 + (self.y - target_agent.y)**2
             if dist_sq > cfg.HELPING_INTERACTION_RADIUS**2: return False, None
             if self.knowledge.get_relationship(target_id) < cfg.HELPING_MIN_RELATIONSHIP: return False, None
             # <<< Use RELAXED self-need threshold from config >>>
             if self.hunger > cfg.MAX_HUNGER * cfg.HELPING_SELF_NEED_THRESHOLD or \
                self.thirst > cfg.MAX_THIRST * cfg.HELPING_SELF_NEED_THRESHOLD: return False, None

             target_data.update({'target_id': target_id, 'item': item_name})
             target_data['goal'] = (target_agent.x, target_agent.y)
             stand_pos = self._find_stand_pos_for_agent(target_agent.x, target_agent.y, agents)
             if stand_pos: target_data['stand'] = stand_pos; return True, target_data
             else: return False, None

        elif action_name.startswith('Teach:'):
            parts = action_name.split(':');
            if len(parts) != 3: return False, None
            _, target_id_str, skill_name = parts
            try: target_id = int(target_id_str)
            except ValueError: return False, None
            target_agent = self.world.get_agent_by_id(target_id)
            if not target_agent or target_agent.health <= 0: return False, None

            # Check conditions using updated config values
            if skill_name not in self.skills: return False, None
            my_level = self.skills[skill_name]
            other_level = target_agent.skills.get(skill_name, 0)
            if my_level < cfg.TEACHING_MIN_SKILL_ADVANTAGE or \
               my_level < other_level + cfg.TEACHING_MIN_SKILL_ADVANTAGE: return False, None
            dist_sq = (self.x - target_agent.x)**2 + (self.y - target_agent.y)**2
            if dist_sq > cfg.TEACHING_INTERACTION_RADIUS**2: return False, None
            if self.knowledge.get_relationship(target_id) < cfg.TEACHING_MIN_RELATIONSHIP: return False, None
            if self.energy < cfg.MAX_ENERGY * 0.4 or self.hunger > cfg.MAX_HUNGER * 0.7 or self.thirst > cfg.MAX_THIRST * 0.7: return False, None

            target_data.update({'target_id': target_id, 'skill': skill_name})
            target_data['goal'] = (target_agent.x, target_agent.y)
            stand_pos = self._find_stand_pos_for_agent(target_agent.x, target_agent.y, agents)
            if stand_pos: target_data['stand'] = stand_pos; return True, target_data
            else: return False, None

        return False, None # Default: action not feasible


    def _perform_action(self, dt_sim_seconds, agents, social_manager):
        """ Executes the current action step, returns True if completed. Phase 4 actions added. """
        if not self.current_action or self.current_action == "Idle": return True

        # --- 1. Movement Phase ---
        if self.current_path:
            next_pos = self.current_path[0]; nx, ny = next_pos
            other_agent_positions = [(a.x, a.y) for a in agents if a != self and a.health > 0]
            temp_walkability = self.world.update_walkability(agent_positions=other_agent_positions)

            if temp_walkability[ny, nx] == 0:
                stand_pos = self.action_target.get('stand')
                goal_pos = self.action_target.get('goal')
                final_target = stand_pos if stand_pos else goal_pos
                if final_target:
                    if cfg.DEBUG_PATHFINDING: print(f"Agent {self.id}: Path blocked at {next_pos}. Re-planning to {final_target}.")
                    new_path = self._plan_path(final_target, agents)
                    if new_path is not None:
                         self.current_path = new_path
                         if not new_path and (self.x, self.y) != final_target:
                              if cfg.DEBUG_PATHFINDING: print(f"Agent {self.id}: Replan resulted in empty path, but not at target {final_target}. Waiting.")
                              return False # Wait
                         elif new_path:
                              return False # Continue moving
                    else:
                         if cfg.DEBUG_AGENT_ACTIONS: print(f"Agent {self.id}: Failed replan around block for {self.current_action}. Failing action.")
                         return True # Fail
                else:
                    print(f"Agent {self.id}: Path blocked for {self.current_action}, no stand/goal pos to replan! Failing.")
                    return True # Fail
            else: # Move is clear
                self.x = nx; self.y = ny
                self.energy -= cfg.MOVE_ENERGY_COST # Use updated config cost
                self.current_path.pop(0)
                if self.current_path: return False # Still moving

        # --- 2. Action Execution Phase ---
        action_type = self.current_action.split(':')[0]
        # --- Use the REVISED verification logic ---
        if not self._verify_position_for_action(action_type, agents):
             if cfg.DEBUG_AGENT_ACTIONS: print(f"Agent {self.id}: Failed position verification for {self.current_action} after pathing. Failing.")
             return True

        self.action_timer += dt_sim_seconds

        # --- Action Logic ---
        try:
            # Basic Needs & Resource Gathering, Crafting, GoToWorkbench, Invent (Uses updated config values implicitly)
            if action_type == 'SatisfyThirst':
                drink_duration = cfg.DRINK_THIRST_REDUCTION / 25 # Faster drinking if more thirst reduced? Or keep const? Let's keep const for now.
                # drink_duration = 2.5 # Fixed duration example
                if self.action_timer >= drink_duration:
                    self.thirst = max(0, self.thirst - cfg.DRINK_THIRST_REDUCTION); self.energy -= cfg.MOVE_ENERGY_COST * 0.1
                    if cfg.DEBUG_AGENT_ACTIONS: print(f"Agent {self.id} drank. Thirst: {self.thirst:.1f}")
                    goal_pos = self.action_target.get('goal');
                    if goal_pos: self.knowledge.add_resource_location(cfg.RESOURCE_WATER, goal_pos[0], goal_pos[1])
                    return True
                else: return False
            elif action_type == 'SatisfyHunger':
                goal_pos = self.action_target['goal']; resource = self.world.get_resource(goal_pos[0], goal_pos[1])
                eat_duration = cfg.EAT_HUNGER_REDUCTION / 25 # Faster eating if more hunger reduced?
                # eat_duration = 2.0 # Fixed duration example
                if not resource or resource.is_depleted():
                     self.knowledge.remove_resource_location(cfg.RESOURCE_FOOD, goal_pos[0], goal_pos[1]); return True
                if self.action_timer >= eat_duration:
                    amount_eaten = self.world.consume_resource_at(goal_pos[0], goal_pos[1], 1)
                    if amount_eaten > 0:
                        self.hunger = max(0, self.hunger - cfg.EAT_HUNGER_REDUCTION); self.energy -= cfg.MOVE_ENERGY_COST * 0.1
                        if cfg.DEBUG_AGENT_ACTIONS: print(f"Agent {self.id} ate raw food. Hunger: {self.hunger:.1f}")
                        self.knowledge.add_resource_location(cfg.RESOURCE_FOOD, goal_pos[0], goal_pos[1])
                        if resource.is_depleted(): self.knowledge.remove_resource_location(cfg.RESOURCE_FOOD, goal_pos[0], goal_pos[1])
                    else: self.knowledge.remove_resource_location(cfg.RESOURCE_FOOD, goal_pos[0], goal_pos[1])
                    return True
                else: return False
            elif action_type == 'Rest':
                if self.energy >= cfg.MAX_ENERGY or self.thirst > cfg.MAX_THIRST * 0.9 or self.hunger > cfg.MAX_HUNGER * 0.9: return True
                return False # Continue resting
            elif action_type == 'Wander': return True # Completes instantly upon arrival
            elif action_type == 'GatherWood' or action_type == 'GatherStone':
                 is_wood = action_type == 'GatherWood'; res_type = cfg.RESOURCE_WOOD if is_wood else cfg.RESOURCE_STONE
                 skill = 'GatherWood' if is_wood else 'GatherStone'; tool = 'CrudeAxe' if is_wood else 'StonePick'
                 res_name = 'Wood' if is_wood else 'Stone'
                 goal_pos = self.action_target['goal']; resource = self.world.get_resource(goal_pos[0], goal_pos[1])
                 if not resource or resource.is_depleted() or resource.type != res_type:
                      self.knowledge.remove_resource_location(res_type, goal_pos[0], goal_pos[1]); return True
                 tool_mult = cfg.TOOL_EFFICIENCY.get(tool, 1.0) if self.inventory.get(tool, 0) > 0 else 1.0
                 skill_mult = self._get_skill_multiplier(skill)
                 duration = cfg.GATHER_BASE_DURATION / (skill_mult * tool_mult)
                 if self.action_timer >= duration:
                     amount = self.world.consume_resource_at(goal_pos[0], goal_pos[1], 1)
                     if amount > 0:
                         self.inventory[res_name] = self.inventory.get(res_name, 0) + amount; self.energy -= cfg.GATHER_ENERGY_COST / tool_mult # Use updated cost
                         learned = self.learn_skill(skill)
                         if cfg.DEBUG_AGENT_ACTIONS: print(f"Agent {self.id} gathered {amount} {res_name} (Skill:{self.skills[skill]:.1f}{'+' if learned else ''}). Total: {self.inventory.get(res_name)}")
                         self.action_timer = 0; self.knowledge.add_resource_location(res_type, goal_pos[0], goal_pos[1])
                         inv_full = sum(self.inventory.values()) >= cfg.INVENTORY_CAPACITY; low_e = self.energy < cfg.GATHER_ENERGY_COST * 1.5; gone = resource.is_depleted()
                         if inv_full or low_e or gone:
                              if gone: self.knowledge.remove_resource_location(res_type, goal_pos[0], goal_pos[1])
                              if cfg.DEBUG_AGENT_ACTIONS: print(f"Agent {self.id} finished gathering {res_name} (Full:{inv_full}, LowE:{low_e}, Gone:{gone}).")
                              return True
                         else: return False # Continue gathering
                     else: self.knowledge.remove_resource_location(res_type, goal_pos[0], goal_pos[1]); return True
                 else: return False
            elif action_type == 'Craft':
                 recipe_name = self.action_target['recipe']; details = cfg.RECIPES[recipe_name]
                 skill_req = details.get('skill'); skill_mult = self._get_skill_multiplier(skill_req)
                 duration = cfg.CRAFT_BASE_DURATION / skill_mult
                 if self.action_timer >= duration:
                     if not self._has_ingredients(details['ingredients']) or not self._has_skill_for(details): return True # Final check fail
                     for item, count in details['ingredients'].items():
                         self.inventory[item] = self.inventory.get(item, 0) - count
                         if self.inventory[item] <= 0: del self.inventory[item]
                     if recipe_name == 'Workbench':
                          wb_obj = Resource(cfg.RESOURCE_WORKBENCH, self.x, self.y)
                          if self.world.add_world_object(wb_obj, self.x, self.y):
                               self.knowledge.add_resource_location(cfg.RESOURCE_WORKBENCH, self.x, self.y)
                               if cfg.DEBUG_AGENT_ACTIONS: print(f"Agent {self.id} crafted and placed Workbench at ({self.x}, {self.y}).")
                          else: print(f"Agent {self.id} crafted Workbench but FAILED TO PLACE at ({self.x}, {self.y}). Ingredients lost!")
                     elif recipe_name == 'CookedFood':
                          self.inventory['CookedFood'] = self.inventory.get('CookedFood', 0) + 1
                          if cfg.DEBUG_AGENT_ACTIONS: print(f"Agent {self.id} crafted CookedFood.")
                     else:
                          self.inventory[recipe_name] = self.inventory.get(recipe_name, 0) + 1
                          if cfg.DEBUG_AGENT_ACTIONS: print(f"Agent {self.id} crafted {recipe_name}. Have: {self.inventory.get(recipe_name)}")
                     self.energy -= cfg.CRAFT_ENERGY_COST; learned = self.learn_skill(skill_req) # Use updated cost
                     if cfg.DEBUG_AGENT_ACTIONS and skill_req: print(f"  -> Skill '{skill_req}': {self.skills.get(skill_req, 0):.1f} {'+' if learned else ''}")
                     self.knowledge.add_recipe(recipe_name)
                     return True
                 else: return False
            elif action_type == 'GoToWorkbench':
                 if self._is_at_workbench():
                     if cfg.DEBUG_AGENT_ACTIONS: print(f"Agent {self.id} arrived at Workbench {self.action_target.get('goal')} for purpose: {self.action_target.get('purpose', 'N/A')}")
                     wb_pos = self._get_nearby_workbench_pos();
                     if wb_pos: self.knowledge.add_resource_location(cfg.RESOURCE_WORKBENCH, wb_pos[0], wb_pos[1])
                     return True
                 else: print(f"Agent {self.id} finished path for GoToWorkbench but isn't at WB. Target: {self.action_target.get('goal')}. Failing."); return True
            elif action_type == 'Invent':
                 duration = cfg.INVENT_BASE_DURATION / self.intelligence
                 if self.action_timer >= duration:
                     if cfg.DEBUG_INVENTION: print(f"Agent {self.id} finishing invention cycle.")
                     discovered = self.knowledge.attempt_invention(self.inventory, self.skills); self.energy -= cfg.INVENT_ENERGY_COST # Use updated cost
                     if discovered: print(f"Agent {self.id} successfully invented: {discovered}!")
                     else: print(f"Agent {self.id} tried to invent but discovered nothing.")
                     return True
                 else: return False

            # --- Phase 4: Social Action Execution --- (Uses updated costs implicitly)
            elif action_type == 'Signal':
                signal_type = self.action_target.get('signal_type')
                if signal_type:
                    social_manager.broadcast_signal(self, signal_type, (self.x, self.y))
                    self.energy -= cfg.SIGNAL_ENERGY_COST
                    if cfg.DEBUG_SOCIAL: print(f"Agent {self.id} executed Signal:{signal_type}")
                else: print(f"Agent {self.id}: Error - Signal action target missing signal_type.")
                return True # Signal is instantaneous

            elif action_type == 'Help':
                 target_id = self.action_target.get('target_id'); item_name = self.action_target.get('item')
                 target_agent = self.world.get_agent_by_id(target_id)
                 if not target_agent or target_agent.health <= 0: print(f"Agent {self.id}: Help target {target_id} invalid/dead."); return True
                 if self.inventory.get(item_name, 0) <= 0: print(f"Agent {self.id}: Help item {item_name} missing."); return True
                 dist_sq = (self.x - target_agent.x)**2 + (self.y - target_agent.y)**2
                 if dist_sq > cfg.HELPING_INTERACTION_RADIUS**2: print(f"Agent {self.id}: Help target {target_id} moved out of range."); return True

                 if self.action_timer >= cfg.HELP_BASE_DURATION:
                      self.inventory[item_name] -= 1
                      if self.inventory[item_name] <= 0: del self.inventory[item_name]
                      target_agent.inventory[item_name] = target_agent.inventory.get(item_name, 0) + 1
                      self.energy -= cfg.HELP_ENERGY_COST

                      self.knowledge.update_relationship(target_id, cfg.RELATIONSHIP_CHANGE_HELP)
                      target_agent.knowledge.update_relationship(self.id, cfg.RELATIONSHIP_CHANGE_HELP)

                      if cfg.DEBUG_SOCIAL: print(f"Agent {self.id} successfully helped Agent {target_id} by giving {item_name}.")
                      if target_agent.reacted_to_signal_type == cfg.SIGNAL_HELP_NEEDED_FOOD and item_name in cfg.HELPABLE_ITEMS:
                           self.knowledge.update_relationship(target_id, cfg.RELATIONSHIP_CHANGE_SIGNAL_RESPONSE)
                           target_agent.reacted_to_signal_type = None

                      return True
                 else: return False

            elif action_type == 'Teach':
                 target_id = self.action_target.get('target_id'); skill_name = self.action_target.get('skill')
                 target_agent = self.world.get_agent_by_id(target_id)
                 if not target_agent or target_agent.health <= 0: print(f"Agent {self.id}: Teach target {target_id} invalid/dead."); return True
                 my_level = self.skills.get(skill_name, 0)
                 other_level = target_agent.skills.get(skill_name, 0)
                 if my_level < other_level + cfg.TEACHING_MIN_SKILL_ADVANTAGE: print(f"Agent {self.id}: Teach skill advantage lost for {skill_name}."); return True
                 dist_sq = (self.x - target_agent.x)**2 + (self.y - target_agent.y)**2
                 if dist_sq > cfg.TEACHING_INTERACTION_RADIUS**2: print(f"Agent {self.id}: Teach target {target_id} moved out of range."); return True

                 teach_duration = cfg.TEACH_BASE_DURATION / max(0.5, self.intelligence)
                 if self.action_timer >= teach_duration:
                     boost = cfg.TEACHING_BOOST_FACTOR * max(0.5, self.intelligence)
                     learned = target_agent.learn_skill(skill_name, boost=boost)
                     self.energy -= cfg.TEACH_ENERGY_COST

                     self.knowledge.update_relationship(target_id, cfg.RELATIONSHIP_CHANGE_TEACH)
                     target_agent.knowledge.update_relationship(self.id, cfg.RELATIONSHIP_CHANGE_TEACH)

                     if cfg.DEBUG_SOCIAL:
                          print(f"Agent {self.id} (Skill:{my_level:.1f}) finished teaching {skill_name} to Agent {target_id} (Skill:{target_agent.skills.get(skill_name,0):.1f}, Learned: {learned})")
                     return True
                 else: return False # Still teaching

            else: # Fallback for unknown action types
                print(f"Agent {self.id}: Unknown action execution: {self.current_action}")
                return True

        except Exception as e: # General error handling during action logic
            print(f"!!! Error performing action logic {self.current_action} for agent {self.id}: {e}"); traceback.print_exc()
            return True # Fail action to prevent loops


    # --- REVISED _verify_position_for_action ---
    def _verify_position_for_action(self, action_type, agents):
        """ Checks if the agent is in the correct location to start/continue the action. Ver 3: Explicit adjacency check. """
        current_pos = (self.x, self.y)
        expected_stand_pos = self.action_target.get('stand') if self.action_target else None
        goal_pos = self.action_target.get('goal') if self.action_target else None

        # 1. Check if at designated stand position (always valid if provided and matched)
        if expected_stand_pos and current_pos == expected_stand_pos:
            # If it's a workbench action, double-check WB is actually nearby from stand pos
            if action_type in ['Craft', 'Invent'] and self.action_target and self.action_target.get('requires_workbench'):
                 if not self._is_at_workbench():
                      if cfg.DEBUG_AGENT_ACTIONS: print(f"Agent {self.id}: At stand pos, but no WB nearby for {self.current_action}.")
                      return False
            return True # At the specific planned standing spot

        # 2. Check proximity/adjacency based on action type and goal
        if not goal_pos: # If no goal, cannot verify proximity (unless action doesn't need it)
             # Actions that DON'T need a goal/stand check (happen locally)
             if action_type in ["Rest", "Signal"] or \
                (action_type == "Craft" and not (self.action_target and self.action_target.get('requires_workbench'))):
                 return True
             else: # Action needed a goal for verification, but none exists
                  if cfg.DEBUG_AGENT_ACTIONS: print(f"Agent {self.id}: Position error - Action {action_type} needs goal verification, but no goal found. Target: {self.action_target}")
                  return False

        # Calculate Chebyshev distance (max coordinate difference)
        chebyshev_dist = 0
        if goal_pos:
            chebyshev_dist = max(abs(self.x - goal_pos[0]), abs(self.y - goal_pos[1]))

        # --- Action-Specific Checks ---

        # A. Actions requiring strict adjacency (Chebyshev dist = 1) to goal
        strict_adjacency_actions = ['GatherWood', 'GatherStone', 'SatisfyThirst', 'SatisfyHunger']
        is_strict_action = action_type in strict_adjacency_actions

        # Check if the goal itself is non-walkable (requires standing adjacent)
        goal_is_non_walkable = False
        if goal_pos and 0 <= goal_pos[0] < self.world.width and 0 <= goal_pos[1] < self.world.height:
            resource_at_goal = self.world.get_resource(goal_pos[0], goal_pos[1])
            is_water_goal = self.world.get_terrain(goal_pos[0], goal_pos[1]) == cfg.TERRAIN_WATER
            if (resource_at_goal and resource_at_goal.blocks_walk) or is_water_goal:
                goal_is_non_walkable = True
        # Also treat food as requiring adjacency if it's not walkable itself (config says it isn't, but check just in case)
        elif action_type == 'SatisfyHunger' and goal_pos and \
             (0 <= goal_pos[0] < self.world.width and 0 <= goal_pos[1] < self.world.height) and \
             self.world.walkability_matrix[goal_pos[1], goal_pos[0]] == 0:
             goal_is_non_walkable = True


        if is_strict_action and goal_is_non_walkable:
            if chebyshev_dist == 1:
                return True # Standing exactly adjacent
            else:
                if cfg.DEBUG_AGENT_ACTIONS: print(f"Agent {self.id}: Position error - Action {action_type} requires strict adjacency (dist=1) to non-walkable goal {goal_pos}. Current dist={chebyshev_dist}. Current: {current_pos}")
                return False

        # B. Actions requiring proximity based on radius (Workbench, Help, Teach)
        proximity_actions = {}
        # Define the key for workbench craft actions consistently
        wb_craft_key = 'CraftWB' # Define a key for workbench crafting
        if action_type == 'Craft' and self.action_target and self.action_target.get('requires_workbench'):
             proximity_actions[wb_craft_key] = cfg.WORKBENCH_INTERACTION_RADIUS
        elif action_type == 'Invent':
             proximity_actions['Invent'] = cfg.WORKBENCH_INTERACTION_RADIUS
        elif action_type == 'Help':
             proximity_actions['Help'] = cfg.HELPING_INTERACTION_RADIUS
        elif action_type == 'Teach':
             proximity_actions['Teach'] = cfg.TEACHING_INTERACTION_RADIUS

        # Check proximity based actions using the defined keys
        action_key_to_check = wb_craft_key if action_type == 'Craft' and self.action_target and self.action_target.get('requires_workbench') else action_type
        if action_key_to_check in proximity_actions:
            required_radius = proximity_actions[action_key_to_check]
            if chebyshev_dist <= required_radius:
                 # If workbench action, also verify a WB is actually nearby
                 if action_key_to_check in [wb_craft_key, 'Invent']:
                     if not self._is_at_workbench():
                          if cfg.DEBUG_AGENT_ACTIONS: print(f"Agent {self.id}: Position OK relative to goal, but no WB nearby for {self.current_action}.")
                          return False
                 return True # Within required radius
            else:
                 if cfg.DEBUG_AGENT_ACTIONS: print(f"Agent {self.id}: Position error - Action {action_key_to_check} requires proximity radius {required_radius} to goal {goal_pos}. Current dist={chebyshev_dist}. Current: {current_pos}")
                 return False

        # C. Special case: GoToWorkbench - need to be near *a* workbench, not necessarily the specific goal WB if multiple exist
        if action_type == 'GoToWorkbench':
            if self._is_at_workbench(): # Check using radius
                 return True
            else:
                 if cfg.DEBUG_AGENT_ACTIONS: print(f"Agent {self.id}: Position error - Arrived for GoToWorkbench but not near any workbench. Current: {current_pos}, Goal was: {goal_pos}")
                 return False

        # D. Actions allowing standing ON the goal tile if it's walkable (e.g., SatisfyHunger for berries, non-blocking resources)
        if is_strict_action and not goal_is_non_walkable:
             # Allow standing ON or ADJACENT
             if chebyshev_dist <= 1:
                 return True
             else:
                 if cfg.DEBUG_AGENT_ACTIONS: print(f"Agent {self.id}: Position error - Action {action_type} requires standing on or adjacent (dist<=1) to walkable goal {goal_pos}. Current dist={chebyshev_dist}. Current: {current_pos}")
                 return False

        # E. Fallback for actions not covered above (Wander arrival, potentially others)
        if cfg.DEBUG_AGENT_ACTIONS: print(f"Agent {self.id}: Position verification reached fallback for action {action_type}. Assuming OK if no specific check failed. Current: {current_pos}, Goal: {goal_pos}, Stand: {expected_stand_pos}")
        return True # Default assumption if no specific check failed.


    # --- Methods below this line are unchanged from previous refinement ---

    def _complete_action(self):
        self.current_action = None; self.action_target = None
        self.current_path = []; self.action_timer = 0.0

    def _handle_death(self):
        if cfg.DEBUG_AGENT_CHOICE:
            print(f"Agent {self.id} has died at ({self.x}, {self.y}). Needs(Hl,H,T,E): ({self.health:.0f},{self.hunger:.0f},{self.thirst:.0f},{self.energy:.0f})")

    def learn_skill(self, skill_name, boost=1.0):
        if not skill_name: return False
        if skill_name not in self.skills: self.skills[skill_name] = 0.0
        current_level = self.skills[skill_name]
        if current_level >= cfg.MAX_SKILL_LEVEL: return False
        gain_factor = max(0.05, (1.0 - (current_level / (cfg.MAX_SKILL_LEVEL + 1)))**1.2)
        increase = cfg.SKILL_INCREASE_RATE * boost * gain_factor
        increase = max(0.01 * boost, increase)
        new_level = min(cfg.MAX_SKILL_LEVEL, current_level + increase)
        if new_level > current_level + 0.001:
            self.skills[skill_name] = new_level
            return True
        return False

    def _get_skill_multiplier(self, skill_name):
        if not skill_name or skill_name not in self.skills: return 1.0
        level = self.skills.get(skill_name, 0)
        max_bonus = 1.5; exponent = 0.7
        multiplier = 1.0 + max_bonus * (level / cfg.MAX_SKILL_LEVEL)**exponent
        return max(0.1, multiplier)

    def _has_ingredients(self, ingredients):
        if not ingredients: return True
        return all(self.inventory.get(item, 0) >= req for item, req in ingredients.items())

    def _has_skill_for(self, recipe_details):
        skill = recipe_details.get('skill')
        min_level = recipe_details.get('min_level', 0)
        return not skill or self.skills.get(skill, 0) >= min_level

    def _check_passive_learning(self, agents):
        for other in agents:
             if other.id == self.id or other.health <= 0: continue
             dist_sq = (self.x - other.x)**2 + (self.y - other.y)**2
             if dist_sq <= cfg.PASSIVE_LEARN_RADIUS_SQ:
                 action = other.current_action
                 skill_to_learn = None
                 if action:
                      action_type = action.split(':')[0]
                      if action_type == 'GatherWood': skill_to_learn = 'GatherWood'
                      elif action_type == 'GatherStone': skill_to_learn = 'GatherStone'
                      elif action_type == 'Craft':
                           recipe_name = other.action_target.get('recipe') if other.action_target else None
                           if recipe_name and recipe_name in cfg.RECIPES:
                                skill_to_learn = cfg.RECIPES[recipe_name].get('skill')
                 if skill_to_learn and self.skills.get(skill_to_learn, 0) < cfg.MAX_SKILL_LEVEL:
                     rel_factor = max(0.5, 1.0 + self.knowledge.get_relationship(other.id) * 0.5)
                     if random.random() < cfg.PASSIVE_LEARN_CHANCE * rel_factor:
                         learned = self.learn_skill(skill_to_learn, boost=cfg.PASSIVE_LEARN_BOOST)
                         if learned and cfg.DEBUG_SOCIAL:
                              print(f"Agent {self.id} passively learned {skill_to_learn} -> {self.skills[skill_to_learn]:.2f} from observing Agent {other.id}")

    def _find_best_resource_location(self, resource_type, max_search_dist=cfg.AGENT_VIEW_RADIUS):
        best_pos, best_stand_pos, min_dist_sq = None, None, float('inf')
        display_name = cfg.RESOURCE_INFO.get(resource_type, {}).get('name','?')
        if resource_type == cfg.RESOURCE_WATER: display_name = "Water"
        known_locations = self.knowledge.get_known_locations(resource_type)
        locations_to_remove = []
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
        search_threshold_sq = (max_search_dist * 0.7)**2
        if (not best_stand_pos or min_dist_sq > search_threshold_sq):
            g_pos, s_pos, bfs_dist = self.world.find_nearest_resource(self.x, self.y, resource_type, max_dist=max_search_dist)
            if s_pos:
                 if resource_type != cfg.RESOURCE_WATER: self.knowledge.add_resource_location(resource_type, g_pos[0], g_pos[1])
                 dist_sq_bfs = (self.x - s_pos[0])**2 + (self.y - s_pos[1])**2
                 if dist_sq_bfs < min_dist_sq:
                      min_dist_sq = dist_sq_bfs; best_pos = g_pos; best_stand_pos = s_pos
        final_dist = math.sqrt(min_dist_sq) if best_stand_pos else float('inf')
        return best_pos, best_stand_pos, final_dist

    def _find_stand_pos_for_resource(self, res_x, res_y):
        if self.world.get_terrain(res_x, res_y) == cfg.TERRAIN_WATER:
             return self._find_adjacent_walkable(res_x, res_y, self.world.walkability_matrix)
        resource = self.world.get_resource(res_x, res_y)
        if not resource: return None
        if self.world.walkability_matrix[res_y, res_x] == 1: return (res_x, res_y)
        else: return self._find_adjacent_walkable(res_x, res_y, self.world.walkability_matrix)

    def _find_stand_pos_for_agent(self, target_x, target_y, agents):
         other_agent_positions = [(a.x, a.y) for a in agents if a != self and a.health > 0 and (a.x, a.y) != (target_x, target_y)]
         temp_walkability = self.world.update_walkability(agent_positions=other_agent_positions)
         return self._find_adjacent_walkable(target_x, target_y, temp_walkability)

    def _is_at_workbench(self):
        return self._is_near_resource_type(cfg.RESOURCE_WORKBENCH, cfg.WORKBENCH_INTERACTION_RADIUS)

    def _get_nearby_workbench_pos(self):
        return self._find_nearest_resource_pos_in_radius(cfg.RESOURCE_WORKBENCH, cfg.WORKBENCH_INTERACTION_RADIUS)

    def _is_near_resource_type(self, res_type, radius):
         for y in range(max(0, self.y-radius), min(self.world.height, self.y+radius+1)):
              for x in range(max(0, self.x-radius), min(self.world.width, self.x+radius+1)):
                  res = self.world.get_resource(x, y)
                  if res and res.type == res_type: return True
         return False

    def _find_nearest_resource_pos_in_radius(self, res_type, radius):
         min_dist_sq = float('inf'); found_pos = None
         for r in range(radius + 1):
              for dy in range(-r, r + 1):
                   for dx in range(-r, r + 1):
                        if max(abs(dx), abs(dy)) != r: continue
                        x, y = self.x + dx, self.y + dy
                        if 0 <= x < self.world.width and 0 <= y < self.world.height:
                             res = self.world.get_resource(x, y)
                             if res and res.type == res_type:
                                  dist_sq = dx*dx + dy*dy
                                  if dist_sq < min_dist_sq:
                                       min_dist_sq = dist_sq; found_pos = (x, y)
              if found_pos: return found_pos
         return None

    def _has_workbench_knowledge(self):
         return len(self.knowledge.get_known_locations(cfg.RESOURCE_WORKBENCH)) > 0

    def _plan_path(self, target_pos, agents):
        start_pos = (self.x, self.y)
        if not target_pos or start_pos == target_pos: return []
        tx, ty = target_pos
        if not (0 <= tx < self.world.width and 0 <= ty < self.world.height): return None
        other_agent_positions = [(a.x, a.y) for a in agents if a != self and a.health > 0]
        temp_walkability = self.world.update_walkability(agent_positions=other_agent_positions)
        final_start = start_pos
        if temp_walkability[start_pos[1], start_pos[0]] == 0:
            adj_start = self._find_adjacent_walkable(start_pos[0], start_pos[1], temp_walkability)
            if adj_start: final_start = adj_start
            else: 
                if cfg.DEBUG_PATHFINDING: print(f"Agent {self.id}: Start {start_pos} blocked, no adjacent walkable. Path fail."); return None
        final_target = target_pos
        if temp_walkability[ty, tx] == 0:
            adj_target = self._find_adjacent_walkable(tx, ty, temp_walkability)
            if adj_target: final_target = adj_target
            else: 
                if cfg.DEBUG_PATHFINDING: print(f"Agent {self.id}: Target {target_pos} blocked, no adjacent walkable. Path fail."); return None
        path_nodes = find_path(temp_walkability, final_start, final_target)
        if path_nodes is None: return None
        else:
            path_coords = [(node.x, node.y) for node in path_nodes]
            if final_start != start_pos and path_coords: path_coords.insert(0, start_pos)
            if cfg.DEBUG_PATHFINDING and path_coords: print(f"Agent {self.id}: Path found from {start_pos}(adj:{final_start}) to {target_pos}(adj:{final_target}) len {len(path_coords)}")
            return path_coords

    def _find_adjacent_walkable(self, x, y, walkability_matrix):
        neighbors = [(0,-1), (0,1), (1,0), (-1,0), (1,-1), (1,1), (-1,1), (-1,-1)]
        random.shuffle(neighbors)
        for dx, dy in neighbors:
            nx, ny = x + dx, y + dy
            if 0 <= nx < self.world.width and 0 <= ny < self.world.height and walkability_matrix[ny, nx] == 1:
                return (nx, ny)
        return None

    def perceive_signal(self, signal: Signal):
         self.pending_signal = signal
         if cfg.DEBUG_SOCIAL: print(f"Agent {self.id} perceived signal '{signal.type}' from {signal.sender_id} at {signal.position}")

    def _process_signals(self, agents, social_manager):
         if not self.pending_signal: return
         signal = self.pending_signal; sender_id = signal.sender_id; signal_type = signal.type; signal_pos = signal.position
         self.pending_signal = None
         if self.reacted_to_signal_type == signal_type: return
         self.reacted_to_signal_type = signal_type
         if cfg.DEBUG_SOCIAL: print(f"Agent {self.id} processing signal '{signal_type}' from {sender_id}")
         sender_agent = self.world.get_agent_by_id(sender_id)
         if not sender_agent: return
         rel = self.knowledge.get_relationship(sender_id)
         if signal_type == cfg.SIGNAL_HELP_NEEDED_FOOD:
             if self.sociability > 0.4 and rel > cfg.HELPING_MIN_RELATIONSHIP and \
                self.hunger < cfg.MAX_HUNGER * cfg.HELPING_SELF_NEED_THRESHOLD: # Use updated threshold
                 item_to_give = next((item for item in cfg.HELPABLE_ITEMS if self.inventory.get(item, 0) > 0), None)
                 if item_to_give:
                     if cfg.DEBUG_SOCIAL: print(f"Agent {self.id} deciding to help Agent {sender_id} with {item_to_give} due to signal.")
                     self._interrupt_and_set_action(f"Help:{sender_id}:{item_to_give}", agents)
                     return
         elif signal_type == cfg.SIGNAL_FOUND_FOOD:
              if self.hunger > cfg.MAX_HUNGER * 0.5 and rel >= -0.1:
                   is_known_food = any(loc == signal_pos for loc in self.knowledge.get_known_locations(cfg.RESOURCE_FOOD))
                   if not is_known_food:
                        if cfg.DEBUG_SOCIAL: print(f"Agent {self.id} investigating potential food at {signal_pos} due to signal from {sender_id}.")
                        stand_pos = self._find_adjacent_walkable(signal_pos[0], signal_pos[1], self.world.walkability_matrix)
                        if stand_pos:
                             target_data = {'type': 'MoveToSignal', 'goal': signal_pos, 'stand': stand_pos}
                             self._interrupt_and_set_action(f"MoveToSignal:{signal_pos[0]}:{signal_pos[1]}", agents, target_data)
                             return
         elif signal_type == cfg.SIGNAL_DANGER_NEAR:
              if cfg.DEBUG_SOCIAL: print(f"Agent {self.id} attempting to flee from danger signal at {signal_pos} from {sender_id}.")
              for _ in range(5):
                   dx = random.randint(-cfg.WANDER_RADIUS, cfg.WANDER_RADIUS); dy = random.randint(-cfg.WANDER_RADIUS, cfg.WANDER_RADIUS)
                   away_x = self.x - signal_pos[0]; away_y = self.y - signal_pos[1]
                   norm = math.sqrt(away_x**2 + away_y**2)
                   if norm > 0: dx += int(away_x / norm * 2); dy += int(away_y / norm * 2)
                   wx = max(0, min(self.world.width - 1, self.x + dx)); wy = max(0, min(self.world.height - 1, self.y + dy))
                   if self.world.walkability_matrix[wy, wx] == 1 and self.world.terrain_map[wy,wx] == cfg.TERRAIN_GROUND:
                       target_data = {'type': 'Wander', 'goal': (wx, wy), 'stand': (wx, wy)}
                       self._interrupt_and_set_action("Wander", agents, target_data)
                       return
              self._interrupt_and_set_action("Wander", agents) # Fallback wander
         self.reacted_to_signal_type = None

    def _interrupt_and_set_action(self, action_name, agents, action_target_data=None):
         if cfg.DEBUG_AGENT_ACTIONS: print(f"Agent {self.id} interrupting '{self.current_action}' for '{action_name}'")
         self._complete_action()
         self.current_action = action_name
         if not action_target_data:
              feasible, target_data = self._check_action_feasibility(action_name, agents)
              if feasible: self.action_target = target_data
              else:
                   print(f"Agent {self.id}: Failed feasibility check for interruption action {action_name}. Reverting to Idle.")
                   self.current_action = "Idle"; self.action_target = None; return
         else: self.action_target = action_target_data
         self._plan_path_for_action(agents)

    def _find_nearby_agents(self, agents, radius):
         nearby = []
         min_x=self.x-radius; max_x=self.x+radius; min_y=self.y-radius; max_y=self.y+radius
         for other in agents:
              # Ensure we are checking against the current list of *living* agents
              if other.id != self.id and other.health > 0 and min_x <= other.x <= max_x and min_y <= other.y <= max_y:
                  nearby.append(other)
         return nearby