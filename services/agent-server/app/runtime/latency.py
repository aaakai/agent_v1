from __future__ import annotations

from typing import Any

from schemas import Event


def calculate_decision_latencies(
    events: list[Event],
    decisions: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    event_timestamps = {event.event_id: event.timestamp_ms for event in events}
    latencies: list[dict[str, Any]] = []

    for decision in decisions:
        start_ms = decision.get("event_timestamp_ms")
        if start_ms is None and decision.get("event_id") in event_timestamps:
            start_ms = event_timestamps[decision["event_id"]]
        end_ms = decision.get("now_ms") or decision.get("timestamp_ms")
        if not isinstance(start_ms, int) or not isinstance(end_ms, int):
            continue

        latency_ms = max(0, end_ms - start_ms)
        latencies.append(
            {
                "event_id": decision.get("event_id"),
                "event_type": decision.get("event_type"),
                "decision": decision.get("decision"),
                "lane": decision.get("lane"),
                "proposal_id": decision.get("proposal_id"),
                "action_id": decision.get("action_id"),
                "latency_ms": latency_ms,
            }
        )

    return latencies


def summarize_latencies(latencies: list[dict[str, Any]]) -> dict[str, Any]:
    values = [
        latency["latency_ms"]
        for latency in latencies
        if isinstance(latency.get("latency_ms"), (int, float))
    ]
    if not values:
        return {"count": 0, "avg_ms": None, "max_ms": None, "min_ms": None}

    return {
        "count": len(values),
        "avg_ms": sum(values) / len(values),
        "max_ms": max(values),
        "min_ms": min(values),
    }
