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
GRAY = (128, 128, 128) # Obstacle / Stone
BROWN = (139, 69, 19)  # Tree / Wood
RED = (200, 0, 0)     # Agent color
YELLOW = (255, 255, 0) # Food (Berries)
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
RESOURCE_REGEN_RATE = 0.01 # Chance per second resource quantity increases (if applicable)

# Agent Defaults
INITIAL_AGENT_COUNT = 10
MAX_HEALTH = 100
MAX_ENERGY = 100
MAX_HUNGER = 100 # Lower value means more hungry
MAX_THIRST = 100 # Lower value means more thirsty

# Needs Decay Rates (per simulation second)
HEALTH_REGEN_RATE = 0.05 # While resting
ENERGY_DECAY_RATE = 0.2
ENERGY_REGEN_RATE = 1.0 # While resting
HUNGER_INCREASE_RATE = 0.4 # Hunger value increases towards MAX_HUNGER
THIRST_INCREASE_RATE = 0.6 # Thirst value increases towards MAX_THIRST

# Action Costs / Effects
MOVE_ENERGY_COST = 0.1
EAT_HUNGER_REDUCTION = 40
DRINK_THIRST_REDUCTION = 50
REST_ENERGY_RECOVERY = 10
GATHER_ENERGY_COST = 0.5 # Phase 2+
CRAFT_ENERGY_COST = 1.0  # Phase 2+

# AI Settings
WANDER_RADIUS = 5
UTILITY_THRESHOLD = 0.3 # Minimum utility score to consider an action

# Phase 2+ Skill Settings
INITIAL_SKILL_LEVEL = 0
MAX_SKILL_LEVEL = 100
SKILL_INCREASE_RATE = 0.5 # Base increase per successful action

# Phase 2+ Crafting Recipes (Example)
# Format: 'result_item': {'ingredients': {'item1': count, 'item2': count}, 'skill': 'skill_name', 'min_level': level, 'workbench': bool}
RECIPES = {
    'CrudeAxe': {
        'ingredients': {'Wood': 1, 'Stone': 1},
        'skill': 'BasicCrafting',
        'min_level': 1,
        'workbench': False # Does it require a workbench?
    },
     'SmallShelter': {
         'ingredients': {'Wood': 5},
         'skill': 'BasicCrafting',
         'min_level': 5,
         'workbench': False
     }
    # Add more recipes here
}

# --- Terrain/Resource Codes ---
TERRAIN_GROUND = 0
TERRAIN_WATER = 1
TERRAIN_OBSTACLE = 2

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
    TERRAIN_OBSTACLE: GRAY,
}

# --- Map resource type to display info ---
RESOURCE_INFO = {
    RESOURCE_FOOD: {'color': YELLOW, 'name': 'Food Bush'},
    RESOURCE_WOOD: {'color': BROWN, 'name': 'Tree'},
    RESOURCE_STONE: {'color': GRAY, 'name': 'Rock'}, # Use slightly different gray?
    RESOURCE_WORKBENCH: {'color': (100, 60, 20), 'name': 'Workbench'}
    # Water is handled by terrain
}