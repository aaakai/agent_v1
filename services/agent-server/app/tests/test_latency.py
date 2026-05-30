from __future__ import annotations

from runtime import calculate_decision_latencies, summarize_latencies
from schemas import Event


def test_empty_latency_summary_has_zero_count() -> None:
    assert summarize_latencies([]) == {
        "count": 0,
        "avg_ms": None,
        "max_ms": None,
        "min_ms": None,
    }


def test_calculate_and_summarize_latency_data() -> None:
    event = Event(
        event_id="event-1",
        session_id="session-1",
        type="TEST",
        timestamp_ms=100,
    )
    decisions = [
        {
            "event_id": "event-1",
            "event_type": "TEST",
            "decision": "play",
            "lane": "speech",
            "now_ms": 130,
        },
        {
            "event_id": "event-1",
            "event_type": "TEST",
            "decision": "duck",
            "lane": "sfx",
            "now_ms": 150,
        },
    ]

    latencies = calculate_decision_latencies([event], decisions)
    summary = summarize_latencies(latencies)

    assert [latency["latency_ms"] for latency in latencies] == [30, 50]
    assert summary == {
        "count": 2,
        "avg_ms": 40.0,
        "max_ms": 50,
        "min_ms": 30,
    }
