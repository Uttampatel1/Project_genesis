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
    pygame.font.init() # Ensure font module is initialized
    screen = pygame.display.set_mode((cfg.SCREEN_WIDTH, cfg.SCREEN_HEIGHT))
    pygame.display.set_caption("Project Genesis - Agent Simulation")
    clock = pygame.time.Clock()

    # --- Initialization ---
    print("Initializing World...")
    world = World(cfg.GRID_WIDTH, cfg.GRID_HEIGHT)

    # Optional: Try loading saved state
    # if world.load_state():
    #     print("Loaded world state.")
    #     # TODO: Need agent loading logic as well for full persistence
    # else:
    #     print("Starting new simulation world.")

    print("Initializing Agents...")
    agents = []
    for i in range(cfg.INITIAL_AGENT_COUNT):
        while True:
            start_x = random.randint(0, world.width - 1)
            start_y = random.randint(0, world.height - 1)
            if world.walkability_matrix[start_y, start_x] == 1:
                agent = Agent(start_x, start_y, world)
                # Give some initial knowledge?
                # agent.knowledge.add_recipe('CrudeAxe')
                agents.append(agent)
                print(f"  Agent {agent.id} created at ({start_x},{start_y})")
                break
            # Safety break if somehow can't place agents
            if i > cfg.INITIAL_AGENT_COUNT * 10:
                print("Error: Could not find valid starting position for all agents!")
                break


    print("Initializing Social Manager...")
    social_manager = SocialManager(agents)

    selected_agent = None
    running = True
    paused = False

    # Performance tracking
    last_update_time = time.time()
    update_times = []

    # --- Main Loop ---
    print("Starting Simulation Loop...")
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
                    print("--- Simulation Paused ---" if paused else "--- Simulation Resumed ---")
                # --- Persistence Hotkeys (Add Agent Save/Load Later) ---
                if event.key == pygame.K_s and pygame.key.get_mods() & pygame.KMOD_CTRL:
                    print("Saving world state...")
                    world.save_state()
                    # TODO: Save agent states
                    print("World state saved (Agent state NOT saved).")
                if event.key == pygame.K_l and pygame.key.get_mods() & pygame.KMOD_CTRL:
                     print("Loading world state...")
                     if world.load_state():
                         # TODO: Load agent states matching the world
                         agents = [] # Clear current agents, needs reload logic
                         social_manager.update_agent_list(agents) # Update social manager too
                         selected_agent = None
                         print("World state loaded. Agents cleared - requires agent loading implementation.")
                     else:
                         print("World load failed.")


            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1: # Left click
                 # Allow selection even if paused
                 mouse_x, mouse_y = event.pos
                 # Check if click is within the game world area
                 if mouse_x < cfg.GAME_WIDTH:
                     grid_x = mouse_x // cfg.CELL_SIZE
                     grid_y = mouse_y // cfg.CELL_SIZE
                     # Find agent at this grid cell (topmost if multiple)
                     clicked_agent = None
                     min_dist_sq = float('inf') # Select precisely clicked agent
                     for agent in reversed(agents): # Check later agents first (drawn on top)
                         if agent.health > 0 and agent.x == grid_x and agent.y == grid_y:
                              clicked_agent = agent
                              break # Found the topmost agent

                     if selected_agent != clicked_agent:
                          selected_agent = clicked_agent
                          print(f"Selected Agent: {selected_agent.id if selected_agent else 'None'}")
                 else:
                      # Clicked on UI panel - deselect agent? Or handle UI buttons later.
                      # selected_agent = None
                      # print("Clicked UI Panel.")
                      pass


        # --- Simulation Update ---
        if not paused:
            start_update_time = time.time()

            current_time = time.time()
            dt_real_seconds = current_time - last_update_time
            last_update_time = current_time

            # Clamp dt to prevent spiral of death, but allow catching up slightly
            max_dt = 1.0 / cfg.FPS # Target frame time
            dt_clamped = min(dt_real_seconds, max_dt * 3) # Allow up to 3x target frame time

            # Update World (time, resources)
            world.update(dt_clamped)

            # Update Agents (needs, decisions, actions)
            agents_alive_before_update = len(agents)
            dead_this_tick = []
            for agent in agents: # Iterate directly, removal happens after loop
                if agent.health > 0:
                    try:
                        agent.update(dt_clamped, agents, social_manager)
                    except Exception as e:
                         print(f"!!! Runtime Error updating Agent {agent.id}: {e}")
                         import traceback
                         traceback.print_exc()
                         # Option: Kill the agent? Or just log and continue?
                         # agent.health = 0 # Kill buggy agent
                if agent.health <= 0:
                     if agent not in dead_this_tick: # Only add once
                         dead_this_tick.append(agent)

            # Remove dead agents after the update loop
            if dead_this_tick:
                print(f"Removing {len(dead_this_tick)} dead agents: {[a.id for a in dead_this_tick]}")
                agents = [a for a in agents if a.health > 0]
                social_manager.update_agent_list(agents) # Update social manager's view
                if selected_agent and selected_agent.health <= 0:
                    selected_agent = None # Deselect if dead

            # Update Social Manager? (Could handle global events, relationship decay)
            # social_manager.update(dt_clamped)

            # Performance monitoring
            end_update_time = time.time()
            update_times.append(end_update_time - start_update_time)
            if len(update_times) > 100: update_times.pop(0) # Keep last 100 samples


        # --- Drawing ---
        screen.fill(cfg.BLACK) # Clear screen

        # Draw Game World
        draw_world(screen, world)

        # Draw Agents (draw selected last to be on top?)
        for agent in agents:
            if agent != selected_agent:
                 draw_agent(screen, agent)
        if selected_agent: # Draw selected agent last/on top
             draw_agent(screen, selected_agent)

        # Draw UI Panel
        draw_ui(screen, world, agents, selected_agent, clock)

        # Update display
        pygame.display.flip()

        # Cap FPS
        clock.tick(cfg.FPS)

        # Optional: Print average update time periodically
        # if not paused and len(update_times) > 0 and world.simulation_time % 5 < dt_clamped * cfg.SIMULATION_SPEED_FACTOR: # Approx every 5 sim seconds
        #      avg_update = sum(update_times) / len(update_times)
        #      print(f"Avg update time (last 100): {avg_update*1000:.2f} ms")


    # --- Cleanup ---
    print("Exiting Simulation.")
    pygame.quit()
    # Print final stats?
    # avg_update = sum(update_times) / len(update_times) if update_times else 0
    # print(f"Final Avg update time: {avg_update*1000:.2f} ms")
    sys.exit()

if __name__ == '__main__':
    main()
