# social.py
import config as cfg
import random
import time # For signal timestamping

class Signal:
    """ Represents a signal broadcast by an agent. """
    def __init__(self, sender_id, signal_type, position, strength=1.0, timestamp=None):
        self.sender_id = sender_id
        self.type = signal_type
        self.position = position # (x, y) where the signal originated
        self.strength = strength # Potential future use (e.g., fades over distance)
        self.timestamp = timestamp if timestamp is not None else time.time() # Real world timestamp for visualization decay

class SocialManager:
    """ Manages social interactions between agents (Phase 4). """
    def __init__(self, agents):
        """ Initializes the manager with the current list of agents. """
        self.agents_dict = {agent.id: agent for agent in agents}
        # List to keep track of active signals for visualization or broader processing
        self.active_signals = []

    def update_agent_list(self, agents):
        """ Call this if the main agent list changes (e.g., agent death). """
        self.agents_dict = {agent.id: agent for agent in agents if agent.health > 0}

    def broadcast_signal(self, sending_agent, signal_type, position):
        """ Creates a Signal object and notifies nearby agents. """
        if sending_agent.id not in self.agents_dict:
             if cfg.DEBUG_SOCIAL: print(f"Warning: Dead agent {sending_agent.id} tried to broadcast.")
             return # Sender might have just died or is invalid

        sender_pos = (sending_agent.x, sending_agent.y) # Use sender's current position
        new_signal = Signal(sending_agent.id, signal_type, sender_pos)
        self.active_signals.append(new_signal) # Add to active signals list

        if cfg.DEBUG_SOCIAL: print(f"Agent {sending_agent.id} broadcasting '{signal_type}' from {sender_pos}")

        recipients = []
        for agent_id, agent in self.agents_dict.items():
            # Don't signal self, ensure agent is alive
            if agent.id != sending_agent.id and agent.health > 0:
                # Use squared distance for efficiency
                dist_sq = (agent.x - sender_pos[0])**2 + (agent.y - sender_pos[1])**2
                if dist_sq < cfg.SIGNAL_RANGE_SQ:
                    # Agent perceives the signal (handled in agent.py - perceive_signal)
                    agent.perceive_signal(new_signal) # Pass the whole Signal object
                    recipients.append(agent.id)

        if cfg.DEBUG_SOCIAL and recipients: print(f" -> Signal '{signal_type}' received by agents: {recipients}")
        if cfg.DEBUG_SOCIAL and not recipients: print(f" -> Signal '{signal_type}' received by no one in range.")


    def update(self, dt_sim_seconds):
         """ Periodic updates: Signal cleanup and relationship decay. """
         # 1. Clean up old signals from the active list (for visualization/memory)
         current_time = time.time()
         self.active_signals = [s for s in self.active_signals
                                if current_time - s.timestamp < (cfg.SIGNAL_DURATION_TICKS / cfg.FPS) * 1.5] # Keep a bit longer than visualization

         # 2. Apply relationship decay for all agents
         for agent in self.agents_dict.values():
             agent.knowledge.decay_relationships(dt_sim_seconds)