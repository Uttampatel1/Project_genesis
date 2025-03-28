
**Project Title:** Project Genesis 

**Core Vision:** A persistent, real-time simulation sandbox where autonomous agents evolve complex behaviors, skills, and social structures through interaction with the environment and each other.

**Key Pillars:**

1.  **Autonomous Agents:** Agents driven by internal needs and AI, not direct player control (though player might influence the environment or observe).
2.  **Emergent Behavior:** Complexity arises from simple rules and interactions, not pre-scripted scenarios.
3.  **Continuous Learning:** Agents constantly adapt and improve based on experience.
4.  **Creation & Invention:** Agents can combine knowledge and resources to create novel tools, structures, or even concepts.
5.  **Social Dynamics:** Agents interact, communicate (rudimentarily at first), cooperate, compete, and share knowledge.
6.  **Real-Time & Persistent:** The simulation runs continuously, and agent states/world changes persist over time.

**Phase 1: Foundation - The Core Simulation Loop**

*   **Goal:** Establish the basic simulation environment and agent existence.
*   **Components:**
    *   **Game Engine:** Choose (e.g., Unity, Unreal, Godot, or a custom engine if necessary). Focus on suitability for simulation and AI integration.
    *   **World Representation:**
        *   Define the space (e.g., 2D grid, 3D continuous). Start simple (e.g., grid).
        *   Basic terrain types (ground, water, obstacles).
        *   Time System: Day/night cycle.
    *   **Basic Agent Entity:**
        *   Representation (simple sprite/model).
        *   Core Attributes: Health, Energy/Stamina, Hunger, Thirst.
        *   Basic Needs System: Attributes decay over time, creating needs.
        *   Simple Movement: Pathfinding (e.g., A* on the grid).
    *   **Basic AI - Decision Making:**
        *   **Needs-Based Utility AI:** Agents evaluate possible actions (e.g., wander, rest, drink, eat) based on how well they satisfy current needs. The action with the highest "utility" (need satisfaction) is chosen.
        *   **Finite State Machine (FSM) or Behavior Tree (BT):** To structure simple behaviors like `SeekingWater`, `Resting`, `Exploring`.
    *   **Environment Interaction:**
        *   Basic Resources: Water sources, Food sources (e.g., berry bushes).
        *   Actions: `MoveTo`, `Drink`, `Eat`, `Rest`.
    *   **Simulation Core:**
        *   Time progression.
        *   Update agent states (needs decay).
        *   Execute agent actions.
        *   Update environment (e.g., resource depletion if applicable).
    *   **Visualization:** Basic rendering of the world, agents, and resources. Simple UI to show simulation time and maybe select an agent to view stats.

*   **Outcome:** Agents exist, move around, and fulfill basic survival needs autonomously in real-time.

**Phase 2: Interaction & Basic Learning**

*   **Goal:** Introduce more complex interactions, resource gathering, basic crafting, and skill learning through practice.
*   **Components:**
    *   **Expanded Environment:**
        *   More resource types: Wood, Stone.
        *   Resource objects: Trees, Rocks.
    *   **Agent Enhancements:**
        *   Inventory system.
        *   Skills: Define basic skills (e.g., `GatherWood`, `GatherStone`, `BasicCrafting`). Represent skills with levels/proficiency.
        *   Memory: Simple short-term memory (e.g., location of recently visited resources).
    *   **New Actions:** `Gather(Resource)`, `Drop(Item)`, `Craft(Recipe)`.
    *   **Simple Crafting System:**
        *   Define simple recipes (e.g., `Wood + Stone -> CrudeAxe`).
        *   Agents need required items in inventory and the `BasicCrafting` skill.
    *   **Learning by Doing:**
        *   Skill proficiency increases slightly each time an action using that skill is successfully performed.
        *   Higher proficiency might increase success rate, speed, or yield.
    *   **Improved AI:**
        *   Decision-making now includes resource gathering and crafting when needs are met (e.g., using Behavior Trees with conditions like "HasAxe?" or "InventoryFull?").
        *   Agents need to "learn" resource locations (add known locations to memory upon discovery).

*   **Outcome:** Agents gather resources, craft basic items (like tools to improve gathering), and get better at skills through repetition.

**Phase 3: Invention & Knowledge Representation**

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

