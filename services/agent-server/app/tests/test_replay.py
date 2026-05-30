from __future__ import annotations

import json

from runtime import load_jsonl_events, replay_events, replay_jsonl
from schemas import Event
from schemas.event_types import ASR_FINAL, USER_SPEECH_END


def test_load_jsonl_events_reads_events(tmp_path) -> None:
    path = tmp_path / "events.jsonl"
    rows = [
        {"session_id": "session-1", "type": USER_SPEECH_END},
        {
            "session_id": "session-1",
            "type": ASR_FINAL,
            "payload": {"text": "hello"},
        },
    ]
    path.write_text(
        "\n".join(json.dumps(row, ensure_ascii=False) for row in rows),
        encoding="utf-8",
    )

    events = load_jsonl_events(path)

    assert len(events) == 2
    assert all(isinstance(event, Event) for event in events)
    assert events[0].event_id
    assert events[1].payload == {"text": "hello"}


def test_replay_events_returns_summary() -> None:
    events = [
        Event(session_id="session-1", type=USER_SPEECH_END),
        Event(
            session_id="session-1",
            type=ASR_FINAL,
            payload={"text": "hello"},
        ),
    ]

    result = replay_events(events)

    assert result["event_count"] == 2
    assert result["decision_count"] == len(result["decisions"])
    assert "session-1" in result["sessions"]
    assert result["sessions"]["session-1"]["event_count"] == 2
    assert result["sessions"]["session-1"]["final_state"]["asr"]["final"] == "hello"


def test_replay_jsonl_runs_from_path(tmp_path) -> None:
    path = tmp_path / "events.jsonl"
    path.write_text(
        json.dumps(
            {
                "session_id": "session-1",
                "type": ASR_FINAL,
                "payload": {"text": "hello"},
            },
            ensure_ascii=False,
        )
        + "\n",
        encoding="utf-8",
    )

    result = replay_jsonl(path)

    assert result["event_count"] == 1
    assert result["sessions"]["session-1"]["final_state"]["asr"]["final"] == "hello"
