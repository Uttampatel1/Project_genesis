# main.py
import pygame
import sys
import random
import time # For performance tracking

import config as cfg
from world import World
from agent import Agent
from ui import draw_world, draw_agent, draw_ui
from social import SocialManager # Keep structure for Phase 4+

def main():
    """ Main function to initialize and run the simulation. """
    # --- Pygame Initialization ---
    pygame.init()
    pygame.font.init() # Explicitly initialize font system
    screen = pygame.display.set_mode((cfg.SCREEN_WIDTH, cfg.SCREEN_HEIGHT))
    pygame.display.set_caption("Project Genesis - Simulation (Phase 3)")
    clock = pygame.time.Clock()

    # --- World and Agent Initialization ---
    print("Initializing World...")
    world = World(cfg.GRID_WIDTH, cfg.GRID_HEIGHT)

    # Optional: Load existing world state instead of generating new
    # if world.load_state():
    #     print("Loaded world state from world_save.pkl")
    # else:
    #     print("Starting new simulation world.")

    print("Initializing Agents...")
    agents = []
    for i in range(cfg.INITIAL_AGENT_COUNT):
        placed = False
        # Try many times to find a valid starting spot
        for attempt in range(cfg.GRID_WIDTH * cfg.GRID_HEIGHT * 2):
            start_x = random.randint(0, world.width - 1)
            start_y = random.randint(0, world.height - 1)
            # Check if tile is walkable ground and not blocked by a resource
            if world.walkability_matrix[start_y, start_x] == 1 and \
               world.terrain_map[start_y, start_x] == cfg.TERRAIN_GROUND:
                # Optional: More robust check - ensure resource isn't blocking
                res_at_start = world.get_resource(start_x, start_y)
                if not res_at_start or not res_at_start.blocks_walk:
                    # Create and add agent
                    agent = Agent(start_x, start_y, world)
                    agents.append(agent)
                    if cfg.DEBUG_AGENT_CHOICE:
                        print(f"  Agent {agent.id} created at ({start_x},{start_y})")
                    placed = True
                    break # Stop attempts for this agent
        if not placed:
            print(f"Error: Could not find valid starting position for agent {i+1} after many attempts!")
            # Option: Reduce agent count or raise error

    print(f"Initialized {len(agents)} agents.")
    world.agents_by_id = {a.id: a for a in agents} # Initial population of world dict

    # Initialize Social Manager (for potential future use)
    print("Initializing Social Manager...")
    social_manager = SocialManager(agents)

    # --- Simulation State Variables ---
    selected_agent = None       # Agent currently selected by the user
    running = True              # Main loop flag
    paused = False              # Simulation pause flag
    last_update_time = time.time() # For calculating delta time
    update_times = []           # For performance monitoring (optional)

    # --- Main Simulation Loop ---
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
                # Save world state (Ctrl+S)
                if event.key == pygame.K_s and pygame.key.get_mods() & pygame.KMOD_CTRL:
                    print("Saving world state...")
                    world.save_state()
                    # Note: Agent state saving is not implemented here. Loading world
                    # state will currently require restarting agent initialization.
                    print("World state saved. Agent state NOT saved.")
                # Load world state (Ctrl+L)
                if event.key == pygame.K_l and pygame.key.get_mods() & pygame.KMOD_CTRL:
                     print("Loading world state...")
                     if world.load_state():
                         # --- IMPORTANT: Agent state requires loading/reinitialization ---
                         agents = [] # Clear current agents - Requires agent loading logic!
                         social_manager.update_agent_list(agents) # Update social manager
                         selected_agent = None # Clear selection
                         world.agents_by_id = {} # Clear agent dict in world
                         print("World state loaded. Agents cleared - Requires agent save/load implementation or re-initialization.")
                         # Option: Re-initialize agents here if desired after load
                         # for i in range(cfg.INITIAL_AGENT_COUNT): ... (spawn logic) ...
                     else:
                         print("World load failed.")

            # Agent Selection (Left Click)
            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                 mouse_x, mouse_y = event.pos
                 # Check if click is within the game area (not UI panel)
                 if mouse_x < cfg.GAME_WIDTH:
                     grid_x = mouse_x // cfg.CELL_SIZE
                     grid_y = mouse_y // cfg.CELL_SIZE
                     clicked_agent = None
                     min_dist_sq = float('inf')
                     # Find the agent closest to the click on the specific tile
                     for agent in agents:
                          if agent.health > 0:
                               # Check if agent is on the clicked tile
                               if agent.x == grid_x and agent.y == grid_y:
                                   # Simple selection: first agent found on tile
                                   clicked_agent = agent
                                   break # Select the first one found on the tile
                                   # Optional: find *closest* center if multiple on tile (more complex)
                     if selected_agent != clicked_agent:
                          selected_agent = clicked_agent
                          if cfg.DEBUG_AGENT_CHOICE: print(f"Selected Agent: {selected_agent.id if selected_agent else 'None'}")


        # --- Simulation Update Step (if not paused) ---
        if not paused:
            current_time = time.time()
            # Calculate delta time, clamp to prevent large jumps if lagging
            dt_real_seconds = min(current_time - last_update_time, 1.0 / (cfg.FPS * 0.5)) # Clamp dt
            last_update_time = current_time
            start_update_time = current_time # For perf timing

            # 1. Update World (Time, Resources)
            world.update(dt_real_seconds, agents) # Pass agent list for context if needed

            # 2. Update Agents (Needs, Decisions, Actions)
            agents_to_remove = []
            for agent in agents:
                if agent.health > 0:
                    agent.update(dt_real_seconds, agents, social_manager) # Update individual agent
                if agent.health <= 0:
                     if agent not in agents_to_remove: agents_to_remove.append(agent)

            # 3. Remove Dead Agents
            if agents_to_remove:
                if cfg.DEBUG_AGENT_CHOICE: print(f"Removing {len(agents_to_remove)} dead agents: {[a.id for a in agents_to_remove]}")
                agents = [a for a in agents if a.health > 0] # Filter list
                social_manager.update_agent_list(agents) # Update social manager's view
                world.agents_by_id = {a.id: a for a in agents} # Update world's agent dict
                # Clear selection if the selected agent died
                if selected_agent and selected_agent.health <= 0: selected_agent = None

            # 4. Update Social Manager (Phase 4+)
            # social_manager.update(dt_real_seconds * cfg.SIMULATION_SPEED_FACTOR)

            # Optional: Performance Monitoring
            end_update_time = time.time()
            update_times.append(end_update_time - start_update_time)
            if len(update_times) > 100: update_times.pop(0) # Keep last 100 timings


        # --- Drawing Step ---
        screen.fill(cfg.BLACK) # Clear screen
        draw_world(screen, world) # Draw terrain and resources

        # Draw agents (draw selected last so it's on top)
        for agent in agents:
            if agent != selected_agent and agent.health > 0:
                draw_agent(screen, agent)
        if selected_agent and selected_agent.health > 0:
            draw_agent(screen, selected_agent)

        draw_ui(screen, world, agents, selected_agent, clock) # Draw UI panel
        pygame.display.flip() # Update the full display Surface to the screen
        clock.tick(cfg.FPS) # Maintain frame rate

        # Optional: Periodic performance print
        # sim_tick = int(world.simulation_time)
        # if not paused and len(update_times) > 0 and sim_tick % 60 == 0: # Print approx every minute
        #      avg_update = sum(update_times) / len(update_times)
        #      print(f"[Perf] Avg update time (last 100): {avg_update*1000:.2f} ms | Sim Time: {world.simulation_time:.0f}s")


    # --- Cleanup ---
    print("Exiting Simulation.")
    pygame.quit()
    sys.exit()

if __name__ == '__main__':
    main()