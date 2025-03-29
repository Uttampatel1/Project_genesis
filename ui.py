# ui.py
import pygame
import config as cfg
# from config import * # Can be risky, better to use cfg. prefix

# Initialize font module
pygame.font.init()
try:
    # Try loading a common system font
    FONT_SMALL = pygame.font.SysFont('Arial', 16)
    FONT_MEDIUM = pygame.font.SysFont('Arial', 20)
    FONT_LARGE = pygame.font.SysFont('Arial', 24)
except Exception as e:
    # Fallback to default pygame font if system font fails
    print(f"Error loading system font (Arial): {e}. Using default font.")
    FONT_SMALL = pygame.font.Font(None, 18) # Slightly larger defaults
    FONT_MEDIUM = pygame.font.Font(None, 24)
    FONT_LARGE = pygame.font.Font(None, 30)


def draw_world(screen, world):
    """ Draws the world grid, terrain, and resources """
    # Create a separate surface for the game area for clarity
    game_surf = pygame.Surface((cfg.GAME_WIDTH, cfg.SCREEN_HEIGHT))
    game_surf.fill(cfg.BLACK) # Black background for game area

    for y in range(world.height):
        for x in range(world.width):
            # --- Draw Terrain ---
            terrain_type = world.terrain_map[y, x]
            color = cfg.TERRAIN_COLORS.get(terrain_type, cfg.DARK_GRAY) # Default color if unknown
            rect = pygame.Rect(x * cfg.CELL_SIZE, y * cfg.CELL_SIZE, cfg.CELL_SIZE, cfg.CELL_SIZE)
            pygame.draw.rect(game_surf, color, rect)

            # --- Draw Resources (on top of terrain) ---
            resource = world.resource_map[y, x]
            # Draw if resource exists AND (it has quantity OR it's a workbench)
            if resource and (resource.quantity > 0 or resource.type == cfg.RESOURCE_WORKBENCH):
                res_info = cfg.RESOURCE_INFO.get(resource.type)
                if res_info:
                    res_color = res_info['color']
                    # Make workbench slightly larger visually
                    res_size_ratio = 0.7 if resource.type == cfg.RESOURCE_WORKBENCH else 0.6
                    res_size = int(cfg.CELL_SIZE * res_size_ratio)
                    offset = (cfg.CELL_SIZE - res_size) // 2 # Center the resource icon
                    res_rect = pygame.Rect(x * cfg.CELL_SIZE + offset,
                                           y * cfg.CELL_SIZE + offset,
                                           res_size, res_size)
                    pygame.draw.rect(game_surf, res_color, res_rect)
                    pygame.draw.rect(game_surf, cfg.BLACK, res_rect, 1) # Add black border

                    # Optional: Draw quantity for depletable resources (can clutter)
                    # if resource.max_quantity > 1 and resource.quantity < resource.max_quantity:
                    #    qty_surf = FONT_SMALL.render(str(resource.quantity), True, cfg.WHITE)
                    #    qty_rect = qty_surf.get_rect(center=(res_rect.centerx, res_rect.top - 5))
                    #    game_surf.blit(qty_surf, qty_rect)

            # --- Draw Grid Lines (Optional) ---
            # pygame.draw.rect(game_surf, cfg.DARK_GRAY, rect, 1) # Draw cell borders

    # Blit the game surface onto the main screen
    screen.blit(game_surf, (0, 0))


