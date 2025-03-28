# main.py
import pygame
import sys
import random
import time # For performance tracking

import config as cfg
from world import World
from agent import Agent
from ui import draw_world, draw_agent, draw_ui
from social import SocialManager # Phase 4+ - Keep for structure

def main():
    pygame.init()
    pygame.font.init()
    screen = pygame.display.set_mode((cfg.SCREEN_WIDTH, cfg.SCREEN_HEIGHT))
    pygame.display.set_caption("Project Genesis - Agent Simulation (Phase 2)")
    clock = pygame.time.Clock()

    # --- Initialization ---
    print("Initializing World...")
    world = World(cfg.GRID_WIDTH, cfg.GRID_HEIGHT)

    # Optional: Load world state
    # if world.load_state():
    #     print("Loaded world state.")
    # else:
    #     print("Starting new simulation world.")

    print("Initializing Agents...")
    agents = []
    for i in range(cfg.INITIAL_AGENT_COUNT):
        placed = False
        for attempt in range(cfg.GRID_WIDTH * cfg.GRID_HEIGHT): # Limit attempts
            start_x = random.randint(0, world.width - 1)
            start_y = random.randint(0, world.height - 1)
            # Ensure starting on walkable ground
            if world.walkability_matrix[start_y, start_x] == 1 and world.terrain_map[start_y, start_x] == cfg.TERRAIN_GROUND:
                agent = Agent(start_x, start_y, world)
                # Give initial knowledge? Phase 2: Maybe know CrudeAxe implicitly?
                # agent.knowledge.add_recipe('CrudeAxe') # Or let them discover via crafting
                agents.append(agent)
                if cfg.DEBUG_AGENT_CHOICE: print(f"  Agent {agent.id} created at ({start_x},{start_y})")
                placed = True
                break
        if not placed:
            print(f"Error: Could not find valid starting position for agent {i+1} after many attempts!")
            # Optionally break or continue with fewer agents

    print("Initializing Social Manager...") # Keep structure for later phases
    social_manager = SocialManager(agents)

    selected_agent = None
    running = True
    paused = False
    last_update_time = time.time()
    update_times = []

    # --- Main Loop ---
    print("Starting Simulation Loop...")
    while running:
        # --- Event Handling ---
        for event in pygame.event.get():
            if event.type == pygame.QUIT: running = False
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE: running = False
                if event.key == pygame.K_SPACE:
                    paused = not paused
                    print("--- Simulation Paused ---" if paused else "--- Simulation Resumed ---")
                if event.key == pygame.K_s and pygame.key.get_mods() & pygame.KMOD_CTRL:
                    print("Saving world state...")
                    world.save_state()
                    # TODO: Save agent states (Phase ?)
                    print("World state saved (Agent state NOT saved).")
                if event.key == pygame.K_l and pygame.key.get_mods() & pygame.KMOD_CTRL:
                     print("Loading world state...")
                     if world.load_state():
                         # TODO: Load agent states matching the world (Phase ?)
                         agents = [] # Clear current agents - Requires agent loading logic
                         social_manager.update_agent_list(agents)
                         selected_agent = None
                         print("World state loaded. Agents cleared - requires agent loading implementation.")
                     else: print("World load failed.")

            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1: # Left click
                 mouse_x, mouse_y = event.pos
                 if mouse_x < cfg.GAME_WIDTH:
                     grid_x = mouse_x // cfg.CELL_SIZE; grid_y = mouse_y // cfg.CELL_SIZE
                     clicked_agent = None
                     # Find agent at click, prioritizing those drawn later (on top)
                     for agent in reversed(agents):
                         if agent.health > 0 and agent.x == grid_x and agent.y == grid_y:
                              clicked_agent = agent; break
                     if selected_agent != clicked_agent:
                          selected_agent = clicked_agent
                          print(f"Selected Agent: {selected_agent.id if selected_agent else 'None'}")
                 # else: Clicked on UI panel


        # --- Simulation Update ---
        if not paused:
            start_update_time = time.time()
            current_time = time.time()
            dt_real_seconds = current_time - last_update_time
            last_update_time = current_time
            max_dt = 1.0 / cfg.FPS
            dt_clamped = min(dt_real_seconds, max_dt * 3) # Clamp dt

            # Update World (time, resources, agent dict)
            world.update(dt_clamped, agents) # Pass agents list

            # Update Agents
            dead_this_tick = []
            for agent in agents:
                if agent.health > 0:
                    # Pass necessary context to agent update
                    agent.update(dt_clamped, agents, social_manager)
                if agent.health <= 0:
                     if agent not in dead_this_tick: dead_this_tick.append(agent)

            # Remove dead agents
            if dead_this_tick:
                print(f"Removing {len(dead_this_tick)} dead agents: {[a.id for a in dead_this_tick]}")
                agents = [a for a in agents if a.health > 0]
                social_manager.update_agent_list(agents) # Update social manager
                world.agents_by_id = {a.id: a for a in agents} # Update world's dict too
                if selected_agent and selected_agent.health <= 0: selected_agent = None

            # Update Social Manager (Phase 4+)
            # social_manager.update(dt_clamped)

            # Performance monitoring
            end_update_time = time.time()
            update_times.append(end_update_time - start_update_time)
            if len(update_times) > 100: update_times.pop(0)


        # --- Drawing ---
        screen.fill(cfg.BLACK)
        draw_world(screen, world)
        for agent in agents: # Draw non-selected first
            if agent != selected_agent: draw_agent(screen, agent)
        if selected_agent: draw_agent(screen, selected_agent) # Draw selected last
        draw_ui(screen, world, agents, selected_agent, clock)
        pygame.display.flip()
        clock.tick(cfg.FPS)

        # Optional: Periodic performance print
        # if not paused and len(update_times) > 0 and world.simulation_time % 10 < dt_clamped * cfg.SIMULATION_SPEED_FACTOR: # Approx every 10 sim seconds
        #      avg_update = sum(update_times) / len(update_times)
        #      print(f"Avg update time (last 100): {avg_update*1000:.2f} ms | Sim Time: {world.simulation_time:.0f}s")


    # --- Cleanup ---
    print("Exiting Simulation.")
    pygame.quit()
    sys.exit()

if __name__ == '__main__':
    main()