# ui.py
import pygame
import config as cfg
import time # For signal visualization timing

# Initialize font module
pygame.font.init()
try:
    FONT_SMALL = pygame.font.SysFont('Arial', 16)
    FONT_MEDIUM = pygame.font.SysFont('Arial', 20)
    FONT_LARGE = pygame.font.SysFont('Arial', 24)
except Exception as e:
    print(f"Error loading system font (Arial): {e}. Using default font.")
    FONT_SMALL = pygame.font.Font(None, 18)
    FONT_MEDIUM = pygame.font.Font(None, 24)
    FONT_LARGE = pygame.font.Font(None, 30)


def draw_world(screen, world, social_manager):
    """ Draws the world grid, terrain, resources, and active signals """
    game_surf = pygame.Surface((cfg.GAME_WIDTH, cfg.SCREEN_HEIGHT))
    game_surf.fill(cfg.BLACK)

    # Draw Terrain and Resources (as before)
    for y in range(world.height):
        for x in range(world.width):
            terrain_type = world.terrain_map[y, x]
            color = cfg.TERRAIN_COLORS.get(terrain_type, cfg.DARK_GRAY)
            rect = pygame.Rect(x * cfg.CELL_SIZE, y * cfg.CELL_SIZE, cfg.CELL_SIZE, cfg.CELL_SIZE)
            pygame.draw.rect(game_surf, color, rect)

            resource = world.resource_map[y, x]
            if resource and (resource.quantity > 0 or resource.type == cfg.RESOURCE_WORKBENCH):
                res_info = cfg.RESOURCE_INFO.get(resource.type)
                if res_info:
                    res_color = res_info['color']
                    res_size_ratio = 0.7 if resource.type == cfg.RESOURCE_WORKBENCH else 0.6
                    res_size = int(cfg.CELL_SIZE * res_size_ratio)
                    offset = (cfg.CELL_SIZE - res_size) // 2
                    res_rect = pygame.Rect(x * cfg.CELL_SIZE + offset, y * cfg.CELL_SIZE + offset, res_size, res_size)
                    pygame.draw.rect(game_surf, res_color, res_rect)
                    pygame.draw.rect(game_surf, cfg.BLACK, res_rect, 1)

    # --- Phase 4: Draw Active Signals ---
    current_time = time.time()
    signals_to_draw = social_manager.active_signals # Get current signals
    for signal in signals_to_draw:
         time_elapsed = current_time - signal.timestamp
         # Fade out effect (optional) - decrease alpha over time
         max_alpha = 200
         alpha = max(0, int(max_alpha * (1 - (time_elapsed / (cfg.SIGNAL_DURATION_TICKS / cfg.FPS)))))
         if alpha > 0:
             try:
                 # Draw a simple circle indicator for the signal
                 signal_x, signal_y = signal.position
                 center_x = signal_x * cfg.CELL_SIZE + cfg.CELL_SIZE // 2
                 center_y = signal_y * cfg.CELL_SIZE + cfg.CELL_SIZE // 2
                 radius = cfg.CELL_SIZE // 2

                 # Create a temporary surface for transparency
                 temp_surf = pygame.Surface((radius * 2, radius * 2), pygame.SRCALPHA)
                 pygame.draw.circle(temp_surf, (*cfg.PURPLE, alpha), (radius, radius), radius) # Use signal color
                 game_surf.blit(temp_surf, (center_x - radius, center_y - radius))

                 # Optional: Draw signal type text briefly
                 # if time_elapsed < 0.5: # Only show text for first half second
                 #    sig_font = pygame.font.Font(None, 14)
                 #    sig_surf = sig_font.render(signal.type, True, cfg.WHITE)
                 #    sig_rect = sig_surf.get_rect(center=(center_x, center_y - radius - 5))
                 #    game_surf.blit(sig_surf, sig_rect)

             except Exception as e: # Catch potential drawing errors
                 print(f"Warning: Error drawing signal {signal.type}: {e}")


    # Blit the game surface onto the main screen
    screen.blit(game_surf, (0, 0))


