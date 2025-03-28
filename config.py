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
DEBUG_SOCIAL = True       # Print social interactions (signals, learning, helping)
DEBUG_KNOWLEDGE = False   # Print knowledge updates (recipes, locations)
DEBUG_WORLD_GEN = False   # Print detailed world gen steps (can be verbose)

# Colors
WHITE = (255, 255, 255)
BLACK = (0, 0, 0)
GREEN = (0, 150, 0)   # Ground
BLUE = (0, 0, 200)    # Water
GRAY = (128, 128, 128) # Obstacle / Stone Resource
DARK_GRAY = (80, 80, 80) # Obstacle Terrain
BROWN = (139, 69, 19)  # Tree / Wood
RED = (200, 0, 0)     # Agent color
YELLOW = (255, 255, 0) # Food (Berries)
ORANGE = (255, 165, 0) # Workbench Color
UI_BG_COLOR = (50, 50, 50)
UI_TEXT_COLOR = (200, 200, 200)

# Time System
SIMULATION_SPEED_FACTOR = 50 # How many simulation seconds pass per real second (e.g., 50 means 1 min real time = ~50 min sim time)
DAY_LENGTH_SECONDS = 60 * 10 # How long a full day-night cycle lasts in simulation time (e.g., 600 sim seconds = 1 day)

# World Generation
NUM_WATER_PATCHES = 5
WATER_PATCH_SIZE = (3, 8)
NUM_FOOD_SOURCES = 30 # Increased food slightly
NUM_TREES = 25       # Increased wood slightly
NUM_ROCKS = 15       # Increased stone slightly
NUM_INITIAL_WORKBENCHES = 1 # Start with one workbench for testing Phase 3+
RESOURCE_REGEN_RATE = 0.005 # Chance per sim second resource quantity increases (if applicable) - Reduced regen

# Agent Defaults
INITIAL_AGENT_COUNT = 10
MAX_HEALTH = 100
MAX_ENERGY = 100
MAX_HUNGER = 100 # Higher value means MORE hungry (0 = full)
MAX_THIRST = 100 # Higher value means MORE thirsty (0 = full)
INVENTORY_CAPACITY = 20

# Needs Decay Rates (per simulation second)
HEALTH_REGEN_RATE = 0.1  # While resting and needs met
ENERGY_DECAY_RATE = 0.20 # Increased energy decay slightly
ENERGY_REGEN_RATE = 1.5  # While resting
HUNGER_INCREASE_RATE = 0.50 # Rate at which hunger value increases
THIRST_INCREASE_RATE = 0.70 # Rate at which thirst value increases

# Action Costs / Effects
MOVE_ENERGY_COST = 0.08 # Reduced move cost slightly
EAT_HUNGER_REDUCTION = 50
DRINK_THIRST_REDUCTION = 60
GATHER_BASE_DURATION = 2.0 # Base time in sim seconds to gather 1 unit
GATHER_ENERGY_COST = 0.6   # Base energy cost per gather action (can be modified by tools/skill)
CRAFT_BASE_DURATION = 4.0  # Base time in sim seconds to craft an item
CRAFT_ENERGY_COST = 1.2
INVENT_BASE_DURATION = 8.0 # Base time in sim seconds for an invention attempt
INVENT_ENERGY_COST = 2.0
TEACH_ENERGY_COST = 0.5
LEARN_ENERGY_COST = 0.2
HELP_ENERGY_COST = 0.3    # Energy cost for the helper when performing a help action

# AI Settings
WANDER_RADIUS = 6
UTILITY_THRESHOLD = 0.15 # Minimum utility score to consider an action (lower means more exploration)
AGENT_VIEW_RADIUS = 25   # How far agents can "see" for finding resources/agents (used in find_nearest_*)
WORKBENCH_INTERACTION_RADIUS = 1 # Chebyshev distance (0=on tile, 1=adjacent) required to use workbench

# Skill Settings
INITIAL_SKILL_LEVEL = 0
MAX_SKILL_LEVEL = 100
SKILL_INCREASE_RATE = 0.8 # Base increase per successful action (adjusted by diminishing returns)
TEACHING_BOOST_FACTOR = 5.0 # Multiplier for skill gain when taught

