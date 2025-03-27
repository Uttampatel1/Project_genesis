# ui.py
import pygame
import config as cfg

pygame.font.init()
FONT_SMALL = pygame.font.SysFont(None, 18)
FONT_MEDIUM = pygame.font.SysFont(None, 24)
FONT_LARGE = pygame.font.SysFont(None, 30)

def draw_world(screen, world):
    """ Draws the world grid, terrain, and resources """
    for y in range(world.height):
        for x in range(world.width):
            # Draw Terrain
            terrain_type = world.terrain_map[y, x]
            color = cfg.TERRAIN_COLORS.get(terrain_type, cfg.GRAY)
            rect = pygame.Rect(x * cfg.CELL_SIZE, y * cfg.CELL_SIZE, cfg.CELL_SIZE, cfg.CELL_SIZE)
            pygame.draw.rect(screen, color, rect)

            # Draw Resources (on top of terrain)
            resource = world.resource_map[y, x]
            if resource and not resource.is_depleted(): # Don't draw depleted resource
                res_info = cfg.RESOURCE_INFO.get(resource.type)
                if res_info:
                    res_color = res_info['color']
                    # Draw slightly smaller rect or circle for resource
                    res_rect = pygame.Rect(x * cfg.CELL_SIZE + cfg.CELL_SIZE // 4,
                                           y * cfg.CELL_SIZE + cfg.CELL_SIZE // 4,
                                           cfg.CELL_SIZE // 2, cfg.CELL_SIZE // 2)
                    pygame.draw.rect(screen, res_color, res_rect)
                    # Optional: Draw quantity indicator?
                    # quantity_text = FONT_SMALL.render(str(resource.quantity), True, cfg.WHITE)
                    # screen.blit(quantity_text, (res_rect.x, res_rect.y - 10))

            # Draw Grid lines (optional)
            pygame.draw.rect(screen, cfg.GRAY, rect, 1) # Border


def draw_agent(screen, agent):
    """ Draws a single agent """
    if agent.health <= 0: return # Don't draw dead agents

    rect = pygame.Rect(agent.x * cfg.CELL_SIZE, agent.y * cfg.CELL_SIZE, cfg.CELL_SIZE, cfg.CELL_SIZE)
    # Draw agent as a circle
    center_x = rect.left + cfg.CELL_SIZE // 2
    center_y = rect.top + cfg.CELL_SIZE // 2
    pygame.draw.circle(screen, cfg.RED, (center_x, center_y), cfg.CELL_SIZE // 2 - 1)

    # Draw Health Bar above agent
    health_percent = agent.health / cfg.MAX_HEALTH
    bar_width = cfg.CELL_SIZE * 0.8
    bar_height = 4
    health_bar_rect = pygame.Rect(rect.left + (cfg.CELL_SIZE - bar_width) // 2, rect.top - bar_height - 2, bar_width, bar_height)
    filled_width = int(bar_width * health_percent)
    filled_rect = pygame.Rect(health_bar_rect.left, health_bar_rect.top, filled_width, bar_height)
    pygame.draw.rect(screen, cfg.GRAY, health_bar_rect) # Background
    pygame.draw.rect(screen, cfg.GREEN if health_percent > 0.3 else cfg.RED, filled_rect) # Fill


def draw_ui(screen, world, agents, selected_agent, clock):
    """ Draws the UI panel with simulation info and selected agent details """
    panel_rect = pygame.Rect(cfg.GAME_WIDTH, 0, cfg.SIDE_PANEL_WIDTH, cfg.SCREEN_HEIGHT)
    pygame.draw.rect(screen, cfg.UI_BG_COLOR, panel_rect)

    y_offset = 10

    # Simulation Info
    sim_time_text = FONT_MEDIUM.render(f"Day: {world.day_count}, Time: {world.day_time:.0f}s", True, cfg.UI_TEXT_COLOR)
    screen.blit(sim_time_text, (cfg.GAME_WIDTH + 10, y_offset))
    y_offset += 30

    fps_text = FONT_MEDIUM.render(f"FPS: {clock.get_fps():.1f}", True, cfg.UI_TEXT_COLOR)
    screen.blit(fps_text, (cfg.GAME_WIDTH + 10, y_offset))
    y_offset += 30

    agent_count_text = FONT_MEDIUM.render(f"Agents: {len([a for a in agents if a.health > 0])}", True, cfg.UI_TEXT_COLOR)
    screen.blit(agent_count_text, (cfg.GAME_WIDTH + 10, y_offset))
    y_offset += 40

    # Selected Agent Info
    title_text = FONT_LARGE.render("Selected Agent", True, cfg.WHITE)
    screen.blit(title_text, (cfg.GAME_WIDTH + 10, y_offset))
    y_offset += 40

    if selected_agent and selected_agent.health > 0:
        agent_id_text = FONT_MEDIUM.render(f"ID: {selected_agent.id}", True, cfg.UI_TEXT_COLOR)
        screen.blit(agent_id_text, (cfg.GAME_WIDTH + 10, y_offset))
        y_offset += 25

        health_text = FONT_MEDIUM.render(f"Health: {selected_agent.health:.0f}/{cfg.MAX_HEALTH}", True, cfg.UI_TEXT_COLOR)
        screen.blit(health_text, (cfg.GAME_WIDTH + 10, y_offset))
        y_offset += 25

        energy_text = FONT_MEDIUM.render(f"Energy: {selected_agent.energy:.0f}/{cfg.MAX_ENERGY}", True, cfg.UI_TEXT_COLOR)
        screen.blit(energy_text, (cfg.GAME_WIDTH + 10, y_offset))
        y_offset += 25

        hunger_text = FONT_MEDIUM.render(f"Hunger: {selected_agent.hunger:.0f}/{cfg.MAX_HUNGER}", True, cfg.UI_TEXT_COLOR)
        screen.blit(hunger_text, (cfg.GAME_WIDTH + 10, y_offset))
        y_offset += 25

        thirst_text = FONT_MEDIUM.render(f"Thirst: {selected_agent.thirst:.0f}/{cfg.MAX_THIRST}", True, cfg.UI_TEXT_COLOR)
        screen.blit(thirst_text, (cfg.GAME_WIDTH + 10, y_offset))
        y_offset += 25

        action_text = FONT_MEDIUM.render(f"Action: {selected_agent.current_action}", True, cfg.YELLOW)
        screen.blit(action_text, (cfg.GAME_WIDTH + 10, y_offset))
        y_offset += 35

        inventory_text = FONT_MEDIUM.render("Inventory:", True, cfg.WHITE)
        screen.blit(inventory_text, (cfg.GAME_WIDTH + 10, y_offset))
        y_offset += 25
        if not selected_agent.inventory:
             none_text = FONT_SMALL.render("  Empty", True, cfg.UI_TEXT_COLOR)
             screen.blit(none_text, (cfg.GAME_WIDTH + 15, y_offset))
             y_offset += 20
        else:
             for item, count in selected_agent.inventory.items():
                 item_text = FONT_SMALL.render(f"  {item}: {count}", True, cfg.UI_TEXT_COLOR)
                 screen.blit(item_text, (cfg.GAME_WIDTH + 15, y_offset))
                 y_offset += 20
        y_offset += 10

        skills_text = FONT_MEDIUM.render("Skills:", True, cfg.WHITE)
        screen.blit(skills_text, (cfg.GAME_WIDTH + 10, y_offset))
        y_offset += 25
        # Display only skills with level > 0? Or all known skills?
        skills_to_show = {k: v for k, v in selected_agent.skills.items() if v > 0}
        if not skills_to_show:
            none_text = FONT_SMALL.render("  None learned", True, cfg.UI_TEXT_COLOR)
            screen.blit(none_text, (cfg.GAME_WIDTH + 15, y_offset))
            y_offset += 20
        else:
            for skill, level in skills_to_show.items():
                 skill_text = FONT_SMALL.render(f"  {skill}: {level:.1f}", True, cfg.UI_TEXT_COLOR)
                 screen.blit(skill_text, (cfg.GAME_WIDTH + 15, y_offset))
                 y_offset += 20
        y_offset += 10

        knowledge_text = FONT_MEDIUM.render("Known Recipes:", True, cfg.WHITE)
        screen.blit(knowledge_text, (cfg.GAME_WIDTH + 10, y_offset))
        y_offset += 25
        if not selected_agent.knowledge.known_recipes:
            none_text = FONT_SMALL.render("  None", True, cfg.UI_TEXT_COLOR)
            screen.blit(none_text, (cfg.GAME_WIDTH + 15, y_offset))
            y_offset += 20
        else:
             # Limit display if too many recipes
             for i, recipe in enumerate(list(selected_agent.knowledge.known_recipes)[:5]):
                 recipe_text = FONT_SMALL.render(f"  {recipe}", True, cfg.UI_TEXT_COLOR)
                 screen.blit(recipe_text, (cfg.GAME_WIDTH + 15, y_offset))
                 y_offset += 20
             if len(selected_agent.knowledge.known_recipes) > 5:
                  more_text = FONT_SMALL.render("  ...", True, cfg.UI_TEXT_COLOR)
                  screen.blit(more_text, (cfg.GAME_WIDTH + 15, y_offset))
                  y_offset += 20


    else:
        no_select_text = FONT_MEDIUM.render("Click on an agent to select", True, cfg.UI_TEXT_COLOR)
        screen.blit(no_select_text, (cfg.GAME_WIDTH + 10, y_offset))