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
SIMULATION_SPEED_FACTOR = 50 # How many simulation seconds pass per real second
DAY_LENGTH_SECONDS = 60 * 5 # How long a full day-night cycle lasts in simulation time

# World Generation
NUM_WATER_PATCHES = 5
WATER_PATCH_SIZE = (3, 8)
NUM_FOOD_SOURCES = 20
NUM_TREES = 15       # Phase 2+
NUM_ROCKS = 10       # Phase 2+
NUM_INITIAL_WORKBENCHES = 0 # Phase 3+ (Agents must build)
RESOURCE_REGEN_RATE = 0.01 # Chance per second resource quantity increases (if applicable)

# Agent Defaults
INITIAL_AGENT_COUNT = 10
MAX_HEALTH = 100
MAX_ENERGY = 100
MAX_HUNGER = 100 # Lower value means more hungry
MAX_THIRST = 100 # Lower value means more thirsty
INVENTORY_CAPACITY = 20 # Phase 2+

# Needs Decay Rates (per simulation second) - Adjusted Phase 1
HEALTH_REGEN_RATE = 0.05 # While resting
ENERGY_DECAY_RATE = 0.18 # Slightly reduced
ENERGY_REGEN_RATE = 1.0 # While resting
HUNGER_INCREASE_RATE = 0.45 # Slightly increased
THIRST_INCREASE_RATE = 0.65 # Slightly increased

# Action Costs / Effects
MOVE_ENERGY_COST = 0.1
EAT_HUNGER_REDUCTION = 40
DRINK_THIRST_REDUCTION = 50
REST_ENERGY_RECOVERY = 10 # Covered by ENERGY_REGEN_RATE
GATHER_ENERGY_COST = 0.5 # Phase 2+
CRAFT_ENERGY_COST = 1.0  # Phase 2+
INVENT_ENERGY_COST = 1.5 # Phase 3+
TEACH_ENERGY_COST = 0.3 # Phase 4+
LEARN_ENERGY_COST = 0.1 # Phase 4+

# AI Settings
WANDER_RADIUS = 5
UTILITY_THRESHOLD = 0.2 # Minimum utility score to consider an action (lowered slightly)
AGENT_VIEW_RADIUS = 10 # How far agents can "see" for finding resources/agents (used in find_nearest_*)

# Phase 2+ Skill Settings
INITIAL_SKILL_LEVEL = 0
MAX_SKILL_LEVEL = 100
SKILL_INCREASE_RATE = 0.5 # Base increase per successful action
TEACHING_BOOST_FACTOR = 4.0 # Multiplier for skill gain when taught (Phase 4+)

# Phase 2+ Crafting Recipes (Example)
# Format: 'result_item': {'ingredients': {'item1': count, 'item2': count}, 'skill': 'skill_name', 'min_level': level, 'workbench': bool}
RECIPES = {
    'CrudeAxe': {
        'ingredients': {'Wood': 1, 'Stone': 1},
        'skill': 'BasicCrafting',
        'min_level': 1,
        'workbench': False # Does it require a workbench?
    },
    'Workbench': { # Phase 3+
        'ingredients': {'Wood': 4, 'Stone': 2},
        'skill': 'BasicCrafting',
        'min_level': 5,
        'workbench': False # You don't need a workbench to make the first one
    },
     'SmallShelter': { # Phase 2+, updated Phase 3
         'ingredients': {'Wood': 5},
         'skill': 'BasicCrafting',
         'min_level': 10, # Increased level slightly
         'workbench': True # Let's say shelter needs more precise work
     },
     'StonePick': { # Example expansion
         'ingredients': {'Wood': 2, 'Stone': 3},
         'skill': 'BasicCrafting',
         'min_level': 8,
         'workbench': True
     }
    # Add more recipes here
}

# --- Terrain/Resource Codes ---
TERRAIN_GROUND = 0
TERRAIN_WATER = 1
TERRAIN_OBSTACLE = 2 # Impassable terrain like mountains (can use DARK_GRAY)

RESOURCE_NONE = 0
RESOURCE_FOOD = 1
RESOURCE_WATER = 2 # Water terrain implicitly provides water
RESOURCE_WOOD = 3  # Phase 2+
RESOURCE_STONE = 4 # Phase 2+
RESOURCE_WORKBENCH = 5 # Phase 3+

# --- Map terrain to colors ---
TERRAIN_COLORS = {
    TERRAIN_GROUND: GREEN,
    TERRAIN_WATER: BLUE,
    TERRAIN_OBSTACLE: DARK_GRAY, # Updated color
}

# --- Map resource type to display info ---
RESOURCE_INFO = {
    RESOURCE_FOOD: {'color': YELLOW, 'name': 'Food Bush', 'block_walk': False},
    RESOURCE_WOOD: {'color': BROWN, 'name': 'Tree', 'block_walk': True}, # Trees block walk
    RESOURCE_STONE: {'color': GRAY, 'name': 'Rock', 'block_walk': True}, # Rocks block walk
    RESOURCE_WORKBENCH: {'color': ORANGE, 'name': 'Workbench', 'block_walk': False} # Workbench usually doesn't block
    # Water is handled by terrain
}

# Pathfinding Settings
MAX_PATHFINDING_ITERATIONS = 2000 # Limit A* search steps for performance

# Social Settings (Phase 4+)
SIGNAL_RANGE = 15
HELPING_RELATIONSHIP_THRESHOLD = -0.2 # Minimum relationship to offer help
TEACHING_RELATIONSHIP_THRESHOLD = 0.1 # Minimum relationship to offer teaching
LEARNING_RELATIONSHIP_THRESHOLD = -0.1 # Minimum relationship to accept learning
PASSIVE_LEARN_CHANCE = 0.6 # Chance to learn recipe from observed crafting signal