# Tool Settings (Multipliers for speed/efficiency)
TOOL_EFFICIENCY = {
    'CrudeAxe': 1.8,
    'StonePick': 1.8,
    # Add other tools here
}

# Crafting Recipes
# Format: 'result_item': {'ingredients': {'item1': count,...}, 'skill': 'skill_name', 'min_level': level, 'workbench': bool}
RECIPES = {
    'CrudeAxe': {
        'ingredients': {'Wood': 2, 'Stone': 1}, # Adjusted ingredients slightly
        'skill': 'BasicCrafting',
        'min_level': 1,
        'workbench': False
    },
    'StonePick': {
        'ingredients': {'Wood': 2, 'Stone': 3},
        'skill': 'BasicCrafting',
        'min_level': 5, # Requires slightly more skill
        'workbench': True # Let's require workbench for a better tool
     },
    'Workbench': {
        'ingredients': {'Wood': 5, 'Stone': 2}, # Increased wood cost
        'skill': 'BasicCrafting',
        'min_level': 3, # Lowered skill requirement for first workbench
        'workbench': False # Can make the first one anywhere
    },
     'SmallShelter': {
         'ingredients': {'Wood': 8}, # Increased wood cost
         'skill': 'BasicCrafting',
         'min_level': 8,
         'workbench': True # Requires workbench
     },
    # Add more recipes here (e.g., better tools, food items, containers)
    # 'WoodenTorch': {'ingredients': {'Wood': 1}, 'skill': 'BasicCrafting', 'min_level': 2, 'workbench': False},
    # 'CookedFood': {'ingredients': {'Food': 1, 'Wood': 1}, 'skill': 'Cooking', 'min_level': 1, 'workbench': True}, # Requires 'Campfire' object?
}

# Terrain/Resource Codes
TERRAIN_GROUND = 0
TERRAIN_WATER = 1
TERRAIN_OBSTACLE = 2 # Impassable terrain

RESOURCE_NONE = 0
RESOURCE_FOOD = 1
RESOURCE_WATER = 2 # Water terrain implicitly provides water
RESOURCE_WOOD = 3
RESOURCE_STONE = 4
RESOURCE_WORKBENCH = 5

# Map terrain to colors
TERRAIN_COLORS = {
    TERRAIN_GROUND: GREEN,
    TERRAIN_WATER: BLUE,
    TERRAIN_OBSTACLE: DARK_GRAY,
}

# Map resource type to display info
RESOURCE_INFO = {
    RESOURCE_FOOD: {'color': YELLOW, 'name': 'Food Bush', 'block_walk': False, 'max_quantity': 5, 'regen': 0.01},
    RESOURCE_WOOD: {'color': BROWN, 'name': 'Tree', 'block_walk': True, 'max_quantity': 8, 'regen': 0.002}, # Trees block walk, slower regen
    RESOURCE_STONE: {'color': GRAY, 'name': 'Rock', 'block_walk': True, 'max_quantity': 10, 'regen': 0.001}, # Rocks block walk, very slow regen
    RESOURCE_WORKBENCH: {'color': ORANGE, 'name': 'Workbench', 'block_walk': False, 'max_quantity': 1, 'regen': 0} # Workbench doesn't block, no regen
    # Water is handled by terrain
}

# Pathfinding Settings
MAX_PATHFINDING_ITERATIONS = 3000 # Increased limit slightly

# Social Settings
SIGNAL_RANGE = 18 # Increased broadcast range
HELPING_RELATIONSHIP_THRESHOLD = -0.3 # Minimum relationship to offer help (slightly more lenient)
HELPING_INTERACTION_RADIUS = 2     # Max Chebyshev distance to perform help action
TEACHING_RELATIONSHIP_THRESHOLD = 0.0 # Minimum relationship to offer teaching (neutral or positive)
LEARNING_RELATIONSHIP_THRESHOLD = -0.2 # Minimum relationship to accept learning (not strongly disliked)
PASSIVE_LEARN_CHANCE = 0.5 # Base chance to learn recipe from observed crafting signal (modified by distance, relationship)