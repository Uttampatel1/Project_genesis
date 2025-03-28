import os

def create_file_structure(base_path, structure):
    for key, value in structure.items():
        path = os.path.join(base_path, key)
        if isinstance(value, dict):
            os.makedirs(path, exist_ok=True)
            create_file_structure(path, value)
        else:
            os.makedirs(os.path.dirname(path), exist_ok=True)
            with open(path, 'w') as f:
                f.write(value)

file_structure = {
    "ai_life_sim": {
        "config": {
            "simulation_params.yaml": "# General sim settings\n",
            "agent_templates.yaml": "# Base stats/traits for different agent types\n",
            "item_definitions.json": "{}\n",
            "recipe_definitions.json": "{}\n",
            "skill_tree.yaml": "# Skill dependencies and effects\n",
            "world_generation.yaml": "# Parameters for procedural world gen\n"
        },
        "data": {
            "logs": {
                "simulation.log": "",
                "events.jsonl": "",
                "population_stats.csv": ""
            },
            "saves": {
                "save_slot_1.pkl": ""
            },
            "analysis": {
                "population_trend.png": "",
                "knowledge_spread.csv": ""
            }
        },
        "assets": {
            "images": {
                "agent.png": "",
                "tree.png": ""
            },
            "sounds": {}
        },
        "simulation": {
            "__init__.py": "",
            "core": {
                "__init__.py": "",
                "simulation_loop.py": "",
                "time_manager.py": "",
                "global_state.py": ""
            },
            "world": {
                "__init__.py": "",
                "grid.py": "",
                "resource_node.py": "",
                "environment.py": "",
                "structure.py": ""
            },
            "agents": {
                "__init__.py": "",
                "agent.py": "",
                "needs.py": "",
                "attributes.py": "",
                "inventory.py": "",
                "skills.py": "",
                "memory.py": "",
                "genetics.py": ""
            },
            "ai": {
                "__init__.py": "",
                "decision_maker.py": "",
                "utility_ai.py": "",
                "fsm_ai.py": "",
                "bt_ai.py": "",
                "pathfinding.py": ""
            },
            "actions": {
                "__init__.py": "",
                "base_action.py": "",
                "movement.py": "",
                "resource_gathering.py": "",
                "crafting.py": "",
                "social.py": "",
                "survival.py": ""
            },
            "items": {
                "__init__.py": "",
                "item.py": "",
                "tool.py": "",
                "blueprint.py": "",
                "recipe_manager.py": ""
            },
            "knowledge": {
                "__init__.py": "",
                "knowledge_base.py": "",
                "invention.py": ""
            },
            "social": {
                "__init__.py": "",
                "relationship_manager.py": "",
                "communication.py": "",
                "group_manager.py": ""
            },
            "utils": {
                "__init__.py": "",
                "constants.py": "",
                "helpers.py": "",
                "spatial_grid.py": ""
            }
        },
        "visualization": {
            "__init__.py": "",
            "renderer_interface.py": "",
            "pygame_renderer.py": "",
            "arcade_renderer.py": "",
            "headless_renderer.py": ""
        },
        "tests": {
            "__init__.py": "",
            "simulation": {
                "agents": {
                    "test_agent.py": ""
                },
                "world": {
                    "test_grid.py": ""
                }
            }
        },
        "analysis_scripts": {
            "plot_population.py": "",
            "analyze_economy.py": ""
        },
        "main.py": "",
        "requirements.txt": "",
        "README.md": "# AI Life Simulation Project\n",
        ".gitignore": "__pycache__/\n*.pkl\n*.png\n"
    }
}

base_directory = os.getcwd()
create_file_structure(base_directory, file_structure)

print("File structure created successfully.")
