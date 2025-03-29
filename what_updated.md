*   **Goal:** Enable agents to "invent" new recipes/things and manage knowledge more robustly.
*   **Components:**
    *   **Knowledge System:**
        *   Represent agent knowledge explicitly: Known resource locations, known crafting recipes, learned facts.
        *   Could be a simple list/dictionary or a more complex knowledge graph.
    *   **Invention Mechanism:** This is challenging! Potential approaches:
        *   **Combinatorial Exploration:** Agents with high "Curiosity" or "Intelligence" attributes might periodically try combining items in their inventory at a "Workbench" object (new environmental object). If a valid (predefined but initially unknown to the agent) combination is found, the recipe is "discovered" and added to their knowledge.
        *   **Goal-Driven Experimentation:** If an agent has a goal (e.g., "GatherWoodFaster") but lacks the means (e.g., a good axe), it might try crafting variations or combinations of known items/materials related to "Tool" or "Wood".
        *   **Inspiration Events:** Random chance (perhaps increased by intelligence/environment state) grants an agent a new recipe idea.
    *   **Refined Crafting:** Crafting requires specific tools or locations (Workbench). Recipe complexity increases.
    *   **Skill Tree/Dependencies:** Some skills might require prerequisite skills (e.g., `AdvancedCrafting` requires `BasicCrafting` level X). New actions/recipes unlocked by specific skills.

*   **Outcome:** Agents are no longer limited to predefined recipes known from the start. They can discover new ways to combine resources, leading to potentially novel item creation within the simulation's defined possibilities.