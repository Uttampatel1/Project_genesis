

import traceback
# world.py
import random
import numpy as np
import config as cfg
from pathfinding_utils import create_walkability_matrix
import pickle # For saving/loading
import time # For simple timing/debug if needed
import math # For distance calculation in arrival check fix

class Resource:
    """ Represents a resource node in the world. """
    def __init__(self, type, x, y, quantity=10, max_quantity=10, regen_rate=cfg.RESOURCE_REGEN_RATE):
        self.type = type
        self.x = x
        self.y = y
        self.quantity = quantity
        self.max_quantity = max_quantity
        # Ensure regen rate comes from config if not overridden, handle potential None case
        self.regen_rate = regen_rate if regen_rate is not None else cfg.RESOURCE_REGEN_RATE
        self.name = cfg.RESOURCE_INFO.get(type, {}).get('name', 'Unknown')
        self.blocks_walk = cfg.RESOURCE_INFO.get(type, {}).get('block_walk', False)

    def consume(self, amount=1):
        """ Consumes a specified amount of the resource, returns amount actually consumed. """
        consumed = min(amount, self.quantity)
        self.quantity -= consumed
        return consumed

    def update(self, dt_sim_seconds):
        """ Updates resource quantity based on regeneration rate. """
        if self.quantity < self.max_quantity and self.regen_rate > 0:
             if random.random() < self.regen_rate * dt_sim_seconds:
                 self.quantity = min(self.max_quantity, self.quantity + 1)

    def is_depleted(self):
        """ Returns True if the resource quantity is zero or less. """
        return self.quantity <= 0

    # --- Persistence Methods ---
    def __getstate__(self):
        """ Define what gets pickled. """
        return (self.type, self.x, self.y, self.quantity, self.max_quantity, self.regen_rate)

    def __setstate__(self, state):
        """ Define how to unpickle and reinitialize derived attributes. """
        self.type, self.x, self.y, self.quantity, self.max_quantity, self.regen_rate = state
        self.name = cfg.RESOURCE_INFO.get(self.type, {}).get('name', 'Unknown')
        self.blocks_walk = cfg.RESOURCE_INFO.get(self.type, {}).get('block_walk', False)
        if self.regen_rate is None: self.regen_rate = cfg.RESOURCE_REGEN_RATE

