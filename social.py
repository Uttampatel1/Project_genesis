# social.py
import config as cfg
import random

class SocialManager:
    def __init__(self, agents):
        # Use a dictionary for faster agent lookup by ID
        self.agents_dict = {agent.id: agent for agent in agents}

    def update_agent_list(self, agents):
        """ Call this if the main agent list changes (e.g., agent death). """
        self.agents_dict = {agent.id: agent for agent in agents if agent.health > 0}

    def broadcast_signal(self, sending_agent, signal_type, position, range_limit=cfg.SIGNAL_RANGE):
        """ Simple broadcast mechanism to nearby agents. """
        if sending_agent.id not in self.agents_dict: return # Sender might have just died

        # print(f"Agent {sending_agent.id} broadcasting '{signal_type}' at {position}") # Debug
        recipients = []
        for agent_id, agent in self.agents_dict.items():
            if agent.id != sending_agent.id:
                # Use squared distance for efficiency
                dist_sq = (agent.x - position[0])**2 + (agent.y - position[1])**2
                if dist_sq < range_limit**2:
                    agent.perceive_signal(sending_agent.id, signal_type, position)
                    recipients.append(agent.id)
        # if recipients: print(f" -> Signal received by agents: {recipients}")


    def attempt_teaching(self, teacher, student, skill_name):
        """ Teacher initiates teaching interaction. """
        if teacher.id not in self.agents_dict or student.id not in self.agents_dict: return False # Agent gone
        if teacher.id == student.id: return False

        # Conditions: Teacher skill, proximity, relationship, student willingness
        teacher_skill_level = teacher.skills.get(skill_name, 0)
        student_skill_level = student.skills.get(skill_name, 0)
        required_level_diff = 5 # Teacher needs to be noticeably better

        distance = abs(teacher.x - student.x) + abs(teacher.y - student.y)
        max_teach_distance = 3 # Increased slightly

        # Use teacher's perspective for initiating
        relationship_teacher_student = teacher.knowledge.get_relationship(student.id)

        if distance <= max_teach_distance and \
           teacher_skill_level > student_skill_level + required_level_diff and \
           relationship_teacher_student >= cfg.TEACHING_RELATIONSHIP_THRESHOLD and \
           teacher.energy > cfg.TEACH_ENERGY_COST * 2: # Teacher needs energy

            # Student AI decides whether to accept
            if student.decide_to_learn(teacher.id, skill_name):
                print(f"Agent {teacher.id} teaches '{skill_name}' to Agent {student.id}")

                # Simulate teaching time/cost? For now, boost student skill, cost teacher energy.
                teacher.energy -= cfg.TEACH_ENERGY_COST
                success = student.learn_skill(skill_name, boost=cfg.TEACHING_BOOST_FACTOR)

                if success:
                    # Positive relationship boost for both
                    teacher.knowledge.update_relationship(student.id, 0.05)
                    student.knowledge.update_relationship(teacher.id, 0.08) # Student slightly more grateful?
                    return True
                else:
                    # Student accepted but failed to learn (e.g., already maxed)? Small penalty?
                    teacher.knowledge.update_relationship(student.id, -0.01)
                    student.knowledge.update_relationship(teacher.id, -0.01)
                    return False
            else:
                 # Student refused, small relationship penalty for teacher?
                 teacher.knowledge.update_relationship(student.id, -0.02)
                 return False # Student refused
        return False


    def attempt_helping(self, helper, target):
         """ Helper agent performs the help action (e.g., giving food). """
         if helper.id not in self.agents_dict or target.id not in self.agents_dict: return False
         if helper.id == target.id: return False

         # Re-check conditions (proximity, target need, helper means)
         distance = abs(helper.x - target.x) + abs(helper.y - target.y)
         max_help_distance = 2

         relationship = helper.knowledge.get_relationship(target.id)

         if distance > max_help_distance:
              # print(f"Help Fail: {helper.id} too far from {target.id}")
              return False
         if relationship < cfg.HELPING_RELATIONSHIP_THRESHOLD:
              # print(f"Help Fail: {helper.id} relationship too low with {target.id} ({relationship:.2f})")
              return False

         # --- Specific Help Types ---
         helped = False
         # 1. Give Food
         if target.hunger > cfg.MAX_HUNGER * 0.7 and helper.inventory.get('Food', 0) >= 1:
             # Helper AI check: Don't give food if helper is also starving
             if helper.hunger < cfg.MAX_HUNGER * 0.85:
                 print(f"Agent {helper.id} gives Food to Agent {target.id}.")
                 # Transfer item / Reduce need
                 helper.inventory['Food'] -= 1
                 if helper.inventory['Food'] <= 0: del helper.inventory['Food']
                 target.hunger = max(0, target.hunger - cfg.EAT_HUNGER_REDUCTION * 0.75) # Slightly less effective?
                 helped = True
             # else: print(f"Help Fail: {helper.id} is too hungry to give food.")


         # 2. Give Water (if carrying mechanism exists - e.g., Waterskin item)
         # if not helped and target.thirst > cfg.MAX_THIRST * 0.7 and helper.inventory.get('WaterskinFull', 0) >= 1:
         #     if helper.thirst < cfg.MAX_THIRST * 0.85:
         #          print(f"Agent {helper.id} gives Water to Agent {target.id}.")
         #          helper.inventory['WaterskinFull'] -= 1
         #          # Add WaterskinEmpty?
         #          target.thirst = max(0, target.thirst - cfg.DRINK_THIRST_REDUCTION * 0.75)
         #          helped = True

         # --- Update Relationship on Success ---
         if helped:
             helper.knowledge.update_relationship(target.id, 0.15) # Significant boost for helping
             target.knowledge.update_relationship(helper.id, 0.20) # Target is grateful
             # Small energy cost to helper handled in agent's _perform_action
             return True
         else:
             # print(f"Help Fail: {helper.id} could not find way to help {target.id}")
             return False