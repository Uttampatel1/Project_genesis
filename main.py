# main.py
import pygame
import sys
import random
import time # For performance tracking

import config as cfg
from world import World
from agent import Agent
from ui import draw_world, draw_agent, draw_ui # draw_world now needs social_manager
from social import SocialManager # Phase 4

def main():
    """ Main function to initialize and run the simulation. """
    pygame.init()
    pygame.font.init()
    screen = pygame.display.set_mode((cfg.SCREEN_WIDTH, cfg.SCREEN_HEIGHT))
    pygame.display.set_caption("Project Genesis - Simulation (Phase 4)")
    clock = pygame.time.Clock()

    print("Initializing World...")
    world = World(cfg.GRID_WIDTH, cfg.GRID_HEIGHT)
    # Optional: Load world state (Remember agent state is not saved/loaded yet)
    # world.load_state()

    print("Initializing Agents...")
    agents = []
    for i in range(cfg.INITIAL_AGENT_COUNT):
        placed = False
        for attempt in range(cfg.GRID_WIDTH * cfg.GRID_HEIGHT * 2):
            start_x = random.randint(0, world.width - 1)
            start_y = random.randint(0, world.height - 1)
            if world.walkability_matrix[start_y, start_x] == 1 and \
               world.terrain_map[start_y, start_x] == cfg.TERRAIN_GROUND:
                res_at_start = world.get_resource(start_x, start_y)
                if not res_at_start or not getattr(res_at_start, 'blocks_walk', False):
                    agent = Agent(start_x, start_y, world)
                    agents.append(agent)
                    if cfg.DEBUG_AGENT_CHOICE: print(f"  Agent {agent.id} created at ({start_x},{start_y}) Soc:{agent.sociability:.2f}")
                    placed = True; break
        if not placed: print(f"Error: Could not find valid starting position for agent {i+1}!")

    print(f"Initialized {len(agents)} agents.")
    world.agents_by_id = {a.id: a for a in agents}

    print("Initializing Social Manager...")
    social_manager = SocialManager(agents) # Pass initial agent list

    selected_agent = None
    running = True; paused = False
    last_update_time = time.time(); update_times = []

    print("Starting Simulation Loop...")
    while running:
        # --- Event Handling ---
        for event in pygame.event.get():
            if event.type == pygame.QUIT: running = False
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE: running = False
                if event.key == pygame.K_SPACE: paused = not paused; print("Paused" if paused else "Resumed")
                if event.key == pygame.K_s and pygame.key.get_mods() & pygame.KMOD_CTRL:
                     print("Saving world state (Agent state NOT saved)..."); world.save_state()
                if event.key == pygame.K_l and pygame.key.get_mods() & pygame.KMOD_CTRL:
                     print("Loading world state...")
                     if world.load_state():
                          print("World loaded. Clearing agents - Requires re-initialization or agent load logic.")
                          agents = []; social_manager.update_agent_list(agents); selected_agent = None; world.agents_by_id = {}
                          # Optionally re-spawn agents here
                     else: print("World load failed.")

            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                 mouse_x, mouse_y = event.pos
                 if mouse_x < cfg.GAME_WIDTH:
                     grid_x = mouse_x // cfg.CELL_SIZE; grid_y = mouse_y // cfg.CELL_SIZE
                     clicked_on_tile = [a for a in agents if a.health > 0 and a.x == grid_x and a.y == grid_y]
                     if clicked_on_tile:
                         # Cycle selection if clicking same tile multiple times
                         current_idx = -1
                         if selected_agent and selected_agent in clicked_on_tile:
                              try: current_idx = clicked_on_tile.index(selected_agent)
                              except ValueError: current_idx = -1 # Should not happen
                         next_idx = (current_idx + 1) % len(clicked_on_tile)
                         new_selection = clicked_on_tile[next_idx]
                     else: new_selection = None # Clicked empty space

                     if selected_agent != new_selection:
                         selected_agent = new_selection
                         if cfg.DEBUG_AGENT_CHOICE: print(f"Selected Agent: {selected_agent.id if selected_agent else 'None'}")

        # --- Simulation Update Step (if not paused) ---
        if not paused:
            current_time = time.time()
            dt_real_seconds = min(current_time - last_update_time, 1.0 / (cfg.FPS * 0.5))
            last_update_time = current_time
            start_update_time = current_time
            dt_sim_seconds = dt_real_seconds * cfg.SIMULATION_SPEED_FACTOR

            # 1. Update World (Time, Resources)
            world.update(dt_real_seconds, agents) # agents potentially used for context

            # 2. Update Social Manager (Signal cleanup, Relationship decay)
            social_manager.update(dt_sim_seconds) # Pass sim time for decay rate

            # 3. Update Agents (Needs, Decisions, Actions, Passive Learning)
            agents_to_remove = []
            current_agents_list = list(agents) # Use a stable list for this tick's updates
            for agent in current_agents_list:
                if agent.health > 0:
                    # Pass the current, stable list of agents for decision context
                    agent.update(dt_real_seconds, current_agents_list, social_manager)
                if agent.health <= 0 and agent not in agents_to_remove:
                     agents_to_remove.append(agent)

            # 4. Remove Dead Agents
            if agents_to_remove:
                if cfg.DEBUG_AGENT_CHOICE: print(f"Removing {len(agents_to_remove)} dead agents: {[a.id for a in agents_to_remove]}")
                agents = [a for a in agents if a.health > 0] # Update main list
                social_manager.update_agent_list(agents) # Update social manager's view
                world.agents_by_id = {a.id: a for a in agents} # Update world's agent dict
                if selected_agent in agents_to_remove: selected_agent = None

            # Optional: Performance Monitoring
            end_update_time = time.time()
            update_times.append(end_update_time - start_update_time)
            if len(update_times) > 100: update_times.pop(0)


        # --- Drawing Step ---
        screen.fill(cfg.BLACK)
        draw_world(screen, world, social_manager) # Pass social_manager to draw signals

        # Draw agents
        # for agent in agents: # Draw from the potentially updated list
        #     if agent != selected_agent and agent.health > 0: draw_agent(screen, agent)
        for agent in agents: # Draw from the potentially updated list
            if agent.health > 0:
                is_sel = (agent == selected_agent) # Check if this agent is the selected one
                draw_agent(screen, agent, is_selected=is_sel) 
        # if selected_agent and selected_agent.health > 0: draw_agent(screen, selected_agent) # Draw selected last

        draw_ui(screen, world, agents, selected_agent, social_manager, clock) # Pass social_manager for UI info? (Not used yet)
        pygame.display.flip()
        clock.tick(cfg.FPS)

        # Optional: Periodic performance print
        # if not paused and len(update_times) > 0 and int(world.simulation_time) % 60 == 0:
        #      avg_update = sum(update_times) / len(update_times)
        #      print(f"[Perf] Avg update time: {avg_update*1000:.2f} ms | Sim Time: {world.simulation_time:.0f}s")


    # --- Cleanup ---
    print("Exiting Simulation.")
    pygame.quit()
    sys.exit()

if __name__ == '__main__':
    main()