# Contents of config.py
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
DEBUG_KNOWLEDGE = False   # Print knowledge updates (recipes, locations) - Less verbose now
DEBUG_WORLD_GEN = False   # Print detailed world gen steps (can be verbose)
DEBUG_INVENTION = False   # Print invention attempt details

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
PURPLE = (128, 0, 128) # Signal visualization color
UI_BG_COLOR = (50, 50, 50)
UI_TEXT_COLOR = (200, 200, 200)

# Time System
SIMULATION_SPEED_FACTOR = 50 # How many simulation seconds pass per real second
DAY_LENGTH_SECONDS = 60 * 10 # Duration of a full day-night cycle in simulation seconds

# World Generation
NUM_WATER_PATCHES = 5
WATER_PATCH_SIZE = (3, 8)
NUM_FOOD_SOURCES = 35 # Increased slightly
NUM_TREES = 25
NUM_ROCKS = 15
NUM_INITIAL_WORKBENCHES = 1 # Start with one workbench for testing Phase 3+
RESOURCE_REGEN_RATE = 0.005 # Chance per sim second resource quantity increases

# Agent Defaults
INITIAL_AGENT_COUNT = 5 # Keep small for observation
MAX_HEALTH = 100
MAX_ENERGY = 100
MAX_HUNGER = 100 # Higher value means MORE hungry (0 = full)
MAX_THIRST = 100 # Higher value means MORE thirsty (0 = full)
INVENTORY_CAPACITY = 20
BASE_INTELLIGENCE = 0.5 # Affects invention speed

# Needs Decay Rates (per simulation second)
HEALTH_REGEN_RATE = 0.15 # Slightly increased regen when resting
ENERGY_DECAY_RATE = 0.18 # Slightly lower base decay
ENERGY_REGEN_RATE = 1.5  # While resting
HUNGER_INCREASE_RATE = 0.40 # <<< SIGNIFICANTLY DECREASED from 0.50
THIRST_INCREASE_RATE = 0.55 # <<< SIGNIFICANTLY DECREASED from 0.65

# Action Costs / Effects (Durations in sim seconds, Costs per action/tick)
MOVE_ENERGY_COST = 0.07    # Slightly lower move cost
EAT_HUNGER_REDUCTION = 60  # <<< INCREASED from 50
DRINK_THIRST_REDUCTION = 70  # <<< INCREASED from 60
GATHER_BASE_DURATION = 2.0 # Base time to gather 1 unit
GATHER_ENERGY_COST = 0.5   # Slightly lower gather cost
CRAFT_BASE_DURATION = 4.0  # Base time to craft an item
CRAFT_ENERGY_COST = 1.0    # Slightly lower craft cost
INVENT_BASE_DURATION = 8.0 # Base time for an invention attempt cycle
INVENT_ENERGY_COST = 1.8   # Slightly lower invent cost
# --- Phase 4: Social Costs ---
SIGNAL_ENERGY_COST = 0.1
TEACH_BASE_DURATION = 15.0
TEACH_ENERGY_COST = 1.2 # Slightly lower teach cost
LEARN_BASE_DURATION = 15.0
LEARN_ENERGY_COST = 0.8 # Slightly lower learn cost
HELP_BASE_DURATION = 1.0
HELP_ENERGY_COST = 0.2 # Slightly lower help cost

# AI Settings
WANDER_RADIUS = 6        # Max distance for random wander target
UTILITY_THRESHOLD = 0.15 # Minimum utility score to consider an action (except Wander)
AGENT_VIEW_RADIUS = 25   # How far agents can "see" for finding resources (BFS limit)
WORKBENCH_INTERACTION_RADIUS = 1 # Chebyshev distance (0=on tile, 1=adjacent) to use workbench
INVENTION_ITEM_TYPES_THRESHOLD = 3 # Min different item types in inventory to attempt invention
# --- AI Utility Weights ---
UTILITY_THIRST_WEIGHT = 1.25 # <<< Further slight increase
UTILITY_HUNGER_WEIGHT = 1.20 # <<< Increased


