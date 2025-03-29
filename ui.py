# ui.py
import pygame
import config as cfg
import time # For signal visualization timing
import math # For day/night cycle calculation
from collections import deque # For event log
import random # For subtle variations

# --- Constants ---
PANEL_X = cfg.GAME_WIDTH
PANEL_WIDTH = cfg.SIDE_PANEL_WIDTH
PANEL_HEIGHT = cfg.SCREEN_HEIGHT
MARGIN = 10
CONTENT_WIDTH = PANEL_WIDTH - 2 * MARGIN
SECTION_SPACING = 8
BAR_HEIGHT = 16
TAB_HEIGHT = 25
EVENT_LOG_HEIGHT = 80
EVENT_LOG_MAX_LINES = 5

# --- Fonts (Consider adjusting sizes) ---
pygame.font.init()
try:
    FONT_TINY = pygame.font.SysFont('Arial', 11)
    FONT_SMALL = pygame.font.SysFont('Arial', 13)
    FONT_MEDIUM = pygame.font.SysFont('Arial', 16)
    FONT_LARGE = pygame.font.SysFont('Arial', 20)
    FONT_ICON = pygame.font.SysFont('Arial', 14) # For simple text icons if needed
except Exception as e:
    print(f"Error loading system font (Arial): {e}. Using default font.")
    FONT_TINY = pygame.font.Font(None, 14)
    FONT_SMALL = pygame.font.Font(None, 16)
    FONT_MEDIUM = pygame.font.Font(None, 20)
    FONT_LARGE = pygame.font.Font(None, 26)
    FONT_ICON = pygame.font.Font(None, 18)

# --- Colors ---
COLOR_TAB_INACTIVE = (80, 80, 80)
COLOR_TAB_ACTIVE = (110, 110, 110)
COLOR_TAB_TEXT = cfg.UI_TEXT_COLOR
COLOR_SECTION_HEADER = cfg.WHITE
COLOR_LABEL = (180, 180, 180)
COLOR_VALUE = cfg.WHITE
COLOR_BAR_BG = (60, 60, 60)
COLOR_EVENT_LOG_BG = (40, 40, 40)
COLOR_HEALTH = (0, 200, 0)
COLOR_ENERGY = (60, 100, 255)
COLOR_HUNGER = (255, 165, 0)
COLOR_THIRST = (0, 150, 255)
COLOR_SKILL = (200, 200, 0)
COLOR_REL_GOOD = (0, 255, 100)
COLOR_REL_NEUTRAL = (200, 200, 200)
COLOR_REL_BAD = (255, 80, 80)
COLOR_PAUSE_BTN_ACTIVE = (200, 50, 50)
COLOR_PAUSE_BTN_INACTIVE = (50, 180, 50)
COLOR_ICON_BG = (70, 70, 70)

# --- New Object Colors ---
TRUNK_COLOR = (101, 67, 33)
LEAF_COLOR_MAIN = (34, 139, 34)
LEAF_COLOR_HIGHLIGHT = (50, 205, 50)
BERRY_COLOR = (220, 20, 60) # Crimson Red
STONE_COLOR_MAIN = (105, 105, 105) # DimGray
STONE_COLOR_SHADOW = (80, 80, 80)
WATER_COLOR_LIGHT = (60, 60, 220) # Lighter blue for waves
WORKBENCH_TOP = (210, 180, 140) # Tan
WORKBENCH_LEGS = (139, 69, 19) # SaddleBrown
AGENT_HEAD = (255, 220, 180) # Simple skin tone for head

# --- UI State (Managed externally or passed into draw_ui) ---
# Placeholder - should be managed in main.py
# ui_state = { ... }

# --- Helper Functions (draw_text, draw_progress_bar, etc. - UNCHANGED) ---
# Keep all the helper functions from the previous advanced UI version:
# draw_text, draw_progress_bar, draw_icon, get_relationship_descriptor,
# get_time_of_day_color_alpha, draw_circular_clock

# --- START PASTE HELPER FUNCTIONS HERE ---
def draw_text(surface, text, pos, font, color, align="left", width=None, shadow_color=None, shadow_offset=(1,1)):
    """Draws text with alignment and optional shadow."""
    if shadow_color:
        text_surf_shadow = font.render(text, True, shadow_color)
        shadow_pos = (pos[0] + shadow_offset[0], pos[1] + shadow_offset[1])
        if align == "center":
             shadow_pos = text_surf_shadow.get_rect(center=(pos[0] + shadow_offset[0], pos[1] + shadow_offset[1]))
        elif align == "right" and width:
             shadow_pos = text_surf_shadow.get_rect(topright=(pos[0] + width + shadow_offset[0], pos[1] + shadow_offset[1]))
        # Default to left alignment if not specified or width missing for right align
        surface.blit(text_surf_shadow, shadow_pos)

    text_surf = font.render(text, True, color)
    text_rect = text_surf.get_rect(topleft=pos)
    if align == "center":
        text_rect = text_surf.get_rect(center=pos)
    elif align == "right" and width:
        text_rect = text_surf.get_rect(topright=(pos[0] + width, pos[1]))

    surface.blit(text_surf, text_rect)
    return text_rect # Return the rect for layout

def draw_progress_bar(surface, pos, size, current, maximum, bar_color, bg_color=COLOR_BAR_BG, text_color=cfg.WHITE, show_value=True):
    """Draws a simple progress bar, returns its rect."""
    x, y = pos
    width, height = size
    bg_rect = pygame.Rect(x, y, width, height)
    pygame.draw.rect(surface, bg_color, bg_rect, border_radius=2)

    percent = max(0, min(1, current / maximum)) if maximum > 0 else 0
    fill_width = int(width * percent)
    fill_rect = pygame.Rect(x, y, fill_width, height)
    pygame.draw.rect(surface, bar_color, fill_rect, border_radius=2)

    pygame.draw.rect(surface, cfg.WHITE, bg_rect, 1, border_radius=2) # Border

    if show_value:
        val_text = f"{current:.0f}/{maximum:.0f}"
        try:
            draw_text(surface, val_text, bg_rect.center, FONT_TINY, text_color, align="center", shadow_color=(0,0,0))
        except Exception as e: print(f"Warn: Bar text error {e}")

    return bg_rect

