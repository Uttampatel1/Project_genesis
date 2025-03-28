# ui.py
import pygame
import config as cfg

pygame.font.init()
try:
    FONT_SMALL = pygame.font.SysFont(None, 18)
    FONT_MEDIUM = pygame.font.SysFont(None, 24)
    FONT_LARGE = pygame.font.SysFont(None, 30)
except Exception as e:
    print(f"Error loading system font: {e}. Using default.")
    FONT_SMALL = pygame.font.Font(None, 18)
    FONT_MEDIUM = pygame.font.Font(None, 24)
    FONT_LARGE = pygame.font.Font(None, 30)


def draw_world(screen, world):
    """ Draws the world grid, terrain, and resources """
    game_surf = pygame.Surface((cfg.GAME_WIDTH, cfg.SCREEN_HEIGHT))
    game_surf.fill(cfg.BLACK) # Background for the game area

    for y in range(world.height):
        for x in range(world.width):
            # Draw Terrain
            terrain_type = world.terrain_map[y, x]
            color = cfg.TERRAIN_COLORS.get(terrain_type, cfg.GRAY) # Default to gray if unknown
            rect = pygame.Rect(x * cfg.CELL_SIZE, y * cfg.CELL_SIZE, cfg.CELL_SIZE, cfg.CELL_SIZE)
            pygame.draw.rect(game_surf, color, rect)

            # Draw Resources (on top of terrain)
            resource = world.resource_map[y, x]
            if resource and resource.quantity > 0: # Draw only if quantity > 0
                res_info = cfg.RESOURCE_INFO.get(resource.type)
                if res_info:
                    res_color = res_info['color']
                    # Draw slightly smaller rect or circle for resource
                    res_rect = pygame.Rect(x * cfg.CELL_SIZE + cfg.CELL_SIZE // 4,
                                           y * cfg.CELL_SIZE + cfg.CELL_SIZE // 4,
                                           cfg.CELL_SIZE // 2, cfg.CELL_SIZE // 2)
                    pygame.draw.rect(game_surf, res_color, res_rect)
                    # Optional: Draw quantity indicator (small number)
                    if resource.max_quantity > 1: # Only show quantity if not binary (like workbench)
                        qty_surf = FONT_SMALL.render(str(resource.quantity), True, cfg.WHITE)
                        qty_rect = qty_surf.get_rect(center=(res_rect.centerx, res_rect.top - 5))
                        game_surf.blit(qty_surf, qty_rect)

            # Draw Grid lines (optional, can make it look busy)
            # pygame.draw.rect(game_surf, cfg.DARK_GRAY, rect, 1) # Thin border

    screen.blit(game_surf, (0, 0))


def draw_agent(screen, agent):
    """ Draws a single agent on the main screen """
    if agent.health <= 0: return # Don't draw dead agents

    rect = pygame.Rect(agent.x * cfg.CELL_SIZE, agent.y * cfg.CELL_SIZE, cfg.CELL_SIZE, cfg.CELL_SIZE)
    # Draw agent as a circle
    center_x = rect.left + cfg.CELL_SIZE // 2
    center_y = rect.top + cfg.CELL_SIZE // 2
    radius = cfg.CELL_SIZE // 2 - 2 # Slightly smaller circle
    pygame.draw.circle(screen, cfg.RED, (center_x, center_y), radius)

    # Draw Health Bar above agent
    health_percent = max(0, agent.health / cfg.MAX_HEALTH)
    bar_width = cfg.CELL_SIZE * 0.8
    bar_height = 3
    bar_x = rect.left + (cfg.CELL_SIZE - bar_width) // 2
    bar_y = rect.top - bar_height - 2
    health_bar_bg_rect = pygame.Rect(bar_x, bar_y, bar_width, bar_height)
    filled_width = int(bar_width * health_percent)
    health_bar_fill_rect = pygame.Rect(bar_x, bar_y, filled_width, bar_height)

    # Choose color based on health
    bar_color = cfg.GREEN
    if health_percent < 0.6: bar_color = cfg.YELLOW
    if health_percent < 0.3: bar_color = cfg.RED

    pygame.draw.rect(screen, cfg.DARK_GRAY, health_bar_bg_rect) # Background
    pygame.draw.rect(screen, bar_color, health_bar_fill_rect) # Fill

    # Draw Energy Bar below agent (optional)
    # energy_percent = max(0, agent.energy / cfg.MAX_ENERGY)
    # energy_bar_y = rect.bottom + 2
    # energy_bar_rect = pygame.Rect(bar_x, energy_bar_y, bar_width, bar_height)
    # filled_energy_width = int(bar_width * energy_percent)
    # energy_fill_rect = pygame.Rect(bar_x, energy_bar_y, filled_energy_width, bar_height)
    # pygame.draw.rect(screen, cfg.DARK_GRAY, energy_bar_rect)
    # pygame.draw.rect(screen, cfg.BLUE, energy_fill_rect) # Blue for energy


def draw_ui(screen, world, agents, selected_agent, clock):
    """ Draws the UI panel with simulation info and selected agent details """
    panel_rect = pygame.Rect(cfg.GAME_WIDTH, 0, cfg.SIDE_PANEL_WIDTH, cfg.SCREEN_HEIGHT)
    pygame.draw.rect(screen, cfg.UI_BG_COLOR, panel_rect)
    pygame.draw.line(screen, cfg.WHITE, (cfg.GAME_WIDTH, 0), (cfg.GAME_WIDTH, cfg.SCREEN_HEIGHT), 1) # Separator line

    y_offset = 10
    x_margin = cfg.GAME_WIDTH + 10
    col_width = cfg.SIDE_PANEL_WIDTH - 20

    # --- Simulation Info ---
    sim_time_text = FONT_MEDIUM.render(f"Day: {world.day_count}, Time: {world.day_time:.0f}s", True, cfg.UI_TEXT_COLOR)
    screen.blit(sim_time_text, (x_margin, y_offset))
    y_offset += 25

    fps_text = FONT_MEDIUM.render(f"FPS: {clock.get_fps():.1f}", True, cfg.UI_TEXT_COLOR)
    screen.blit(fps_text, (x_margin, y_offset))
    y_offset += 25

    live_agents = len([a for a in agents if a.health > 0])
    agent_count_text = FONT_MEDIUM.render(f"Agents: {live_agents}", True, cfg.UI_TEXT_COLOR)
    screen.blit(agent_count_text, (x_margin, y_offset))
    y_offset += 35

    # --- Selected Agent Info ---
    title_text = FONT_LARGE.render("Selected Agent", True, cfg.WHITE)
    screen.blit(title_text, (x_margin, y_offset))
    y_offset += 35

    if selected_agent and selected_agent.health > 0:
        agent_id_text = FONT_MEDIUM.render(f"ID: {selected_agent.id} @ ({selected_agent.x},{selected_agent.y})", True, cfg.UI_TEXT_COLOR)
        screen.blit(agent_id_text, (x_margin, y_offset))
        y_offset += 25

        # Needs Bars
        needs = [
            ("Health", selected_agent.health, cfg.MAX_HEALTH, cfg.GREEN, cfg.RED),
            ("Energy", selected_agent.energy, cfg.MAX_ENERGY, cfg.BLUE, cfg.DARK_GRAY),
            ("Hunger", cfg.MAX_HUNGER - selected_agent.hunger, cfg.MAX_HUNGER, cfg.ORANGE, cfg.DARK_GRAY), # Invert hunger display
            ("Thirst", cfg.MAX_THIRST - selected_agent.thirst, cfg.MAX_THIRST, cfg.BLUE, cfg.DARK_GRAY), # Invert thirst display
        ]
        bar_height_ui = 15
        for name, current, maximum, color_full, color_empty in needs:
            percent = max(0, min(1, current / maximum))
            bar_width_ui = col_width - 60 # Leave space for text
            fill_width = int(bar_width_ui * percent)

            name_surf = FONT_SMALL.render(f"{name}:", True, cfg.UI_TEXT_COLOR)
            screen.blit(name_surf, (x_margin, y_offset + 2))

            bg_rect = pygame.Rect(x_margin + 55, y_offset, bar_width_ui, bar_height_ui)
            fill_rect = pygame.Rect(x_margin + 55, y_offset, fill_width, bar_height_ui)

            # Choose color based on percentage (similar to health bar)
            bar_color = color_full
            if percent < 0.6: bar_color = cfg.YELLOW if name in ["Health", "Energy"] else color_full # Keep hunger/thirst color
            if percent < 0.3: bar_color = cfg.RED if name in ["Health", "Energy"] else color_full

            pygame.draw.rect(screen, color_empty, bg_rect)
            pygame.draw.rect(screen, bar_color, fill_rect)
            pygame.draw.rect(screen, cfg.WHITE, bg_rect, 1) # Border

            val_surf = FONT_SMALL.render(f"{current:.0f}", True, cfg.WHITE)
            val_rect = val_surf.get_rect(center=bg_rect.center)
            screen.blit(val_surf, val_rect)


            y_offset += bar_height_ui + 5
        y_offset += 10

        # Action
        action_name = selected_agent.current_action if selected_agent.current_action else "Idle"
        action_text = FONT_MEDIUM.render(f"Action: {action_name}", True, cfg.YELLOW)
        screen.blit(action_text, (x_margin, y_offset))
        y_offset += 30

        # Inventory
        inv_title = FONT_MEDIUM.render("Inventory:", True, cfg.WHITE)
        screen.blit(inv_title, (x_margin, y_offset))
        y_offset += 25
        if not selected_agent.inventory:
             none_text = FONT_SMALL.render("  Empty", True, cfg.UI_TEXT_COLOR)
             screen.blit(none_text, (x_margin + 5, y_offset))
             y_offset += 20
        else:
             # Simple two-column display if many items
             items_list = list(selected_agent.inventory.items())
             rows = (len(items_list) + 1) // 2
             for i in range(rows):
                 # Left column item
                 item_left, count_left = items_list[i]
                 text_left = f"  {item_left}: {count_left}"
                 surf_left = FONT_SMALL.render(text_left, True, cfg.UI_TEXT_COLOR)
                 screen.blit(surf_left, (x_margin + 5, y_offset))

                 # Right column item (if exists)
                 idx_right = i + rows
                 if idx_right < len(items_list):
                     item_right, count_right = items_list[idx_right]
                     text_right = f"  {item_right}: {count_right}"
                     surf_right = FONT_SMALL.render(text_right, True, cfg.UI_TEXT_COLOR)
                     screen.blit(surf_right, (x_margin + col_width // 2, y_offset))

                 y_offset += 18 # Line height
        y_offset += 10

        # Skills
        skills_title = FONT_MEDIUM.render("Skills:", True, cfg.WHITE)
        screen.blit(skills_title, (x_margin, y_offset))
        y_offset += 25
        skills_to_show = {k: v for k, v in sorted(selected_agent.skills.items()) if v > 0.1} # Show skills with noticeable level
        if not skills_to_show:
            none_text = FONT_SMALL.render("  None learned", True, cfg.UI_TEXT_COLOR)
            screen.blit(none_text, (x_margin + 5, y_offset))
            y_offset += 20
        else:
            skills_list = list(skills_to_show.items())
            rows = (len(skills_list) + 1) // 2
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
                     screen.blit(surf_right, (x_margin + col_width // 2 + 10, y_offset))

                 y_offset += 18 # Line height
        y_offset += 10

        # Known Recipes
        recipes_title = FONT_MEDIUM.render("Known Recipes:", True, cfg.WHITE)
        screen.blit(recipes_title, (x_margin, y_offset))
        y_offset += 25
        known_recipes = sorted(list(selected_agent.knowledge.known_recipes))
        if not known_recipes:
            none_text = FONT_SMALL.render("  None", True, cfg.UI_TEXT_COLOR)
            screen.blit(none_text, (x_margin + 5, y_offset))
            y_offset += 20
        else:
             # Simple list, wrap if needed (basic wrap)
             current_x = x_margin + 5
             line_start_y = y_offset
             max_items_per_line = 3 # Adjust based on text width
             count = 0
             for i, recipe in enumerate(known_recipes):
                 recipe_text = f"{recipe}" + (", " if i < len(known_recipes)-1 else "")
                 recipe_surf = FONT_SMALL.render(recipe_text, True, cfg.UI_TEXT_COLOR)
                 recipe_rect = recipe_surf.get_rect(topleft=(current_x, y_offset))

                 if recipe_rect.right > cfg.SCREEN_WIDTH - 10 and count > 0: # Wrap line
                     y_offset += 18
                     current_x = x_margin + 5
                     recipe_rect.topleft = (current_x, y_offset)
                     count = 0

                 screen.blit(recipe_surf, recipe_rect)
                 current_x = recipe_rect.right
                 count += 1

             y_offset += 18 # Move past last line

    else:
        no_select_text = FONT_MEDIUM.render("Click on an agent to select", True, cfg.UI_TEXT_COLOR)
        screen.blit(no_select_text, (x_margin, y_offset))