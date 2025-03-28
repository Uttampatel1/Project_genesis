

**Proposed File Structure**

```
ai_life_sim/
├── config/                 # Configuration files (non-code)
│   ├── simulation_params.yaml  # General sim settings (speed, grid size, day length)
│   ├── agent_templates.yaml  # Base stats/traits for different agent types
│   ├── item_definitions.json   # Definitions of all possible items
│   ├── recipe_definitions.json # Crafting recipes
│   ├── skill_tree.yaml         # Skill dependencies and effects
│   └── world_generation.yaml   # Parameters for procedural world gen
│
├── data/                   # Data generated during runtime
│   ├── logs/                 # Simulation logs
│   │   ├── simulation.log    # General events, errors, performance
│   │   ├── events.jsonl      # Specific structured events (birth, death, invention, trade)
│   │   └── population_stats.csv # Periodic stats (population, avg skills, etc.)
│   ├── saves/                # Saved simulation states
│   │   └── save_slot_1.pkl   # Example save file (or .json, .db)
│   └── analysis/             # Output from data analysis scripts
│       ├── population_trend.png
│       └── knowledge_spread.csv
│
├── assets/                 # Optional: For graphics/sound resources
│   ├── images/
│   │   ├── agent.png
│   │   ├── tree.png
│   │   └── ...
│   └── sounds/
│       └── ...
│
├── simulation/             # Core simulation source code package
│   ├── __init__.py
│   │
│   ├── core/                 # Main loop, time, global state management
│   │   ├── __init__.py
│   │   ├── simulation_loop.py # The main engine tick loop
│   │   ├── time_manager.py    # Handles day/night cycles, seasons
│   │   └── global_state.py    # Potentially holds shared state accessible safely
│   │
│   ├── world/                # World representation
│   │   ├── __init__.py
│   │   ├── grid.py           # The main grid (terrain, hazards)
│   │   ├── resource_node.py  # Tree, Rock, etc. classes
│   │   ├── environment.py    # Manages resources, weather, hazards on the grid
│   │   └── structure.py      # Walls, Chests, Workbenches placed in world
│   │
│   ├── agents/               # Agent-related code
│   │   ├── __init__.py
│   │   ├── agent.py          # Base Agent class
│   │   ├── needs.py          # Hunger, Thirst, Energy logic
│   │   ├── attributes.py     # Health, Stamina, inherent traits
│   │   ├── inventory.py      # Inventory management
│   │   ├── skills.py         # Skill system, XP, levels, rustiness
│   │   ├── memory.py         # Agent memory representation and decay
│   │   └── genetics.py       # Handling genetic inheritance
│   │
│   ├── ai/                   # Artificial intelligence logic
│   │   ├── __init__.py
│   │   ├── decision_maker.py # Interface or base class for AI (Utility, FSM, BT)
│   │   ├── utility_ai.py     # Implementation of utility-based AI
│   │   ├── fsm_ai.py         # Implementation of Finite State Machine AI
│   │   ├── bt_ai.py          # Implementation using Behavior Trees (e.g., with py_trees)
│   │   └── pathfinding.py    # A* or other pathfinding algorithms
│   │
│   ├── actions/              # Definitions of agent actions
│   │   ├── __init__.py
│   │   ├── base_action.py    # Optional: Base class for actions
│   │   ├── movement.py       # Move action logic
│   │   ├── resource_gathering.py # Gather, Chop, Mine actions
│   │   ├── crafting.py       # Craft action, invention attempts
│   │   ├── social.py         # Communicate, Teach, Trade, Help actions
│   │   └── survival.py       # Eat, Drink, Rest actions
│   │
│   ├── items/                # Item and recipe logic
│   │   ├── __init__.py
│   │   ├── item.py           # Item class (data holder, maybe simple methods)
│   │   ├── tool.py           # Tool class (inherits Item, adds durability)
│   │   ├── blueprint.py      # Blueprint item class
│   │   └── recipe_manager.py # Loads and manages recipes from config
│   │
│   ├── knowledge/            # Knowledge representation and invention
│   │   ├── __init__.py
│   │   ├── knowledge_base.py # Agent's known recipes, locations etc.
│   │   └── invention.py      # Logic for discovering new recipes
│   │
│   ├── social/               # Social systems
│   │   ├── __init__.py
│   │   ├── relationship_manager.py # Tracks agent relationships/reputation
│   │   ├── communication.py  # Signal processing, message passing
│   │   └── group_manager.py  # Manages tribes/groups
│   │
│   └── utils/                # Utility functions and constants
│       ├── __init__.py
│       ├── constants.py      # Shared constants (e.g., MAX_HEALTH)
│       ├── helpers.py        # Misc helper functions (e.g., distance calc)
│       └── spatial_grid.py   # Optional: For optimizing proximity queries
│
├── visualization/          # Visualization code (separate concern)
│   ├── __init__.py
│   ├── renderer_interface.py # Defines how the simulation state is drawn
│   ├── pygame_renderer.py  # Example using Pygame
│   ├── arcade_renderer.py  # Example using Arcade
│   └── headless_renderer.py # A 'null' renderer for headless mode
│
├── tests/                  # Unit and integration tests
│   ├── __init__.py
│   ├── simulation/
│   │   ├── agents/
│   │   │   └── test_agent.py
│   │   └── world/
│   │       └── test_grid.py
│   └── ...                 # Mirror structure of 'simulation' package
│
├── analysis_scripts/       # Scripts for offline data analysis
│   ├── plot_population.py
│   ├── analyze_economy.py
│   └── ...
│
├── main.py                 # Main entry point to start the simulation
├── requirements.txt        # Python package dependencies
├── README.md               # Project description
└── .gitignore              # Files/directories to ignore for Git
```