class World:
    """ Manages the simulation grid, terrain, resources, and time. """
    def __init__(self, width, height):
        self.width = width
        self.height = height
        self.terrain_map = np.full((height, width), cfg.TERRAIN_GROUND, dtype=int)
        self.resource_map = np.full((height, width), None, dtype=object)
        self.resources = []
        self.walkability_matrix = None
        self.simulation_time = 0.0
        self.day_time = 0.0
        self.day_count = 0
        self._generate_world()
        self.update_walkability()

    def _generate_world(self):
        """ Generates the initial terrain and resource layout. """
        print("Generating world terrain and resources...")
        start_time = time.time()

        # 1. Water patches
        print(f"  Placing {cfg.NUM_WATER_PATCHES} water patches...")
        for _ in range(cfg.NUM_WATER_PATCHES):
            size_x = random.randint(cfg.WATER_PATCH_SIZE[0], cfg.WATER_PATCH_SIZE[1])
            size_y = random.randint(cfg.WATER_PATCH_SIZE[0], cfg.WATER_PATCH_SIZE[1])
            start_x = random.randint(0, self.width - size_x)
            start_y = random.randint(0, self.height - size_y)
            self.terrain_map[start_y:start_y+size_y, start_x:start_x+size_x] = cfg.TERRAIN_WATER

        # 2. Place Resources
        print("  Placing resources...")
        resource_placements = {
            cfg.RESOURCE_FOOD: cfg.NUM_FOOD_SOURCES,
            cfg.RESOURCE_WOOD: cfg.NUM_TREES,
            cfg.RESOURCE_STONE: cfg.NUM_ROCKS,
            cfg.RESOURCE_WORKBENCH: cfg.NUM_INITIAL_WORKBENCHES
        }

        for res_type, count in resource_placements.items():
            if count == 0: continue
            placed = 0
            attempts = 0
            max_attempts = count * 100 # *** INCREASED ATTEMPTS ***
            res_name = cfg.RESOURCE_INFO.get(res_type, {}).get('name', f'Type {res_type}')

            while placed < count and attempts < max_attempts:
                x = random.randint(0, self.width - 1)
                y = random.randint(0, self.height - 1)
                is_valid_terrain = (0 <= x < self.width and 0 <= y < self.height and
                                  self.terrain_map[y, x] == cfg.TERRAIN_GROUND)
                is_empty = self.resource_map[y, x] is None

                if is_valid_terrain and is_empty:
                    quantity = 10; max_quantity = quantity
                    regen = cfg.RESOURCE_REGEN_RATE
                    if res_type == cfg.RESOURCE_WORKBENCH:
                        quantity = 1; max_quantity = 1; regen = 0
                    resource = Resource(res_type, x, y, quantity=quantity, max_quantity=max_quantity, regen_rate=regen)
                    if self.add_world_object(resource, x, y): placed += 1
                attempts += 1

            if placed < count:
                 print(f"    Warning: Could only place {placed}/{count} of {res_name} (tried {attempts} times)")

        # --- World Generation Report (Keep for debugging) ---
        print("\n--- World Generation Report ---")
        final_resource_counts = {}
        for res in self.resources:
            res_type = getattr(res, 'type', 'UNKNOWN')
            final_resource_counts[res_type] = final_resource_counts.get(res_type, 0) + 1
        print(f"Resource Counts in self.resources list ({len(self.resources)} total): {final_resource_counts}")
        map_counts = {}
        for y in range(self.height):
            for x in range(self.width):
                res = self.resource_map[y, x]
                if res:
                     res_type = getattr(res, 'type', 'UNKNOWN')
                     map_counts[res_type] = map_counts.get(res_type, 0) + 1
        print(f"Resource Counts found on resource_map: {map_counts}")
        print(f"Expected Wood({cfg.RESOURCE_WOOD}): {cfg.NUM_TREES}, Stone({cfg.RESOURCE_STONE}): {cfg.NUM_ROCKS}, Food({cfg.RESOURCE_FOOD}): {cfg.NUM_FOOD_SOURCES}")
        if map_counts.get(cfg.RESOURCE_WOOD, 0) == 0: print(">>> CRITICAL: NO WOOD PLACED ON MAP!")
        if map_counts.get(cfg.RESOURCE_STONE, 0) == 0: print(">>> CRITICAL: NO STONE PLACED ON MAP!")
        print(f"World generation took {time.time() - start_time:.2f} seconds.")
        print("--- End World Generation Report ---\n")
        # --- End Report ---


    def update_walkability(self, agent_positions=None):
         """ Creates/updates walkability matrix based on terrain and blocking resources/agents. """
         matrix = create_walkability_matrix(self.terrain_map, self.resource_map)
         if agent_positions:
             temp_matrix = matrix.copy()
             for x, y in agent_positions:
                 if 0 <= x < self.width and 0 <= y < self.height:
                     temp_matrix[y, x] = 0
             return temp_matrix
         else:
             self.walkability_matrix = matrix
             return self.walkability_matrix

    def update(self, dt_real_seconds):
        """ Updates world time and resource regeneration. """
        dt_sim_seconds = dt_real_seconds * cfg.SIMULATION_SPEED_FACTOR
        self.simulation_time += dt_sim_seconds
        self.day_time = (self.day_time + dt_sim_seconds) % cfg.DAY_LENGTH_SECONDS
        self.day_count = int(self.simulation_time // cfg.DAY_LENGTH_SECONDS)
        for resource in list(self.resources): resource.update(dt_sim_seconds)

    def get_terrain(self, x, y):
        """ Returns terrain type at (x, y) or OBSTACLE if out of bounds. """
        if 0 <= x < self.width and 0 <= y < self.height: return self.terrain_map[y, x]
        return cfg.TERRAIN_OBSTACLE

    def get_resource(self, x, y):
        """ Returns Resource object at (x, y) or None. """
        if 0 <= x < self.width and 0 <= y < self.height: return self.resource_map[y, x]
        return None

    def consume_resource_at(self, x, y, amount=1):
        """ Consumes resource/water, returns amount consumed. """
        resource = self.get_resource(x, y)
        if resource and not resource.is_depleted(): return resource.consume(amount)
        elif self.get_terrain(x, y) == cfg.TERRAIN_WATER: return amount
        return 0

    def find_nearest_resource(self, start_x, start_y, resource_type, max_dist=cfg.AGENT_VIEW_RADIUS):
        """ BFS to find nearest resource, handling non-walkable resources. """
        q = [(start_x, start_y, 0)]; visited = set([(start_x, start_y)])
        walkability = self.walkability_matrix
        if not (0 <= start_x < self.width and 0 <= start_y < self.height and walkability[start_y, start_x] == 1):
             # print(f"Warning: find_nearest_resource started from invalid/non-walkable pos ({start_x},{start_y})")
             return None, None, float('inf')

        while q:
            curr_x, curr_y, dist = q.pop(0)
            if dist >= max_dist: continue

            # --- Check CURRENT tile for resource ---
            resource = self.get_resource(curr_x, curr_y)
            is_water_tile = self.get_terrain(curr_x, curr_y) == cfg.TERRAIN_WATER
            target_found = False; goal_pos = (curr_x, curr_y); stand_pos = None

            if resource_type == cfg.RESOURCE_WATER:
                if is_water_tile:
                    stand_pos = self._find_adjacent_walkable(curr_x, curr_y, walkability)
                    if stand_pos: target_found = True
            else:
                if resource and resource.type == resource_type and not resource.is_depleted():
                    # print(f"  >>> BFS Potential Match: {resource.name} at ({curr_x},{curr_y})...") # DEBUG
                    if walkability[curr_y, curr_x] == 1:
                        stand_pos = (curr_x, curr_y); target_found = True
                    else:
                        # print(f"    Resource {resource.name} blocks walk. Searching adjacent...") # DEBUG
                        stand_pos = self._find_adjacent_walkable(curr_x, curr_y, walkability)
                        # print(f"    _find_adjacent_walkable returned: {stand_pos}") # DEBUG
                        if stand_pos: target_found = True

            if target_found:
                # print(f"  >>> find_nearest_resource SUCCESS: Type {resource_type}, Goal={goal_pos}, Stand={stand_pos}, Dist={dist}")
                return goal_pos, stand_pos, dist

            # --- Explore neighbors ONLY IF current node is walkable ---
            if walkability[curr_y, curr_x] == 1:
                neighbors = [(0,1), (0,-1), (1,0), (-1,0), (1,1), (1,-1), (-1,1), (-1,-1)]
                for dx, dy in neighbors:
                    nx, ny = curr_x + dx, curr_y + dy
                    if 0 <= nx < self.width and 0 <= ny < self.height and (nx, ny) not in visited:
                         visited.add((nx, ny))
                         q.append((nx, ny, dist + 1))
            # --- End Neighbor Exploration ---

        # print(f"  find_nearest_resource FAILED for type {resource_type} starting at ({start_x},{start_y}) after checking {len(visited)} locations (max_dist={max_dist}).")
        return None, None, float('inf')


    def _find_adjacent_walkable(self, x, y, walkability_matrix):
        """ Finds a walkable tile adjacent to (x, y). """
        for dx, dy in [(0,1), (0,-1), (1,0), (-1,0), (1,1), (1,-1), (-1,1), (-1,-1)]:
            nx, ny = x + dx, y + dy
            if 0 <= nx < self.width and 0 <= ny < self.height and walkability_matrix[ny, nx] == 1:
                return (nx, ny)
        return None

    def add_world_object(self, obj, x, y):
        """ Adds object, updates resources list and walkability if needed. """
        if 0 <= x < self.width and 0 <= y < self.height:
             if self.terrain_map[y, x] == cfg.TERRAIN_GROUND and self.resource_map[y, x] is None:
                 self.resource_map[y, x] = obj
                 if isinstance(obj, Resource) and obj not in self.resources:
                     self.resources.append(obj)
                 if hasattr(obj, 'blocks_walk') and obj.blocks_walk:
                     self.update_walkability() # Recalculate if blocking object added
                 return True
        return False

    # --- Persistence ---
    def save_state(self, filename="world_save.pkl"):
        """ Saves world state using pickle. """
        state = { 'width': self.width, 'height': self.height, 'terrain_map': self.terrain_map,
                  'resources': self.resources, 'simulation_time': self.simulation_time,
                  'day_time': self.day_time, 'day_count': self.day_count }
        try:
            with open(filename, 'wb') as f: pickle.dump(state, f)
            print(f"World state saved to {filename}")
        except Exception as e: print(f"Error saving world state: {e}"); traceback.print_exc()

    def load_state(self, filename="world_save.pkl"):
        """ Loads world state using pickle. Returns True on success. """
        try:
            with open(filename, 'rb') as f: state = pickle.load(f)
            self.width = state['width']; self.height = state['height']
            self.terrain_map = state['terrain_map']; self.simulation_time = state['simulation_time']
            self.day_time = state['day_time']; self.day_count = state['day_count']
            self.resources = state['resources']
            self.resource_map = np.full((self.height, self.width), None, dtype=object)
            valid_resources = []
            for resource in self.resources:
                 if 0 <= resource.x < self.width and 0 <= resource.y < self.height:
                     if not hasattr(resource, 'name'): resource.__setstate__(resource.__getstate__())
                     if self.resource_map[resource.y, resource.x] is None:
                          self.resource_map[resource.y, resource.x] = resource
                          valid_resources.append(resource)
                     else: print(f"Warning: Conflict loading resource '{resource.name}' at ({resource.x},{resource.y}). Skipping.")
                 else: print(f"Warning: Loaded resource at invalid coords ({resource.x},{resource.y}). Discarding.")
            self.resources = valid_resources
            self.update_walkability()
            print(f"World state loaded from {filename}. Resource count: {len(self.resources)}")
            return True
        except FileNotFoundError: print(f"Save file {filename} not found."); return False
        except Exception as e: print(f"Error loading world state: {e}"); traceback.print_exc(); return False