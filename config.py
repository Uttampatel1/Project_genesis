# config.py
import pygame

# Screen/Display Settings
SCREEN_WIDTH = 1000
SCREEN_HEIGHT = 750
SIDE_PANEL_WIDTH = 250 # For UI Info
GAME_WIDTH = SCREEN_WIDTH - SIDE_PANEL_WIDTH
CELL_SIZE = 20
GRID_WIDTH = GAME_WIDTH // CELL_SIZE
GRID_HEIGHT = SCREEN_HEIGHT // CELL_SIZE
FPS = 15 # Simulation steps per second

# --- Debug Flags ---
DEBUG_PATHFINDING = False # Print pathfinding details
DEBUG_AGENT_AI = False    # Print agent utility scores
DEBUG_AGENT_CHOICE = True   # Print chosen action and basic info
DEBUG_AGENT_ACTIONS = True  # Print action execution steps (Gather, Craft, Eat, etc.)
DEBUG_SOCIAL = False      # Print social interactions (signals, learning, helping)
DEBUG_KNOWLEDGE = True    # Print knowledge updates (recipes, locations)
DEBUG_WORLD_GEN = False   # Print detailed world gen steps (can be verbose)
DEBUG_INVENTION = True    # Print invention attempt details

# Colors
WHITE = (255, 255, 255)
BLACK = (0, 0, 0)
GREEN = (0, 150, 0)   # Ground
BLUE = (0, 0, 200)    # Water
GRAY = (128, 128, 128) # Stone Resource Color (distinct from Dark Gray terrain)
DARK_GRAY = (80, 80, 80) # Obstacle Terrain
BROWN = (139, 69, 19)  # Tree / Wood
RED = (200, 0, 0)     # Agent color
YELLOW = (255, 255, 0) # Food (Berries)
ORANGE = (255, 165, 0) # Workbench Color
UI_BG_COLOR = (50, 50, 50)
UI_TEXT_COLOR = (200, 200, 200)

# Time System
SIMULATION_SPEED_FACTOR = 50 # How many simulation seconds pass per real second
DAY_LENGTH_SECONDS = 60 * 10 # Duration of a full day-night cycle in simulation seconds

# World Generation
NUM_WATER_PATCHES = 5
WATER_PATCH_SIZE = (3, 8)
NUM_FOOD_SOURCES = 30
NUM_TREES = 25
NUM_ROCKS = 15
NUM_INITIAL_WORKBENCHES = 1 # Start with one workbench for testing Phase 3+
RESOURCE_REGEN_RATE = 0.005 # Chance per sim second resource quantity increases

# Agent Defaults
INITIAL_AGENT_COUNT = 5 # Reduced for easier testing/observation
MAX_HEALTH = 100
MAX_ENERGY = 100
MAX_HUNGER = 100 # Higher value means MORE hungry (0 = full)
MAX_THIRST = 100 # Higher value means MORE thirsty (0 = full)
INVENTORY_CAPACITY = 20
BASE_INTELLIGENCE = 0.5 # Affects invention speed

# Needs Decay Rates (per simulation second)
HEALTH_REGEN_RATE = 0.1  # While resting and needs met
ENERGY_DECAY_RATE = 0.20
ENERGY_REGEN_RATE = 1.5  # While resting
HUNGER_INCREASE_RATE = 0.50
THIRST_INCREASE_RATE = 0.70

# Action Costs / Effects (Durations in sim seconds, Costs per action/tick)
MOVE_ENERGY_COST = 0.08    # Energy cost per step moved
EAT_HUNGER_REDUCTION = 50
DRINK_THIRST_REDUCTION = 60
GATHER_BASE_DURATION = 2.0 # Base time to gather 1 unit
GATHER_ENERGY_COST = 0.6   # Base energy cost per completed gather action
CRAFT_BASE_DURATION = 4.0  # Base time to craft an item
CRAFT_ENERGY_COST = 1.2    # Energy cost per completed craft action
INVENT_BASE_DURATION = 8.0 # Base time for an invention attempt cycle
INVENT_ENERGY_COST = 2.0   # Energy cost per invention attempt cycle
# Social costs (Phase 4+)
TEACH_ENERGY_COST = 0.5
LEARN_ENERGY_COST = 0.2
HELP_ENERGY_COST = 0.3

