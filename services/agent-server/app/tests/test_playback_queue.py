from __future__ import annotations

import json

from audio_runtime import PlaybackQueue, PlaybackQueueItem


def test_playback_queue_push_peek_pop_priority_and_clear() -> None:
    queue = PlaybackQueue()
    low = PlaybackQueueItem(command_id="low", type="PLAY_TTS", priority=10)
    high = PlaybackQueueItem(command_id="high", type="PLAY_TTS", priority=90)

    queue.push(low)
    queue.push(high)

    assert len(queue) == 2
    assert queue.peek().command_id == "high"
    assert queue.pop_next().command_id == "high"
    assert queue.pop_next().command_id == "low"
    assert queue.pop_next() is None

    queue.push(low)
    queue.clear()
    assert len(queue) == 0


def test_playback_queue_to_list_is_json_friendly() -> None:
    queue = PlaybackQueue()
    queue.push(
        PlaybackQueueItem(
            command_id="cmd1",
            type="PLAY_SFX",
            payload={"event": "door_knock"},
            lane="sfx",
        )
    )

    payload = queue.to_list()

    assert payload[0]["payload"]["event"] == "door_knock"
    assert json.loads(json.dumps(payload, ensure_ascii=False))[0]["lane"] == "sfx"
