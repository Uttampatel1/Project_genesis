# Functions within modules like resource_gathering.py, crafting.py, etc.
# These functions are typically called by the Agent._execute_action_step method
# based on the action chosen by the AI.

def gather(agent: 'Agent', target_node: 'ResourceNode', environment: 'Environment', dt: float) -> tuple[bool, float]:
    """Performs the gathering action over a time slice dt.

    Args:
        agent (Agent): The agent performing the action.
        target_node (ResourceNode): The resource being gathered.
        environment (Environment): World context.
        dt (float): Time slice for this execution step.

    Returns:
        tuple[bool, float]: (action_completed, progress_made_this_tick)
                            Progress is normalized (0.0 to 1.0 for the whole action).
    """
    # 1. Check prerequisites (e.g., distance to node, tool equipped?)
    # 2. Determine gather speed (based on skill, tool)
    # 3. Calculate progress this tick: progress = gather_speed * dt / total_gather_time
    # 4. If agent.action_progress + progress >= 1.0:
    #    a. Calculate actual amount gathered (considering node quantity, quality, skill bonus)
    #    b. Check tool durability use
    #    c. Harvest from node: target_node.harvest(amount)
    #    d. Add item to agent inventory: agent.inventory.add_item(...)
    #    e. Grant skill XP: agent.skills.add_xp('gathering', xp_amount)
    #    f. Remove node if depleted: environment.remove_resource(...)
    #    g. Return (True, 1.0 - agent.action_progress) # Completed
    # 5. Else:
    #    a. Return (False, progress) # Not completed
    pass

def craft_item(agent: 'Agent', recipe_id: str, recipe_manager: 'RecipeManager', environment: 'Environment', dt: float) -> tuple[bool, float]:
    """Performs the crafting action over a time slice dt.

    Args:
        agent (Agent): The agent crafting.
        recipe_id (str): The ID of the recipe being crafted.
        recipe_manager (RecipeManager): To get recipe details.
        environment (Environment): World context (e.g., check for workbench).
        dt (float): Time slice for this execution step.

    Returns:
        tuple[bool, float]: (action_completed, progress_made_this_tick)
    """
    # Similar structure to gather:
    # 1. Get recipe details from recipe_manager.
    # 2. On first tick (agent.action_progress == 0): Check ingredients, skill level, workbench presence. If fail, return (True, 0). Consume ingredients.
    # 3. Calculate progress this tick based on recipe time / dt.
    # 4. If completed:
    #    a. Add output item(s) to agent.inventory.
    #    b. Grant skill XP.
    #    c. Return (True, remaining_progress).
    # 5. Else:
    #    a. Return (False, progress).
    pass

def move_along_path(agent: 'Agent', dt: float) -> tuple[bool, float]:
    """Moves the agent along its current path over a time slice dt.

    Args:
        agent (Agent): The agent moving.
        dt (float): Time slice for this execution step.

    Returns:
        tuple[bool, float]: (action_completed, progress_made_this_tick)
                            Progress here might just be 1.0 if move successful, 0 otherwise.
                            Completion means reaching the end of the path.
    """
    # 1. Check if agent.path exists. If not, return (True, 0).
    # 2. Get agent speed (from attributes).
    # 3. Calculate distance movable: distance = speed * dt.
    # 4. While distance > 0 and agent.path is not empty:
    #    a. Get next waypoint in agent.path.
    #    b. Calculate distance to waypoint.
    #    c. If distance_to_waypoint <= distance:
    #       i. Move agent exactly to waypoint: agent.position = waypoint.
    #       ii. Remove waypoint from agent.path.
    #       iii. Reduce distance budget: distance -= distance_to_waypoint.
    #    d. Else (cannot reach waypoint this tick):
    #       i. Move agent partially towards waypoint along the vector.
    #       ii. Set distance = 0.
    # 5. Consume energy/stamina based on distance moved.
    # 6. If agent.path is now empty, return (True, 1.0).
    # 7. Else return (False, 1.0) # Still moving. Progress conceptually tricky here.
    pass