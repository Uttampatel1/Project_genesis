# world.py
import random
import numpy as np
import config as cfg
from pathfinding_utils import create_walkability_matrix
import pickle
import time
import math
import traceback

class Resource:
    """ Represents a resource node in the world (e.g., Tree, Rock, Workbench). """
    def __init__(self, type, x, y, quantity=None, max_quantity=None, regen_rate=None):
        """ Initializes a resource instance. """
        self.type = type
        self.x = x
        self.y = y

        # Get defaults from config if not provided
        res_info = cfg.RESOURCE_INFO.get(type, {})
        self.max_quantity = max_quantity if max_quantity is not None else res_info.get('max_quantity', 1)
        self.quantity = quantity if quantity is not None else self.max_quantity # Start full by default
        self.regen_rate = regen_rate if regen_rate is not None else res_info.get('regen', 0)

        # Derived attributes from config (set here and in __setstate__)
        self.name = res_info.get('name', 'Unknown')
        self.blocks_walk = res_info.get('block_walk', False)

    def consume(self, amount=1):
        """ Consumes a specified amount of the resource. Returns amount actually consumed. """
        consumed = min(amount, self.quantity)
        self.quantity -= consumed
        return consumed

    def update(self, dt_sim_seconds):
        """ Updates resource quantity based on regeneration rate (if applicable). """
        if self.regen_rate > 0 and self.quantity < self.max_quantity:
             # Probabilistic regeneration check
             if random.random() < self.regen_rate * dt_sim_seconds:
                 self.quantity = min(self.max_quantity, self.quantity + 1)

    def is_depleted(self):
        """ Returns True if the resource quantity is zero or less. """
        return self.quantity <= 0

    # --- Persistence Methods (for saving/loading) ---
    def __getstate__(self):
        """ Defines which attributes are saved when pickling. """
        # Store only essential data; derived attributes will be reconstructed on load.
        return (self.type, self.x, self.y, self.quantity, self.max_quantity, self.regen_rate)

    def __setstate__(self, state):
        """ Defines how to restore the object state when unpickling. """
        # Unpack the saved state tuple
        self.type, self.x, self.y, self.quantity, self.max_quantity, self.regen_rate = state

        # Re-initialize derived attributes from config based on the loaded type
        res_info = cfg.RESOURCE_INFO.get(self.type, {})
        self.name = res_info.get('name', 'Unknown')
        self.blocks_walk = res_info.get('block_walk', False)

        # Handle potential missing attributes from older save files (optional robustness)
        if self.regen_rate is None: self.regen_rate = res_info.get('regen', 0)
        if self.max_quantity is None: self.max_quantity = res_info.get('max_quantity', 1)