def draw_agent(screen, agent):
    """ Draws a single agent on the main screen with a health bar. """
    if agent.health <= 0: return # Don't draw dead agents

    # Agent representation (simple circle)
    rect = pygame.Rect(agent.x * cfg.CELL_SIZE, agent.y * cfg.CELL_SIZE, cfg.CELL_SIZE, cfg.CELL_SIZE)
    center_x = rect.left + cfg.CELL_SIZE // 2
    center_y = rect.top + cfg.CELL_SIZE // 2
    radius = cfg.CELL_SIZE // 2 - 2 # Leave a small gap
    pygame.draw.circle(screen, cfg.RED, (center_x, center_y), radius)

    # --- Draw Health Bar above agent ---
    health_percent = max(0, agent.health / cfg.MAX_HEALTH)
    bar_width = int(cfg.CELL_SIZE * 0.8)
    bar_height = 3
    bar_x = rect.left + (cfg.CELL_SIZE - bar_width) // 2
    bar_y = rect.top - bar_height - 2 # Position above the agent circle
    health_bar_bg_rect = pygame.Rect(bar_x, bar_y, bar_width, bar_height)
    # Calculate width of the filled portion based on health percentage
    filled_width = int(bar_width * health_percent)
    health_bar_fill_rect = pygame.Rect(bar_x, bar_y, filled_width, bar_height)

    # Choose color based on health level
    bar_color = cfg.GREEN if health_percent > 0.6 else cfg.YELLOW if health_percent > 0.3 else cfg.RED

    # Draw background and filled portion of the health bar
    pygame.draw.rect(screen, cfg.DARK_GRAY, health_bar_bg_rect)
    pygame.draw.rect(screen, bar_color, health_bar_fill_rect)


