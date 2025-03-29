# main.py
import pygame
import sys
import random
import time # For performance tracking
from collections import deque # For UI event log

# --- Configuration and Core Modules ---
import config as cfg
from world import World
from agent import Agent
# Import the ADVANCED UI functions
from ui import draw_world, draw_agent, draw_ui
from social import SocialManager

def main():
    """ Main function to initialize and run the simulation with advanced UI. """
    pygame.init()
    pygame.font.init()
    screen = pygame.display.set_mode((cfg.SCREEN_WIDTH, cfg.SCREEN_HEIGHT))
    pygame.display.set_caption("Project Genesis - Simulation (Phase 4 - Advanced UI)")
    clock = pygame.time.Clock()

    print("Initializing World...")
    world = World(cfg.GRID_WIDTH, cfg.GRID_HEIGHT)
    # Optional: Load world state (Remember agent state is not saved/loaded yet)
    # world.load_state()

    print("Initializing Agents...")
    agents = []
    for i in range(cfg.INITIAL_AGENT_COUNT):
        placed = False
        # Increased attempts in case of dense maps or bad luck
        for attempt in range(cfg.GRID_WIDTH * cfg.GRID_HEIGHT * 5):
            start_x = random.randint(0, world.width - 1)
            start_y = random.randint(0, world.height - 1)
            # Check walkability and ensure not spawning inside a blocking resource
            if world.walkability_matrix[start_y, start_x] == 1 and \
               world.terrain_map[start_y, start_x] == cfg.TERRAIN_GROUND:
                # Double check resource map directly, walkability might not be updated if world gen had issues
                res_at_start = world.get_resource(start_x, start_y)
                if not res_at_start or not getattr(res_at_start, 'blocks_walk', False):
                    agent = Agent(start_x, start_y, world)
                    agents.append(agent)
                    if cfg.DEBUG_AGENT_CHOICE: print(f"  Agent {agent.id} created at ({start_x},{start_y}) Soc:{agent.sociability:.2f}")
                    placed = True; break
        if not placed: print(f"Error: Could not find valid starting position for agent {i+1}!")

    print(f"Initialized {len(agents)} agents.")
    world.agents_by_id = {a.id: a for a in agents} # Initial population

    print("Initializing Social Manager...")
    social_manager = SocialManager(agents) # Pass initial agent list

    # --- UI State Initialization ---
    # This dictionary holds state relevant to the UI's display and interaction
    ui_state = {
        "active_tab": "Status",               # Default tab for selected agent/object
        "selected_world_object_info": None,   # Stores dict of info if a world tile is selected
        "event_log": deque(maxlen=cfg.EVENT_LOG_MAX_LINES if hasattr(cfg, 'EVENT_LOG_MAX_LINES') else 5), # Event log queue
        "paused": False,                      # Simulation pause state
        "_pause_btn_clicked_last_frame": False,# Internal flag to prevent rapid pause toggling
        # Add other UI specific states here if needed (e.g., scroll offsets)
    }
    # --- End UI State Initialization ---

    selected_agent = None # Agent currently selected for detailed view
    running = True
    last_update_time = time.time(); update_times = [] # For dt calculation and perf monitoring

    print("Starting Simulation Loop...")
    while running:
        # --- Event Handling ---
        # Get mouse state before event loop for reliable button checks in draw_ui
        mouse_pos = pygame.mouse.get_pos()
        mouse_click_this_frame = False # Track if a click happened THIS frame

        for event in pygame.event.get():
            if event.type == pygame.QUIT: running = False
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE: running = False
                # Pause toggle is now handled by the UI button click check within draw_ui
                # if event.key == pygame.K_SPACE:
                #     ui_state["paused"] = not ui_state.get("paused", False)
                #     print("Paused" if ui_state["paused"] else "Resumed")
                if event.key == pygame.K_s and pygame.key.get_mods() & pygame.KMOD_CTRL:
                     print("Saving world state (Agent state NOT saved)..."); world.save_state()
                if event.key == pygame.K_l and pygame.key.get_mods() & pygame.KMOD_CTRL:
                     print("Loading world state...")
                     if world.load_state():
                          print("World loaded. Clearing agents/UI state - Requires re-initialization or agent load logic.")
                          agents = []; social_manager.update_agent_list(agents); selected_agent = None; world.agents_by_id = {}
                          ui_state["selected_world_object_info"] = None; ui_state["event_log"].clear()
                          # TODO: Add agent re-initialization logic here if needed after load
                     else: print("World load failed.")

            # --- Handle Clicks for Selection ---
            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                 mouse_click_this_frame = True # Record the click event
                 click_x, click_y = event.pos

                 if click_x >= cfg.GAME_WIDTH: # Click is on the UI panel
                      # Let draw_ui handle internal button/tab clicks based on mouse_pos
                      pass
                 else: # Click is on the game world
                      grid_x = click_x // cfg.CELL_SIZE
                      grid_y = click_y // cfg.CELL_SIZE

                      if 0 <= grid_x < world.width and 0 <= grid_y < world.height:
                          clicked_agents = [a for a in agents if a.health > 0 and a.x == grid_x and a.y == grid_y]

                          if clicked_agents: # Clicked on one or more agents
                              # --- Agent Selection Logic ---
                              current_idx = -1
                              if selected_agent and selected_agent in clicked_agents:
                                   try: current_idx = clicked_agents.index(selected_agent)
                                   except ValueError: current_idx = -1
                              next_idx = (current_idx + 1) % len(clicked_agents)
                              new_selection = clicked_agents[next_idx]

                              if selected_agent != new_selection:
                                   selected_agent = new_selection
                                   ui_state["selected_world_object_info"] = None # Clear world object selection
                                   if cfg.DEBUG_AGENT_CHOICE: print(f"Selected Agent: {selected_agent.id}")
                          else: # Clicked on empty space or resource/terrain
                              # --- World Object Selection Logic ---
                              selected_agent = None # Deselect agent
                              resource = world.get_resource(grid_x, grid_y)
                              terrain = world.get_terrain(grid_x, grid_y)
                              world_info = {"pos": (grid_x, grid_y)} # Base info

                              if resource and (resource.quantity > 0 or resource.type == cfg.RESOURCE_WORKBENCH) :
                                   world_info["type"] = "Resource"
                                   world_info["name"] = getattr(resource, 'name', 'Unknown')
                                   # Only add quantity if applicable
                                   if hasattr(resource, 'quantity') and hasattr(resource, 'max_quantity'):
                                        world_info["quantity"] = resource.quantity
                                        world_info["max_quantity"] = resource.max_quantity
                                   world_info["resource_type_enum"] = resource.type # For UI lookup
                              elif terrain == cfg.TERRAIN_WATER:
                                   world_info["type"] = "Terrain"; world_info["name"] = "Water"
                              elif terrain == cfg.TERRAIN_GROUND:
                                   world_info["type"] = "Terrain"; world_info["name"] = "Ground"
                              elif terrain == cfg.TERRAIN_OBSTACLE:
                                   world_info["type"] = "Terrain"; world_info["name"] = "Obstacle"
                              else:
                                   world_info = None # Unknown tile clicked

                              ui_state["selected_world_object_info"] = world_info
                              if world_info and cfg.DEBUG_AGENT_CHOICE:
                                   print(f"Selected World Object: {world_info['name']} at {world_info['pos']}")

        # --- Simulation Update Step (conditional on pause state) ---
        is_paused = ui_state.get("paused", False)
        if not is_paused:
            current_time = time.time()
            # Calculate delta time, limiting max dt to avoid large jumps after pause/lag
            dt_real_seconds = min(current_time - last_update_time, 1.0 / (cfg.FPS * 0.5))
            last_update_time = current_time
            start_update_time = current_time # For perf monitoring
            dt_sim_seconds = dt_real_seconds * cfg.SIMULATION_SPEED_FACTOR

            # 1. Update World (Time, Resources)
            world.update(dt_real_seconds, agents) # agents potentially used for context

            # 2. Update Social Manager (Signal cleanup, Relationship decay)
            social_manager.update(dt_sim_seconds) # Pass sim time for decay rate

            # 3. Update Agents (Needs, Decisions, Actions, Passive Learning)
            agents_to_remove = []
            # Use a stable list for this tick's updates, prevents issues if agents list changes mid-update
            current_agents_list = list(agents)
            for agent in current_agents_list:
                if agent.health > 0:
                    # Pass the current, stable list of agents for decision context
                    try:
                        agent.update(dt_real_seconds, current_agents_list, social_manager)
                    except Exception as e:
                         print(f"!!! Agent {agent.id} update CRASHED: {e}")
                         import traceback
                         traceback.print_exc()
                         # Optional: kill the agent or handle error recovery
                         # agent.health = 0
                # Check health *after* update
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
            if len(update_times) > 100: update_times.pop(0) # Keep rolling window

        else: # Simulation is Paused
             # Keep updating time to prevent large dt jump when resuming
             last_update_time = time.time()


        # --- Drawing Step ---
        screen.fill(cfg.BLACK) # Clear screen

        # 1. Draw World (Terrain, Resources, Signals, Day/Night Overlay)
        draw_world(screen, world, social_manager)

        # 2. Draw Agents (with selection highlight, path, target)
        for agent in agents:
            if agent.health > 0:
                is_sel = (agent == selected_agent) # Check if this agent is the selected one
                draw_agent(screen, agent, is_selected=is_sel) # Pass the flag

        # 3. Draw UI Panel (pass the ui_state dictionary)
        # The draw_ui function now internally handles button/tab clicks based on mouse_pos
        draw_ui(screen, world, agents, selected_agent, social_manager, clock, ui_state)

        # 4. Update Display
        pygame.display.flip()

        # 5. Control Framerate
        clock.tick(cfg.FPS)

        # Optional: Periodic performance print
        # if not is_paused and len(update_times) > 0 and int(world.simulation_time) % 120 == 0 and world.simulation_time > 1:
        #      avg_update = sum(update_times) / len(update_times)
        #      print(f"[Perf] Avg update time: {avg_update*1000:.2f} ms | Sim Time: {world.simulation_time:.0f}s ({world.day_count}d {world.day_time:.0f}s)")


    # --- Cleanup ---
    print("Exiting Simulation.")
    pygame.quit()
    sys.exit()

if __name__ == '__main__':
    main()