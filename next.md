

**Next Steps & Considerations:**

*   **Phase 1 Refinement:** Balance needs decay, action effects, resource availability. Improve pathfinding robustness (e.g., what if target is unreachable?).
*   **Phase 2 Implementation:** Flesh out `Gather`, `Craft` actions. Implement skill gain logic more thoroughly. Add `Inventory` UI display. Define more `RECIPES`.
*   **Phase 3 Implementation:** Design the `Workbench` object/interaction. Implement the `Invent` action logic (combinatorial or otherwise). Refine `KnowledgeSystem`.
*   **Phase 4 Implementation:** Build out `SocialManager`. Implement `Teach`, `Help`, `Signal` actions and agent reactions in `agent.py`. Add relationship tracking and display.
*   **Phase 5 Implementation:** Explore agent reproduction/genetics. Add environmental dynamics (weather, seasons). Implement saving/loading agent states alongside world state. Optimize performance (spatial hashing, profiling). Consider ML-Agents if tackling RL.
*   **Debugging:** Emergent systems are notoriously hard to debug. Add extensive logging and visualization tools.
*   **UI/UX:** The current UI is basic. Improve agent selection, add time controls (speed up/slow down), potentially graphs for simulation statistics.