def draw_ui(screen, world, agents, selected_agent, clock):
    """ Draws the UI panel with simulation info and selected agent details (Phase 3). """
    # --- Panel Background and Separator ---
    panel_rect = pygame.Rect(cfg.GAME_WIDTH, 0, cfg.SIDE_PANEL_WIDTH, cfg.SCREEN_HEIGHT)
    pygame.draw.rect(screen, cfg.UI_BG_COLOR, panel_rect)
    pygame.draw.line(screen, cfg.WHITE, (cfg.GAME_WIDTH, 0), (cfg.GAME_WIDTH, cfg.SCREEN_HEIGHT), 1)

    # --- UI Element Positioning ---
    y_offset = 10
    x_margin = cfg.GAME_WIDTH + 10
    col_width = cfg.SIDE_PANEL_WIDTH - 20 # Width available for content
    line_height_small = FONT_SMALL.get_linesize()
    line_height_medium = FONT_MEDIUM.get_linesize()
    line_height_large = FONT_LARGE.get_linesize()

    # --- Simulation Info ---
    sim_time_text = FONT_MEDIUM.render(f"Day: {world.day_count}, Time: {world.day_time:.0f}s", True, cfg.UI_TEXT_COLOR)
    screen.blit(sim_time_text, (x_margin, y_offset)); y_offset += line_height_medium

    fps_text = FONT_MEDIUM.render(f"FPS: {clock.get_fps():.1f}", True, cfg.UI_TEXT_COLOR)
    screen.blit(fps_text, (x_margin, y_offset)); y_offset += line_height_medium

    live_agents = len([a for a in agents if a.health > 0])
    agent_count_text = FONT_MEDIUM.render(f"Agents: {live_agents}", True, cfg.UI_TEXT_COLOR)
    screen.blit(agent_count_text, (x_margin, y_offset)); y_offset += line_height_medium + 10

    # --- Selected Agent Info ---
    title_text = FONT_LARGE.render("Selected Agent", True, cfg.WHITE)
    screen.blit(title_text, (x_margin, y_offset)); y_offset += line_height_large + 5

    if selected_agent and selected_agent.health > 0:
        # Agent ID and Position
        agent_id_text = FONT_MEDIUM.render(f"ID: {selected_agent.id} @ ({selected_agent.x},{selected_agent.y})", True, cfg.UI_TEXT_COLOR)
        screen.blit(agent_id_text, (x_margin, y_offset)); y_offset += line_height_medium

        # --- Needs Bars ---
        needs_data = [
            ("Health", selected_agent.health, cfg.MAX_HEALTH, cfg.GREEN, cfg.RED),
            ("Energy", selected_agent.energy, cfg.MAX_ENERGY, (60, 100, 255), cfg.DARK_GRAY), # Bright blue for energy
            ("Hunger", cfg.MAX_HUNGER - selected_agent.hunger, cfg.MAX_HUNGER, cfg.ORANGE, cfg.DARK_GRAY), # Inverted (display fullness)
            ("Thirst", cfg.MAX_THIRST - selected_agent.thirst, cfg.MAX_THIRST, cfg.BLUE, cfg.DARK_GRAY), # Inverted (display fullness)
        ]
        bar_height_ui = 15
        bar_label_width = 55 # Space for "Health:", "Energy:", etc.
        bar_width_ui = col_width - bar_label_width - 5 # Width of the actual bar

        for name, current, maximum, color_full, color_empty in needs_data:
            percent = max(0, min(1, current / maximum)) if maximum > 0 else 0
            fill_width = int(bar_width_ui * percent)

            # Draw label
            name_surf = FONT_SMALL.render(f"{name}:", True, cfg.UI_TEXT_COLOR)
            screen.blit(name_surf, (x_margin, y_offset + 1)) # +1 for vertical alignment

            # Determine bar color based on percentage (critical/medium/full)
            is_inverted = name in ["Hunger", "Thirst"]
            low_threshold = 0.3
            medium_threshold = 0.6
            is_low = percent < low_threshold
            is_medium = percent < medium_threshold and not is_low

            bar_color = color_full
            if (is_inverted and (is_low or is_medium)) or (not is_inverted and is_low):
                bar_color = cfg.RED
            elif (is_inverted and not is_low and not is_medium) or (not is_inverted and is_medium):
                 bar_color = cfg.YELLOW # Use Yellow for medium range

            # Draw bar background and fill
            bg_rect = pygame.Rect(x_margin + bar_label_width, y_offset, bar_width_ui, bar_height_ui)
            fill_rect = pygame.Rect(x_margin + bar_label_width, y_offset, fill_width, bar_height_ui)
            pygame.draw.rect(screen, color_empty, bg_rect)
            pygame.draw.rect(screen, bar_color, fill_rect)
            pygame.draw.rect(screen, cfg.WHITE, bg_rect, 1) # Border

            # Display numeric value inside bar (optional)
            try: # Handle potential font rendering errors
                val_text = f"{current:.0f}" if name not in ["Hunger", "Thirst"] else f"{maximum - current:.0f}"
                val_surf = FONT_SMALL.render(val_text, True, cfg.WHITE if percent > 0.4 else cfg.BLACK) # Contrasting text
                val_rect = val_surf.get_rect(center=bg_rect.center)
                screen.blit(val_surf, val_rect)
            except Exception as e:
                print(f"Warning: Font rendering error for value {val_text}: {e}")


            y_offset += bar_height_ui + 4 # Spacing between bars
        y_offset += 10 # Extra space after needs

        # --- Current Action ---
        action_name = selected_agent.current_action if selected_agent.current_action else "Idle"
        target_info_str = "" # String to show target details
        if selected_agent.action_target:
            target_type = selected_agent.action_target.get('type')
            goal = selected_agent.action_target.get('goal')
            recipe = selected_agent.action_target.get('recipe')
            purpose = selected_agent.action_target.get('purpose') # For GoToWorkbench

            if recipe: target_info_str = f" ({recipe})"
            elif purpose: target_info_str = f" ({purpose})"
            # Show goal coords only if moving towards a different tile
            elif goal and goal != (selected_agent.x, selected_agent.y): target_info_str = f" -> {goal}"

        action_text = FONT_MEDIUM.render(f"Action: {action_name}{target_info_str}", True, cfg.YELLOW)
        screen.blit(action_text, (x_margin, y_offset)); y_offset += line_height_medium

        # --- Inventory ---
        inv_sum = sum(selected_agent.inventory.values())
        inv_title = FONT_MEDIUM.render(f"Inventory ({inv_sum}/{cfg.INVENTORY_CAPACITY}):", True, cfg.WHITE)
        screen.blit(inv_title, (x_margin, y_offset)); y_offset += line_height_medium
        if not selected_agent.inventory:
             screen.blit(FONT_SMALL.render("  Empty", True, cfg.UI_TEXT_COLOR), (x_margin + 5, y_offset)); y_offset += line_height_small
        else:
             items_list = sorted(list(selected_agent.inventory.items()))
             # Simple list display for now
             for item, count in items_list:
                  screen.blit(FONT_SMALL.render(f"  {item}: {count}", True, cfg.UI_TEXT_COLOR), (x_margin + 5, y_offset))
                  y_offset += line_height_small
        y_offset += 10

        # --- Skills ---
        skills_title = FONT_MEDIUM.render("Skills:", True, cfg.WHITE)
        screen.blit(skills_title, (x_margin, y_offset)); y_offset += line_height_medium
        skills_to_show = {k: v for k, v in sorted(selected_agent.skills.items()) if v >= 0.1} # Show skills with some level
        if not skills_to_show:
            screen.blit(FONT_SMALL.render("  None", True, cfg.UI_TEXT_COLOR), (x_margin + 5, y_offset)); y_offset += line_height_small
        else:
            # Two-column display for skills
            skills_list = list(skills_to_show.items())
            rows = (len(skills_list) + 1) // 2 # Calculate rows needed for two columns
            col1_width = col_width // 2 - 5
            col2_x = x_margin + col1_width + 10

            for i in range(rows):
                 # Left column skill
                 skill_left, level_left = skills_list[i]
                 text_left = f"  {skill_left}: {level_left:.1f}"
                 surf_left = FONT_SMALL.render(text_left, True, cfg.UI_TEXT_COLOR)
                 screen.blit(surf_left, (x_margin + 5, y_offset))

                 # Right column skill (if exists)
                 idx_right = i + rows
                 if idx_right < len(skills_list):
                     skill_right, level_right = skills_list[idx_right]
                     text_right = f"  {skill_right}: {level_right:.1f}"
                     surf_right = FONT_SMALL.render(text_right, True, cfg.UI_TEXT_COLOR)
                     screen.blit(surf_right, (col2_x, y_offset))

                 y_offset += line_height_small # Move to next row
        y_offset += 10

        # --- Known Recipes ---
        recipes_title = FONT_MEDIUM.render("Known Recipes:", True, cfg.WHITE)
        screen.blit(recipes_title, (x_margin, y_offset)); y_offset += line_height_medium
        known_recipes = sorted(list(selected_agent.knowledge.known_recipes))
        if not known_recipes:
            screen.blit(FONT_SMALL.render("  None", True, cfg.UI_TEXT_COLOR), (x_margin + 5, y_offset)); y_offset += line_height_small
        else:
             # Display recipes in potentially wrapping lines
             current_x = x_margin + 5
             line_start_y = y_offset
             max_panel_width = cfg.SIDE_PANEL_WIDTH - 15 # Allow margin

             for i, recipe in enumerate(known_recipes):
                 # Add comma and space unless it's the last item
                 recipe_text = f"{recipe}" + (", " if i < len(known_recipes)-1 else "")
                 recipe_surf = FONT_SMALL.render(recipe_text, True, cfg.UI_TEXT_COLOR)
                 recipe_rect = recipe_surf.get_rect(topleft=(current_x, y_offset))

                 # Check for wrapping
                 if recipe_rect.right > cfg.GAME_WIDTH + max_panel_width:
                     # Only wrap if not the first item on the line
                     if current_x > x_margin + 5:
                         y_offset += line_height_small # Move to next line
                         current_x = x_margin + 5      # Reset X position
                         recipe_rect.topleft = (current_x, y_offset) # Update rect pos

                 screen.blit(recipe_surf, recipe_rect)
                 current_x = recipe_rect.right + 2 # Position for next item

             y_offset += line_height_small # Move past the last line of recipes
        y_offset += 10

        # Optional: Display known workbench locations
        # known_wbs = selected_agent.knowledge.get_known_locations(cfg.RESOURCE_WORKBENCH)
        # wb_title = FONT_SMALL.render(f"Known WBs: {len(known_wbs)} {known_wbs}", True, cfg.UI_TEXT_COLOR)
        # screen.blit(wb_title, (x_margin, y_offset)); y_offset += line_height_small

    else: # No agent selected
        no_select_text = FONT_MEDIUM.render("Click on an agent to select", True, cfg.UI_TEXT_COLOR)
        screen.blit(no_select_text, (x_margin, y_offset))