def draw_icon(surface, pos, size, icon_type, value=None):
    """Draws a simple placeholder icon."""
    icon_rect = pygame.Rect(pos, (size, size))
    pygame.draw.rect(surface, COLOR_ICON_BG, icon_rect, border_radius=3) # Background

    center = icon_rect.center
    radius = size // 3

    if icon_type == "Health": pygame.draw.circle(surface, COLOR_HEALTH, center, radius)
    elif icon_type == "Energy": pygame.draw.rect(surface, COLOR_ENERGY, (center[0]-radius, center[1]-radius, radius*2, radius*2))
    elif icon_type == "Hunger": pygame.draw.polygon(surface, COLOR_HUNGER, [(center[0], center[1]-radius), (center[0]-radius, center[1]+radius), (center[0]+radius, center[1]+radius)])
    elif icon_type == "Thirst": pygame.draw.circle(surface, COLOR_THIRST, center, radius)
    elif icon_type == "Wood": pygame.draw.rect(surface, TRUNK_COLOR, icon_rect.inflate(-4,-4)) # Brown square
    elif icon_type == "Stone": pygame.draw.circle(surface, STONE_COLOR_MAIN, center, radius) # Gray circle
    elif icon_type == "Food": pygame.draw.circle(surface, BERRY_COLOR, center, radius) # Red circle for icon
    elif icon_type == "Workbench": pygame.draw.rect(surface, WORKBENCH_TOP, icon_rect.inflate(-4,-4)) # Tan square
    elif icon_type == "Skill": pygame.draw.polygon(surface, COLOR_SKILL, [(center[0], center[1]-radius),(center[0]+radius, center[1]),(center[0], center[1]+radius),(center[0]-radius, center[1])]) # Diamond
    elif icon_type == "Recipe": pygame.draw.rect(surface, cfg.PURPLE, icon_rect.inflate(-6,-6)) # Purple square
    elif icon_type == "Relationship": pygame.draw.line(surface, COLOR_REL_NEUTRAL, (center[0]-radius, center[1]), (center[0]+radius, center[1]), 2) # Simple line for now
    else: # Default icon
        pygame.draw.line(surface, cfg.WHITE, (center[0]-radius, center[1]-radius), (center[0]+radius, center[1]+radius), 1)
        pygame.draw.line(surface, cfg.WHITE, (center[0]-radius, center[1]+radius), (center[0]+radius, center[1]-radius), 1)

    pygame.draw.rect(surface, cfg.WHITE, icon_rect, 1, border_radius=3) # Border
    return icon_rect

def get_relationship_descriptor(score):
    if score > 0.7: return "Ally", COLOR_REL_GOOD
    if score > 0.3: return "Friend", COLOR_REL_GOOD
    if score > -0.1: return "Neutral", COLOR_REL_NEUTRAL
    if score > -0.5: return "Disliked", COLOR_REL_BAD
    return "Hostile", COLOR_REL_BAD

def get_time_of_day_color_alpha(day_time, day_length):
    """Calculates color and alpha for day/night visual overlay."""
    time_norm = (day_time % day_length) / day_length
    darkness = (math.sin(time_norm * 2 * math.pi - math.pi/2) + 1) / 2
    darkness = darkness * 0.75 + 0.05 # Scale darkness from 0.05 to 0.8
    alpha = int(darkness * 180) # Max alpha lower for less intense night
    color = (15, 15, 50) # Slightly darker blue
    return (*color, alpha)

def draw_circular_clock(surface, center_pos, radius, day_time, day_length):
    """Draws a simple analog-style day/night clock."""
    # Background
    pygame.draw.circle(surface, (40, 40, 40), center_pos, radius)
    pygame.draw.circle(surface, cfg.WHITE, center_pos, radius, 1)

    # Time calculation (angle in radians)
    time_fraction = (day_time % day_length) / day_length
    angle = time_fraction * 2 * math.pi - math.pi / 2 # Start at top (midnight)

    # Hand endpoint
    hand_length = radius * 0.85
    end_x = center_pos[0] + hand_length * math.cos(angle)
    end_y = center_pos[1] + hand_length * math.sin(angle)

    # Determine hand color (sun/moon)
    is_day = 0.25 < time_fraction < 0.75 # Rough day period
    hand_color = cfg.YELLOW if is_day else (200, 200, 255) # Yellow for sun, light blue for moon

    pygame.draw.line(surface, hand_color, center_pos, (int(end_x), int(end_y)), 2)
    pygame.draw.circle(surface, hand_color, (int(end_x), int(end_y)), 3) # Small circle at end
# --- END PASTE HELPER FUNCTIONS ---


# --- Enhanced Object Drawing Functions ---