**Phase 4: Social Interaction, Skill Sharing & Cooperation**

*   **Goal:** Implement meaningful agent-to-agent interaction, including communication, teaching, and helping.
*   **Components:**
    *   **Basic Communication:**
        *   Agents can emit simple signals (e.g., `HelpNeeded`, `FoundFood`, `Danger`).
        *   Other agents within range perceive these signals.
        *   AI needs to interpret signals and decide whether/how to react (e.g., move towards `FoundFood`, flee from `Danger`).
    *   **Social Attributes:** Add attributes like `Sociability`, `Trustworthiness` (perhaps based on past interactions).
    *   **Relationship Model:** Agents track their relationship status with other agents they've encountered (e.g., Neutral, Friendly, Hostile) based on interactions.
    *   **Skill Sharing/Teaching:**
        *   An agent with high proficiency in a skill (`Teacher`) can perform a `Teach` action targeting another agent (`Student`).
        *   Requires proximity and willingness (e.g., friendly relationship, student AI decides to learn).
        *   The student gains a boost in skill learning/unlocks the basic skill. This could take simulation time.
        *   Alternative: Students learn by *observing* skilled agents performing actions successfully (requires perception checks and AI logic).
    *   **Cooperative Behavior:**
        *   **Helping:** Agent A perceives Agent B is in critical need (e.g., very low health/hunger) and Agent A has the means to help (e.g., food item, `Heal` skill if implemented). Agent A's AI decides whether to help based on relationship, own needs, personality.
        *   **Collaborative Tasks:** Define tasks requiring multiple agents (e.g., building a large structure, hunting large prey). Agents need to signal intent, coordinate actions. This requires more advanced AI (e.g., shared plans, role assignment).
    *   **Trading/Gifting:** Simple item exchange between agents.

*   **Outcome:** Agents form rudimentary social structures. They can warn each other, teach skills, help those in need, and potentially work together, leading to more complex emergent societies.

**Phase 5: Refinement, Scaling & Long-Term Evolution**

*   **Goal:** Improve realism, performance, add more complex systems, and ensure long-term interesting simulation.
*   **Components:**
    *   **Advanced Learning:** Consider Reinforcement Learning (RL) for certain behaviors, allowing agents to learn truly novel strategies based on rewards (e.g., survival, resource acquisition, social success). This is computationally intensive.
    *   **More Complex Needs:** Social needs, entertainment, creativity.
    *   **Environmental Dynamics:** Weather, seasons, resource regrowth/depletion cycles, ecological simulation (predator/prey).
    *   **Agent Lifecycle:** Aging, reproduction (passing on traits/skills?), death.
    *   **Cultural Evolution:** Transmission of knowledge (recipes, social norms) across generations or groups. Maybe emergence of simple language/symbols.
    *   **Performance Optimization:** Crucial for real-time simulation with many agents. Profiling, spatial partitioning, efficient AI updates.
    *   **User Interface:** More sophisticated observation tools, data visualization (agent stats, social networks, knowledge spread).
    *   **Persistence:** Saving/loading simulation state.

*   **Outcome:** A rich, evolving ecosystem of agents with complex individual and group behaviors that feels more "alive."

**Technology Stack Considerations:**

*   **AI:** Behavior Trees, Utility AI systems, potentially Finite State Machines for simpler behaviors. Consider ML libraries (like ML-Agents for Unity, TensorFlow/PyTorch if integrating RL) for advanced learning.
*   **Programming Language:** C# (Unity), C++ (Unreal), GDScript/C# (Godot). Python is often used for AI prototyping but might need integration.
*   **Data Management:** Efficient storage for agent states, knowledge, world data.

**Key Challenges:**

*   **AI Complexity:** Designing decision-making that is robust, allows for learning, and leads to believable emergent behavior is hard.
*   **Invention Mechanism:** Creating a system for true "novelty" beyond predefined combinations is a major AI research challenge. Start with combinatorial discovery.
*   **Performance:** Real-time simulation with many complex agents is computationally expensive.
*   **Balancing:** Ensuring needs, resources, learning rates, and social interactions are balanced for interesting long-term dynamics.
*   **Debugging Emergent Behavior:** Unexpected (and often undesirable) behaviors will arise. Debugging these can be difficult.

