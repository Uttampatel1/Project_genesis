# ui.py
import pygame
import config as cfg
import time # For signal visualization timing
import math # For day/night cycle calculation

# Initialize font module
pygame.font.init()
try:
    FONT_TINY = pygame.font.SysFont('Arial', 12)
    FONT_SMALL = pygame.font.SysFont('Arial', 14) # Slightly smaller for more dense info
    FONT_MEDIUM = pygame.font.SysFont('Arial', 18) # Slightly smaller
    FONT_LARGE = pygame.font.SysFont('Arial', 22)  # Slightly smaller
except Exception as e:
    print(f"Error loading system font (Arial): {e}. Using default font.")
    FONT_TINY = pygame.font.Font(None, 14)
    FONT_SMALL = pygame.font.Font(None, 18)
    FONT_MEDIUM = pygame.font.Font(None, 22)
    FONT_LARGE = pygame.font.Font(None, 26)

# --- UI Helper Functions ---

def draw_text(surface, text, pos, font, color, shadow_color=None, shadow_offset=(1,1)):
    """Draws text with an optional shadow for better visibility."""
    if shadow_color:
        text_surf_shadow = font.render(text, True, shadow_color)
        surface.blit(text_surf_shadow, (pos[0] + shadow_offset[0], pos[1] + shadow_offset[1]))
    text_surf = font.render(text, True, color)
    surface.blit(text_surf, pos)
    return text_surf.get_rect(topleft=pos) # Return the rect for layout purposes

