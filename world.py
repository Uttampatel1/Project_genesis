# world.py
import random
import numpy as np
import config as cfg
from pathfinding_utils import create_walkability_matrix
import pickle # For saving/loading

class Resource:
    # Added name property based on config
    def __init__(self, type, x, y, quantity=10, max_quantity=10, regen_rate=cfg.RESOURCE_REGEN_RATE):
        self.type = type
        self.x = x
        self.y = y
        self.quantity = quantity
        self.max_quantity = max_quantity
        self.regen_rate = regen_rate # Per sim second
        self.name = cfg.RESOURCE_INFO.get(type, {}).get('name', 'Unknown')
        self.blocks_walk = cfg.RESOURCE_INFO.get(type, {}).get('block_walk', False)

    def consume(self, amount=1):
        consumed = min(amount, self.quantity)
        self.quantity -= consumed
        return consumed

    def update(self, dt_sim_seconds):
        if self.quantity < self.max_quantity:
            # Simple probabilistic regeneration
             if random.random() < self.regen_rate * dt_sim_seconds:
                 self.quantity = min(self.max_quantity, self.quantity + 1)

    def is_depleted(self):
        return self.quantity <= 0

    def __getstate__(self):
        # Define what gets pickled
        return (self.type, self.x, self.y, self.quantity, self.max_quantity, self.regen_rate)

    def __setstate__(self, state):
        # Define how to unpickle
        self.type, self.x, self.y, self.quantity, self.max_quantity, self.regen_rate = state
        self.name = cfg.RESOURCE_INFO.get(self.type, {}).get('name', 'Unknown')
        self.blocks_walk = cfg.RESOURCE_INFO.get(self.type, {}).get('block_walk', False)


