# world.py
import random
import numpy as np
import config as cfg
from pathfinding_utils import create_walkability_matrix

class Resource:
    def __init__(self, type, x, y, quantity=100, max_quantity=100, regen_rate=cfg.RESOURCE_REGEN_RATE):
        self.type = type
        self.x = x
        self.y = y
        self.quantity = quantity
        self.max_quantity = max_quantity
        self.regen_rate = regen_rate # Per sim second

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

class World:
    def __init__(self, width, height):
        self.width = width
        self.height = height
        # Terrain Layer: Stores terrain type (e.g., Ground, Water)
        self.terrain_map = np.full((height, width), cfg.TERRAIN_GROUND, dtype=int)
        # Resource Layer: Stores Resource objects or None
        self.resource_map = np.full((height, width), None, dtype=object)
        self.resources = [] # Keep a list for faster iteration/update

        self.walkability_matrix = None # Updated when world changes significantly
        self._generate_world()
        self.update_walkability()

        self.simulation_time = 0.0 # Total seconds passed in simulation
        self.day_time = 0.0 # Time within the current day cycle (0 to DAY_LENGTH_SECONDS)
        self.day_count = 0

    def _generate_world(self):
        # Basic world generation
        # 1. Water patches
        for _ in range(cfg.NUM_WATER_PATCHES):
            size_x = random.randint(cfg.WATER_PATCH_SIZE[0], cfg.WATER_PATCH_SIZE[1])
            size_y = random.randint(cfg.WATER_PATCH_SIZE[0], cfg.WATER_PATCH_SIZE[1])
            start_x = random.randint(0, self.width - size_x)
            start_y = random.randint(0, self.height - size_y)
            self.terrain_map[start_y:start_y+size_y, start_x:start_x+size_x] = cfg.TERRAIN_WATER

        # 2. Place Resources (avoiding water/obstacles initially)
        resource_placements = {
            cfg.RESOURCE_FOOD: cfg.NUM_FOOD_SOURCES,
            cfg.RESOURCE_WOOD: cfg.NUM_TREES,    # Phase 2+
            cfg.RESOURCE_STONE: cfg.NUM_ROCKS,    # Phase 2+
        }

        for res_type, count in resource_placements.items():
            placed = 0
            attempts = 0
            while placed < count and attempts < count * 10: # Limit attempts
                x = random.randint(0, self.width - 1)
                y = random.randint(0, self.height - 1)
                if self.terrain_map[y, x] == cfg.TERRAIN_GROUND and self.resource_map[y, x] is None:
                    resource = Resource(res_type, x, y)
                    self.resource_map[y, x] = resource
                    self.resources.append(resource)
                    placed += 1
                attempts += 1

        # Phase 3+: Place initial Workbenches? Or let agents build them
        # ...

    def update_walkability(self):
         self.walkability_matrix = create_walkability_matrix(self.terrain_map)
         # Future: consider dynamic obstacles like buildings or felled trees

    def update(self, dt_real_seconds):
        dt_sim_seconds = dt_real_seconds * cfg.SIMULATION_SPEED_FACTOR
        self.simulation_time += dt_sim_seconds
        self.day_time = (self.day_time + dt_sim_seconds) % cfg.DAY_LENGTH_SECONDS
        self.day_count = int(self.simulation_time // cfg.DAY_LENGTH_SECONDS)

        # Update resources (regeneration)
        for resource in self.resources:
            resource.update(dt_sim_seconds)
            if resource.is_depleted():
                # Option 1: Remove permanently
                # self.resource_map[resource.y, resource.x] = None
                # self.resources.remove(resource) # Careful when iterating
                # Option 2: Keep object, just visually indicate depletion
                pass # Currently handled in drawing

        # Potential future updates: Weather, seasons, ecological changes...

    def get_terrain(self, x, y):
        if 0 <= x < self.width and 0 <= y < self.height:
            return self.terrain_map[y, x]
        return cfg.TERRAIN_OBSTACLE # Treat out of bounds as obstacle

    def get_resource(self, x, y):
        if 0 <= x < self.width and 0 <= y < self.height:
            return self.resource_map[y, x]
        return None

    def consume_resource_at(self, x, y, amount=1):
        resource = self.get_resource(x, y)
        if resource:
            consumed = resource.consume(amount)
            # Maybe remove if depleted? Depends on regeneration design
            # if resource.is_depleted():
            #    self.resource_map[y, x] = None
            #    self.resources.remove(resource) # Be careful modifying list while iterating elsewhere
            return consumed
        elif self.get_terrain(x, y) == cfg.TERRAIN_WATER:
             return amount # Water terrain is infinite source for now
        return 0

    def find_nearest_resource(self, x, y, resource_type):
        """ Finds the nearest accessible resource of a given type. """
        q = [(x, y, 0)] # x, y, distance
        visited = set([(x, y)])
        walkability = self.walkability_matrix # Use precomputed matrix

        while q:
            curr_x, curr_y, dist = q.pop(0)

            # Check current location
            if resource_type == cfg.RESOURCE_WATER:
                 if self.get_terrain(curr_x, curr_y) == cfg.TERRAIN_WATER:
                     # Need to find adjacent land tile to stand on
                     for dx, dy in [(0,1), (0,-1), (1,0), (-1,0), (1,1), (1,-1), (-1,1), (-1,-1)]:
                         adj_x, adj_y = curr_x + dx, curr_y + dy
                         if 0 <= adj_x < self.width and 0 <= adj_y < self.height and walkability[adj_y, adj_x] == 1:
                              # Return the water tile coords, and the land tile to stand on
                             return (curr_x, curr_y), (adj_x, adj_y), dist + 1 # Approx distance
            else:
                resource = self.get_resource(curr_x, curr_y)
                if resource and resource.type == resource_type and not resource.is_depleted():
                    # Return resource location (target), and current location (stand on)
                    return (curr_x, curr_y), (curr_x, curr_y), dist

            # Explore neighbors
            for dx, dy in [(0,1), (0,-1), (1,0), (-1,0), (1,1), (1,-1), (-1,1), (-1,-1)]: # Check diagonals too
                nx, ny = curr_x + dx, curr_y + dy
                if 0 <= nx < self.width and 0 <= ny < self.height and (nx, ny) not in visited:
                    # Only add walkable neighbours for pathfinding BFS
                    # Water source finding needs to check water tiles, but agent stands on land
                    is_walkable = walkability[ny, nx] == 1
                    is_target_water_tile = resource_type == cfg.RESOURCE_WATER and self.get_terrain(nx, ny) == cfg.TERRAIN_WATER

                    if is_walkable or is_target_water_tile:
                         visited.add((nx, ny))
                         q.append((nx, ny, dist + 1))

        return None, None, float('inf') # Not found

    # --- Phase 3+ Methods ---
    def add_world_object(self, obj, x, y):
        """ Adds objects like workbenches, buildings etc. """
        # Example: Could be a special type of Resource or distinct object map layer
        if self.terrain_map[y, x] == cfg.TERRAIN_GROUND and self.resource_map[y, x] is None:
            self.resource_map[y, x] = obj # Treat as a resource for now
            if isinstance(obj, Resource) and obj not in self.resources:
                self.resources.append(obj)
            # Need to update walkability if it's an obstacle
            # self.update_walkability()
            return True
        return False

    # --- Persistence ---
    def save_state(self, filename="world_save.pkl"):
        # Requires careful handling of object references, esp. with agents
        import pickle
        state = {
            'width': self.width,
            'height': self.height,
            'terrain_map': self.terrain_map,
            # Need to serialize resource objects carefully
            'resources': [(r.type, r.x, r.y, r.quantity, r.max_quantity, r.regen_rate) for r in self.resources],
            'simulation_time': self.simulation_time,
            'day_time': self.day_time,
            'day_count': self.day_count,
            # Missing: dynamic objects, potentially agent references? Better saved separately
        }
        try:
            with open(filename, 'wb') as f:
                pickle.dump(state, f)
            print(f"World state saved to {filename}")
        except Exception as e:
            print(f"Error saving world state: {e}")

    def load_state(self, filename="world_save.pkl"):
        import pickle
        try:
            with open(filename, 'rb') as f:
                state = pickle.load(f)
            self.width = state['width']
            self.height = state['height']
            self.terrain_map = state['terrain_map']
            self.simulation_time = state['simulation_time']
            self.day_time = state['day_time']
            self.day_count = state['day_count']

            self.resources = []
            self.resource_map = np.full((self.height, self.width), None, dtype=object)
            for r_data in state['resources']:
                res_type, x, y, quantity, max_q, regen = r_data
                resource = Resource(res_type, x, y, quantity, max_q, regen)
                if 0 <= x < self.width and 0 <= y < self.height:
                    self.resource_map[y, x] = resource
                    self.resources.append(resource)
                else:
                    print(f"Warning: Loaded resource at invalid coords ({x},{y})")

            self.update_walkability() # Important after loading terrain/resources
            print(f"World state loaded from {filename}")
            return True
        except FileNotFoundError:
            print(f"Save file {filename} not found. Starting new world.")
            return False
        except Exception as e:
            print(f"Error loading world state: {e}")
            return False