def draw_tree(surface, rect):
    """Draws a tree within the given rect."""
    trunk_width = max(2, rect.width // 4)
    trunk_height = rect.height // 2
    trunk_rect = pygame.Rect(rect.centerx - trunk_width // 2, rect.bottom - trunk_height, trunk_width, trunk_height)
    pygame.draw.rect(surface, TRUNK_COLOR, trunk_rect, border_radius=1)

    canopy_radius = rect.width // 2 - 1
    canopy_center_y = rect.bottom - trunk_height - canopy_radius // 3
    canopy_center = (rect.centerx, canopy_center_y)

    # Draw overlapping circles for canopy
    pygame.draw.circle(surface, LEAF_COLOR_MAIN, canopy_center, canopy_radius)
    pygame.draw.circle(surface, LEAF_COLOR_HIGHLIGHT, (canopy_center[0] - canopy_radius//3, canopy_center[1] - canopy_radius//3), canopy_radius//2)
    pygame.draw.circle(surface, LEAF_COLOR_HIGHLIGHT, (canopy_center[0] + canopy_radius//3, canopy_center[1] - canopy_radius//4), canopy_radius//2)

    # Outline
    pygame.draw.circle(surface, cfg.BLACK, canopy_center, canopy_radius, 1)
    pygame.draw.rect(surface, cfg.BLACK, trunk_rect, 1, border_radius=1)

def draw_food_bush(surface, rect):
    """Draws a berry bush within the given rect."""
    bush_height = rect.height // 3
    bush_base_y = rect.bottom - bush_height
    # Simple green base
    base_rect = pygame.Rect(rect.left + rect.width//4, bush_base_y, rect.width//2, bush_height)
    pygame.draw.rect(surface, LEAF_COLOR_MAIN, base_rect, border_radius=2)
    pygame.draw.rect(surface, cfg.BLACK, base_rect, 1, border_radius=2)

    # Berries (small circles)
    berry_radius = max(1, rect.width // 8)
    berry_positions = [
        (rect.centerx, bush_base_y - berry_radius//2),
        (rect.centerx - rect.width//4, bush_base_y + berry_radius),
        (rect.centerx + rect.width//4, bush_base_y + berry_radius),
        (rect.centerx, bush_base_y + bush_height//2 + berry_radius)
    ]
    for pos in berry_positions:
        pygame.draw.circle(surface, BERRY_COLOR, pos, berry_radius)
        pygame.draw.circle(surface, cfg.BLACK, pos, berry_radius, 1)

def draw_stone(surface, rect):
    """Draws a stone/boulder within the given rect."""
    main_radius = rect.width // 2 - 2
    main_center = rect.center
    # Base rock shape
    pygame.draw.circle(surface, STONE_COLOR_MAIN, main_center, main_radius)

    # Add overlapping shadow/highlight circles for texture
    shadow_radius = main_radius // 2
    shadow_center = (main_center[0] - main_radius // 3, main_center[1] + main_radius // 3)
    pygame.draw.circle(surface, STONE_COLOR_SHADOW, shadow_center, shadow_radius)

    # Outline
    pygame.draw.circle(surface, cfg.BLACK, main_center, main_radius, 1)
    # Optional detail lines
    pygame.draw.aaline(surface, STONE_COLOR_SHADOW, (main_center[0]-main_radius//2, main_center[1]-main_radius//3), (main_center[0]+main_radius//3, main_center[1]))

def draw_water_tile(surface, rect):
    """Draws a water tile with simple wave effect."""
    pygame.draw.rect(surface, cfg.TERRAIN_COLORS[cfg.TERRAIN_WATER], rect)
    # Draw a couple of wavy lines
    wave_y1 = rect.top + rect.height // 3
    wave_y2 = rect.top + rect.height * 2 // 3
    num_points = 5
    points1 = []
    points2 = []
    for i in range(num_points + 1):
        x = rect.left + i * (rect.width / num_points)
        offset1 = math.sin(x * 0.5 + time.time() * 2) * 2 # Slow sine wave offset
        offset2 = math.sin(x * 0.4 + time.time() * 2.5 + 1) * 2
        points1.append((int(x), int(wave_y1 + offset1)))
        points2.append((int(x), int(wave_y2 + offset2)))

    if len(points1) > 1: pygame.draw.lines(surface, WATER_COLOR_LIGHT, False, points1, 1)
    if len(points2) > 1: pygame.draw.lines(surface, WATER_COLOR_LIGHT, False, points2, 1)

def draw_workbench(surface, rect):
    """Draws a simple workbench."""
    top_height = rect.height // 3
    leg_height = rect.height - top_height
    leg_width = max(1, rect.width // 6)

    # Table top
    top_rect = pygame.Rect(rect.left, rect.top, rect.width, top_height)
    pygame.draw.rect(surface, WORKBENCH_TOP, top_rect, border_radius=1)
    pygame.draw.rect(surface, cfg.BLACK, top_rect, 1, border_radius=1)

    # Legs
    leg1_x = rect.left + leg_width
    leg2_x = rect.right - leg_width * 2
    leg_y = rect.top + top_height
    pygame.draw.rect(surface, WORKBENCH_LEGS, (leg1_x, leg_y, leg_width, leg_height))
    pygame.draw.rect(surface, WORKBENCH_LEGS, (leg2_x, leg_y, leg_width, leg_height))


# --- Main World/Agent Drawing ---

def draw_world(screen, world, social_manager):
    """ Draws world grid, terrain, resources, signals, and day/night overlay """
    game_surf = pygame.Surface((cfg.GAME_WIDTH, cfg.SCREEN_HEIGHT))
    game_surf.fill(cfg.BLACK) # Base background

    for y in range(world.height):
        for x in range(world.width):
            rect = pygame.Rect(x * cfg.CELL_SIZE, y * cfg.CELL_SIZE, cfg.CELL_SIZE, cfg.CELL_SIZE)
            terrain_type = world.terrain_map[y, x]

            # --- Draw Terrain ---
            if terrain_type == cfg.TERRAIN_WATER:
                draw_water_tile(game_surf, rect)
            else:
                color = cfg.TERRAIN_COLORS.get(terrain_type, cfg.DARK_GRAY)
                pygame.draw.rect(game_surf, color, rect)

            # --- Draw Resources ---
            resource = world.resource_map[y, x]
            if resource and (resource.quantity > 0 or resource.type == cfg.RESOURCE_WORKBENCH):
                try: # Add try-except for drawing functions
                    if resource.type == cfg.RESOURCE_WOOD:
                        draw_tree(game_surf, rect)
                    elif resource.type == cfg.RESOURCE_FOOD:
                        draw_food_bush(game_surf, rect)
                    elif resource.type == cfg.RESOURCE_STONE:
                        draw_stone(game_surf, rect)
                    elif resource.type == cfg.RESOURCE_WORKBENCH:
                        draw_workbench(game_surf, rect)
                    else: # Default fallback drawing
                        res_info = cfg.RESOURCE_INFO.get(resource.type)
                        if res_info:
                            res_color = res_info['color']
                            res_size = int(cfg.CELL_SIZE * 0.6)
                            offset = (cfg.CELL_SIZE - res_size) // 2
                            res_rect = pygame.Rect(rect.left + offset, rect.top + offset, res_size, res_size)
                            pygame.draw.rect(game_surf, res_color, res_rect, border_radius=2)
                            pygame.draw.rect(game_surf, cfg.BLACK, res_rect, 1, border_radius=2)
                except Exception as e:
                     print(f"Error drawing resource type {resource.type} at ({x},{y}): {e}")


    # --- Draw Signals --- (Keep previous signal drawing logic)
    current_time = time.time()
    for signal in social_manager.active_signals:
         time_elapsed = current_time - signal.timestamp
         max_signal_time = (cfg.SIGNAL_DURATION_TICKS / cfg.FPS)
         if time_elapsed < max_signal_time:
             alpha = max(0, int(200 * (1 - (time_elapsed / max_signal_time))))
             pulse_factor = math.sin(time_elapsed * math.pi * 2.5 / max_signal_time)**2 # Smoother pulse
             base_radius = cfg.CELL_SIZE // 2 + 1
             radius = int(base_radius * (1 + pulse_factor * 0.3))
             try:
                 signal_x, signal_y = signal.position
                 center_x = signal_x * cfg.CELL_SIZE + cfg.CELL_SIZE // 2
                 center_y = signal_y * cfg.CELL_SIZE + cfg.CELL_SIZE // 2
                 temp_surf = pygame.Surface((radius * 2 + 4, radius * 2 + 4), pygame.SRCALPHA)
                 pygame.draw.circle(temp_surf, (*cfg.PURPLE, int(alpha*0.8)), (radius+2, radius+2), radius, 2) # Outer ring
                 pygame.draw.circle(temp_surf, (*cfg.PURPLE, int(alpha*0.3)), (radius+2, radius+2), radius // 2) # Inner fill
                 game_surf.blit(temp_surf, (center_x - radius - 2, center_y - radius - 2))
             except Exception as e: print(f"Warn: Sig draw error {e}")

    # --- Draw Day/Night Overlay ---
    overlay_color_alpha = get_time_of_day_color_alpha(world.day_time, cfg.DAY_LENGTH_SECONDS)
    if overlay_color_alpha[3] > 0:
        overlay_surface = pygame.Surface((cfg.GAME_WIDTH, cfg.SCREEN_HEIGHT), pygame.SRCALPHA)
        overlay_surface.fill(overlay_color_alpha)
        game_surf.blit(overlay_surface, (0, 0))

    screen.blit(game_surf, (0, 0))


def draw_agent(screen, agent, is_selected=False):
    """ Draws agent with simple head/body shape, selection, path, target marker """
    if agent.health <= 0: return

    base_rect = pygame.Rect(agent.x * cfg.CELL_SIZE, agent.y * cfg.CELL_SIZE, cfg.CELL_SIZE, cfg.CELL_SIZE)
    center_x = base_rect.centerx
    body_height = int(cfg.CELL_SIZE * 0.6)
    body_width = int(cfg.CELL_SIZE * 0.5)
    body_top = base_rect.centery - body_height // 4 # Shift body slightly up
    body_rect = pygame.Rect(center_x - body_width // 2, body_top, body_width, body_height)

    head_radius = max(2, cfg.CELL_SIZE // 6)
    head_center = (center_x, body_top - head_radius + 1) # Place head just above body

    # Determine body color based on need state
    agent_body_color = cfg.RED
    low_need = agent.hunger > cfg.MAX_HUNGER * 0.8 or \
               agent.thirst > cfg.MAX_THIRST * 0.8 or \
               agent.energy < cfg.MAX_ENERGY * 0.2
    if low_need:
        agent_body_color = (max(0, agent_body_color[0]-60), max(0, agent_body_color[1]-60), max(0, agent_body_color[2]-60))

    # Draw Body and Head
    pygame.draw.rect(screen, agent_body_color, body_rect, border_radius=2)
    pygame.draw.circle(screen, AGENT_HEAD, head_center, head_radius)

    # Outline
    pygame.draw.rect(screen, cfg.BLACK, body_rect, 1, border_radius=2)
    pygame.draw.circle(screen, cfg.BLACK, head_center, head_radius, 1)

    # Selection Highlight
    if is_selected:
        # Use a bounding box around the whole shape for highlight
        highlight_rect = body_rect.union(pygame.Rect(head_center[0]-head_radius, head_center[1]-head_radius, head_radius*2, head_radius*2))
        highlight_rect.inflate_ip(4, 4) # Inflate slightly for outline
        pygame.draw.rect(screen, cfg.WHITE, highlight_rect, 1, border_radius=3)
        highlight_rect.inflate_ip(2, 2)
        pygame.draw.rect(screen, cfg.YELLOW, highlight_rect, 1, border_radius=4)

    # Health Bar (Positioned above the head)
    health_percent = max(0, agent.health / cfg.MAX_HEALTH)
    bar_width = int(cfg.CELL_SIZE * 0.8); bar_height = 3
    bar_x = base_rect.left + (cfg.CELL_SIZE - bar_width) // 2
    bar_y = head_center[1] - head_radius - bar_height - 2 # Above head
    bg_rect = pygame.Rect(bar_x, bar_y, bar_width, bar_height)
    fill_width = int(bar_width * health_percent)
    fill_rect = pygame.Rect(bar_x, bar_y, fill_width, bar_height)
    bar_color = COLOR_HEALTH if health_percent > 0.6 else cfg.YELLOW if health_percent > 0.3 else cfg.RED
    pygame.draw.rect(screen, cfg.DARK_GRAY, bg_rect)
    pygame.draw.rect(screen, bar_color, fill_rect)

    # Draw path/target only if selected (Keep previous logic)
    if is_selected:
        # Path
        if agent.current_path and len(agent.current_path) > 1:
            # Start path from agent's current center
            agent_center = (agent.x * cfg.CELL_SIZE + cfg.CELL_SIZE // 2, agent.y * cfg.CELL_SIZE + cfg.CELL_SIZE // 2)
            path_points = [agent_center] + \
                          [(px * cfg.CELL_SIZE + cfg.CELL_SIZE // 2, py * cfg.CELL_SIZE + cfg.CELL_SIZE // 2) for px, py in agent.current_path]
            try: pygame.draw.lines(screen, cfg.YELLOW, False, path_points, 2)
            except Exception as e: print(f"Warn: Path draw error {e}")

        # Target Marker
        if agent.action_target and agent.action_target.get('goal'):
             goal_pos = agent.action_target['goal']
             if goal_pos != (agent.x, agent.y):
                 target_x = goal_pos[0] * cfg.CELL_SIZE + cfg.CELL_SIZE // 2
                 target_y = goal_pos[1] * cfg.CELL_SIZE + cfg.CELL_SIZE // 2
                 pulse = (math.sin(time.time() * 5) + 1) / 2 # 0 to 1 sine wave
                 min_radius = cfg.CELL_SIZE // 4; max_radius = cfg.CELL_SIZE // 3
                 marker_radius = int(min_radius + pulse * (max_radius - min_radius))
                 pygame.draw.circle(screen, cfg.YELLOW, (target_x, target_y), marker_radius, 1)
                 pygame.draw.circle(screen, (255, 255, 0, 100), (target_x, target_y), marker_radius + 2, 1) # Faint outer glow

# --- Tab Content Drawing Functions ---
# (draw_status_tab, draw_inventory_tab, draw_skills_tab, draw_social_tab, draw_world_object_info)
# Keep these functions exactly as they were in the previous "Advanced UI" version.
# They already use the draw_icon helper which has been updated.

# --- START PASTE TAB CONTENT FUNCTIONS HERE ---
def draw_status_tab(surface, y_start, agent):
    y_offset = y_start + MARGIN
    icon_size = 18
    bar_width = CONTENT_WIDTH - icon_size - MARGIN * 2
    bar_pos_x = MARGIN + icon_size + MARGIN

    draw_text(surface, f"Agent {agent.id} Status", (MARGIN, y_offset), FONT_MEDIUM, COLOR_SECTION_HEADER); y_offset += FONT_MEDIUM.get_linesize() + 4

    # Needs with Icons and Bars
    needs_data = [
        ("Health", agent.health, cfg.MAX_HEALTH, COLOR_HEALTH),
        ("Energy", agent.energy, cfg.MAX_ENERGY, COLOR_ENERGY),
        ("Hunger", agent.hunger, cfg.MAX_HUNGER, COLOR_HUNGER), # Display raw hunger (0=low, 100=high)
        ("Thirst", agent.thirst, cfg.MAX_THIRST, COLOR_THIRST), # Display raw thirst
    ]
    for name, current, maximum, color in needs_data:
        draw_icon(surface, (MARGIN, y_offset), icon_size, name)
        # Invert value for display bar for hunger/thirst
        display_val = maximum - current if name in ["Hunger", "Thirst"] else current
        bar_color = color
        # Adjust color urgency based on displayed value (fullness)
        percent = max(0, min(1, display_val / maximum)) if maximum > 0 else 0
        if percent < 0.3: bar_color = cfg.RED
        elif percent < 0.6: bar_color = cfg.YELLOW

        rect = draw_progress_bar(surface, (bar_pos_x, y_offset), (bar_width, icon_size), display_val, maximum, bar_color)
        y_offset += rect.height + 5
    y_offset += SECTION_SPACING

    # Current Action
    draw_text(surface, "Current Action:", (MARGIN, y_offset), FONT_SMALL, COLOR_LABEL); y_offset += FONT_SMALL.get_linesize()
    action_name = agent.current_action or "Idle"
    action_detail = ""
    timer_text = ""
    if agent.current_action and agent.action_timer > 0:
         timer_text = f" (T:{agent.action_timer:.1f}s)" # No reliable % estimate

    if agent.action_target:
        target = agent.action_target; details = []
        if 'recipe' in target: details.append(target['recipe'])
        if 'item' in target: details.append(target['item'])
        if 'skill' in target: details.append(target['skill'])
        if 'target_id' in target: details.append(f"Agent {target['target_id']}")
        goal_pos = target.get('goal')
        if goal_pos and goal_pos != (agent.x, agent.y): details.append(f"@{goal_pos}")
        if details: action_detail = f" ({', '.join(details)})"

    draw_text(surface, f" {action_name}{action_detail}{timer_text}", (MARGIN, y_offset), FONT_SMALL, cfg.YELLOW); y_offset += FONT_SMALL.get_linesize() + SECTION_SPACING

    # Agent Attributes
    draw_text(surface, "Attributes:", (MARGIN, y_offset), FONT_SMALL, COLOR_LABEL); y_offset += FONT_SMALL.get_linesize()
    draw_text(surface, f" Sociability: {agent.sociability:.2f}", (MARGIN + 5, y_offset), FONT_SMALL, COLOR_VALUE); y_offset += FONT_SMALL.get_linesize()
    draw_text(surface, f" Intelligence: {agent.intelligence:.2f}", (MARGIN + 5, y_offset), FONT_SMALL, COLOR_VALUE); y_offset += FONT_SMALL.get_linesize()

    return y_offset # Return final y position

def draw_inventory_tab(surface, y_start, agent):
    y_offset = y_start + MARGIN
    icon_size = 16
    inv_sum = sum(agent.inventory.values())
    draw_text(surface, f"Inventory ({inv_sum}/{cfg.INVENTORY_CAPACITY})", (MARGIN, y_offset), FONT_MEDIUM, COLOR_SECTION_HEADER); y_offset += FONT_MEDIUM.get_linesize() + 4

    if not agent.inventory:
        draw_text(surface, " Empty", (MARGIN + 5, y_offset), FONT_SMALL, COLOR_LABEL); y_offset += FONT_SMALL.get_linesize()
    else:
        items_list = sorted(list(agent.inventory.items()))
        col1_x = MARGIN; col2_x = MARGIN + CONTENT_WIDTH // 2 + 5
        current_x = col1_x; item_y = y_offset
        max_items_per_col = 8 # Adjust as needed
        for i, (item, count) in enumerate(items_list):
            if i >= max_items_per_col * 2:
                draw_text(surface, "...", (current_x, item_y), FONT_SMALL, COLOR_LABEL); break
            if i == max_items_per_col: # Switch to second column
                 current_x = col2_x; item_y = y_offset

            icon_rect = draw_icon(surface, (current_x, item_y), icon_size, item)
            draw_text(surface, f" {item}: {count}", (icon_rect.right + 4, item_y + (icon_size - FONT_SMALL.get_height())//2), FONT_SMALL, COLOR_VALUE)
            item_y += icon_size + 4
        y_offset = item_y + SECTION_SPACING # Update y_offset based on longest column (assume roughly equal)

    # Known Recipes
    draw_text(surface, "Known Recipes", (MARGIN, y_offset), FONT_MEDIUM, COLOR_SECTION_HEADER); y_offset += FONT_MEDIUM.get_linesize() + 4
    known_recipes = sorted(list(agent.knowledge.known_recipes))
    if not known_recipes:
        draw_text(surface, " None", (MARGIN + 5, y_offset), FONT_SMALL, COLOR_LABEL); y_offset += FONT_SMALL.get_linesize()
    else:
        # Simple list layout for recipes
        current_x = MARGIN + 5; max_width = CONTENT_WIDTH - 10
        for i, recipe in enumerate(known_recipes):
            recipe_text = f"{recipe}" + (", " if i < len(known_recipes)-1 else "");
            recipe_rect = draw_text(surface, recipe_text, (current_x, y_offset), FONT_SMALL, COLOR_VALUE)
            if recipe_rect.right > PANEL_X + max_width and current_x > MARGIN + 5: # Wrap line
                 y_offset += FONT_SMALL.get_linesize(); current_x = MARGIN + 5
                 recipe_rect = draw_text(surface, recipe_text, (current_x, y_offset), FONT_SMALL, COLOR_VALUE)
            current_x = recipe_rect.right + 4
        y_offset += FONT_SMALL.get_linesize()

    return y_offset

def draw_skills_tab(surface, y_start, agent):
    y_offset = y_start + MARGIN
    icon_size = 16
    bar_width = CONTENT_WIDTH - MARGIN * 2
    bar_pos_x = MARGIN

    draw_text(surface, "Skills", (MARGIN, y_offset), FONT_MEDIUM, COLOR_SECTION_HEADER); y_offset += FONT_MEDIUM.get_linesize() + 4

    skills_to_show = {k: v for k, v in sorted(agent.skills.items()) if v >= 0.1}
    if not skills_to_show:
        draw_text(surface, " None learned", (MARGIN + 5, y_offset), FONT_SMALL, COLOR_LABEL); y_offset += FONT_SMALL.get_linesize()
    else:
        skill_bar_height = 14
        for skill_name, level in skills_to_show.items():
             # Draw skill name label
             label_rect = draw_text(surface, f"{skill_name}:", (bar_pos_x, y_offset), FONT_SMALL, COLOR_LABEL)
             y_offset += label_rect.height + 1
             # Draw progress bar below label
             rect = draw_progress_bar(surface, (bar_pos_x, y_offset), (bar_width, skill_bar_height), level, cfg.MAX_SKILL_LEVEL, COLOR_SKILL, show_value=True)
             y_offset += rect.height + 6 # More spacing between skills

    return y_offset

def draw_social_tab(surface, y_start, agent, world):
    y_offset = y_start + MARGIN
    icon_size = 16
    rel_bar_width = CONTENT_WIDTH // 2 - MARGIN # Width for relationship bar

    draw_text(surface, "Relationships", (MARGIN, y_offset), FONT_MEDIUM, COLOR_SECTION_HEADER); y_offset += FONT_MEDIUM.get_linesize() + 4

    relationships = sorted(agent.knowledge.relationships.items(), key=lambda item: item[1], reverse=True)
    if not relationships:
         draw_text(surface, " None known", (MARGIN + 5, y_offset), FONT_SMALL, COLOR_LABEL); y_offset += FONT_SMALL.get_linesize()
    else:
         max_rels_shown = 10
         for i, (other_id, score) in enumerate(relationships):
             if i >= max_rels_shown and len(relationships) > max_rels_shown+1:
                  draw_text(surface, f" ... ({len(relationships)-i} more)", (MARGIN + 5, y_offset), FONT_TINY, cfg.GRAY); y_offset += FONT_TINY.get_linesize()
                  break

             other_agent = world.get_agent_by_id(other_id)
             status = " (X)" if not other_agent or other_agent.health <= 0 else ""
             descriptor, rel_color = get_relationship_descriptor(score)

             # Layout: Agent ID | Descriptor | Bar
             id_text = f"Agent {other_id}{status}:"
             id_rect = draw_text(surface, id_text, (MARGIN + 5, y_offset), FONT_SMALL, COLOR_VALUE)

             desc_text = f"({descriptor})"
             desc_rect = draw_text(surface, desc_text, (id_rect.right + 5, y_offset), FONT_SMALL, rel_color)

             # Relationship bar (visualizing -1 to +1)
             bar_x = desc_rect.right + 10
             # Clamp bar_x to prevent overflow if names are long
             bar_x = min(bar_x, PANEL_WIDTH - rel_bar_width - MARGIN*2) # Adjust PANEL_WIDTH to CONTENT_WIDTH if drawing on subsurface
             bar_y = y_offset + (FONT_SMALL.get_height() - BAR_HEIGHT)//2 # Align vertically
             norm_score = (score + 1.0) / 2.0 # Normalize score from -1..1 to 0..1
             rect = draw_progress_bar(surface, (bar_x, bar_y), (rel_bar_width, BAR_HEIGHT), norm_score * 100, 100, rel_color, show_value=False) # Show bar fill based on score

             y_offset += FONT_SMALL.get_linesize() + 5 # Spacing between relationships

             if y_offset > PANEL_HEIGHT - EVENT_LOG_HEIGHT - 30: # Avoid overlap with event log
                  draw_text(surface, "...", (MARGIN + 5, y_offset), FONT_TINY, cfg.GRAY)
                  break
    return y_offset

def draw_world_object_info(surface, y_start, info):
    y_offset = y_start + MARGIN
    draw_text(surface, "World Object Info", (MARGIN, y_offset), FONT_MEDIUM, COLOR_SECTION_HEADER); y_offset += FONT_MEDIUM.get_linesize() + 4

    if not info:
        draw_text(surface, " Click on world tile...", (MARGIN + 5, y_offset), FONT_SMALL, COLOR_LABEL); y_offset += FONT_SMALL.get_linesize()
        return y_offset

    obj_type = info.get("type", "Unknown")
    pos = info.get("pos", "?,?")
    name = info.get("name", "N/A")
    quantity = info.get("quantity", None)
    max_quantity = info.get("max_quantity", None)

    draw_text(surface, f"Type: {obj_type} at ({pos[0]},{pos[1]})", (MARGIN, y_offset), FONT_SMALL, COLOR_VALUE); y_offset += FONT_SMALL.get_linesize()
    draw_text(surface, f"Name: {name}", (MARGIN + 5, y_offset), FONT_SMALL, COLOR_VALUE); y_offset += FONT_SMALL.get_linesize()

    if quantity is not None and max_quantity is not None:
        draw_text(surface, "Quantity:", (MARGIN + 5, y_offset), FONT_SMALL, COLOR_LABEL)
        bar_y = y_offset + (FONT_SMALL.get_height() - BAR_HEIGHT)//2
        bar_x = MARGIN + 70
        bar_w = CONTENT_WIDTH - 80
        # Use default resource color from config if possible
        resource_enum = info.get("resource_type_enum")
        color = cfg.RESOURCE_INFO.get(resource_enum, {}).get('color', cfg.GRAY) if resource_enum else cfg.GRAY
        draw_progress_bar(surface, (bar_x, bar_y), (bar_w, BAR_HEIGHT), quantity, max_quantity, color)
        y_offset += BAR_HEIGHT + 5

    return y_offset
# --- END PASTE TAB CONTENT FUNCTIONS ---


# --- Main UI Drawing Function ---
# Keep track of UI state persistently between calls (using a dictionary)
# This should ideally be managed by a UI class or passed in/out by main.py
ui_persistent_state = {
    "active_tab": "Status",
    "event_log": deque(maxlen=EVENT_LOG_MAX_LINES),
    # Add dummy events for demonstration
    "last_event_add_time": 0,
}

def draw_ui(screen, world, agents, selected_agent, social_manager, clock, ui_state):
    """ Draws the advanced UI panel with tabs, info, log, controls. """
    # --- Update UI State (Tab Clicks, Pause Button) ---
    mouse_pos = pygame.mouse.get_pos()
    # Check mouse pressed state THIS FRAME. Need main loop to track release for proper buttons.
    mouse_pressed = pygame.mouse.get_pressed()[0]

    # Panel Background
    panel_rect = pygame.Rect(PANEL_X, 0, PANEL_WIDTH, PANEL_HEIGHT)
    pygame.draw.rect(screen, cfg.UI_BG_COLOR, panel_rect)
    pygame.draw.line(screen, cfg.WHITE, (PANEL_X, 0), (PANEL_X, PANEL_HEIGHT), 1)

    y_offset = MARGIN
    lh_medium = FONT_MEDIUM.get_linesize()

    # --- Top Section: Simulation Info & Controls ---
    sim_info_y = y_offset
    # Time / Day
    draw_text(screen, f"Day {world.day_count}", (PANEL_X + MARGIN, sim_info_y), FONT_MEDIUM, COLOR_LABEL)
    clock_radius = 15
    clock_center_x = PANEL_X + PANEL_WIDTH - MARGIN - clock_radius
    draw_circular_clock(screen, (clock_center_x, sim_info_y + clock_radius), clock_radius, world.day_time, cfg.DAY_LENGTH_SECONDS)
    y_offset += clock_radius * 2 + 4

    # FPS / Agent Count
    draw_text(screen, f"FPS: {clock.get_fps():.1f}", (PANEL_X + MARGIN, y_offset), FONT_SMALL, COLOR_LABEL); y_offset += FONT_SMALL.get_linesize()
    live_agents = len([a for a in agents if a.health > 0])
    draw_text(screen, f"Agents: {live_agents}/{cfg.INITIAL_AGENT_COUNT}", (PANEL_X + MARGIN, y_offset), FONT_SMALL, COLOR_LABEL); y_offset += FONT_SMALL.get_linesize() + 4

    # Pause Button
    pause_btn_width = 60; pause_btn_height = 20
    pause_btn_x = PANEL_X + (PANEL_WIDTH - pause_btn_width) // 2
    pause_btn_rect = pygame.Rect(pause_btn_x, y_offset, pause_btn_width, pause_btn_height)
    is_paused = ui_state.get("paused", False)
    pause_btn_color = COLOR_PAUSE_BTN_ACTIVE if is_paused else COLOR_PAUSE_BTN_INACTIVE
    pause_btn_text = "PAUSED" if is_paused else "RUNNING"
    pygame.draw.rect(screen, pause_btn_color, pause_btn_rect, border_radius=3)
    draw_text(screen, pause_btn_text, pause_btn_rect.center, FONT_SMALL, cfg.WHITE, align="center")
    pygame.draw.rect(screen, cfg.WHITE, pause_btn_rect, 1, border_radius=3)
    y_offset += pause_btn_height + SECTION_SPACING

    # Check pause button click (simple click-down detection - requires main loop state change)
    if mouse_pressed and pause_btn_rect.collidepoint(mouse_pos):
         if not ui_state.get("_pause_btn_clicked_last_frame", False): # Prevent rapid toggling
             ui_state["paused"] = not is_paused
         ui_state["_pause_btn_clicked_last_frame"] = True
    else:
         ui_state["_pause_btn_clicked_last_frame"] = False


    # Divider
    pygame.draw.line(screen, cfg.GRAY, (PANEL_X + MARGIN // 2, y_offset), (PANEL_X + PANEL_WIDTH - MARGIN // 2, y_offset), 1)
    y_offset += 5

    # --- Tabs ---
    tabs = ["Status", "Inventory", "Skills", "Social"]
    tab_width = (CONTENT_WIDTH - (len(tabs)-1)*2) // len(tabs) # Allow small gap
    tab_y = y_offset
    tab_start_x = PANEL_X + MARGIN
    active_tab = ui_state.get("active_tab", "Status")
    tab_rects = {}

    for i, tab_name in enumerate(tabs):
        tab_x = tab_start_x + i * (tab_width + 2)
        tab_rect = pygame.Rect(tab_x, tab_y, tab_width, TAB_HEIGHT)
        tab_rects[tab_name] = tab_rect
        is_active = (tab_name == active_tab)
        tab_color = COLOR_TAB_ACTIVE if is_active else COLOR_TAB_INACTIVE
        pygame.draw.rect(screen, tab_color, tab_rect, border_top_left_radius=4, border_top_right_radius=4)
        draw_text(screen, tab_name, tab_rect.center, FONT_SMALL, COLOR_TAB_TEXT, align="center")
        pygame.draw.rect(screen, cfg.WHITE, tab_rect, 1, border_top_left_radius=4, border_top_right_radius=4) # Border

        # Check for tab click (simple click-down detection)
        if mouse_pressed and tab_rect.collidepoint(mouse_pos):
             ui_state["active_tab"] = tab_name # Update active tab

    y_offset += TAB_HEIGHT # Move below tabs

    # --- Tab Content Area ---
    content_bg_rect = pygame.Rect(PANEL_X + MARGIN//2, y_offset, PANEL_WIDTH - MARGIN, PANEL_HEIGHT - y_offset - EVENT_LOG_HEIGHT - MARGIN)
    pygame.draw.rect(screen, COLOR_TAB_ACTIVE, content_bg_rect) # Background for content matching active tab color
    pygame.draw.line(screen, cfg.WHITE, content_bg_rect.topleft, content_bg_rect.bottomleft, 1) # Left border
    pygame.draw.line(screen, cfg.WHITE, content_bg_rect.topright, content_bg_rect.bottomright, 1) # Right border
    pygame.draw.line(screen, cfg.WHITE, content_bg_rect.bottomleft, content_bg_rect.bottomright, 1) # Bottom border

    content_y_start = y_offset
    # Create a subsurface to clip drawing within the content area
    try:
        content_surface = screen.subsurface(pygame.Rect(PANEL_X, content_y_start, PANEL_WIDTH, content_bg_rect.height))
    except ValueError as e:
         print(f"Error creating subsurface for UI content: {e}. Rect: {pygame.Rect(PANEL_X, content_y_start, PANEL_WIDTH, content_bg_rect.height)}")
         # Fallback: Draw directly on screen, might draw outside bounds
         content_surface = screen


    # Determine what information to show
    display_target = None
    if selected_agent and selected_agent.health > 0:
        display_target = selected_agent
        target_type = "agent"
    elif ui_state.get("selected_world_object_info"):
        display_target = ui_state["selected_world_object_info"]
        target_type = "world"
    else:
        target_type = "none"


    # Draw content based on active tab and selection
    # Use the subsurface - coordinates for drawing functions are relative to subsurface (topleft is 0,0)
    if target_type == "agent":
        if active_tab == "Status": draw_status_tab(content_surface, 0, display_target)
        elif active_tab == "Inventory": draw_inventory_tab(content_surface, 0, display_target)
        elif active_tab == "Skills": draw_skills_tab(content_surface, 0, display_target)
        elif active_tab == "Social": draw_social_tab(content_surface, 0, display_target, world)
    elif target_type == "world":
        draw_world_object_info(content_surface, 0, display_target)
    else: # Nothing selected
        # Calculate center relative to subsurface
        center_pos = (content_surface.get_width() // 2, content_surface.get_height() // 2)
        draw_text(content_surface, "Select Agent or World Tile", center_pos, FONT_MEDIUM, COLOR_LABEL, align="center")

    y_offset += content_bg_rect.height + 5 # Move below content area

    # --- Event Log ---
    event_log_rect = pygame.Rect(PANEL_X + MARGIN // 2, y_offset, PANEL_WIDTH - MARGIN, EVENT_LOG_HEIGHT)
    pygame.draw.rect(screen, COLOR_EVENT_LOG_BG, event_log_rect, border_radius=3)
    pygame.draw.rect(screen, cfg.WHITE, event_log_rect, 1, border_radius=3)
    draw_text(screen, "Event Log", (event_log_rect.x + 5, event_log_rect.y + 3), FONT_SMALL, COLOR_LABEL)

    # Add Dummy Events (Keep for Demo if real events not yet implemented)
    event_log = ui_state.get("event_log", deque(maxlen=EVENT_LOG_MAX_LINES))
    current_sim_time = world.simulation_time
    if current_sim_time - ui_persistent_state.get("last_event_add_time", 0) > random.uniform(4.0, 8.0): # Random interval
         event_type = random.choice(["Crafted", "Gathered", "Ate", "Drank", "Rested", "Learned", "Helped", "Signaled"])
         item = random.choice(["Wood", "Stone", "Axe", "Pick", "Food", "Skill", "Water", "WB"])
         target_id = random.randint(1, 5) if event_type in ["Helped", "Learned", "Signaled"] else None
         agent_id_source = selected_agent.id if selected_agent else random.randint(0,cfg.INITIAL_AGENT_COUNT-1)

         event_text = f"[{current_sim_time:.0f}s] Ag {agent_id_source}: {event_type} {item}"
         if target_id: event_text += f" (-> Ag {target_id})"
         event_log.appendleft(event_text) # Add to front
         ui_persistent_state["last_event_add_time"] = current_sim_time

    # Display events
    log_y = event_log_rect.y + FONT_SMALL.get_linesize() + 5
    for i, event_msg in enumerate(event_log):
         if log_y + FONT_TINY.get_linesize() > event_log_rect.bottom - 3: break
         draw_text(screen, event_msg, (event_log_rect.x + 5, log_y), FONT_TINY, COLOR_VALUE)
         log_y += FONT_TINY.get_linesize() + 1

    # --- Tooltip (Draw Last) ---
    tooltip_text = None
    if panel_rect.collidepoint(mouse_pos):
        if pause_btn_rect.collidepoint(mouse_pos):
             tooltip_text = "Click to Pause/Resume Simulation"
        else:
             for name, rect in tab_rects.items():
                  if rect.collidepoint(mouse_pos): tooltip_text = f"View {name} Info"; break
    elif mouse_pos[0] < cfg.GAME_WIDTH: # Mouse is over the game world
        grid_x = mouse_pos[0] // cfg.CELL_SIZE; grid_y = mouse_pos[1] // cfg.CELL_SIZE
        if 0 <= grid_x < world.width and 0 <= grid_y < world.height:
            agent_at_pos = next((a for a in agents if a.health > 0 and a.x == grid_x and a.y == grid_y), None)
            if agent_at_pos:
                tooltip_text = f"Agent {agent_at_pos.id} | HP: {agent_at_pos.health:.0f} | Act: {agent_at_pos.current_action or 'Idle'}"
            else:
                 resource = world.get_resource(grid_x, grid_y)
                 if resource and (resource.quantity > 0 or resource.type == cfg.RESOURCE_WORKBENCH):
                      tooltip_text = f"{resource.name}"
                      if resource.type != cfg.RESOURCE_WORKBENCH: tooltip_text += f" ({resource.quantity}/{resource.max_quantity})"
                 elif world.get_terrain(grid_x, grid_y) == cfg.TERRAIN_WATER: tooltip_text = "Water"
                 else: tooltip_text = f"Ground ({grid_x},{grid_y})"

    if tooltip_text:
        tooltip_surf = FONT_SMALL.render(tooltip_text, True, cfg.BLACK, (255, 255, 150)) # Light yellow BG
        tooltip_rect = tooltip_surf.get_rect(bottomleft=(mouse_pos[0] + 12, mouse_pos[1] - 8))
        tooltip_rect.clamp_ip(screen.get_rect()) # Clamp within screen bounds
        border_rect = tooltip_rect.inflate(4, 4)
        pygame.draw.rect(screen, (50,50,50), border_rect, border_radius=2)
        screen.blit(tooltip_surf, tooltip_rect)