class World:
    def __init__(self, width, height):
        self.width = width
        self.height = height
        self.terrain_map = np.full((height, width), cfg.TERRAIN_GROUND, dtype=int)
        self.resource_map = np.full((height, width), None, dtype=object)
        self.resources = [] # Keep a list for faster iteration/update

        self.walkability_matrix = None
        self._generate_world()
        self.update_walkability() # Initial walkability calculation

        self.simulation_time = 0.0
        self.day_time = 0.0
        self.day_count = 0

    def _generate_world(self):
        # 1. Water patches
        for _ in range(cfg.NUM_WATER_PATCHES):
            size_x = random.randint(cfg.WATER_PATCH_SIZE[0], cfg.WATER_PATCH_SIZE[1])
            size_y = random.randint(cfg.WATER_PATCH_SIZE[0], cfg.WATER_PATCH_SIZE[1])
            start_x = random.randint(0, self.width - size_x)
            start_y = random.randint(0, self.height - size_y)
            self.terrain_map[start_y:start_y+size_y, start_x:start_x+size_x] = cfg.TERRAIN_WATER

        # 2. Obstacles (non-resource rocks/mountains) - Optional addition
        # num_obstacles = 5
        # for _ in range(num_obstacles):
        #     size_x = random.randint(2, 5)
        #     size_y = random.randint(2, 5)
        #     start_x = random.randint(0, self.width - size_x)
        #     start_y = random.randint(0, self.height - size_y)
        #     # Avoid overwriting water
        #     can_place = True
        #     for y in range(start_y, start_y + size_y):
        #         for x in range(start_x, start_x + size_x):
        #             if self.terrain_map[y, x] == cfg.TERRAIN_WATER:
        #                 can_place = False
        #                 break
        #         if not can_place: break
        #     if can_place:
        #         self.terrain_map[start_y:start_y+size_y, start_x:start_x+size_x] = cfg.TERRAIN_OBSTACLE


        # 3. Place Resources (avoiding water/obstacles)
        resource_placements = {
            cfg.RESOURCE_FOOD: cfg.NUM_FOOD_SOURCES,
            cfg.RESOURCE_WOOD: cfg.NUM_TREES,
            cfg.RESOURCE_STONE: cfg.NUM_ROCKS,
            cfg.RESOURCE_WORKBENCH: cfg.NUM_INITIAL_WORKBENCHES # Usually 0, agents build
        }

        for res_type, count in resource_placements.items():
            placed = 0
            attempts = 0
            while placed < count and attempts < count * 20: # Limit attempts
                x = random.randint(0, self.width - 1)
                y = random.randint(0, self.height - 1)
                # Check terrain is ground AND no existing resource AND target location is within bounds
                if 0 <= x < self.width and 0 <= y < self.height and \
                   self.terrain_map[y, x] == cfg.TERRAIN_GROUND and \
                   self.resource_map[y, x] is None:
                    # Determine quantity based on type
                    quantity = 10 # Default for Food, Wood, Stone
                    max_quantity = quantity
                    if res_type == cfg.RESOURCE_WORKBENCH:
                        quantity = 1 # Workbenches are usually single units
                        max_quantity = 1
                    resource = Resource(res_type, x, y, quantity=quantity, max_quantity=max_quantity)
                    self.add_world_object(resource, x, y) # Use helper to add
                    placed += 1
                attempts += 1
            if placed < count:
                 print(f"Warning: Could only place {placed}/{count} of resource type {res_type}")


    def update_walkability(self, agent_positions=None):
         """
         Creates/updates the walkability matrix.
         Optionally takes agent positions to mark them as temporarily unwalkable for specific pathfinding calls.
         Returns the updated matrix. If agent_positions is None, updates self.walkability_matrix.
         """
         matrix = create_walkability_matrix(self.terrain_map, self.resource_map)

         # If agent positions are provided, create a temporary copy and mark agent locations
         if agent_positions:
             temp_matrix = matrix.copy()
             for x, y in agent_positions:
                 if 0 <= x < self.width and 0 <= y < self.height:
                     temp_matrix[y, x] = 0 # Mark agent location as unwalkable
             return temp_matrix # Return the temporary matrix
         else:
             # Update the main world walkability matrix
             self.walkability_matrix = matrix
             return self.walkability_matrix


    def update(self, dt_real_seconds):
        dt_sim_seconds = dt_real_seconds * cfg.SIMULATION_SPEED_FACTOR
        self.simulation_time += dt_sim_seconds
        self.day_time = (self.day_time + dt_sim_seconds) % cfg.DAY_LENGTH_SECONDS
        self.day_count = int(self.simulation_time // cfg.DAY_LENGTH_SECONDS)

        # Update resources (regeneration) - Use list copy for safe removal if needed
        resources_to_remove = []
        for resource in list(self.resources): # Iterate over a copy
            resource.update(dt_sim_seconds)
            if resource.is_depleted() and resource.regen_rate <= 0: # Remove if depleted and non-regenerating
                resources_to_remove.append(resource)

        # Remove depleted non-regenerating resources (optional)
        # for res in resources_to_remove:
        #     if self.resource_map[res.y, res.x] == res:
        #         self.resource_map[res.y, res.x] = None
        #     if res in self.resources:
        #         self.resources.remove(res)
        # if resources_to_remove:
        #     self.update_walkability() # Update if resources affecting walkability were removed

    def get_terrain(self, x, y):
        if 0 <= x < self.width and 0 <= y < self.height:
            return self.terrain_map[y, x]
        return cfg.TERRAIN_OBSTACLE

    def get_resource(self, x, y):
        if 0 <= x < self.width and 0 <= y < self.height:
            return self.resource_map[y, x]
        return None

    def consume_resource_at(self, x, y, amount=1):
        resource = self.get_resource(x, y)
        if resource and not resource.is_depleted(): # Check depletion again
            consumed = resource.consume(amount)
            # Optional: Remove if depleted immediately (affects finding nearest)
            # if resource.is_depleted():
            #    self.resource_map[y, x] = None
            #    if resource in self.resources:
            #         self.resources.remove(resource) # Careful modifying list
            #    self.update_walkability() # Resource might have blocked path
            return consumed
        elif self.get_terrain(x, y) == cfg.TERRAIN_WATER:
             return amount # Water terrain is infinite source
        return 0

    def find_nearest_resource(self, start_x, start_y, resource_type, max_dist=cfg.AGENT_VIEW_RADIUS):
        """ Finds the nearest accessible resource using BFS. Returns (goal_pos, stand_pos, distance). """
        q = [(start_x, start_y, 0)] # x, y, distance
        visited = set([(start_x, start_y)])
        walkability = self.walkability_matrix # Use precomputed matrix

        while q:
            curr_x, curr_y, dist = q.pop(0)

            if dist >= max_dist: # Limit search range
                continue

            # Check current location for the resource
            resource = self.get_resource(curr_x, curr_y)
            is_water_tile = self.get_terrain(curr_x, curr_y) == cfg.TERRAIN_WATER

            target_found = False
            goal_pos = (curr_x, curr_y)
            stand_pos = None

            if resource_type == cfg.RESOURCE_WATER:
                if is_water_tile:
                    # Find adjacent walkable land tile to stand on
                    stand_pos = self._find_adjacent_walkable(curr_x, curr_y, walkability)
                    if stand_pos:
                        target_found = True
                        # Distance is to the stand_pos, slightly adjust estimate
                        dist = abs(start_x - stand_pos[0]) + abs(start_y - stand_pos[1]) # Manhattan estimate
            else:
                if resource and resource.type == resource_type and not resource.is_depleted():
                    # Resource found. Standing position is the resource tile itself IF it's walkable.
                    # If resource blocks walk (Tree, Rock), need adjacent stand pos.
                    if walkability[curr_y, curr_x] == 1:
                        stand_pos = (curr_x, curr_y)
                        target_found = True
                    else: # Resource exists but is on non-walkable tile (e.g. Tree/Rock itself)
                        stand_pos = self._find_adjacent_walkable(curr_x, curr_y, walkability)
                        if stand_pos:
                             target_found = True
                             dist = abs(start_x - stand_pos[0]) + abs(start_y - stand_pos[1]) # Manhattan estimate to stand pos

            if target_found:
                return goal_pos, stand_pos, dist

            # Explore neighbors (only explore from walkable tiles)
            if walkability[curr_y, curr_x] == 1: # Can only move FROM walkable tiles
                for dx, dy in [(0,1), (0,-1), (1,0), (-1,0)]: # Cardinal directions only for BFS speed
                    nx, ny = curr_x + dx, curr_y + dy
                    if 0 <= nx < self.width and 0 <= ny < self.height and (nx, ny) not in visited:
                         # Add to queue if it's walkable OR if we are searching for water and it's a water tile
                         is_walkable = walkability[ny, nx] == 1
                         is_target_water_tile = resource_type == cfg.RESOURCE_WATER and self.get_terrain(nx, ny) == cfg.TERRAIN_WATER

                         if is_walkable or is_target_water_tile:
                             visited.add((nx, ny))
                             q.append((nx, ny, dist + 1))

        return None, None, float('inf') # Not found


    def _find_adjacent_walkable(self, x, y, walkability_matrix):
        """ Finds a walkable tile adjacent to (x, y) using the provided matrix. """
        for dx, dy in [(0,1), (0,-1), (1,0), (-1,0), (1,1), (1,-1), (-1,1), (-1,-1)]: # Check diagonals too
            nx, ny = x + dx, y + dy
            if 0 <= nx < self.width and 0 <= ny < self.height:
                if walkability_matrix[ny, nx] == 1:
                    return (nx, ny)
        return None


    def add_world_object(self, obj, x, y):
        """ Adds objects like resources, workbenches, buildings. Updates walkability if needed. """
        if 0 <= x < self.width and 0 <= y < self.height:
             if self.terrain_map[y, x] == cfg.TERRAIN_GROUND and self.resource_map[y, x] is None:
                 self.resource_map[y, x] = obj
                 if isinstance(obj, Resource) and obj not in self.resources:
                     self.resources.append(obj)
                 # Update walkability if the object blocks movement
                 if hasattr(obj, 'blocks_walk') and obj.blocks_walk:
                     self.update_walkability() # Recalculate the main matrix
                 return True
        return False

    # --- Persistence ---
    def save_state(self, filename="world_save.pkl"):
        # Using pickle with __getstate__ and __setstate__ for Resource
        state = {
            'width': self.width,
            'height': self.height,
            'terrain_map': self.terrain_map,
            'resources': self.resources, # Pickle Resource objects directly now
            'simulation_time': self.simulation_time,
            'day_time': self.day_time,
            'day_count': self.day_count,
        }
        try:
            with open(filename, 'wb') as f:
                pickle.dump(state, f)
            print(f"World state saved to {filename}")
        except Exception as e:
            print(f"Error saving world state: {e}")

    def load_state(self, filename="world_save.pkl"):
        try:
            with open(filename, 'rb') as f:
                state = pickle.load(f)
            self.width = state['width']
            self.height = state['height']
            self.terrain_map = state['terrain_map']
            self.simulation_time = state['simulation_time']
            self.day_time = state['day_time']
            self.day_count = state['day_count']

            self.resources = state['resources'] # Load pickled Resource objects
            # Reconstruct resource_map from the loaded resources list
            self.resource_map = np.full((self.height, self.width), None, dtype=object)
            for resource in self.resources:
                 if 0 <= resource.x < self.width and 0 <= resource.y < self.height:
                     self.resource_map[resource.y, resource.x] = resource
                 else:
                     print(f"Warning: Loaded resource '{resource.name}' at invalid coords ({resource.x},{resource.y})")

            self.update_walkability() # Important after loading terrain/resources
            print(f"World state loaded from {filename}")
            return True
        except FileNotFoundError:
            print(f"Save file {filename} not found. Starting new world.")
            return False
        except Exception as e:
            print(f"Error loading world state: {e}")
            return False