class World:
    """ Manages the simulation grid, terrain, resources, time, and basic world queries. """
    def __init__(self, width, height):
        """ Initializes the world grid and generates initial layout. """
        self.width = width
        self.height = height
        # Terrain map: Stores terrain type (Ground, Water, Obstacle) for each tile
        self.terrain_map = np.full((height, width), cfg.TERRAIN_GROUND, dtype=int)
        # Resource map: Stores Resource object or None for each tile
        self.resource_map = np.full((height, width), None, dtype=object)
        # List of all active Resource objects (for efficient iteration)
        self.resources = []
        # Walkability matrix (1=walkable, 0=obstacle) derived from terrain and resources
        self.walkability_matrix = None
        # Simulation time tracking
        self.simulation_time = 0.0
        self.day_time = 0.0
        self.day_count = 0
        # Dictionary for quick agent lookup by ID (updated externally)
        self.agents_by_id = {}

        # Generate initial world features
        self._generate_world()
        # Calculate initial walkability based on generated features
        self.update_walkability()

    def _generate_world(self):
        """ Generates the initial terrain (water) and resource layout. """
        print("Generating world terrain and resources...")
        start_time = time.time()

        # 1. Place Water Patches
        if cfg.DEBUG_WORLD_GEN: print(f"  Placing {cfg.NUM_WATER_PATCHES} water patches...")
        for _ in range(cfg.NUM_WATER_PATCHES):
            size_x = random.randint(cfg.WATER_PATCH_SIZE[0], cfg.WATER_PATCH_SIZE[1])
            size_y = random.randint(cfg.WATER_PATCH_SIZE[0], cfg.WATER_PATCH_SIZE[1])
            start_x = random.randint(0, self.width - size_x)
            start_y = random.randint(0, self.height - size_y)
            # Set terrain type to Water within the patch boundaries
            self.terrain_map[start_y:start_y+size_y, start_x:start_x+size_x] = cfg.TERRAIN_WATER

        # 2. Place Resource Objects (Food, Wood, Stone, Initial Workbenches)
        if cfg.DEBUG_WORLD_GEN: print("  Placing resources...")
        resource_placements = {
            cfg.RESOURCE_FOOD: cfg.NUM_FOOD_SOURCES,
            cfg.RESOURCE_WOOD: cfg.NUM_TREES,
            cfg.RESOURCE_STONE: cfg.NUM_ROCKS,
            cfg.RESOURCE_WORKBENCH: cfg.NUM_INITIAL_WORKBENCHES # Include workbenches
        }

        for res_type, count in resource_placements.items():
            if count <= 0: continue # Skip if zero count configured
            placed = 0
            attempts = 0
            # Allow more attempts for placing resources, especially if map is dense
            max_attempts = count * 200
            res_info = cfg.RESOURCE_INFO.get(res_type, {})
            res_name = res_info.get('name', f'Type {res_type}')
            if cfg.DEBUG_WORLD_GEN: print(f"    Attempting to place {count} {res_name}...")

            while placed < count and attempts < max_attempts:
                # Choose random coordinates
                x = random.randint(0, self.width - 1)
                y = random.randint(0, self.height - 1)

                # Check placement validity: Must be on Ground terrain and the tile must be empty
                is_valid_terrain = (self.terrain_map[y, x] == cfg.TERRAIN_GROUND)
                is_empty = self.resource_map[y, x] is None

                if is_valid_terrain and is_empty:
                    # Create the resource instance
                    resource = Resource(res_type, x, y)
                    # Use add_world_object to handle map/list updates and logging
                    if self.add_world_object(resource, x, y):
                         placed += 1
                attempts += 1

            # Log outcome of placement attempts
            if placed < count:
                 print(f"    Warning: Could only place {placed}/{count} of {res_name} (tried {attempts} times)")
            elif cfg.DEBUG_WORLD_GEN:
                 print(f"    Successfully placed {placed}/{count} of {res_name}.")

        if cfg.DEBUG_WORLD_GEN:
             print(f"World generation completed in {time.time() - start_time:.2f} seconds.")


    def update_walkability(self, agent_positions=None):
         """
         Recalculates the walkability matrix based on terrain and blocking resources.
         If agent_positions is provided, returns a temporary matrix with agents blocked,
         otherwise updates self.walkability_matrix.
         """
         # Create base matrix considering terrain and blocking resources
         matrix = create_walkability_matrix(self.terrain_map, self.resource_map)

         if agent_positions:
             # Create a temporary copy and mark agent positions as non-walkable
             temp_matrix = matrix.copy()
             for x, y in agent_positions:
                 if 0 <= x < self.width and 0 <= y < self.height:
                     temp_matrix[y, x] = 0 # Mark agent position as obstacle
             return temp_matrix
         else:
             # Update the world's persistent walkability matrix
             self.walkability_matrix = matrix
             return self.walkability_matrix

    def update(self, dt_real_seconds, agents):
        """ Updates world time and resource regeneration. Agent dict updated in main loop. """
        dt_sim_seconds = dt_real_seconds * cfg.SIMULATION_SPEED_FACTOR

        # Update simulation time and day cycle
        self.simulation_time += dt_sim_seconds
        self.day_time = (self.day_time + dt_sim_seconds) % cfg.DAY_LENGTH_SECONDS
        self.day_count = int(self.simulation_time // cfg.DAY_LENGTH_SECONDS)

        # Update resource regeneration
        # Iterate over a copy `[:]` in case resources get removed during update (optional)
        for resource in self.resources[:]:
            resource.update(dt_sim_seconds)
            # Optional: Remove depleted, non-regenerating resources here if desired
            # if resource.is_depleted() and resource.regen_rate <= 0 and resource.type != cfg.RESOURCE_WORKBENCH:
            #    self.remove_world_object(resource.x, resource.y)

        # Note: self.agents_by_id is updated in the main simulation loop after agent updates/deaths


    def get_terrain(self, x, y):
        """ Returns terrain type at (x, y), handling bounds checks. """
        if 0 <= x < self.width and 0 <= y < self.height:
             return self.terrain_map[y, x]
        return cfg.TERRAIN_OBSTACLE # Treat out-of-bounds as obstacle


    def get_resource(self, x, y):
        """ Returns Resource object at (x, y) or None, handling bounds checks. """
        if 0 <= x < self.width and 0 <= y < self.height:
             return self.resource_map[y, x]
        return None


    def consume_resource_at(self, x, y, amount=1):
        """ Consumes resource at location, returns amount actually consumed. Handles implicit Water. """
        if not (0 <= x < self.width and 0 <= y < self.height):
             return 0 # Out of bounds

        # Check for Resource object first
        resource = self.resource_map[y, x]
        if resource and not resource.is_depleted():
            consumed = resource.consume(amount)
            # Optional: Remove depleted non-regenerating resources immediately
            # if resource.is_depleted() and resource.regen_rate <= 0:
            #    self.remove_world_object(x,y)
            return consumed
        # Check for Water terrain if no consumable resource object found
        elif self.terrain_map[y, x] == cfg.TERRAIN_WATER:
            return amount # Water is effectively infinite for consumption
        return 0 # No consumable resource found


    def find_nearest_resource(self, start_x, start_y, resource_type, max_dist=cfg.AGENT_VIEW_RADIUS):
        """
        Performs a Breadth-First Search (BFS) from (start_x, start_y) to find the nearest
        resource of the specified type within max_dist.
        Returns (goal_pos, stand_pos, distance) or (None, None, float('inf')).
        goal_pos: The (x, y) of the resource tile itself.
        stand_pos: A walkable (x, y) adjacent to or on the resource tile to interact from.
        """
        # Basic input validation
        if not (0 <= start_x < self.width and 0 <= start_y < self.height):
             print(f"Warning: find_nearest_resource called with invalid start ({start_x},{start_y})")
             return None, None, float('inf')

        # Initialize BFS queue and visited set
        # Queue stores (x, y, distance_from_start)
        q = [(start_x, start_y, 0)]
        visited = set([(start_x, start_y)])
        # Use the world's base walkability grid for the search (ignoring agents)
        walkability = self.walkability_matrix

        while q:
            curr_x, curr_y, dist = q.pop(0)

            # Stop searching if distance limit exceeded
            if dist >= max_dist: continue

            # --- Check CURRENT tile (curr_x, curr_y) for the target resource ---
            target_found = False
            goal_pos = (curr_x, curr_y) # Assume current tile is the goal for now
            stand_pos = None            # Position to stand to interact

            # Case 1: Searching for Water
            if resource_type == cfg.RESOURCE_WATER:
                if self.get_terrain(curr_x, curr_y) == cfg.TERRAIN_WATER:
                    # Found water tile, now find adjacent walkable ground to stand on
                    stand_pos = self._find_adjacent_walkable(curr_x, curr_y, walkability)
                    if stand_pos: target_found = True
            # Case 2: Searching for a specific Resource object type
            else:
                resource = self.get_resource(curr_x, curr_y)
                if resource and resource.type == resource_type and not resource.is_depleted():
                    # Found the correct resource type, now find where to stand
                    if walkability[curr_y, curr_x] == 1:
                        # Resource is on a walkable tile (e.g., Workbench), stand on it.
                        stand_pos = (curr_x, curr_y)
                        target_found = True
                    else:
                        # Resource blocks walking (e.g., Tree, Rock), find adjacent walkable.
                        stand_pos = self._find_adjacent_walkable(curr_x, curr_y, walkability)
                        if stand_pos: target_found = True

            # --- If Target Found ---
            if target_found:
                # Return the goal position, valid standing position, and BFS grid distance
                if cfg.DEBUG_PATHFINDING or cfg.DEBUG_KNOWLEDGE:
                     res_name = "Water" if resource_type == cfg.RESOURCE_WATER else cfg.RESOURCE_INFO.get(resource_type, {}).get('name', '?')
                     print(f"  World BFS Found: {res_name} at {goal_pos}, stand at {stand_pos}, grid dist {dist}")
                return goal_pos, stand_pos, dist

            # --- Explore Neighbors ---
            # Explore neighbors using 8-directional movement (including diagonals)
            neighbors = [(0,1), (0,-1), (1,0), (-1,0), (1,1), (1,-1), (-1,1), (-1,-1)]
            random.shuffle(neighbors) # Avoid directional bias in exploration
            for dx, dy in neighbors:
                nx, ny = curr_x + dx, curr_y + dy
                # Check bounds and if neighbor has already been visited
                if 0 <= nx < self.width and 0 <= ny < self.height and (nx, ny) not in visited:
                     visited.add((nx, ny))
                     # Add neighbor to queue to check later
                     q.append((nx, ny, dist + 1))

        # If queue becomes empty and target not found
        return None, None, float('inf')


    def _find_adjacent_walkable(self, x, y, walkability_matrix):
        """ Finds the first walkable tile adjacent (including diagonals) to (x, y). """
        neighbors = [(0,-1), (0,1), (1,0), (-1,0), (1,-1), (1,1), (-1,1), (-1,-1)]
        for dx, dy in neighbors:
            nx, ny = x + dx, y + dy
            if 0 <= nx < self.width and 0 <= ny < self.height and walkability_matrix[ny, nx] == 1:
                return (nx, ny)
        return None # No walkable neighbor found


    def add_world_object(self, obj, x, y):
        """
        Adds an object (like a Resource) to the world at (x, y).
        Updates resource_map, resources list, and walkability matrix if needed.
        Returns True if successful, False otherwise.
        """
        if not (0 <= x < self.width and 0 <= y < self.height):
             print(f"Warning: Attempted to add object outside world bounds at ({x},{y})")
             return False

        # Check if placement location is valid (Ground terrain and currently empty)
        if self.terrain_map[y, x] == cfg.TERRAIN_GROUND and self.resource_map[y, x] is None:
             # Place object on the map
             self.resource_map[y, x] = obj
             # If it's a Resource object, add it to the list for updates
             if isinstance(obj, Resource):
                 if obj not in self.resources: # Avoid adding duplicates
                      self.resources.append(obj)

             # Update walkability matrix if the new object blocks movement
             if getattr(obj, 'blocks_walk', False):
                 self.update_walkability() # Recalculate the base walkability

             if cfg.DEBUG_WORLD_GEN or cfg.DEBUG_AGENT_ACTIONS: # Log placement
                 print(f"World: Added object '{getattr(obj, 'name', '?')}' at ({x},{y})")
             return True
        else:
             # Log failure reason
             if cfg.DEBUG_WORLD_GEN or cfg.DEBUG_AGENT_ACTIONS:
                 reason = "not ground" if self.terrain_map[y, x] != cfg.TERRAIN_GROUND else "tile occupied"
                 print(f"World: Failed to add object '{getattr(obj, 'name', '?')}' at ({x},{y}) - {reason}")
             return False


    def remove_world_object(self, x, y):
         """ Removes object at (x,y), updating map, list, and walkability. Returns True if successful. """
         if not (0 <= x < self.width and 0 <= y < self.height):
              return False # Out of bounds

         obj = self.resource_map[y, x]
         if obj is not None:
             was_blocking = getattr(obj, 'blocks_walk', False)
             # Remove from map
             self.resource_map[y, x] = None
             # Remove from resource list if applicable
             if isinstance(obj, Resource) and obj in self.resources:
                 try:
                    self.resources.remove(obj)
                 except ValueError: # Should not happen if logic is correct
                     if cfg.DEBUG_WORLD_GEN: print(f"Warning: Tried to remove resource from list but it wasn't found: {obj}")

             # Update walkability only if a blocking object was removed
             if was_blocking:
                 self.update_walkability()

             if cfg.DEBUG_WORLD_GEN or cfg.DEBUG_AGENT_ACTIONS:
                  print(f"World: Removed object '{getattr(obj, 'name', '?')}' from ({x},{y})")
             return True
         return False # Nothing to remove at location


    def get_agent_by_id(self, agent_id):
        """ Returns the agent object with the given ID, or None if not found/dead. """
        # Uses the dictionary updated in the main loop
        return self.agents_by_id.get(agent_id)


    # --- Persistence (Save/Load World State) ---
    def save_state(self, filename="world_save.pkl"):
        """ Saves the current world state (terrain, resources, time) to a file using pickle. """
        # Note: Agent states are NOT saved here; that requires separate logic.
        # self.agents_by_id is transient and rebuilt after agent loading/creation.
        state = {
            'width': self.width,
            'height': self.height,
            'terrain_map': self.terrain_map,
            'resources': self.resources, # Save the list of Resource objects
            'simulation_time': self.simulation_time,
            'day_time': self.day_time,
            'day_count': self.day_count
        }
        try:
            with open(filename, 'wb') as f:
                pickle.dump(state, f)
            print(f"World state saved to {filename}")
        except Exception as e:
            print(f"Error saving world state: {e}")
            traceback.print_exc()

    def load_state(self, filename="world_save.pkl"):
        """ Loads world state from a file. Returns True on success, False otherwise. """
        try:
            with open(filename, 'rb') as f:
                state = pickle.load(f)

            # Restore basic attributes
            self.width = state['width']
            self.height = state['height']
            self.terrain_map = state['terrain_map']
            self.simulation_time = state['simulation_time']
            self.day_time = state['day_time']
            self.day_count = state['day_count']
            loaded_resources = state.get('resources', []) # Use .get for potential backward compatibility

            # --- Rebuild resource map and list from loaded resources ---
            self.resource_map = np.full((self.height, self.width), None, dtype=object)
            self.resources = [] # Start with empty list, add valid loaded resources back

            for resource_state in loaded_resources:
                 resource = None
                 try:
                     # Check if loaded data is a state tuple or already an object
                     if isinstance(resource_state, tuple):
                         # If it's a tuple (from __getstate__), reconstruct the object
                         res_obj = Resource(0,0,0) # Create dummy object
                         res_obj.__setstate__(resource_state) # Populate from state
                         resource = res_obj
                     elif isinstance(resource_state, Resource):
                         # If it's already an object, ensure derived attributes are refreshed
                         resource = resource_state
                         resource.__setstate__(resource.__getstate__()) # Call setstate to refresh name, blocks_walk etc.
                     else:
                          print(f"Warning: Unknown data type found in loaded resources list: {type(resource_state)}")
                          continue # Skip unknown data

                     # Validate coordinates and place on map/list
                     if 0 <= resource.x < self.width and 0 <= resource.y < self.height:
                         if self.resource_map[resource.y, resource.x] is None:
                              self.resource_map[resource.y, resource.x] = resource
                              self.resources.append(resource) # Add to the primary list
                         else:
                              # Handle conflict: Tile already occupied on map after loading previous resource
                              print(f"Warning: Conflict loading resource '{getattr(resource,'name','?')}' at ({resource.x},{resource.y}). Tile already occupied on map. Overwriting map, keeping list resource.")
                              self.resource_map[resource.y, resource.x] = resource # Overwrite map
                              if resource not in self.resources: self.resources.append(resource) # Ensure it's in list
                     else:
                          print(f"Warning: Loaded resource at invalid coords ({resource.x},{resource.y}). Discarding.")

                 except Exception as e:
                      print(f"Error processing loaded resource state: {e}. Resource State: {resource_state}")
                      traceback.print_exc()
                      continue # Skip problematic resource

            # Recalculate walkability based on loaded terrain and resources
            self.update_walkability()
            # Clear agent dictionary; needs to be rebuilt after agents are loaded/created
            self.agents_by_id = {}
            print(f"World state loaded from {filename}. Resource count: {len(self.resources)}")
            # Verify workbench count after load
            wb_count = sum(1 for r in self.resources if r.type == cfg.RESOURCE_WORKBENCH)
            print(f"  Workbenches loaded: {wb_count}")
            return True

        except FileNotFoundError:
            print(f"Save file {filename} not found.")
            return False
        except Exception as e:
            print(f"Error loading world state: {e}")
            traceback.print_exc()
            return False