def draw_agent(screen, agent):
    """ Draws a single agent on the main screen with a health bar. """
    if agent.health <= 0: return # Don't draw dead agents

    rect = pygame.Rect(agent.x * cfg.CELL_SIZE, agent.y * cfg.CELL_SIZE, cfg.CELL_SIZE, cfg.CELL_SIZE)
    center_x = rect.left + cfg.CELL_SIZE // 2
    center_y = rect.top + cfg.CELL_SIZE // 2
    radius = cfg.CELL_SIZE // 2 - 2
    pygame.draw.circle(screen, cfg.RED, (center_x, center_y), radius)

    # Health Bar
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


def draw_ui(screen, world, agents, selected_agent, social_manager, clock):
    """ Draws the UI panel with simulation info and selected agent details (Phase 4). """
    panel_rect = pygame.Rect(cfg.GAME_WIDTH, 0, cfg.SIDE_PANEL_WIDTH, cfg.SCREEN_HEIGHT)
    pygame.draw.rect(screen, cfg.UI_BG_COLOR, panel_rect)
    pygame.draw.line(screen, cfg.WHITE, (cfg.GAME_WIDTH, 0), (cfg.GAME_WIDTH, cfg.SCREEN_HEIGHT), 1)

    y_offset = 10
    x_margin = cfg.GAME_WIDTH + 10
    col_width = cfg.SIDE_PANEL_WIDTH - 20
    lh_small = FONT_SMALL.get_linesize(); lh_medium = FONT_MEDIUM.get_linesize(); lh_large = FONT_LARGE.get_linesize()

    # --- Simulation Info ---
    sim_time_text = FONT_MEDIUM.render(f"Day: {world.day_count}, Time: {world.day_time:.0f}s", True, cfg.UI_TEXT_COLOR)
    screen.blit(sim_time_text, (x_margin, y_offset)); y_offset += lh_medium
    fps_text = FONT_MEDIUM.render(f"FPS: {clock.get_fps():.1f}", True, cfg.UI_TEXT_COLOR)
    screen.blit(fps_text, (x_margin, y_offset)); y_offset += lh_medium
    live_agents = len([a for a in agents if a.health > 0])
    agent_count_text = FONT_MEDIUM.render(f"Agents: {live_agents}", True, cfg.UI_TEXT_COLOR)
    screen.blit(agent_count_text, (x_margin, y_offset)); y_offset += lh_medium + 10

    # --- Selected Agent Info ---
    title_text = FONT_LARGE.render("Selected Agent", True, cfg.WHITE)
    screen.blit(title_text, (x_margin, y_offset)); y_offset += lh_large + 5

    if selected_agent and selected_agent.health > 0:
        # Agent ID, Position, Sociability
        soc_text = f"Soc: {selected_agent.sociability:.2f}"
        agent_id_text = FONT_MEDIUM.render(f"ID: {selected_agent.id} @ ({selected_agent.x},{selected_agent.y}) {soc_text}", True, cfg.UI_TEXT_COLOR)
        screen.blit(agent_id_text, (x_margin, y_offset)); y_offset += lh_medium

        # Needs Bars (Unchanged from Phase 3)
        needs_data = [
            ("Health", selected_agent.health, cfg.MAX_HEALTH, cfg.GREEN, cfg.RED),
            ("Energy", selected_agent.energy, cfg.MAX_ENERGY, (60, 100, 255), cfg.DARK_GRAY),
            ("Hunger", cfg.MAX_HUNGER - selected_agent.hunger, cfg.MAX_HUNGER, cfg.ORANGE, cfg.DARK_GRAY),
            ("Thirst", cfg.MAX_THIRST - selected_agent.thirst, cfg.MAX_THIRST, cfg.BLUE, cfg.DARK_GRAY),
        ]
        bar_height_ui=15; bar_label_width=55; bar_width_ui=col_width-bar_label_width-5
        for name, current, maximum, color_full, color_empty in needs_data:
            percent=max(0,min(1,current/maximum)) if maximum>0 else 0; fill_width=int(bar_width_ui*percent)
            name_surf=FONT_SMALL.render(f"{name}:",True,cfg.UI_TEXT_COLOR); screen.blit(name_surf,(x_margin,y_offset+1))
            is_inverted=name in ["Hunger","Thirst"]; low_thresh=0.3; med_thresh=0.6
            is_low=percent<low_thresh; is_med=percent<med_thresh and not is_low
            bar_color=color_full
            if (is_inverted and (is_low or is_med)) or (not is_inverted and is_low): bar_color=cfg.RED
            elif (is_inverted and not is_low and not is_med) or (not is_inverted and is_med): bar_color=cfg.YELLOW
            bg_rect=pygame.Rect(x_margin+bar_label_width,y_offset,bar_width_ui,bar_height_ui)
            fill_rect=pygame.Rect(x_margin+bar_label_width,y_offset,fill_width,bar_height_ui)
            pygame.draw.rect(screen,color_empty,bg_rect); pygame.draw.rect(screen,bar_color,fill_rect); pygame.draw.rect(screen,cfg.WHITE,bg_rect,1)
            try:
                val_text=f"{current:.0f}" if not is_inverted else f"{maximum-current:.0f}"
                val_surf=FONT_SMALL.render(val_text,True,cfg.WHITE if percent>0.4 else cfg.BLACK)
                val_rect=val_surf.get_rect(center=bg_rect.center); screen.blit(val_surf,val_rect)
            except Exception as e: print(f"Warning: Font render error: {e}")
            y_offset += bar_height_ui + 4
        y_offset += 10

        # Current Action (Display includes target ID for social actions)
        action_name = selected_agent.current_action if selected_agent.current_action else "Idle"
        target_info_str = ""
        if selected_agent.action_target:
            target_id = selected_agent.action_target.get('target_id')
            goal = selected_agent.action_target.get('goal')
            recipe = selected_agent.action_target.get('recipe')
            item = selected_agent.action_target.get('item')
            skill = selected_agent.action_target.get('skill')
            sig_type = selected_agent.action_target.get('signal_type')

            if target_id is not None: target_info_str += f" -> Agent {target_id}"
            if recipe: target_info_str += f" ({recipe})"
            elif item: target_info_str += f" ({item})"
            elif skill: target_info_str += f" ({skill})"
            elif sig_type: target_info_str += f" ({sig_type})"
            elif goal and goal != (selected_agent.x, selected_agent.y): target_info_str += f" @{goal}"


        action_text = FONT_MEDIUM.render(f"Action: {action_name}{target_info_str}", True, cfg.YELLOW)
        screen.blit(action_text, (x_margin, y_offset)); y_offset += lh_medium

        # Inventory (Unchanged)
        inv_sum = sum(selected_agent.inventory.values())
        inv_title = FONT_MEDIUM.render(f"Inventory ({inv_sum}/{cfg.INVENTORY_CAPACITY}):", True, cfg.WHITE)
        screen.blit(inv_title, (x_margin, y_offset)); y_offset += lh_medium
        if not selected_agent.inventory: screen.blit(FONT_SMALL.render("  Empty", True, cfg.UI_TEXT_COLOR), (x_margin + 5, y_offset)); y_offset += lh_small
        else:
             items_list = sorted(list(selected_agent.inventory.items()))
             for item, count in items_list: screen.blit(FONT_SMALL.render(f"  {item}: {count}", True, cfg.UI_TEXT_COLOR), (x_margin + 5, y_offset)); y_offset += lh_small
        y_offset += 10

        # Skills (Unchanged)
        skills_title = FONT_MEDIUM.render("Skills:", True, cfg.WHITE)
        screen.blit(skills_title, (x_margin, y_offset)); y_offset += lh_medium
        skills_to_show = {k: v for k, v in sorted(selected_agent.skills.items()) if v >= 0.1}
        if not skills_to_show: screen.blit(FONT_SMALL.render("  None", True, cfg.UI_TEXT_COLOR), (x_margin + 5, y_offset)); y_offset += lh_small
        else:
            skills_list = list(skills_to_show.items()); rows = (len(skills_list) + 1) // 2
            col1_width = col_width // 2 - 5; col2_x = x_margin + col1_width + 10
            for i in range(rows):
                 skill_left, level_left = skills_list[i]; text_left = f"  {skill_left}: {level_left:.1f}"
                 surf_left = FONT_SMALL.render(text_left, True, cfg.UI_TEXT_COLOR); screen.blit(surf_left, (x_margin + 5, y_offset))
                 idx_right = i + rows
                 if idx_right < len(skills_list):
                     skill_right, level_right = skills_list[idx_right]; text_right = f"  {skill_right}: {level_right:.1f}"
                     surf_right = FONT_SMALL.render(text_right, True, cfg.UI_TEXT_COLOR); screen.blit(surf_right, (col2_x, y_offset))
                 y_offset += lh_small
        y_offset += 10

        # Known Recipes (Unchanged)
        recipes_title = FONT_MEDIUM.render("Known Recipes:", True, cfg.WHITE)
        screen.blit(recipes_title, (x_margin, y_offset)); y_offset += lh_medium
        known_recipes = sorted(list(selected_agent.knowledge.known_recipes))
        if not known_recipes: screen.blit(FONT_SMALL.render("  None", True, cfg.UI_TEXT_COLOR), (x_margin + 5, y_offset)); y_offset += lh_small
        else:
             current_x = x_margin + 5; max_panel_width = cfg.SIDE_PANEL_WIDTH - 15
             for i, recipe in enumerate(known_recipes):
                 recipe_text = f"{recipe}" + (", " if i < len(known_recipes)-1 else ""); recipe_surf = FONT_SMALL.render(recipe_text, True, cfg.UI_TEXT_COLOR)
                 recipe_rect = recipe_surf.get_rect(topleft=(current_x, y_offset))
                 if recipe_rect.right > cfg.GAME_WIDTH + max_panel_width and current_x > x_margin + 5:
                      y_offset += lh_small; current_x = x_margin + 5; recipe_rect.topleft = (current_x, y_offset)
                 screen.blit(recipe_surf, recipe_rect); current_x = recipe_rect.right + 2
             y_offset += lh_small
        y_offset += 10

        # --- Phase 4: Relationships ---
        rels_title = FONT_MEDIUM.render("Relationships:", True, cfg.WHITE)
        screen.blit(rels_title, (x_margin, y_offset)); y_offset += lh_medium
        relationships = sorted(selected_agent.knowledge.relationships.items())
        if not relationships:
             screen.blit(FONT_SMALL.render("  None known", True, cfg.UI_TEXT_COLOR), (x_margin + 5, y_offset)); y_offset += lh_small
        else:
             # Simple list for now
             for other_id, score in relationships:
                  # Check if agent is still alive (optional, relationship might persist)
                  # other_agent = world.get_agent_by_id(other_id)
                  # status = "" if other_agent and other_agent.health > 0 else " (Dead?)"
                  rel_text = f"  Agent {other_id}: {score:.2f}" #+ status
                  rel_color = cfg.GREEN if score > 0.5 else cfg.YELLOW if score > -0.2 else cfg.RED
                  screen.blit(FONT_SMALL.render(rel_text, True, rel_color), (x_margin + 5, y_offset))
                  y_offset += lh_small
                  # Limit displayed relationships if too many?
                  if y_offset > cfg.SCREEN_HEIGHT - 30: # Avoid drawing off screen
                       screen.blit(FONT_SMALL.render("  ...", True, cfg.UI_TEXT_COLOR), (x_margin + 5, y_offset)); y_offset += lh_small
                       break


    else: # No agent selected
        no_select_text = FONT_MEDIUM.render("Click on an agent to select", True, cfg.UI_TEXT_COLOR)
        screen.blit(no_select_text, (x_margin, y_offset))