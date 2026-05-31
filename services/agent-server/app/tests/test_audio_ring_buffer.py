from __future__ import annotations

from audio_input import AudioFrame, AudioRingBuffer


def make_frame(index: int) -> AudioFrame:
    return AudioFrame(
        session_id="session-1",
        frame_id=f"frame-{index}",
        timestamp_ms=index * 100,
    )


def test_append_len_and_latest() -> None:
    buffer = AudioRingBuffer(max_frames=3)
    frame = make_frame(1)

    buffer.append(frame)

    assert len(buffer) == 1
    assert buffer.latest() == frame


def test_exceeding_max_frames_drops_old_frames() -> None:
    buffer = AudioRingBuffer(max_frames=2)
    frames = [make_frame(index) for index in range(3)]

    for frame in frames:
        buffer.append(frame)

    assert len(buffer) == 2
    assert buffer.get_recent() == frames[1:]


def test_get_recent_returns_last_n_frames() -> None:
    buffer = AudioRingBuffer(max_frames=5)
    frames = [make_frame(index) for index in range(5)]
    for frame in frames:
        buffer.append(frame)

    assert buffer.get_recent(2) == frames[-2:]
    assert buffer.get_recent(0) == []


def test_get_since_filters_by_timestamp() -> None:
    buffer = AudioRingBuffer(max_frames=5)
    frames = [make_frame(index) for index in range(5)]
    for frame in frames:
        buffer.append(frame)

    assert buffer.get_since(200) == frames[2:]


def test_clear_empties_buffer() -> None:
    buffer = AudioRingBuffer(max_frames=5)
    buffer.append(make_frame(1))

    buffer.clear()

    assert len(buffer) == 0
    assert buffer.latest() is None