**Explanation and Data Management Strategy:**

1.  **`config/` Directory:**
    *   **Purpose:** Stores all static, configurable data that defines the simulation's rules and starting conditions. Separates configuration from code.
    *   **Data Format:** YAML (`.yaml`) or JSON (`.json`) are excellent choices. They are human-readable, easy to edit, and standard Python libraries (`PyYAML`, `json`) make them trivial to parse into dictionaries or lists.
    *   **Management:** Load these files once at the start of the simulation. The data can be stored in dedicated manager classes (e.g., `RecipeManager`) or passed around as configuration objects/dictionaries.

2.  **`data/` Directory:**
    *   **Purpose:** Stores dynamic data generated *by* the simulation during runtime. This should generally be ignored by version control (add `data/` to `.gitignore`, except maybe sample files).
    *   **`logs/`:**
        *   **Purpose:** Debugging, monitoring, and offline analysis.
        *   **Format:**
            *   `.log`: Plain text for general messages, using Python's `logging` module. Good for human inspection and basic debugging.
            *   `.jsonl` (JSON Lines): Each line is a valid JSON object. Excellent for structured event data (births, deaths, trades, inventions). Easy to parse line-by-line for analysis scripts (e.g., with Pandas `read_json(lines=True)`).
            *   `.csv`: Good for tabular, time-series data (e.g., snapshotting population size, average skill levels every N ticks). Easily loaded into Pandas or spreadsheets.
        *   **Management:** Use Python's built-in `logging` module. Configure different handlers (e.g., `FileHandler`, `StreamHandler`) and formatters. Rotate log files to prevent them from becoming excessively large.
    *   **`saves/`:**
        *   **Purpose:** Persisting the simulation state to allow resuming later.
        *   **Format:**
            *   `pickle` (`.pkl`): Easiest way to save/load arbitrary Python objects (the entire simulation state). **Pros:** Simple implementation. **Cons:** Python-version specific, potential security risks with untrusted pickles, can break if class definitions change. Best for personal use or rapid development.
            *   JSON/YAML + Custom Serialization: Define `to_dict()` methods on your core classes (Agent, World, Item, etc.) to convert the state to basic Python types, then serialize using `json` or `yaml`. Requires `from_dict()` class methods or functions for loading. **Pros:** More robust to code changes, language-agnostic format, safer. **Cons:** More upfront implementation work.
            *   SQLite (`.db`): Use the built-in `sqlite3` module. Can store agent data, world state etc. in tables. Complex objects might need to be serialized (e.g., to JSON strings) within database fields. **Pros:** Transactional, allows querying specific parts of the state (though potentially slow for complex queries on serialized data). **Cons:** Can be overkill/slower than pickle for simply saving/loading the *entire* state; requires mapping your object model to relational tables.
        *   **Management:** Implement `save_simulation(filepath)` and `load_simulation(filepath)` functions in your `simulation_loop.py` or a dedicated `persistence.py` module. Ensure you capture *all* necessary state (world grid, all agent data, resource states, current time, RNG state if needed for reproducibility).
    *   **`analysis/`:** Stores the *outputs* of analysis scripts (plots, reports).

3.  **`simulation/` Package:**
    *   This is the heart of your project, organized into sub-packages based on functionality (World, Agents, AI, Actions, etc.).
    *   Using `__init__.py` makes these directories Python packages, allowing imports like `from simulation.agents.agent import Agent`.
    *   This modularity helps manage complexity, allows different people to work on different parts, and makes testing easier.

4.  **`visualization/` Package:**
    *   Keeps the graphics rendering logic separate from the simulation logic.
    *   An `RendererInterface` could define methods like `setup()`, `render(world, agents)`, `update()`. Different implementations (Pygame, Headless) implement this interface.
    *   The `main.py` script would choose which renderer to instantiate and pass it the simulation state each tick.

5.  **`tests/` Directory:**
    *   Crucial for complex projects. Use `pytest` or `unittest`.
    *   Mirror the `simulation` structure to make tests easy to find. Test individual components (unit tests) and interactions (integration tests).

6.  **`analysis_scripts/` Directory:**
    *   Scripts that are *not* part of the simulation itself but operate on the logged data (`data/logs/`).
    *   Use libraries like Pandas, Matplotlib, Seaborn, NetworkX here.

7.  **Root Directory Files:**
    *   `main.py`: Orchestrates everything. Parses command-line arguments (e.g., `--load-save`, `--headless`, `--config-file`), initializes the world, agents, renderer, and starts the main simulation loop.
    *   `requirements.txt`: Lists Python dependencies (`pip freeze > requirements.txt`). Essential for reproducibility. Use virtual environments (`python -m venv venv`).
    *   `README.md`: Explains what the project is, how to set it up, and how to run it.
    *   `.gitignore`: Prevents generated files, virtual environments, IDE configs, etc., from being committed to Git.

**Key Data Management Considerations in Code:**

*   **State Management:** Where does the "truth" live? Typically, the `SimulationLoop` orchestrates updates, calling methods on the `World` and `Agent` objects. Agents need access to world information (nearby resources, terrain) and potentially other agents. Pass necessary context into agent update methods or use spatial indexing structures queried by agents.
*   **Immutability vs. Mutability:** Be careful when passing data. If an agent gets a list of nearby items, should it be able to modify that list directly? Sometimes passing copies (`list.copy()`, `dict.copy()`) is safer.
*   **Data Structures:** Use appropriate Python data structures. `dict` for lookups (agents by ID), `set` for fast membership checking (known recipes), `list` or `collections.deque` for sequences (inventory, memory queues), `numpy.ndarray` for grid data.
*   **Loading:** Load configurations early. Load save games carefully, ensuring all object references are correctly re-established.

