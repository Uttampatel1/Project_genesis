import config as cfg
import random

class SocialManager:
    """ Manages social interactions between agents (Phase 4+). """
    def __init__(self, agents):
        # Use a dictionary for faster agent lookup by ID
        self.agents_dict = {agent.id: agent for agent in agents}

    def update_agent_list(self, agents):
        """ Call this if the main agent list changes (e.g., agent death). """
        self.agents_dict = {agent.id: agent for agent in agents if agent.health > 0}

    def broadcast_signal(self, sending_agent, signal_type, position, range_limit=cfg.SIGNAL_RANGE):
        """ Simple broadcast mechanism to nearby agents (Placeholder). """
        if sending_agent.id not in self.agents_dict: return # Sender might have just died

        # if cfg.DEBUG_SOCIAL: print(f"Agent {sending_agent.id} broadcasting '{signal_type}' at {position}")
        recipients = []
        for agent_id, agent in self.agents_dict.items():
            if agent.id != sending_agent.id and agent.health > 0:
                # Use squared distance for efficiency
                dist_sq = (agent.x - position[0])**2 + (agent.y - position[1])**2
                if dist_sq < range_limit**2:
                    # Agent perceives the signal (handled in agent.py - perceive_signal)
                    agent.perceive_signal(sending_agent.id, signal_type, position)
                    recipients.append(agent.id)
        # if cfg.DEBUG_SOCIAL and recipients: print(f" -> Signal received by agents: {recipients}")
        pass # Placeholder


    def attempt_teaching(self, teacher, student, skill_name):
        """ Placeholder for teaching interaction. """
        # Conditions: Teacher skill, proximity, relationship, student willingness
        # ... (detailed logic for Phase 4) ...
        return False


    def attempt_helping(self, helper, target):
         """ Placeholder for helping interaction (e.g., giving items). """
         # Conditions: Proximity, target need, helper means, relationship
         # ... (detailed logic for Phase 4) ...
         return False

    def update(self, dt_sim_seconds):
         """ Placeholder for periodic social manager updates (e.g., relationship decay). """
         pass