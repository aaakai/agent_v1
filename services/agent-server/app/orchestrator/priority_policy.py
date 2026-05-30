from __future__ import annotations


class PriorityPolicy:
    EMERGENCY = 100
    INTERRUPT = 95
    USER_BARGE_IN = 80
    SHORT_CORRECTION = 60
    DIALOGUE = 50
    MEANINGFUL_BACKCHANNEL = 35
    SIMPLE_BACKCHANNEL = 30
    EVENT_SFX = 20
    AMBIENCE = 10

    def get_default_priority(
        self,
        action: str,
        agent: str | None = None,
        lane: str | None = None,
    ) -> int:
        action_name = action.upper()
        agent_name = agent.lower() if agent is not None else None
        lane_name = lane.lower() if lane is not None else None

        if action_name in {"STOP_SPEAKING", "INTERRUPT_USER"}:
            return self.INTERRUPT
        if action_name == "SPEAK" and agent_name == "dialogue":
            return self.DIALOGUE
        if action_name == "BACKCHANNEL":
            return self.SIMPLE_BACKCHANNEL
        if action_name == "PLAY_SFX":
            return self.EVENT_SFX
        if action_name == "SET_AMBIENCE":
            return self.AMBIENCE
        if lane_name == "ambience":
            return self.AMBIENCE
        return self.DIALOGUE

    def is_higher_priority(self, new_priority: int, current_priority: int) -> bool:
        return new_priority > current_priority

    def should_duck_under_speech(self, lane: str) -> bool:
        return lane.lower() in {"sfx", "ambience"}


def effective_proposal_priority(
    action: str,
    agent: str | None,
    lane: str | None,
    priority: int,
    explicit_fields: set[str],
) -> int:
    if "priority" in explicit_fields:
        return priority
    return PriorityPolicy().get_default_priority(action=action, agent=agent, lane=lane)


def effective_control_priority(
    action: str,
    agent: str | None,
    priority: int,
    explicit_fields: set[str],
) -> int:
    if "priority" in explicit_fields:
        return priority
    return PriorityPolicy().get_default_priority(action=action, agent=agent)
