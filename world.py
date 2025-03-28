# world.py
import random
import numpy as np
import config as cfg
from pathfinding_utils import create_walkability_matrix
import pickle # For saving/loading
import time # For simple timing/debug if needed
import math # For distance calculation in arrival check fix
import traceback # For error logging

class Resource:
    """ Represents a resource node in the world. """
    def __init__(self, type, x, y, quantity=None, max_quantity=None, regen_rate=None):
        self.type = type
        self.x = x
        self.y = y
        res_info = cfg.RESOURCE_INFO.get(type, {})
        # Use defaults from config if not provided
        self.max_quantity = max_quantity if max_quantity is not None else res_info.get('max_quantity', 1)
        self.quantity = quantity if quantity is not None else self.max_quantity # Start full by default
        self.regen_rate = regen_rate if regen_rate is not None else res_info.get('regen', 0)

        self.name = res_info.get('name', 'Unknown')
        self.blocks_walk = res_info.get('block_walk', False)

    def consume(self, amount=1):
        """ Consumes a specified amount of the resource, returns amount actually consumed. """
        consumed = min(amount, self.quantity)
        self.quantity -= consumed
        return consumed

    def update(self, dt_sim_seconds):
        """ Updates resource quantity based on regeneration rate. """
        if self.quantity < self.max_quantity and self.regen_rate > 0:
             # Regen check happens probabilistically based on rate and time delta
             if random.random() < self.regen_rate * dt_sim_seconds:
                 self.quantity = min(self.max_quantity, self.quantity + 1)

    def is_depleted(self):
        """ Returns True if the resource quantity is zero or less. """
        return self.quantity <= 0

    # --- Persistence Methods ---
    def __getstate__(self):
        """ Define what gets pickled. """
        # Only store core data, derived data (name, blocks_walk) will be set on load
        return (self.type, self.x, self.y, self.quantity, self.max_quantity, self.regen_rate)

    def __setstate__(self, state):
        """ Define how to unpickle and reinitialize derived attributes. """
        self.type, self.x, self.y, self.quantity, self.max_quantity, self.regen_rate = state
        # Re-initialize derived attributes from config
        res_info = cfg.RESOURCE_INFO.get(self.type, {})
        self.name = res_info.get('name', 'Unknown')
        self.blocks_walk = res_info.get('block_walk', False)
        # Handle potential None state from older saves if necessary
        if self.regen_rate is None: self.regen_rate = res_info.get('regen', 0)
        if self.max_quantity is None: self.max_quantity = res_info.get('max_quantity', 1)


