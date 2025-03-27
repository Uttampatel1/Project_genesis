# social.py
# Defines social actions and interactions

class SocialManager:
    def __init__(self, agents):
        self.agents = agents # Keep reference to the list of all agents

    def broadcast_signal(self, sending_agent, signal_type, position, range_limit=10):
        """ Simple broadcast mechanism. """
        print(f"Agent {sending_agent.id} broadcasting '{signal_type}' at {position}")
        recipients = []
        for agent in self.agents:
            if agent != sending_agent:
                dist_sq = (agent.x - position[0])**2 + (agent.y - position[1])**2
                if dist_sq < range_limit**2:
                    agent.perceive_signal(sending_agent.id, signal_type, position)
                    recipients.append(agent.id)
        # print(f" -> Received by agents: {recipients}")

    def attempt_teaching(self, teacher, student, skill_name):
        """ Placeholder for teaching interaction. """
        if teacher == student: return False

        # Conditions: Teacher has skill, student doesn't or has lower level, proximity, relationship?
        teacher_skill_level = teacher.skills.get(skill_name, 0)
        student_skill_level = student.skills.get(skill_name, 0)
        required_level_diff = 5 # Example: Teacher needs to be somewhat better

        # Check proximity (simple grid distance)
        distance = abs(teacher.x - student.x) + abs(teacher.y - student.y)
        max_teach_distance = 2

        # Check relationship (using teacher's perspective for now)
        relationship = teacher.knowledge.get_relationship(student.id)
        min_relationship_to_teach = 0.2 # Example: Must be somewhat friendly

        if distance <= max_teach_distance and \
           teacher_skill_level > student_skill_level and \
           teacher_skill_level >= required_level_diff and \
           relationship >= min_relationship_to_teach:

            # Student AI decides whether to accept learning (e.g., if not busy with critical need)
            if student.decide_to_learn(teacher.id, skill_name):
                print(f"Agent {teacher.id} starts teaching '{skill_name}' to Agent {student.id}")
                # Simulate teaching time/process? For now, instant small boost.
                success = student.learn_skill(skill_name, boost=cfg.SKILL_INCREASE_RATE * 5) # Give a bonus
                if success:
                    # Maybe positive relationship boost?
                    teacher.knowledge.update_relationship(student.id, 0.05)
                    student.knowledge.update_relationship(teacher.id, 0.05)
                    return True
        return False

    def attempt_helping(self, helper, target):
         """ Placeholder for helping behavior (e.g., giving food). """
         if helper == target: return False

         # Conditions: Proximity, target in need, helper has means, relationship?
         distance = abs(helper.x - target.x) + abs(helper.y - target.y)
         max_help_distance = 2

         relationship = helper.knowledge.get_relationship(target.id)
         min_relationship_to_help = 0.0 # Example: Neutral or friendly

         needs_help = target.hunger > cfg.MAX_HUNGER * 0.8 or target.thirst > cfg.MAX_THIRST * 0.8 # Example need condition

         if distance <= max_help_distance and needs_help and relationship >= min_relationship_to_help:
             # Check if helper has surplus food/water
             if helper.inventory.get('Food', 0) > 1 and target.hunger > cfg.MAX_HUNGER * 0.8:
                 # Helper AI decides (maybe factor in own needs)
                 if helper.current_action != 'Helping': # Basic check to prevent loops
                     print(f"Agent {helper.id} decides to help Agent {target.id} with food.")
                     # Simulate giving item - needs inventory transfer logic
                     # For now, just reduce target's need directly & give relationship boost
                     target.hunger = max(0, target.hunger - cfg.EAT_HUNGER_REDUCTION // 2) # Less effective than eating self?
                     helper.inventory['Food'] = helper.inventory.get('Food', 0) - 1
                     if helper.inventory['Food'] <= 0: del helper.inventory['Food']

                     helper.knowledge.update_relationship(target.id, 0.1)
                     target.knowledge.update_relationship(helper.id, 0.1)
                     helper.current_action = 'Helping' # Briefly set state
                     return True

             # Add similar check for water if needed (less likely to carry water?)

         return False

    # Add methods for cooperative tasks, trading, etc.