def draw_progress_bar(surface, pos, size, label, current, maximum, bar_color, bg_color, text_color=cfg.WHITE, show_percent=False):
    """Draws a labeled progress bar."""
    x, y = pos
    width, height = size
    label_width = FONT_SMALL.size(label + ": ")[0] + 5 # Width of the label text + padding

    # Draw Label
    draw_text(surface, f"{label}:", (x, y + (height - FONT_SMALL.get_height()) // 2), FONT_SMALL, cfg.UI_TEXT_COLOR)

    # Draw Bar Background
    bar_x = x + label_width
    bar_width = width - label_width
    bg_rect = pygame.Rect(bar_x, y, bar_width, height)
    pygame.draw.rect(surface, bg_color, bg_rect)

    # Draw Bar Fill
    percent = max(0, min(1, current / maximum)) if maximum > 0 else 0
    fill_width = int(bar_width * percent)
    fill_rect = pygame.Rect(bar_x, y, fill_width, height)
    pygame.draw.rect(surface, bar_color, fill_rect)

    # Draw Border
    pygame.draw.rect(surface, cfg.WHITE, bg_rect, 1)

    # Draw Value Text inside bar
    try:
        val_text = f"{current:.0f}/{maximum:.0f}"
        if show_percent:
            val_text = f"{percent*100:.0f}%"

        val_surf = FONT_TINY.render(val_text, True, text_color)
        val_rect = val_surf.get_rect(center=bg_rect.center)
        # Check if text fits, otherwise don't draw it
        if val_rect.width < bg_rect.width - 4:
            surface.blit(val_surf, val_rect)
    except Exception as e:
        print(f"Warning: Font render error in progress bar: {e}")

    return pygame.Rect(pos, size) # Return the bounding box

def get_relationship_descriptor(score):
    """Returns a text description based on relationship score."""
    if score > 0.7: return "Ally"
    if score > 0.3: return "Friend"
    if score > -0.1: return "Neutral"
    if score > -0.5: return "Disliked"
    return "Hostile"

def get_time_of_day_overlay(day_time, day_length):
    """Calculates color and alpha for a day/night visual overlay."""
    # Normalize time from 0 to 1
    time_norm = (day_time % day_length) / day_length

    # Define darkness intensity (0 = full day, 1 = full night)
    # Simple sine wave: peaks at midnight (0.5), troughs at noon (0) and ends (1)
    darkness = (math.sin(time_norm * 2 * math.pi - math.pi/2) + 1) / 2
    darkness = darkness * 0.8 + 0.1 # Scale to range from 0.1 (min dim) to 0.9 (max darkness)

    max_alpha = 150 # Max opacity for the overlay
    alpha = int(darkness * max_alpha)
    color = (10, 10, 40) # Dark blueish tint for night

    return (*color, alpha)


# --- Main Drawing Functions ---

# Keep draw_world mostly the same, but add the day/night overlay
def draw_world(screen, world, social_manager):
    """ Draws the world grid, terrain, resources, signals, and day/night overlay """
    game_surf = pygame.Surface((cfg.GAME_WIDTH, cfg.SCREEN_HEIGHT))
    game_surf.fill(cfg.BLACK) # Base background

    # 1. Draw Terrain and Resources (as before)
    for y in range(world.height):
        for x in range(world.width):
            # Terrain
            terrain_type = world.terrain_map[y, x]
            color = cfg.TERRAIN_COLORS.get(terrain_type, cfg.DARK_GRAY)
            rect = pygame.Rect(x * cfg.CELL_SIZE, y * cfg.CELL_SIZE, cfg.CELL_SIZE, cfg.CELL_SIZE)
            pygame.draw.rect(game_surf, color, rect)

            # Resources
            resource = world.resource_map[y, x]
            if resource and (resource.quantity > 0 or resource.type == cfg.RESOURCE_WORKBENCH):
                res_info = cfg.RESOURCE_INFO.get(resource.type)
                if res_info:
                    res_color = res_info['color']
                    # Different shape/size for different resources
                    size_mod = 0.7 if resource.type == cfg.RESOURCE_WORKBENCH else 0.6
                    if resource.type == cfg.RESOURCE_WOOD:
                        # Tree-like shape (triangle on rect)
                        base_h = int(cfg.CELL_SIZE * 0.3)
                        base_w = int(cfg.CELL_SIZE * 0.5)
                        trunk_rect = pygame.Rect(x * cfg.CELL_SIZE + (cfg.CELL_SIZE - base_w)//2, y * cfg.CELL_SIZE + cfg.CELL_SIZE - base_h, base_w, base_h)
                        pygame.draw.rect(game_surf, (101, 67, 33), trunk_rect) # Darker brown for trunk
                        top_y = y * cfg.CELL_SIZE + cfg.CELL_SIZE - base_h
                        points = [
                            (x * cfg.CELL_SIZE + cfg.CELL_SIZE // 2, y * cfg.CELL_SIZE + int(cfg.CELL_SIZE*0.1)),
                            (x * cfg.CELL_SIZE + int(cfg.CELL_SIZE * 0.1), top_y),
                            (x * cfg.CELL_SIZE + cfg.CELL_SIZE - int(cfg.CELL_SIZE * 0.1), top_y)
                        ]
                        pygame.draw.polygon(game_surf, res_color, points) # Green top
                    elif resource.type == cfg.RESOURCE_STONE:
                         # Rounded rect / blob
                         blob_rect = pygame.Rect(x * cfg.CELL_SIZE + int(cfg.CELL_SIZE*0.2), y * cfg.CELL_SIZE + int(cfg.CELL_SIZE*0.3), int(cfg.CELL_SIZE*0.6), int(cfg.CELL_SIZE*0.5))
                         pygame.draw.rect(game_surf, res_color, blob_rect, border_radius=int(cfg.CELL_SIZE*0.15))
                         pygame.draw.rect(game_surf, cfg.BLACK, blob_rect, 1, border_radius=int(cfg.CELL_SIZE*0.15)) # Outline
                    elif resource.type == cfg.RESOURCE_FOOD:
                        # Multiple small circles (berries)
                        radius = int(cfg.CELL_SIZE * 0.15)
                        offsets = [(0.3, 0.3), (0.7, 0.3), (0.5, 0.6)]
                        for off_x, off_y in offsets:
                            cx = int(x * cfg.CELL_SIZE + cfg.CELL_SIZE * off_x)
                            cy = int(y * cfg.CELL_SIZE + cfg.CELL_SIZE * off_y)
                            pygame.draw.circle(game_surf, res_color, (cx, cy), radius)
                            pygame.draw.circle(game_surf, cfg.BLACK, (cx, cy), radius, 1) # Outline
                    else: # Default: centered rectangle (Workbench, etc.)
                        res_size = int(cfg.CELL_SIZE * size_mod)
                        offset = (cfg.CELL_SIZE - res_size) // 2
                        res_rect = pygame.Rect(x * cfg.CELL_SIZE + offset, y * cfg.CELL_SIZE + offset, res_size, res_size)
                        pygame.draw.rect(game_surf, res_color, res_rect)
                        pygame.draw.rect(game_surf, cfg.BLACK, res_rect, 1)

    # 2. Draw Active Signals (as before)
    current_time = time.time()
    signals_to_draw = social_manager.active_signals
    for signal in signals_to_draw:
         time_elapsed = current_time - signal.timestamp
         max_signal_time = (cfg.SIGNAL_DURATION_TICKS / cfg.FPS)
         if time_elapsed < max_signal_time:
             # Fade out effect for alpha
             alpha = max(0, int(200 * (1 - (time_elapsed / max_signal_time))))
             # Pulsating effect for radius
             pulse_factor = math.sin(time_elapsed * math.pi * 2 / max_signal_time) # Simple sine pulse
             base_radius = cfg.CELL_SIZE // 2
             radius = int(base_radius * (1 + pulse_factor * 0.2)) # Pulse radius slightly

             try:
                 signal_x, signal_y = signal.position
                 center_x = signal_x * cfg.CELL_SIZE + cfg.CELL_SIZE // 2
                 center_y = signal_y * cfg.CELL_SIZE + cfg.CELL_SIZE // 2

                 temp_surf = pygame.Surface((radius * 2 + 4, radius * 2 + 4), pygame.SRCALPHA)
                 pygame.draw.circle(temp_surf, (*cfg.PURPLE, alpha), (radius+2, radius+2), radius, 2) # Draw outline circle
                 game_surf.blit(temp_surf, (center_x - radius - 2, center_y - radius - 2))

             except Exception as e:
                 print(f"Warning: Error drawing signal {signal.type}: {e}")

    # 3. *** NEW: Draw Day/Night Overlay ***
    overlay_color_alpha = get_time_of_day_overlay(world.day_time, cfg.DAY_LENGTH_SECONDS)
    if overlay_color_alpha[3] > 0: # Only draw if alpha > 0
        overlay_surface = pygame.Surface((cfg.GAME_WIDTH, cfg.SCREEN_HEIGHT), pygame.SRCALPHA)
        overlay_surface.fill(overlay_color_alpha)
        game_surf.blit(overlay_surface, (0, 0))

    # Blit the final game surface onto the main screen
    screen.blit(game_surf, (0, 0))


# Enhanced draw_agent with selection highlight, path, and target drawing
def draw_agent(screen, agent, is_selected=False):
    """ Draws a single agent, highlighting if selected, and showing path/target. """
    if agent.health <= 0: return

    rect = pygame.Rect(agent.x * cfg.CELL_SIZE, agent.y * cfg.CELL_SIZE, cfg.CELL_SIZE, cfg.CELL_SIZE)
    center_x = rect.left + cfg.CELL_SIZE // 2
    center_y = rect.top + cfg.CELL_SIZE // 2
    radius = cfg.CELL_SIZE // 2 - 2

    # Base agent color
    agent_color = cfg.RED

    # *** NEW: Visual cue for low needs (slightly desaturated/darker?) ***
    low_need = agent.hunger > cfg.MAX_HUNGER * 0.8 or \
               agent.thirst > cfg.MAX_THIRST * 0.8 or \
               agent.energy < cfg.MAX_ENERGY * 0.2
    if low_need:
        agent_color = (max(0, agent_color[0]-50), max(0, agent_color[1]-50), max(0, agent_color[2]-50))


    pygame.draw.circle(screen, agent_color, (center_x, center_y), radius)

    # *** NEW: Selection Highlight ***
    if is_selected:
        pygame.draw.circle(screen, cfg.WHITE, (center_x, center_y), radius + 1, 2) # White outline

    # Health Bar (remains the same)
    health_percent = max(0, agent.health / cfg.MAX_HEALTH)
    bar_width = int(cfg.CELL_SIZE * 0.8); bar_height = 3
    bar_x = rect.left + (cfg.CELL_SIZE - bar_width) // 2
    bar_y = rect.top - bar_height - 2
    bg_rect = pygame.Rect(bar_x, bar_y, bar_width, bar_height)
    fill_width = int(bar_width * health_percent)
    fill_rect = pygame.Rect(bar_x, bar_y, fill_width, bar_height)
    bar_color = cfg.GREEN if health_percent > 0.6 else cfg.YELLOW if health_percent > 0.3 else cfg.RED
    pygame.draw.rect(screen, cfg.DARK_GRAY, bg_rect)
    pygame.draw.rect(screen, bar_color, fill_rect)

    # --- Selected Agent Specific Drawings ---
    if is_selected:
        # *** NEW: Draw Current Path ***
        if agent.current_path and len(agent.current_path) > 1:
            path_points = [(agent.x * cfg.CELL_SIZE + cfg.CELL_SIZE // 2, agent.y * cfg.CELL_SIZE + cfg.CELL_SIZE // 2)] + \
                          [(px * cfg.CELL_SIZE + cfg.CELL_SIZE // 2, py * cfg.CELL_SIZE + cfg.CELL_SIZE // 2) for px, py in agent.current_path]
            try:
                pygame.draw.lines(screen, cfg.YELLOW, False, path_points, 1)
            except Exception as e:
                print(f"Warning: Error drawing path: {e}") # Catch potential errors with large paths

        # *** NEW: Draw Action Target Marker ***
        if agent.action_target and agent.action_target.get('goal'):
             goal_pos = agent.action_target['goal']
             # Only draw if goal is different from agent's current pos
             if goal_pos != (agent.x, agent.y):
                 target_x = goal_pos[0] * cfg.CELL_SIZE + cfg.CELL_SIZE // 2
                 target_y = goal_pos[1] * cfg.CELL_SIZE + cfg.CELL_SIZE // 2
                 marker_size = cfg.CELL_SIZE // 3
                 # Draw a simple crosshair
                 pygame.draw.line(screen, cfg.YELLOW, (target_x - marker_size, target_y), (target_x + marker_size, target_y), 1)
                 pygame.draw.line(screen, cfg.YELLOW, (target_x, target_y - marker_size), (target_x, target_y + marker_size), 1)


# Heavily Revised draw_ui function
def draw_ui(screen, world, agents, selected_agent, social_manager, clock):
    """ Draws the UI panel with enhanced info and layout. Includes hover tooltips. """
    panel_rect = pygame.Rect(cfg.GAME_WIDTH, 0, cfg.SIDE_PANEL_WIDTH, cfg.SCREEN_HEIGHT)
    pygame.draw.rect(screen, cfg.UI_BG_COLOR, panel_rect)
    pygame.draw.line(screen, cfg.WHITE, (cfg.GAME_WIDTH, 0), (cfg.GAME_WIDTH, cfg.SCREEN_HEIGHT), 1)

    y_offset = 10
    x_margin = cfg.GAME_WIDTH + 10
    col_width = cfg.SIDE_PANEL_WIDTH - 20
    lh_tiny = FONT_TINY.get_linesize(); lh_small = FONT_SMALL.get_linesize()
    lh_medium = FONT_MEDIUM.get_linesize(); lh_large = FONT_LARGE.get_linesize()

    def draw_divider(y):
        pygame.draw.line(screen, cfg.GRAY, (x_margin, y), (cfg.SCREEN_WIDTH - 10, y), 1)
        return y + 5

    # --- Simulation Info ---
    draw_text(screen, "Simulation Status", (x_margin, y_offset), FONT_LARGE, cfg.WHITE)
    y_offset += lh_large + 2
    sim_time_text = f"Day: {world.day_count}, Time: {world.day_time:.0f}/{cfg.DAY_LENGTH_SECONDS:.0f}s"
    draw_text(screen, sim_time_text, (x_margin, y_offset), FONT_MEDIUM, cfg.UI_TEXT_COLOR); y_offset += lh_medium
    fps_text = f"FPS: {clock.get_fps():.1f}"
    draw_text(screen, fps_text, (x_margin, y_offset), FONT_MEDIUM, cfg.UI_TEXT_COLOR); y_offset += lh_medium
    live_agents = len([a for a in agents if a.health > 0])
    agent_count_text = f"Agents: {live_agents}/{cfg.INITIAL_AGENT_COUNT}"
    draw_text(screen, agent_count_text, (x_margin, y_offset), FONT_MEDIUM, cfg.UI_TEXT_COLOR); y_offset += lh_medium + 5
    y_offset = draw_divider(y_offset)

    # --- Selected Agent Info ---
    draw_text(screen, "Selected Agent", (x_margin, y_offset), FONT_LARGE, cfg.WHITE)
    y_offset += lh_large + 5

    if selected_agent and selected_agent.health > 0:
        # Agent ID, Position, Sociability, Intelligence
        basic_info = f"ID: {selected_agent.id} @ ({selected_agent.x},{selected_agent.y})"
        draw_text(screen, basic_info, (x_margin, y_offset), FONT_MEDIUM, cfg.UI_TEXT_COLOR); y_offset += lh_medium
        soc_int_info = f"Sociability: {selected_agent.sociability:.2f} | Intel: {selected_agent.intelligence:.2f}"
        draw_text(screen, soc_int_info, (x_margin, y_offset), FONT_SMALL, cfg.UI_TEXT_COLOR); y_offset += lh_small + 5

        # Needs Bars (Using helper function)
        needs_data = [
            ("Health", selected_agent.health, cfg.MAX_HEALTH, cfg.GREEN, cfg.DARK_GRAY),
            ("Energy", selected_agent.energy, cfg.MAX_ENERGY, (60, 100, 255), cfg.DARK_GRAY),
            ("Hunger", cfg.MAX_HUNGER - selected_agent.hunger, cfg.MAX_HUNGER, cfg.ORANGE, cfg.DARK_GRAY), # Inverted display
            ("Thirst", cfg.MAX_THIRST - selected_agent.thirst, cfg.MAX_THIRST, cfg.BLUE, cfg.DARK_GRAY),     # Inverted display
        ]
        bar_height_ui = 15; bar_width_ui = col_width
        for name, current, maximum, color_full, color_empty in needs_data:
            # Determine bar color based on threshold (inverted for hunger/thirst)
            is_inverted = name in ["Hunger", "Thirst"]
            percent = max(0, min(1, current / maximum)) if maximum > 0 else 0
            low_thresh = 0.3; med_thresh = 0.6
            is_low = percent < low_thresh; is_med = percent < med_thresh and not is_low
            bar_color = color_full
            if is_low: bar_color=cfg.RED
            elif is_med: bar_color=cfg.YELLOW

            rect = draw_progress_bar(screen, (x_margin, y_offset), (bar_width_ui, bar_height_ui),
                                     name, current, maximum, bar_color, color_empty, cfg.WHITE if percent > 0.3 else cfg.BLACK, show_percent=True)
            y_offset += rect.height + 4
        y_offset += 5

        # Current Action (More detail)
        action_name = selected_agent.current_action if selected_agent.current_action else "Idle"
        action_detail = ""
        timer_text = ""
        if selected_agent.current_action and selected_agent.action_timer > 0:
            # Estimate completion percentage (simplistic, needs actual duration calculation ideally)
            # This is a guess, as durations vary. Agent logic doesn't store max duration easily.
            # We'll just show the timer value.
            timer_text = f" (T:{selected_agent.action_timer:.1f}s)"

        if selected_agent.action_target:
            target = selected_agent.action_target
            details = []
            if 'recipe' in target: details.append(target['recipe'])
            if 'item' in target: details.append(target['item'])
            if 'skill' in target: details.append(target['skill'])
            if 'signal_type' in target: details.append(target['signal_type'])
            if 'target_id' in target: details.append(f"Agent {target['target_id']}")
            # Don't show goal if it's just the agent's current pos or implicitly defined by WB
            goal_pos = target.get('goal')
            is_at_wb = selected_agent._is_at_workbench() if hasattr(selected_agent, '_is_at_workbench') else False
            requires_wb = target.get('requires_workbench', False)
            if goal_pos and goal_pos != (selected_agent.x, selected_agent.y) and \
               not (requires_wb and is_at_wb):
                 details.append(f"@{goal_pos}")

            if details: action_detail = f" ({', '.join(details)})"

        draw_text(screen, f"Action: {action_name}{action_detail}{timer_text}", (x_margin, y_offset), FONT_SMALL, cfg.YELLOW); y_offset += lh_small + 5
        y_offset = draw_divider(y_offset)

        # --- Two Column Layout Start ---
        col1_x = x_margin
        col2_x = x_margin + col_width // 2 + 5
        col_content_width = col_width // 2 - 5
        col1_y = y_offset; col2_y = y_offset

        # Column 1: Inventory & Recipes
        # Inventory
        inv_sum = sum(selected_agent.inventory.values())
        draw_text(screen, f"Inv ({inv_sum}/{cfg.INVENTORY_CAPACITY})", (col1_x, col1_y), FONT_MEDIUM, cfg.WHITE); col1_y += lh_medium
        if not selected_agent.inventory:
            draw_text(screen, " Empty", (col1_x + 5, col1_y), FONT_SMALL, cfg.UI_TEXT_COLOR); col1_y += lh_small
        else:
             items_list = sorted(list(selected_agent.inventory.items()))
             for item, count in items_list:
                 draw_text(screen, f" {item}: {count}", (col1_x + 5, col1_y), FONT_SMALL, cfg.UI_TEXT_COLOR); col1_y += lh_small
        col1_y += 10

        # Known Recipes
        draw_text(screen, "Recipes", (col1_x, col1_y), FONT_MEDIUM, cfg.WHITE); col1_y += lh_medium
        known_recipes = sorted(list(selected_agent.knowledge.known_recipes))
        if not known_recipes:
            draw_text(screen, " None", (col1_x + 5, col1_y), FONT_SMALL, cfg.UI_TEXT_COLOR); col1_y += lh_small
        else:
             for recipe in known_recipes:
                 draw_text(screen, f" {recipe}", (col1_x + 5, col1_y), FONT_SMALL, cfg.UI_TEXT_COLOR); col1_y += lh_small
        col1_y += 10


        # Column 2: Skills & Relationships
        # Skills (with progress bars)
        draw_text(screen, "Skills", (col2_x, col2_y), FONT_MEDIUM, cfg.WHITE); col2_y += lh_medium
        skills_to_show = {k: v for k, v in sorted(selected_agent.skills.items()) if v >= 0.1}
        if not skills_to_show:
            draw_text(screen, " None", (col2_x + 5, col2_y), FONT_SMALL, cfg.UI_TEXT_COLOR); col2_y += lh_small
        else:
            skill_bar_height = 12
            skill_bar_width = col_content_width
            for skill_name, level in skills_to_show.items():
                 bar_color = (200, 200, 0) # Yellowish for skills
                 rect = draw_progress_bar(screen, (col2_x, col2_y), (skill_bar_width, skill_bar_height),
                                          skill_name, level, cfg.MAX_SKILL_LEVEL, bar_color, cfg.DARK_GRAY, show_percent=False)
                 col2_y += rect.height + 3
        col2_y += 10

        # Relationships (with descriptors)
        draw_text(screen, "Relationships", (col2_x, col2_y), FONT_MEDIUM, cfg.WHITE); col2_y += lh_medium
        relationships = sorted(selected_agent.knowledge.relationships.items(), key=lambda item: item[1], reverse=True) # Sort by score
        if not relationships:
             draw_text(screen, " None known", (col2_x + 5, col2_y), FONT_SMALL, cfg.UI_TEXT_COLOR); col2_y += lh_small
        else:
             max_rels_shown = 6 # Limit displayed relationships
             for i, (other_id, score) in enumerate(relationships):
                 if i >= max_rels_shown and len(relationships) > max_rels_shown+1:
                      draw_text(screen, f" ... ({len(relationships)-i} more)", (col2_x + 5, col2_y), FONT_TINY, cfg.GRAY); col2_y += lh_tiny
                      break

                 other_agent = world.get_agent_by_id(other_id)
                 status = "" if other_agent and other_agent.health > 0 else " (X)" # Indicate if target agent is gone
                 descriptor = get_relationship_descriptor(score)
                 rel_text = f" Agent {other_id}{status}: {score:.2f} ({descriptor})"
                 rel_color = cfg.GREEN if score > 0.3 else cfg.YELLOW if score > -0.1 else cfg.RED
                 draw_text(screen, rel_text, (col2_x + 5, col2_y), FONT_SMALL, rel_color); col2_y += lh_small

                 # Stop drawing if bottom of panel is reached
                 if col2_y > cfg.SCREEN_HEIGHT - 30: break

        # --- End Two Column Layout ---
        y_offset = max(col1_y, col2_y) + 5 # Update y_offset to below the taller column
        y_offset = draw_divider(y_offset)


    else: # No agent selected
        no_select_text = "Click on an agent to select"
        draw_text(screen, no_select_text, (x_margin, y_offset), FONT_MEDIUM, cfg.UI_TEXT_COLOR)
        y_offset += lh_medium
        no_select_text2 = "Hover over objects for info"
        draw_text(screen, no_select_text2, (x_margin, y_offset), FONT_SMALL, cfg.UI_TEXT_COLOR); y_offset += lh_small


    # --- Hover Tooltip Area (Draw last in UI) ---
    mouse_pos = pygame.mouse.get_pos()
    tooltip_text = None

    if panel_rect.collidepoint(mouse_pos):
        # Potentially add tooltips for UI elements here later if needed
        pass
    elif mouse_pos[0] < cfg.GAME_WIDTH: # Mouse is over the game world
        grid_x = mouse_pos[0] // cfg.CELL_SIZE
        grid_y = mouse_pos[1] // cfg.CELL_SIZE

        if 0 <= grid_x < world.width and 0 <= grid_y < world.height:
            # Check for agent first
            agent_at_pos = None
            for agent in agents: # Check living agents
                 if agent.health > 0 and agent.x == grid_x and agent.y == grid_y:
                      agent_at_pos = agent; break # Find first agent at pos

            if agent_at_pos:
                tooltip_text = f"Agent {agent_at_pos.id} | HP: {agent_at_pos.health:.0f} | Act: {agent_at_pos.current_action or 'Idle'}"
            else:
                 # Check for resource
                 resource = world.get_resource(grid_x, grid_y)
                 if resource and (resource.quantity > 0 or resource.type == cfg.RESOURCE_WORKBENCH):
                      tooltip_text = f"{resource.name}"
                      if resource.type != cfg.RESOURCE_WORKBENCH:
                           tooltip_text += f" ({resource.quantity}/{resource.max_quantity})"
                 elif world.get_terrain(grid_x, grid_y) == cfg.TERRAIN_WATER:
                      tooltip_text = "Water"
                 else: # Check terrain
                      terrain_type = world.get_terrain(grid_x, grid_y)
                      if terrain_type == cfg.TERRAIN_GROUND: tooltip_text = f"Ground ({grid_x},{grid_y})"
                      elif terrain_type == cfg.TERRAIN_OBSTACLE: tooltip_text = "Obstacle"


    # Draw the tooltip if text is available
    if tooltip_text:
        tooltip_surf = FONT_SMALL.render(tooltip_text, True, cfg.BLACK, cfg.YELLOW) # Black text on yellow bg
        tooltip_rect = tooltip_surf.get_rect(bottomleft=(mouse_pos[0] + 10, mouse_pos[1] - 5))

        # Keep tooltip on screen
        if tooltip_rect.right > cfg.SCREEN_WIDTH:
            tooltip_rect.right = cfg.SCREEN_WIDTH - 5
        if tooltip_rect.bottom > cfg.SCREEN_HEIGHT:
            tooltip_rect.bottom = cfg.SCREEN_HEIGHT - 5
        if tooltip_rect.left < 0: tooltip_rect.left = 5
        if tooltip_rect.top < 0: tooltip_rect.top = 5

        screen.blit(tooltip_surf, tooltip_rect)