class World:
    """ Manages the simulation grid, terrain, resources, and time. """
    def __init__(self, width, height):
        self.width = width
        self.height = height
        self.terrain_map = np.full((height, width), cfg.TERRAIN_GROUND, dtype=int)
        # self.resource_map maps (y, x) -> Resource object or None
        self.resource_map = np.full((height, width), None, dtype=object)
        # self.resources is a list of all Resource objects for easier iteration (e.g., for update)
        self.resources = []
        self.walkability_matrix = None
        self.simulation_time = 0.0
        self.day_time = 0.0
        self.day_count = 0
        self._generate_world()
        self.update_walkability() # Initial walkability calc
        self.agents_by_id = {} # Added for quick lookup

    def _generate_world(self):
        """ Generates the initial terrain and resource layout. """
        print("Generating world terrain and resources...")
        start_time = time.time()

        # 1. Water patches
        if cfg.DEBUG_WORLD_GEN: print(f"  Placing {cfg.NUM_WATER_PATCHES} water patches...")
        for _ in range(cfg.NUM_WATER_PATCHES):
            size_x = random.randint(cfg.WATER_PATCH_SIZE[0], cfg.WATER_PATCH_SIZE[1])
            size_y = random.randint(cfg.WATER_PATCH_SIZE[0], cfg.WATER_PATCH_SIZE[1])
            start_x = random.randint(0, self.width - size_x)
            start_y = random.randint(0, self.height - size_y)
            self.terrain_map[start_y:start_y+size_y, start_x:start_x+size_x] = cfg.TERRAIN_WATER

        # 2. Place Resources
        if cfg.DEBUG_WORLD_GEN: print("  Placing resources...")
        resource_placements = {
            cfg.RESOURCE_FOOD: cfg.NUM_FOOD_SOURCES,
            cfg.RESOURCE_WOOD: cfg.NUM_TREES,      # Phase 2
            cfg.RESOURCE_STONE: cfg.NUM_ROCKS,     # Phase 2
            cfg.RESOURCE_WORKBENCH: cfg.NUM_INITIAL_WORKBENCHES # Phase 3+
        }

        for res_type, count in resource_placements.items():
            if count == 0: continue
            placed = 0
            attempts = 0
            max_attempts = count * 150 # Give ample attempts
            res_info = cfg.RESOURCE_INFO.get(res_type, {})
            res_name = res_info.get('name', f'Type {res_type}')
            if cfg.DEBUG_WORLD_GEN: print(f"    Attempting to place {count} {res_name}...")

            while placed < count and attempts < max_attempts:
                x = random.randint(0, self.width - 1)
                y = random.randint(0, self.height - 1)
                # Check if terrain is ground AND tile is currently empty
                is_valid_terrain = (self.terrain_map[y, x] == cfg.TERRAIN_GROUND)
                is_empty = self.resource_map[y, x] is None

                if is_valid_terrain and is_empty:
                    # Create resource with defaults from config
                    resource = Resource(res_type, x, y)
                    if self.add_world_object(resource, x, y):
                        placed += 1
                attempts += 1

            if placed < count:
                 print(f"    Warning: Could only place {placed}/{count} of {res_name} (tried {attempts} times)")
            elif cfg.DEBUG_WORLD_GEN:
                 print(f"    Successfully placed {placed}/{count} of {res_name}.")


        # --- World Generation Sanity Check ---
        if cfg.DEBUG_WORLD_GEN: print("\n--- World Generation Report ---")
        final_resource_counts = {}
        for res in self.resources:
            res_type = getattr(res, 'type', 'UNKNOWN')
            final_resource_counts[res_type] = final_resource_counts.get(res_type, 0) + 1
        if cfg.DEBUG_WORLD_GEN: print(f"Resource Counts in self.resources list ({len(self.resources)} total): {final_resource_counts}")

        map_counts = {}
        for y in range(self.height):
            for x in range(self.width):
                res = self.resource_map[y, x]
                if res:
                     res_type = getattr(res, 'type', 'UNKNOWN')
                     map_counts[res_type] = map_counts.get(res_type, 0) + 1
        if cfg.DEBUG_WORLD_GEN: print(f"Resource Counts found on resource_map: {map_counts}")
        if map_counts.get(cfg.RESOURCE_WOOD, 0) == 0 and cfg.NUM_TREES > 0: print(">>> WARNING: NO WOOD PLACED ON MAP!")
        if map_counts.get(cfg.RESOURCE_STONE, 0) == 0 and cfg.NUM_ROCKS > 0: print(">>> WARNING: NO STONE PLACED ON MAP!")
        if cfg.DEBUG_WORLD_GEN: print(f"World generation took {time.time() - start_time:.2f} seconds.")
        if cfg.DEBUG_WORLD_GEN: print("--- End World Generation Report ---\n")
        # --- End Report ---


    def update_walkability(self, agent_positions=None):
         """
         Creates/updates walkability matrix based on terrain and blocking objects.
         If agent_positions is provided, returns a temporary matrix with agents blocked.
         Otherwise, updates self.walkability_matrix.
         """
         # Base walkability from terrain and blocking resources
         matrix = create_walkability_matrix(self.terrain_map, self.resource_map)

         if agent_positions:
             # Return a temporary copy with agents marked as blocked
             temp_matrix = matrix.copy()
             for x, y in agent_positions:
                 if 0 <= x < self.width and 0 <= y < self.height:
                     temp_matrix[y, x] = 0 # Mark agent position as non-walkable
             return temp_matrix
         else:
             # Update the persistent walkability matrix for the world state
             self.walkability_matrix = matrix
             return self.walkability_matrix

    def update(self, dt_real_seconds, agents):
        """ Updates world time, resource regeneration, and agent lookup dictionary. """
        dt_sim_seconds = dt_real_seconds * cfg.SIMULATION_SPEED_FACTOR
        self.simulation_time += dt_sim_seconds
        self.day_time = (self.day_time + dt_sim_seconds) % cfg.DAY_LENGTH_SECONDS
        self.day_count = int(self.simulation_time // cfg.DAY_LENGTH_SECONDS)

        # Update resources (regen)
        for resource in self.resources: # Iterate the list
            resource.update(dt_sim_seconds)
            # Optional: Remove depleted resources entirely? Or just let them sit at 0?
            # If removing, need to handle self.resource_map and self.resources list carefully.
            # For now, let them stay at 0.

        # Update agent dictionary for quick lookups elsewhere
        self.agents_by_id = {agent.id: agent for agent in agents if agent.health > 0}


    def get_terrain(self, x, y):
        """ Returns terrain type at (x, y) or OBSTACLE if out of bounds. """
        if 0 <= x < self.width and 0 <= y < self.height: return self.terrain_map[y, x]
        return cfg.TERRAIN_OBSTACLE

    def get_resource(self, x, y):
        """ Returns Resource object at (x, y) or None. """
        if 0 <= x < self.width and 0 <= y < self.height: return self.resource_map[y, x]
        return None

    def consume_resource_at(self, x, y, amount=1):
        """ Consumes resource at location, returns amount actually consumed. Handles Water implicitly. """
        if not (0 <= x < self.width and 0 <= y < self.height): return 0

        resource = self.resource_map[y, x]
        if resource and not resource.is_depleted():
            consumed = resource.consume(amount)
            # Optionally remove from map/list if depleted and non-regenerating?
            # if resource.is_depleted() and resource.regen_rate <= 0:
            #    self.remove_world_object(x,y) # Needs careful implementation
            return consumed
        elif self.terrain_map[y, x] == cfg.TERRAIN_WATER:
            # Water is infinite for now
            return amount
        return 0

    def find_nearest_resource(self, start_x, start_y, resource_type, max_dist=cfg.AGENT_VIEW_RADIUS):
        """
        BFS to find nearest resource tile of a given type.
        Returns (goal_pos, stand_pos, distance) or (None, None, inf).
        goal_pos: The (x, y) of the resource itself.
        stand_pos: A walkable (x, y) adjacent to or on the resource tile to interact from.
        """
        q = [(start_x, start_y, 0)]; visited = set([(start_x, start_y)])
        # Use the world's current base walkability (ignoring temp agents for broad search)
        walkability = self.walkability_matrix
        if not (0 <= start_x < self.width and 0 <= start_y < self.height):
             return None, None, float('inf') # Invalid start

        # Check if starting on a walkable tile
        # start_is_walkable = walkability[start_y, start_x] == 1
        # BFS needs to explore *from* potentially non-walkable tiles if the *target* might be adjacent

        while q:
            curr_x, curr_y, dist = q.pop(0)

            if dist >= max_dist: continue # Stop searching beyond max_dist

            # --- Check CURRENT tile for the target resource ---
            resource = self.get_resource(curr_x, curr_y)
            is_water_tile = self.get_terrain(curr_x, curr_y) == cfg.TERRAIN_WATER

            target_found = False
            goal_pos = (curr_x, curr_y)
            stand_pos = None

            if resource_type == cfg.RESOURCE_WATER:
                if is_water_tile:
                    # Need to find an adjacent walkable spot to drink from
                    stand_pos = self._find_adjacent_walkable(curr_x, curr_y, walkability)
                    if stand_pos: target_found = True
            else:
                # Check for non-water resource types
                if resource and resource.type == resource_type and not resource.is_depleted():
                    # Found the resource. Now find where to stand.
                    if walkability[curr_y, curr_x] == 1:
                        # Resource is on a walkable tile (e.g., workbench), stand on it.
                        stand_pos = (curr_x, curr_y)
                        target_found = True
                    else:
                        # Resource blocks walking (e.g., tree, rock), find adjacent walkable.
                        stand_pos = self._find_adjacent_walkable(curr_x, curr_y, walkability)
                        if stand_pos: target_found = True

            if target_found:
                # Found the resource and a valid standing spot
                # Calculate path distance later if needed, BFS dist is grid distance
                if cfg.DEBUG_PATHFINDING: print(f"  BFS Found: {cfg.RESOURCE_INFO.get(resource_type,{}).get('name','?')} at {goal_pos}, stand at {stand_pos}, grid dist {dist}")
                return goal_pos, stand_pos, dist

            # --- Explore neighbors ---
            # Explore neighbors only if the current tile is walkable OR if we haven't found the target yet
            # This allows searching 'through' non-walkable areas if the target resource might be on the other side
            explore_neighbors = True # Simplified: always explore neighbors within distance limit
            # Could optimize: if walkability[curr_y, curr_x] == 0 and dist > 0: explore_neighbors = False?

            if explore_neighbors:
                neighbors = [(0,1), (0,-1), (1,0), (-1,0), (1,1), (1,-1), (-1,1), (-1,-1)]
                random.shuffle(neighbors) # Avoid directional bias
                for dx, dy in neighbors:
                    nx, ny = curr_x + dx, curr_y + dy
                    # Check bounds and visited
                    if 0 <= nx < self.width and 0 <= ny < self.height and (nx, ny) not in visited:
                         visited.add((nx, ny))
                         # Add to queue regardless of walkability to check the tile itself
                         q.append((nx, ny, dist + 1))

        # Resource type not found within max_dist
        return None, None, float('inf')


    def _find_adjacent_walkable(self, x, y, walkability_matrix):
        """ Finds a walkable tile adjacent (including diagonals) to (x, y) using the provided matrix. """
        for dx, dy in [(0,1), (0,-1), (1,0), (-1,0), (1,1), (1,-1), (-1,1), (-1,-1)]:
            nx, ny = x + dx, y + dy
            if 0 <= nx < self.width and 0 <= ny < self.height and walkability_matrix[ny, nx] == 1:
                return (nx, ny) # Return the first valid adjacent tile found
        return None

    def add_world_object(self, obj, x, y):
        """ Adds object (like Resource), updates map and list, and walkability if needed. """
        if 0 <= x < self.width and 0 <= y < self.height:
             # Place only on ground and if tile is empty
             if self.terrain_map[y, x] == cfg.TERRAIN_GROUND and self.resource_map[y, x] is None:
                 self.resource_map[y, x] = obj
                 if isinstance(obj, Resource):
                     # Avoid adding duplicates if called multiple times
                     if obj not in self.resources:
                          self.resources.append(obj)
                 # Update walkability if the new object blocks movement
                 if getattr(obj, 'blocks_walk', False):
                     self.update_walkability() # Recalculate the base walkability matrix
                 return True
        return False

    def remove_world_object(self, x, y):
         """ Removes object at (x,y), updates map, list, and walkability. """
         if 0 <= x < self.width and 0 <= y < self.height:
             obj = self.resource_map[y, x]
             if obj is not None:
                 self.resource_map[y, x] = None
                 if isinstance(obj, Resource) and obj in self.resources:
                     self.resources.remove(obj)
                 # Update walkability if a blocking object was removed
                 if getattr(obj, 'blocks_walk', False):
                     self.update_walkability()
                 return True
         return False

    def get_agent_by_id(self, agent_id):
        """ Returns the agent object with the given ID, or None if not found/dead. """
        return self.agents_by_id.get(agent_id)


    # --- Persistence ---
    def save_state(self, filename="world_save.pkl"):
        """ Saves world state using pickle. """
        # Note: self.agents_by_id is transient, rebuild on load
        state = { 'width': self.width, 'height': self.height, 'terrain_map': self.terrain_map,
                  'resources': self.resources, # Save the list of resource objects
                  'simulation_time': self.simulation_time,
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
            self.resources = state['resources'] # Load the list

            # Rebuild the resource_map from the loaded resources list
            self.resource_map = np.full((self.height, self.width), None, dtype=object)
            valid_resources = []
            for resource in self.resources:
                 # Ensure loaded resources have derived attributes correctly set
                 if not hasattr(resource, 'name'): # Simple check if __setstate__ might be needed
                      resource.__setstate__(resource.__getstate__()) # Call setstate to re-init derived attrs

                 if 0 <= resource.x < self.width and 0 <= resource.y < self.height:
                     if self.resource_map[resource.y, resource.x] is None:
                          self.resource_map[resource.y, resource.x] = resource
                          valid_resources.append(resource)
                     else: 
                        print(f"Warning: Conflict loading resource '{getattr(resource,'name','?')}' at ({resource.x},{resource.y}). Overwriting existing map entry? Keeping list version.")
                        # Decide on conflict resolution: Keep first? Keep loaded? Log error?
                        # Current code keeps the one from the list, overwrites map if needed.
                        self.resource_map[resource.y, resource.x] = resource
                        valid_resources.append(resource) # Keep it in the list too
                 else: print(f"Warning: Loaded resource at invalid coords ({resource.x},{resource.y}). Discarding.")
            self.resources = valid_resources # Keep only valid resources

            self.update_walkability() # Recalculate walkability based on loaded state
            self.agents_by_id = {} # Clear agent dict, needs to be rebuilt after agents are loaded/created
            print(f"World state loaded from {filename}. Resource count: {len(self.resources)}")
            return True
        except FileNotFoundError: print(f"Save file {filename} not found."); return False
        except Exception as e: print(f"Error loading world state: {e}"); traceback.print_exc(); return False