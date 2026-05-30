from __future__ import annotations

from agents import MockDialogueAgent
from schemas import SessionState


def test_asr_final_when_user_stopped_produces_dialogue_proposal() -> None:
    agent = MockDialogueAgent()
    state = SessionState(session_id="session-1")
    state.asr.final = "我们怎么拆这个系统？"

    result = agent.propose(state)

    assert len(result.proposals) == 1
    proposal = result.proposals[0]
    assert proposal.agent == "dialogue"
    assert proposal.lane == "speech"
    assert proposal.action == "SPEAK"
    assert proposal.text == "我建议把这个系统拆成输入、决策、调度和音频渲染四层。"
    assert proposal.priority == 50
    assert proposal.timing == {"start_when": "user_turn_end"}
    assert proposal.interrupt_policy == {"interruptible_by_user": True}
    assert proposal.mixing == {"gain": 0.75, "duck_others": True}


def test_user_speaking_blocks_normal_dialogue_proposal() -> None:
    agent = MockDialogueAgent()
    state = SessionState(session_id="session-1")
    state.asr.final = "我们怎么拆这个系统？"
    state.user_audio.is_speaking = True

    result = agent.propose(state)

    assert result.proposals == []


def test_interrupt_followup_metadata_produces_higher_priority_dialogue() -> None:
    agent = MockDialogueAgent()
    state = SessionState(session_id="session-1")
    state.metadata["interrupt_reason"] = "dangerous_operation"

    result = agent.propose(state)

    proposal = result.proposals[0]
    assert proposal.action == "SPEAK"
    assert proposal.priority == 60
    assert proposal.text == "这个操作风险很高。我们先确认备份、影响范围和回滚方案。"