# Skill Settings
INITIAL_SKILL_LEVEL = 0
MAX_SKILL_LEVEL = 100
SKILL_INCREASE_RATE = 0.8 # Base increase per successful action (adjusted by diminishing returns)
TEACHING_BOOST_FACTOR = 5.0 # Multiplier for skill gain when taught
PASSIVE_LEARN_BOOST = 0.05 # Small boost multiplier for passive learning
TEACHING_MIN_SKILL_ADVANTAGE = 8.0 # Keep lowered value


# Tool Settings (Multipliers for speed/efficiency)
TOOL_EFFICIENCY = {
    'CrudeAxe': 1.8,
    'StonePick': 1.8,
}

# Crafting Recipes
RECIPES = {
    'Workbench': {
        'ingredients': {'Wood': 5, 'Stone': 2},
        'skill': 'BasicCrafting',
        'min_level': 3,
        'workbench': False
    },
    'CrudeAxe': {
        'ingredients': {'Wood': 2, 'Stone': 1},
        'skill': 'BasicCrafting',
        'min_level': 1,
        'workbench': False
    },
    'StonePick': {
        'ingredients': {'Wood': 2, 'Stone': 3},
        'skill': 'BasicCrafting',
        'min_level': 5,
        'workbench': True
     },
     'SmallShelter': {
         'ingredients': {'Wood': 8},
         'skill': 'BasicCrafting',
         'min_level': 8,
         'workbench': True
     },
     'CookedFood': {
         'ingredients': {'Food': 1},
         'skill': 'BasicCrafting',
         'min_level': 2,
         'workbench': True,
     },
}

# Terrain/Resource Codes
TERRAIN_GROUND = 0
TERRAIN_WATER = 1
TERRAIN_OBSTACLE = 2

RESOURCE_NONE = 0
RESOURCE_FOOD = 1
RESOURCE_WATER = 2
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
    RESOURCE_FOOD: {'color': YELLOW, 'name': 'Food', 'block_walk': False, 'max_quantity': 6, 'regen': 0.01}, # Slightly more quantity
    RESOURCE_WOOD: {'color': BROWN, 'name': 'Wood', 'block_walk': True, 'max_quantity': 8, 'regen': 0.002},
    RESOURCE_STONE: {'color': GRAY, 'name': 'Stone', 'block_walk': True, 'max_quantity': 10, 'regen': 0.001},
    RESOURCE_WORKBENCH: {'color': ORANGE, 'name': 'Workbench', 'block_walk': False, 'max_quantity': 1, 'regen': 0},
}

# Pathfinding Settings
MAX_PATHFINDING_ITERATIONS = 3500

# --- Phase 4: Social Settings ---
SIGNAL_RANGE_SQ = 18**2
SIGNAL_DURATION_TICKS = 5
RELATIONSHIP_DECAY_RATE = 0.001
HELPING_MIN_RELATIONSHIP = -0.1 # Keep lowered
HELPING_TARGET_NEED_THRESHOLD = 0.8
HELPING_SELF_NEED_THRESHOLD = 0.7 # <<< RELAXED from 0.6
HELPING_INTERACTION_RADIUS = 2
TEACHING_MIN_RELATIONSHIP = 0.0 # Keep lowered
TEACHING_INTERACTION_RADIUS = 2
PASSIVE_LEARN_RADIUS_SQ = 5**2
PASSIVE_LEARN_CHANCE = 0.05
RELATIONSHIP_CHANGE_HELP = 0.20
RELATIONSHIP_CHANGE_TEACH = 0.15
RELATIONSHIP_CHANGE_SIGNAL_RESPONSE = 0.05

# Signal Types
SIGNAL_HELP_NEEDED_FOOD = "HelpFood"
SIGNAL_HELP_NEEDED_HEALTH = "HelpHealth"
SIGNAL_FOUND_FOOD = "FoundFood"
SIGNAL_FOUND_WATER = "FoundWater"
SIGNAL_DANGER_NEAR = "Danger"

# Items that can be 'given' during Help action
HELPABLE_ITEMS = {'Food', 'CookedFood'}