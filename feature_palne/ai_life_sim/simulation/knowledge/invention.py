# Assume MASTER_RECIPE_LIST is loaded globally or passed in
MASTER_RECIPE_LIST = {} # Populated from config/recipe_definitions.json

def perform_invention_attempt(agent: 'Agent', input_items: list[str], workbench: Optional['Structure']) -> Optional[str]:
    """Attempts to invent a new recipe by combining items.

    Checks the combination against known recipes. If a valid, unknown recipe
    is found, it's added to the agent's knowledge. Resources are consumed regardless.

    Args:
        agent (Agent): The agent attempting invention.
        input_items (list[str]): A list of item IDs being combined.
        workbench (Optional['Structure']): The workbench being used, if any.

    Returns:
        Optional[str]: The recipe_id of the discovered recipe if successful, None otherwise.
    """
    # 1. Consume input_items from agent.inventory (handle failure if not enough).
    #    Even failed attempts consume resources (configurable?).

    # 2. Normalize/sort input_items to make combination order-independent?
    combination_key = tuple(sorted(input_items)) # Example key

    # 3. Check MASTER_RECIPE_LIST for a match based on combination_key and workbench type.
    found_recipe_id = None
    for recipe_id, recipe_data in MASTER_RECIPE_LIST.items():
         # Matching logic depends on how recipes store inputs and workbench requirements
         # Example: if tuple(sorted(recipe_data['inputs'].keys())) == combination_key and \
         #           recipe_data.get('workbench_req') == (workbench.structure_type if workbench else None):
         #     found_recipe_id = recipe_id
         #     break
         pass # Implement actual matching logic

    # 4. If a recipe is found AND it's not already known by the agent:
    #    (Requires agent to have a KnowledgeBase or similar)
    #    if found_recipe_id and agent.knowledge.is_recipe_known(found_recipe_id) == False:
    #        agent.knowledge.add_known_recipe(found_recipe_id)
    #        # Grant discovery XP?
    #        agent.skills.add_xp('invention', 50) # Example XP
    #        return found_recipe_id

    # 5. If no new recipe found or already known, return None.
    return None