# AI Settings
WANDER_RADIUS = 6        # Max distance for random wander target
UTILITY_THRESHOLD = 0.15 # Minimum utility score to consider an action (except Wander)
AGENT_VIEW_RADIUS = 25   # How far agents can "see" for finding resources (BFS limit)
WORKBENCH_INTERACTION_RADIUS = 1 # Chebyshev distance (0=on tile, 1=adjacent) to use workbench
INVENTION_ITEM_TYPES_THRESHOLD = 3 # Min different item types in inventory to attempt invention

# Skill Settings
INITIAL_SKILL_LEVEL = 0
MAX_SKILL_LEVEL = 100
SKILL_INCREASE_RATE = 0.8 # Base increase per successful action (adjusted by diminishing returns)
TEACHING_BOOST_FACTOR = 5.0 # Multiplier for skill gain when taught

# Tool Settings (Multipliers for speed/efficiency)
TOOL_EFFICIENCY = {
    'CrudeAxe': 1.8,
    'StonePick': 1.8,
    # Add other tools here (e.g., 'IronAxe': 3.0)
}

# Crafting Recipes (Phase 3 Update)
# Format: 'result_item': {'ingredients': {'item1': count,...}, 'skill': 'skill_name', 'min_level': level, 'workbench': bool}
RECIPES = {
    'Workbench': {
        'ingredients': {'Wood': 5, 'Stone': 2},
        'skill': 'BasicCrafting',
        'min_level': 3, # Requires some crafting skill
        'workbench': False # Can make the first one anywhere
    },
    'CrudeAxe': {
        'ingredients': {'Wood': 2, 'Stone': 1},
        'skill': 'BasicCrafting',
        'min_level': 1, # Low skill requirement
        'workbench': False # Basic axe needs no workbench
    },
    'StonePick': {
        'ingredients': {'Wood': 2, 'Stone': 3},
        'skill': 'BasicCrafting',
        'min_level': 5, # Higher skill than axe
        'workbench': True # Requires workbench
     },
     'SmallShelter': { # Example structure for later
         'ingredients': {'Wood': 8},
         'skill': 'BasicCrafting',
         'min_level': 8,
         'workbench': True # Requires workbench
     },
    # Add more recipes (tools, food, shelter parts, etc.)
}

# Terrain/Resource Codes
TERRAIN_GROUND = 0
TERRAIN_WATER = 1
TERRAIN_OBSTACLE = 2 # Impassable terrain

RESOURCE_NONE = 0
RESOURCE_FOOD = 1
RESOURCE_WATER = 2 # Water terrain implicitly provides water resource
RESOURCE_WOOD = 3
RESOURCE_STONE = 4
RESOURCE_WORKBENCH = 5 # Workbench object

# Map terrain to colors
TERRAIN_COLORS = {
    TERRAIN_GROUND: GREEN,
    TERRAIN_WATER: BLUE,
    TERRAIN_OBSTACLE: DARK_GRAY,
}

# Map resource type to display info (Phase 3 Update)
# 'block_walk': Does this resource prevent movement onto its tile?
# 'max_quantity': Starting/max amount for depletable resources.
# 'regen': Regeneration chance per sim second (0 = no regen).
RESOURCE_INFO = {
    RESOURCE_FOOD: {'color': YELLOW, 'name': 'Food Bush', 'block_walk': False, 'max_quantity': 5, 'regen': 0.01},
    RESOURCE_WOOD: {'color': BROWN, 'name': 'Tree', 'block_walk': True, 'max_quantity': 8, 'regen': 0.002},
    RESOURCE_STONE: {'color': GRAY, 'name': 'Rock', 'block_walk': True, 'max_quantity': 10, 'regen': 0.001},
    RESOURCE_WORKBENCH: {'color': ORANGE, 'name': 'Workbench', 'block_walk': False, 'max_quantity': 1, 'regen': 0}, # Doesn't block, doesn't regen
    # Water (RESOURCE_WATER) is handled implicitly by terrain, not placed as an object.
}

# Pathfinding Settings
MAX_PATHFINDING_ITERATIONS = 3500 # Max steps A* will search

# Social Settings (Phase 4+)
SIGNAL_RANGE = 18
HELPING_RELATIONSHIP_THRESHOLD = -0.3
HELPING_INTERACTION_RADIUS = 2
TEACHING_RELATIONSHIP_THRESHOLD = 0.0
LEARNING_RELATIONSHIP_THRESHOLD = -0.2
PASSIVE_LEARN_CHANCE = 0.5