
---
**Explanation of Changes:**

1.  **Config (`config.py`):**
    *   Added `MAX_AGE_SECONDS`, `MAX_SOCIAL_NEED`, related rates/costs/weights.
    *   Defined `SEASONS`, `SEASON_LENGTH_SECONDS`, and `SEASON_MODIFIERS` dictionary.
    *   Added `SAVE_FILENAME`.
    *   Added debug flags `DEBUG_PERSISTENCE`, `DEBUG_LIFECYCLE`.
    *   Added colors for season overlays and relationship lines.

2.  **Knowledge (`knowledge.py`):**
    *   Added `__getstate__` and `__setstate__` to handle saving/loading of known locations, recipes, and relationships. Uses lists instead of sets in the saved state for compatibility.

3.  **Agent (`agent.py`):**
    *   **ID Management:** Added functions `get_next_agent_id` and `set_agent_id_counter` to manage the global ID counter, allowing it to be reset on load. `__init__` now accepts an optional `agent_id`.
    *   **Initialization:** Added `age` and `social_need` attributes.
    *   **`_update_needs`:** Increments `age`, checks against `MAX_AGE_SECONDS` for death. Increments/decrements `social_need` based on proximity and interaction. Fetches `SEASON_MODIFIERS` from `world` and applies them to hunger/thirst/energy decay rates. Includes optional small health drain for extreme social need. `_handle_death` now takes a reason string.
    *   **`_choose_action`:** Added utility calculation for the new `Socialize` action, factoring in `social_need`, `sociability`, and basic need levels.
    *   **`_check_action_feasibility`:** Added feasibility check for `Socialize`, requiring a nearby agent and calculating a standing position.
    *   **`_perform_action`:** Added execution logic for `Socialize`. It involves a timer, finding the target agent, checking distance, reducing social need for both agents upon completion, and adding a small relationship boost.
    *   **Persistence (`__getstate__`, `__setstate__`)**:
        *   `__getstate__`: Creates a dictionary containing all essential agent data (needs, inventory, skills, attributes, age, social need). Critically, it calls `knowledge.__getstate__()` to embed the knowledge state and *omits* the `world` reference. Action state is simplified (not saved) as resuming actions perfectly is complex.
        *   `__setstate__`: Restores state from the dictionary. Recreates the `KnowledgeSystem` and restores its state. Resets action state. **Crucially, the `world` attribute is left as `None` and *must* be re-linked externally by the loading code in `main.py`**.

4.  **World (`world.py`):**
    *   **Initialization:** Added `current_season_index`, `current_season`, `season_timer`. Added internal `_agent_id_counter` to store the value to be saved/loaded.
    *   **`update`:** Added logic to advance the `season_timer` and cycle through `cfg.SEASONS` based on `cfg.SEASON_LENGTH_SECONDS`.
    *   **Persistence (`get_state`, `set_state`)**:
        *   `get_state`: Returns a dictionary including season state and the current value of the agent ID counter fetched from the `agent` module.
        *   `set_state`: Restores state from the dictionary. Rebuilds the resource map/list robustly. Recalculates walkability. Stores the loaded agent ID counter. **Crucially, it leaves `agents_by_id` empty, as agents are loaded and linked in `main.py`**.

5.  **UI (`ui.py`):**
    *   **`draw_world`:** Adds a semi-transparent color overlay based on the `world.current_season`. Draws relationship lines (simple colored `aaline`) between the `selected_agent` and other agents they have a relationship with, fading by distance and colored by score.
    *   **`draw_ui`:** Displays the current world season. Displays the selected agent's age (in days) and social need (as an inverted bar similar to hunger/thirst).

6.  **Main (`main.py`):**
    *   **Save/Load Logic:**
        *   Introduced `save_simulation_state` and `load_simulation_state` functions.
        *   `save_simulation_state`: Gets state dictionaries from `world` and all `agents`, bundles them into a single dictionary (`{'world': ..., 'agents': ...}`), and pickles it.
        *   `load_simulation_state`: Unpickles the state. Creates a new `World` and sets its state. **Iterates through loaded agent states, creates new `Agent` instances, sets their state using `__setstate__`, and crucially re-links the loaded `world` object to each agent.** Restores the global agent ID counter via `set_agent_id_counter`. Returns the loaded world and agent list.
    *   **Initialization:** Attempts `load_simulation_state` first. If it fails or returns `None`, it proceeds with generating a new world and agents as before. Ensures the agent ID counter is correct after spawning new agents.
    *   **Event Loop:** Added Ctrl+S to trigger saving. Ctrl+L now simply exits the simulation loop (requiring a manual script restart to load - a simpler approach than full in-place reload).
    *   **Agent Management:** Uses `world.agents_by_id` as the primary source for the list of agents to update and draw, ensuring consistency after loading and death handling. Updates `world.agents_by_id` when agents die.
    *   **Drawing:** Passes `selected_agent` to `draw_world` for relationship line drawing.

**Performance Considerations:**

*   **Finding Nearby Agents (`_find_nearby_agents`):** Currently iterates through all agents. For many agents, this becomes slow. Spatial partitioning (e.g., a grid or Quadtree) would significantly speed up finding neighbors for interactions (Socialize, Help, Teach, Passive Learning, Signal Perception).
*   **Pathfinding:** A* is generally efficient, but frequent replanning (due to blocked paths) can be costly. Path caching or more sophisticated collision avoidance could help.
*   **Drawing:** Drawing many relationship lines or complex overlays could impact FPS. Optimizing drawing calls (e.g., drawing static elements to a background surface once) can help.
*   **Object Iteration:** Iterating `world.resources` for updates is fine for now, but could be optimized if resources become extremely numerous.

This Phase 5 implementation adds significant features related to agent lifecycle, needs, environment, and persistence, making the simulation more dynamic and robust. Remember to test the save/load functionality thoroughly!