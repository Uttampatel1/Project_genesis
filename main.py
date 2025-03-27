# main.py
import pygame
import sys
import random
import time # For performance tracking

import config as cfg
from world import World
from agent import Agent
from ui import draw_world, draw_agent, draw_ui
from social import SocialManager # Phase 4+

def main():
    pygame.init()
    screen = pygame.display.set_mode((cfg.SCREEN_WIDTH, cfg.SCREEN_HEIGHT))
    pygame.display.set_caption("Project Genesis - Real-Time Agent Simulation")
    clock = pygame.time.Clock()

    # --- Initialization ---
    world = World(cfg.GRID_WIDTH, cfg.GRID_HEIGHT)

    # Try loading saved state? (Phase 5)
    # if not world.load_state():
    #     print("Starting new simulation world.")
    # else:
    #     # Need to load agents separately or handle consistency
    #     pass

    agents = []
    for _ in range(cfg.INITIAL_AGENT_COUNT):
        # Find a valid starting position (walkable ground)
        while True:
            start_x = random.randint(0, world.width - 1)
            start_y = random.randint(0, world.height - 1)
            if world.walkability_matrix[start_y, start_x] == 1:
                agent = Agent(start_x, start_y, world)
                # Give some initial knowledge? E.g. basic crafting
                # agent.knowledge.add_recipe('CrudeAxe') # Example: Make Axe known initially
                agents.append(agent)
                break

    social_manager = SocialManager(agents) # Phase 4+

    selected_agent = None
    running = True
    paused = False

    # Performance tracking
    last_update_time = time.time()

    # --- Main Loop ---
    while running:
        # --- Event Handling ---
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    running = False
                if event.key == pygame.K_SPACE:
                    paused = not paused
                    print("Simulation Paused" if paused else "Simulation Resumed")
                # --- Persistence Hotkeys (Phase 5) ---
                # if event.key == pygame.K_s:
                #     world.save_state()
                #     # Need agent saving logic too
                #     print("Attempted to save state (World only).")
                # if event.key == pygame.K_l:
                #     if world.load_state():
                #         # Need agent loading logic too
                #         agents = [] # Clear current agents, reload required
                #         # For now, just restart with loaded world
                #         print("Loaded world state. Agent state not handled yet.")

            if event.type == pygame.MOUSEBUTTONDOWN:
                if not paused: # Allow selection even if paused? Maybe?
                     mouse_x, mouse_y = event.pos
                     # Check if click is within the game world area
                     if mouse_x < cfg.GAME_WIDTH:
                         grid_x = mouse_x // cfg.CELL_SIZE
                         grid_y = mouse_y // cfg.CELL_SIZE
                         # Find agent at this grid cell
                         clicked_agent = None
                         for agent in agents:
                             if agent.x == grid_x and agent.y == grid_y and agent.health > 0:
                                 clicked_agent = agent
                                 break
                         selected_agent = clicked_agent
                         print(f"Selected Agent: {selected_agent.id if selected_agent else 'None'}")


        # --- Simulation Update ---
        if not paused:
            current_time = time.time()
            dt_real_seconds = current_time - last_update_time
            last_update_time = current_time

            # Limit dt to prevent spiral of death if performance tanks
            max_dt = 1.0 / cfg.FPS # Max time step based on target FPS
            dt_clamped = min(dt_real_seconds, max_dt * 2) # Allow slightly larger steps

            # Update World (time, resources)
            world.update(dt_clamped)

            # Update Agents (needs, decisions, actions)
            # Create a copy for safe iteration if agents can be removed (death)
            agents_to_update = list(agents)
            for agent in agents_to_update:
                if agent.health > 0:
                    agent.update(dt_clamped, agents, social_manager) # Pass agents list for social interactions
                elif agent in agents: # If agent died and is still in main list
                    agents.remove(agent) # Remove dead agent
                    if selected_agent == agent:
                         selected_agent = None # Deselect if dead

            # Update Social Manager? (Maybe handles global social events)
            # social_manager.update(dt_clamped)


        # --- Drawing ---
        screen.fill(cfg.BLACK) # Clear screen

        # Draw Game World
        draw_world(screen, world)

        # Draw Agents
        for agent in agents:
            draw_agent(screen, agent)

        # Draw UI Panel
        draw_ui(screen, world, agents, selected_agent, clock)

        # Update display
        pygame.display.flip()

        # Cap FPS
        clock.tick(cfg.FPS)

    # --- Cleanup ---
    pygame.quit()
    sys.exit()

if __name__ == '__main__':
    main()