# agent.py
import random
import math
import config as cfg
from pathfinding_utils import find_path
from knowledge import KnowledgeSystem

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
        self.action_target = None # e.g., coordinates (x,y) or target agent ID
        self.current_path = [] # List of (x,y) tuples for movement
        self.action_timer = 0.0 # Time spent on current action segment (e.g., gathering)

        # --- Phase 1 Additions ---
        self.last_known_water_pos = None # Simple memory
        self.last_known_food_pos = None # Simple memory

        # --- Phase 2 Additions ---
        self.inventory = {} # item_name: count
        self.skills = { # skill_name: level (0-100)
            'GatherWood': cfg.INITIAL_SKILL_LEVEL,
            'GatherStone': cfg.INITIAL_SKILL_LEVEL,
            'BasicCrafting': cfg.INITIAL_SKILL_LEVEL,
            # Add more skills
        }

        # --- Phase 3 Additions ---
        self.knowledge = KnowledgeSystem(self.id) # More structured knowledge
        # Add attributes like Curiosity, Intelligence?

        # --- Phase 4 Additions ---
        self.sociability = random.uniform(0.1, 0.9) # Example personality trait
        self.pending_signal = None # Signal received but not yet processed

    def update(self, dt_real_seconds, agents, social_manager):
        dt_sim_seconds = dt_real_seconds * cfg.SIMULATION_SPEED_FACTOR

        self._update_needs(dt_sim_seconds)
        self._process_signals() # Phase 4+

        if self.health <= 0:
            self._handle_death()
            return # Agent is dead, no further updates

        # Action execution / continuation
        if self.current_action:
            action_complete = self._perform_action(dt_sim_seconds, agents, social_manager)
            if action_complete:
                self._complete_action()
        else:
            # Choose a new action if idle
            self._choose_action(agents, social_manager)


    def _update_needs(self, dt_sim_seconds):
        # Decay needs over time
        self.hunger = min(cfg.MAX_HUNGER, self.hunger + cfg.HUNGER_INCREASE_RATE * dt_sim_seconds)
        self.thirst = min(cfg.MAX_THIRST, self.thirst + cfg.THIRST_INCREASE_RATE * dt_sim_seconds)

        if self.current_action != "Resting":
            self.energy = max(0, self.energy - cfg.ENERGY_DECAY_RATE * dt_sim_seconds)
        else:
            # Resting restores energy and potentially health
            self.energy = min(cfg.MAX_ENERGY, self.energy + cfg.ENERGY_REGEN_RATE * dt_sim_seconds)
            if self.energy > cfg.MAX_ENERGY * 0.8: # Only regen health if well-rested
                self.health = min(cfg.MAX_HEALTH, self.health + cfg.HEALTH_REGEN_RATE * dt_sim_seconds)

        # Health drain if needs critical
        if self.hunger >= cfg.MAX_HUNGER * 0.9 or self.thirst >= cfg.MAX_THIRST * 0.9 or self.energy <= 0:
            self.health -= 0.5 * dt_sim_seconds # Gradual health loss

        # Clamp health
        self.health = max(0, self.health)


    def _choose_action(self, agents, social_manager):
        """ Basic Utility AI Decision Making """
        utilities = {}

        # --- Calculate Utility for Basic Needs ---
        utilities['SatisfyThirst'] = self.thirst / cfg.MAX_THIRST
        utilities['SatisfyHunger'] = self.hunger / cfg.MAX_HUNGER
        utilities['Rest'] = (cfg.MAX_ENERGY - self.energy) / cfg.MAX_ENERGY if self.energy < cfg.MAX_ENERGY * 0.7 else 0 # Only rest if tired

        # --- Phase 2+: Resource Gathering ---
        # Need Axe for efficient wood gathering? Example condition.
        has_axe = self.inventory.get('CrudeAxe', 0) > 0
        wood_gather_utility = 0.2 * (1 - (self.inventory.get('Wood', 0) / 10)) # Gather if low on wood (goal: have 10)
        utilities['GatherWood'] = wood_gather_utility * (1.5 if has_axe else 0.5) # Boost if has axe

        stone_gather_utility = 0.2 * (1 - (self.inventory.get('Stone', 0) / 5)) # Goal: have 5 stone
        utilities['GatherStone'] = stone_gather_utility

        # --- Phase 2+: Crafting ---
        # Check if craftable items are known and ingredients available
        best_craft_utility = 0
        best_craft_recipe = None
        for recipe_name in self.knowledge.known_recipes: # Use knowledge system
             details = cfg.RECIPES.get(recipe_name)
             if details and self._has_ingredients(details['ingredients']) and self._has_skill_for(details):
                 # Simple utility: craft if haven't crafted recently, or if needed for goal
                 utility = 0.3 # Base utility for crafting something known
                 # Example: Higher utility if we need an axe and don't have one
                 if recipe_name == 'CrudeAxe' and not has_axe:
                     utility = 0.8
                 if utility > best_craft_utility:
                     best_craft_utility = utility
                     best_craft_recipe = recipe_name
        if best_craft_recipe:
             utilities['Craft:' + best_craft_recipe] = best_craft_utility

        # --- Phase 3+: Invention ---
        # Add utility for 'Invent' action, perhaps based on Curiosity attribute or idle time
        # Requires a workbench nearby?
        can_invent = True # Placeholder logic: requires workbench nearby?
        if can_invent:
            utilities['Invent'] = 0.1 * random.uniform(0.5, 1.5) # Low base utility, maybe higher if curious/intelligent

        # --- Phase 4+: Social Actions ---
        # Utility for teaching, helping based on perceived needs / social goals
        # Example: Help someone if nearby and in need
        target_to_help = self._find_agent_to_help(agents)
        if target_to_help:
             utilities['Help:'+str(target_to_help.id)] = 0.6 * self.sociability # Help more if sociable

        # Placeholder: Utility for finding someone to teach/learn from?
        # Placeholder: Utility for broadcasting signals?

        # --- Default/Fallback Action ---
        utilities['Wander'] = 0.05 # Very low base utility

        # --- Select Best Action ---
        best_action = None
        max_utility = cfg.UTILITY_THRESHOLD # Minimum threshold to act

        # Sort by utility descending to prioritize highest needs
        sorted_actions = sorted(utilities.items(), key=lambda item: item[1], reverse=True)
        # print(f"Agent {self.id} Utilities: {sorted_actions}") # Debug

        for action, utility in sorted_actions:
            if utility >= max_utility:
                # Check if action is feasible (e.g., resource exists)
                feasible = self._check_action_feasibility(action)
                if feasible:
                    best_action = action
                    break # Found the highest priority feasible action

        # --- Initiate Action ---
        if best_action:
            self.current_action = best_action
            self.action_target = None # Reset target
            self.current_path = [] # Reset path
            print(f"Agent {self.id} choosing action: {best_action} (Utility: {utilities[best_action]:.2f}) Needs(H,T,E): ({self.hunger:.0f},{self.thirst:.0f},{self.energy:.0f})")

            # Set target based on action
            if best_action == 'SatisfyThirst':
                target_pos, stand_pos, dist = self.world.find_nearest_resource(self.x, self.y, cfg.RESOURCE_WATER)
                if target_pos:
                    self.action_target = {'type': 'location', 'goal': target_pos, 'stand': stand_pos}
                    self.current_path = self._plan_path(stand_pos)
            elif best_action == 'SatisfyHunger':
                target_pos, stand_pos, dist = self.world.find_nearest_resource(self.x, self.y, cfg.RESOURCE_FOOD)
                if target_pos:
                    self.action_target = {'type': 'location', 'goal': target_pos, 'stand': stand_pos}
                    self.current_path = self._plan_path(stand_pos)
                    self.knowledge.add_resource_location(cfg.RESOURCE_FOOD, target_pos[0], target_pos[1]) # Remember
            elif best_action == 'GatherWood':
                 target_pos, stand_pos, dist = self.world.find_nearest_resource(self.x, self.y, cfg.RESOURCE_WOOD)
                 if target_pos:
                     self.action_target = {'type': 'location', 'goal': target_pos, 'stand': stand_pos}
                     self.current_path = self._plan_path(stand_pos)
                     self.knowledge.add_resource_location(cfg.RESOURCE_WOOD, target_pos[0], target_pos[1])
            elif best_action == 'GatherStone':
                 target_pos, stand_pos, dist = self.world.find_nearest_resource(self.x, self.y, cfg.RESOURCE_STONE)
                 if target_pos:
                     self.action_target = {'type': 'location', 'goal': target_pos, 'stand': stand_pos}
                     self.current_path = self._plan_path(stand_pos)
                     self.knowledge.add_resource_location(cfg.RESOURCE_STONE, target_pos[0], target_pos[1])
            elif best_action.startswith('Craft:'):
                 # For now, craft anywhere. Phase 3 needs workbench check.
                 self.action_target = {'type': 'craft', 'recipe': best_action.split(':')[1]}
                 # No movement needed unless requires workbench
            elif best_action == 'Invent':
                 # For now, invent anywhere. Needs workbench check later.
                 self.action_target = {'type': 'invent'}
                 # No movement needed
            elif best_action.startswith('Help:'):
                target_id = int(best_action.split(':')[1])
                target_agent = next((a for a in agents if a.id == target_id), None)
                if target_agent:
                    self.action_target = {'type': 'agent', 'goal': target_agent.id, 'stand': (target_agent.x, target_agent.y)} # Go near target
                    self.current_path = self._plan_path((target_agent.x, target_agent.y)) # Path to target's current pos
            elif best_action == 'Rest' or best_action == 'Wander':
                self.action_target = {'type': best_action.lower()}
                if best_action == 'Wander':
                    # Pick a random nearby walkable spot
                    for _ in range(10): # Try a few times
                         wx = self.x + random.randint(-cfg.WANDER_RADIUS, cfg.WANDER_RADIUS)
                         wy = self.y + random.randint(-cfg.WANDER_RADIUS, cfg.WANDER_RADIUS)
                         if 0 <= wx < self.world.width and 0 <= wy < self.world.height and self.world.walkability_matrix[wy, wx] == 1:
                              self.action_target['stand'] = (wx, wy)
                              self.current_path = self._plan_path((wx, wy))
                              break
            # If failed to set a path/target for a chosen action, clear it
            if 'stand' in self.action_target and not self.current_path and (self.x, self.y) != self.action_target['stand']:
                 print(f"Agent {self.id}: Could not find path for action {best_action}, clearing action.")
                 self.current_action = None
                 self.action_target = None
            elif not self.action_target:
                 # print(f"Agent {self.id}: No target found for action {best_action}, clearing action.")
                 self.current_action = None


    def _check_action_feasibility(self, action_name):
        """ Checks if resources/targets exist for an action """
        if action_name == 'SatisfyThirst':
            target_pos, _, _ = self.world.find_nearest_resource(self.x, self.y, cfg.RESOURCE_WATER)
            return target_pos is not None
        elif action_name == 'SatisfyHunger':
            target_pos, _, _ = self.world.find_nearest_resource(self.x, self.y, cfg.RESOURCE_FOOD)
            return target_pos is not None
        elif action_name == 'GatherWood':
             target_pos, _, _ = self.world.find_nearest_resource(self.x, self.y, cfg.RESOURCE_WOOD)
             return target_pos is not None
        elif action_name == 'GatherStone':
             target_pos, _, _ = self.world.find_nearest_resource(self.x, self.y, cfg.RESOURCE_STONE)
             return target_pos is not None
        elif action_name.startswith('Craft:'):
             recipe_name = action_name.split(':')[1]
             details = cfg.RECIPES.get(recipe_name)
             # Phase 3+: Check for workbench if details['workbench'] is True
             return details and self.knowledge.knows_recipe(recipe_name) and self._has_ingredients(details['ingredients']) and self._has_skill_for(details)
        elif action_name == 'Invent':
             # Phase 3+: Check for workbench nearby? Check inventory has > 1 item type?
             return len(self.inventory) >= 2 # Simple check: need items to combine
        elif action_name.startswith('Help:'):
             # Feasibility checked during utility calculation (finding target)
             return True
        # Wander, Rest are always feasible (unless maybe trapped)
        return True


    def _plan_path(self, target_pos):
        """ Finds a path using A* """
        if not target_pos or (self.x, self.y) == target_pos:
            return [] # Already there or no target

        path = find_path(self.world.walkability_matrix, (self.x, self.y), target_pos)
        # print(f"Agent {self.id} Path from {(self.x, self.y)} to {target_pos}: {path}") # Debug
        return path


    def _perform_action(self, dt_sim_seconds, agents, social_manager):
        """ Executes the current action, returns True if completed """
        action_type = self.current_action.split(':')[0] # Get base action type

        # 1. Movement (if path exists)
        if self.current_path:
            target_node = self.current_path[0]
            # Basic diagonal movement towards target node center
            dx = target_node[0] - self.x
            dy = target_node[1] - self.y
            dist = math.sqrt(dx*dx + dy*dy)

            if dist > 0:
                 # Simple movement - assumes 1 cell per tick is okay for now
                 # Better: Move based on speed * dt_sim_seconds
                 move_dist = 1 # Cells per action step (adjust for speed)
                 self.x = target_node[0]
                 self.y = target_node[1]
                 self.energy -= cfg.MOVE_ENERGY_COST * move_dist # Cost per cell moved

            # Check if reached the node
            # Need more robust position checking if using float positions/speeds
            if self.x == target_node[0] and self.y == target_node[1]:
                self.current_path.pop(0) # Move to next node in path

            return False # Movement is ongoing until path is empty

        # 2. Action at Target Location
        self.action_timer += dt_sim_seconds
        action_duration = 1.0 # Seconds per action unit (e.g., gather 1 wood)

        # --- Phase 1 Actions ---
        if self.current_action == 'SatisfyThirst':
            target_x, target_y = self.action_target['goal']
            amount = self.world.consume_resource_at(target_x, target_y, 1) # Consume from water tile
            if amount > 0:
                self.thirst = max(0, self.thirst - cfg.DRINK_THIRST_REDUCTION)
                print(f"Agent {self.id} drank. Thirst: {self.thirst:.0f}")
            return True # Drink is instant for now

        elif self.current_action == 'SatisfyHunger':
            target_x, target_y = self.action_target['goal']
            resource = self.world.get_resource(target_x, target_y)
            if resource and resource.type == cfg.RESOURCE_FOOD and not resource.is_depleted():
                 amount = self.world.consume_resource_at(target_x, target_y, 1)
                 if amount > 0:
                     self.hunger = max(0, self.hunger - cfg.EAT_HUNGER_REDUCTION)
                     self.learn_skill('GatherFood', 0.1) # Tiny passive learning? Or make eating a skill?
                     print(f"Agent {self.id} ate. Hunger: {self.hunger:.0f}")
                 return True # Eat is instant
            else:
                 print(f"Agent {self.id} failed to eat at {(target_x, target_y)}")
                 self.knowledge.known_resource_locations[cfg.RESOURCE_FOOD].remove((target_x, target_y)) # Forget depleted/gone source
                 return True # Action failed, but complete

        elif self.current_action == 'Resting':
             # Resting continues until energy is full or interrupted by high need
             if self.energy >= cfg.MAX_ENERGY or self.thirst > cfg.MAX_THIRST * 0.9 or self.hunger > cfg.MAX_HUNGER * 0.9:
                 return True
             return False # Continue resting

        elif self.current_action == 'Wander':
             return True # Wander completes once destination reached (path empty)

        # --- Phase 2 Actions ---
        elif self.current_action == 'GatherWood':
             target_x, target_y = self.action_target['goal']
             resource = self.world.get_resource(target_x, target_y)
             if resource and resource.type == cfg.RESOURCE_WOOD and not resource.is_depleted():
                 # Simulate gathering time
                 if self.action_timer >= action_duration / self._get_skill_multiplier('GatherWood'):
                     amount = self.world.consume_resource_at(target_x, target_y, 1)
                     if amount > 0:
                         self.inventory['Wood'] = self.inventory.get('Wood', 0) + amount
                         self.energy -= cfg.GATHER_ENERGY_COST
                         self.learn_skill('GatherWood') # Learn by doing
                         print(f"Agent {self.id} gathered Wood. Total: {self.inventory['Wood']}. Skill: {self.skills.get('GatherWood',0):.1f}")
                         self.action_timer = 0 # Reset timer for next unit
                         # Decide if want to gather more or stop
                         if self.inventory['Wood'] >= 10: # Stop if goal reached
                              return True
                         else:
                              return False # Continue gathering from this source
                     else: return True # Resource depleted during attempt
                 else: return False # Still gathering
             else:
                 # Target resource gone/depleted
                 if resource: self.knowledge.known_resource_locations.get(cfg.RESOURCE_WOOD, []).remove((target_x, target_y))
                 return True # Action failed/complete

        elif self.current_action == 'GatherStone':
             target_x, target_y = self.action_target['goal']
             resource = self.world.get_resource(target_x, target_y)
             if resource and resource.type == cfg.RESOURCE_STONE and not resource.is_depleted():
                 if self.action_timer >= action_duration / self._get_skill_multiplier('GatherStone'):
                     amount = self.world.consume_resource_at(target_x, target_y, 1)
                     if amount > 0:
                         self.inventory['Stone'] = self.inventory.get('Stone', 0) + amount
                         self.energy -= cfg.GATHER_ENERGY_COST
                         self.learn_skill('GatherStone')
                         print(f"Agent {self.id} gathered Stone. Total: {self.inventory['Stone']}. Skill: {self.skills.get('GatherStone',0):.1f}")
                         self.action_timer = 0
                         if self.inventory['Stone'] >= 5: return True # Stop if goal reached
                         else: return False
                     else: return True
                 else: return False
             else:
                 if resource: self.knowledge.known_resource_locations.get(cfg.RESOURCE_STONE, []).remove((target_x, target_y))
                 return True

        elif action_type == 'Craft':
             recipe_name = self.action_target['recipe']
             details = cfg.RECIPES[recipe_name]
             if self.action_timer >= action_duration * 2 / self._get_skill_multiplier(details['skill']): # Crafting takes longer
                 # Consume ingredients
                 for item, count in details['ingredients'].items():
                     self.inventory[item] = self.inventory.get(item, 0) - count
                     if self.inventory[item] <= 0:
                         del self.inventory[item]
                 # Add result item
                 self.inventory[recipe_name] = self.inventory.get(recipe_name, 0) + 1
                 self.energy -= cfg.CRAFT_ENERGY_COST
                 self.learn_skill(details['skill'])
                 print(f"Agent {self.id} crafted {recipe_name}. Skill: {self.skills.get(details['skill'],0):.1f}")
                 # Broadcast discovery? (Phase 4)
                 social_manager.broadcast_signal(self, f"Crafted:{recipe_name}", (self.x, self.y))
                 return True # Crafting complete
             else:
                 return False # Still crafting

        # --- Phase 3 Actions ---
        elif self.current_action == 'Invent':
             if self.action_timer >= action_duration * 3: # Invention takes time
                 discovered_recipe = self.knowledge.attempt_invention(self.inventory)
                 self.energy -= cfg.CRAFT_ENERGY_COST # Use crafting cost for inventing too
                 if discovered_recipe:
                     self.knowledge.add_recipe(discovered_recipe)
                     print(f"Agent {self.id} *** INVENTED *** {discovered_recipe}!")
                     # Broadcast?
                     social_manager.broadcast_signal(self, f"Invented:{discovered_recipe}", (self.x, self.y))
                 else:
                     # Failed invention attempt (or no new combo found)
                     # print(f"Agent {self.id} invention attempt yielded nothing.")
                     pass
                 return True # Invention attempt complete
             else:
                 return False # Still thinking...

        # --- Phase 4 Actions ---
        elif action_type == 'Help':
             # Action logic already performed in SocialManager.attempt_helping
             # This state might just be a cooldown or confirmation
             # Or could involve moving to target, then triggering the help effect
             target_id = self.action_target['goal']
             target_agent = next((a for a in agents if a.id == target_id), None)
             if target_agent:
                 # Actual help logic might be here or triggered via social manager when close
                 # For now, assume SocialManager handled it, action complete
                 print(f"Agent {self.id} finished 'Help' action towards {target_id}")
             return True # Complete help action

        # --- Fallback ---
        else:
            print(f"Agent {self.id}: Unknown action {self.current_action}")
            return True # Unknown action, stop doing it

        return True # Default to complete if not handled


    def _complete_action(self):
        """ Cleanup after an action is finished """
        # print(f"Agent {self.id} completed action: {self.current_action}")
        self.current_action = None
        self.action_target = None
        self.current_path = []
        self.action_timer = 0.0

    def _handle_death(self):
        print(f"Agent {self.id} has died at ({self.x}, {self.y}).")
        # Drop inventory? Leave corpse? Remove from simulation?
        # For now, just mark as inactive or remove (simplest)
        # This needs proper handling in the main loop's agent list

    # --- Phase 2: Skills & Crafting Helpers ---
    def learn_skill(self, skill_name, amount=cfg.SKILL_INCREASE_RATE):
        """ Increases skill level, learning by doing """
        if skill_name in self.skills:
            current_level = self.skills[skill_name]
            if current_level < cfg.MAX_SKILL_LEVEL:
                # Diminishing returns?
                increase = amount * (1 - (current_level / cfg.MAX_SKILL_LEVEL))
                self.skills[skill_name] = min(cfg.MAX_SKILL_LEVEL, current_level + increase)
                return True
        # Handle learning a brand new skill (e.g., via teaching)
        elif skill_name not in self.skills:
             self.skills[skill_name] = min(cfg.MAX_SKILL_LEVEL, cfg.INITIAL_SKILL_LEVEL + amount)
             print(f"Agent {self.id} learned NEW skill: {skill_name}")
             return True
        return False


    def _get_skill_multiplier(self, skill_name):
        """ Returns a multiplier based on skill level (e.g., for speed/efficiency) """
        level = self.skills.get(skill_name, 0)
        # Example: 1.0 at level 0, up to 2.0 at max level
        return 1.0 + (level / cfg.MAX_SKILL_LEVEL)

    def _has_ingredients(self, ingredients):
        """ Check inventory for required crafting ingredients """
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
        """ Process incoming signals (simple queue for now) """
        # Basic immediate reaction or queue for processing in update?
        # Queueing allows more complex decision based on current state.
        self.pending_signal = (sender_id, signal_type, position)
        # print(f"Agent {self.id} perceived signal '{signal_type}' from {sender_id}")

    def _process_signals(self):
        """ Handle received signals """
        if not self.pending_signal:
            return

        sender_id, signal_type, position = self.pending_signal
        print(f"Agent {self.id} processing signal '{signal_type}' from {sender_id}")

        # Basic Reactions (can be much more complex)
        if signal_type == 'Danger':
            # Flee from danger source? Simple version: just wander away nervously.
            if self.current_action != 'Resting': # Don't interrupt rest unless urgent?
                self.current_action = 'Wander'
                # Could implement specific 'Flee' behavior later
        elif signal_type == 'FoundFood':
            # If hungry, consider going towards the food signal
            if self.hunger > cfg.MAX_HUNGER * 0.5:
                # Check relationship with sender? Trust level?
                relationship = self.knowledge.get_relationship(sender_id)
                if relationship >= -0.2: # Ignore hostile signals?
                    # If not currently busy with higher priority task
                    current_util = self._get_current_action_utility() # Estimate utility of current task
                    if current_util < self.hunger / cfg.MAX_HUNGER: # Go if food is more important
                         print(f"Agent {self.id} reacting to food signal from {sender_id}")
                         self.current_action = 'SatisfyHunger' # Force re-evaluation, hopefully finds new source
                         self.action_target = {'type': 'location', 'goal': position, 'stand': position} # Approx stand pos
                         self.current_path = self._plan_path(position)
        elif signal_type.startswith("Crafted:") or signal_type.startswith("Invented:"):
             # Learn from others' discoveries?
             item_name = signal_type.split(':')[1]
             if item_name in cfg.RECIPES and not self.knowledge.knows_recipe(item_name):
                  # Learn recipe by observation/announcement
                  # Maybe depends on proximity, intelligence, relationship?
                  dist_sq = (self.x - position[0])**2 + (self.y - position[1])**2
                  if dist_sq < 5**2: # Must be close to learn?
                      relationship = self.knowledge.get_relationship(sender_id)
                      if relationship >= 0: # Learn from non-hostiles
                          self.knowledge.add_recipe(item_name)

        # Clear the processed signal
        self.pending_signal = None

    def decide_to_learn(self, teacher_id, skill_name):
        """ AI decides if it wants to accept teaching """
        # Conditions: Not critically needed elsewhere? Trust teacher?
        if self.thirst > cfg.MAX_THIRST * 0.8 or self.hunger > cfg.MAX_HUNGER * 0.8:
            return False # Too busy with survival

        relationship = self.knowledge.get_relationship(teacher_id)
        if relationship < 0: # Don't learn from hostiles?
            return False

        # Simple: Accept if not busy and trust > 0
        print(f"Agent {self.id} accepts learning '{skill_name}' from {teacher_id}")
        return True

    def _find_agent_to_help(self, agents):
         """ Simple check for nearby agents in critical need """
         nearby_agents = []
         for other in agents:
              if other != self and self.health > 0: # Check living agents only
                   dist = abs(self.x - other.x) + abs(self.y - other.y)
                   if dist < 5: # Check within close range
                       needs_help = other.hunger > cfg.MAX_HUNGER * 0.8 or other.thirst > cfg.MAX_THIRST * 0.8
                       if needs_help:
                            # Check if I have means to help (e.g., food)
                            can_help = self.inventory.get('Food', 0) > 0 and other.hunger > cfg.MAX_HUNGER * 0.8
                            if can_help:
                                relationship = self.knowledge.get_relationship(other.id)
                                if relationship >= 0: # Help neutral or friendly
                                    return other # Found someone to help
         return None

    def _get_current_action_utility(self):
         # Estimate utility of the current action (crude version)
         if not self.current_action: return 0
         if self.current_action == 'SatisfyThirst': return self.thirst / cfg.MAX_THIRST
         if self.current_action == 'SatisfyHunger': return self.hunger / cfg.MAX_HUNGER
         if self.current_action == 'Resting': return (cfg.MAX_ENERGY - self.energy) / cfg.MAX_ENERGY
         # Add estimates for other actions...
         return 0.1 # Default low utility