from __future__ import annotations

import asyncio
from typing import Any

from .playback_queue import PlaybackQueue, PlaybackQueueItem
from .playback_state import PlaybackState
from .player_protocol import PlayerCommand, command_to_dict


class MockPlayerRuntime:
    def __init__(self, session_id: str = "debug-session") -> None:
        self.state = PlaybackState(session_id=session_id)
        self.speech_queue = PlaybackQueue()

    def apply_command(self, command: PlayerCommand | dict[str, Any]) -> dict[str, Any]:
        command_dict = self._normalize_command(command)
        command_type = command_dict.get("type")
        self.state.append_history(command_dict)
        self.state.command_count += 1

        if command_type == "PLAY_TTS":
            return self._play_tts(command_dict)
        if command_type == "PLAY_BACKCHANNEL":
            return self._play_backchannel(command_dict)
        if command_type == "STOP_TTS":
            return self._stop_tts(command_dict)
        if command_type == "PLAY_SFX":
            return self._play_sfx(command_dict)
        if command_type == "STOP_SFX":
            return self._stop_sfx(command_dict)
        if command_type == "SET_AMBIENCE":
            return self._set_ambience(command_dict)
        if command_type == "DUCK_AUDIO":
            return self._duck_audio(command_dict)

        return {
            "applied": False,
            "type": command_type,
            "reason": "unknown_command",
            "state": self.snapshot(),
        }

    def apply_commands(
        self,
        commands: list[PlayerCommand | dict[str, Any]],
    ) -> list[dict[str, Any]]:
        return [self.apply_command(command) for command in commands]

    def snapshot(self) -> dict[str, Any]:
        return self.state.snapshot()

    def reset(self) -> None:
        self.state.reset()
        self.speech_queue.clear()

    def _play_tts(self, command_dict: dict[str, Any]) -> dict[str, Any]:
        item = self._playback_item(command_dict)
        current = self.state.speech.current
        if current is not None and self._priority(item) < self._priority(current):
            self.state.speech.queue.append(item)
            self.speech_queue.push(self._queue_item(command_dict, item, lane="speech"))
            lane = "speech"
            return self._update(True, command_dict, lane, "queued_tts")

        if current is not None:
            self.state.speech.queue.append(current)
        self.state.speech.current = item
        self.state.speech.stopped = False
        self.state.speech.ducked = False
        self.state.speech.last_command_id = command_dict.get("command_id")
        return self._update(True, command_dict, "speech", "playing_tts")

    def _play_backchannel(self, command_dict: dict[str, Any]) -> dict[str, Any]:
        item = self._playback_item(command_dict)
        item["kind"] = "backchannel"
        self.state.speech.current = item
        self.state.speech.stopped = False
        self.state.speech.last_command_id = command_dict.get("command_id")
        return self._update(True, command_dict, "speech", "playing_backchannel")

    def _stop_tts(self, command_dict: dict[str, Any]) -> dict[str, Any]:
        self.state.speech.current = None
        self.state.speech.queue = []
        self.speech_queue.clear()
        self.state.speech.stopped = True
        self.state.speech.last_command_id = command_dict.get("command_id")
        return self._update(True, command_dict, "speech", "stopped_tts")

    def _play_sfx(self, command_dict: dict[str, Any]) -> dict[str, Any]:
        item = self._playback_item(command_dict)
        self.state.sfx.active.append(item)
        self.state.sfx.last_command_id = command_dict.get("command_id")
        return self._update(True, command_dict, "sfx", "playing_sfx")

    def _stop_sfx(self, command_dict: dict[str, Any]) -> dict[str, Any]:
        payload = self._payload(command_dict)
        target = payload.get("asset_id") or payload.get("event") or payload.get("proposal_id")
        if target is None:
            stopped = list(self.state.sfx.active)
            self.state.sfx.active = []
        else:
            stopped = [
                item
                for item in self.state.sfx.active
                if self._sfx_item_matches(item, str(target))
            ]
            self.state.sfx.active = [
                item
                for item in self.state.sfx.active
                if not self._sfx_item_matches(item, str(target))
            ]
        self.state.sfx.stopped.extend(stopped)
        self.state.sfx.last_command_id = command_dict.get("command_id")
        return self._update(True, command_dict, "sfx", "stopped_sfx")

    def _set_ambience(self, command_dict: dict[str, Any]) -> dict[str, Any]:
        self.state.ambience.current = self._playback_item(command_dict)
        self.state.ambience.stopped = False
        self.state.ambience.ducked = False
        self.state.ambience.last_command_id = command_dict.get("command_id")
        return self._update(True, command_dict, "ambience", "ambience_set")

    def _duck_audio(self, command_dict: dict[str, Any]) -> dict[str, Any]:
        payload = self._payload(command_dict)
        target = payload.get("target") or payload.get("lane")
        lanes = {str(target).lower()} if target else {"sfx", "ambience"}
        if "all" in lanes or "audio" in lanes:
            lanes = {"speech", "sfx", "ambience"}
        command_id = command_dict.get("command_id")
        if "speech" in lanes:
            self.state.speech.ducked = True
            self.state.speech.last_command_id = command_id
        if "sfx" in lanes:
            self.state.sfx.ducked = True
            self.state.sfx.last_command_id = command_id
        if "ambience" in lanes:
            self.state.ambience.ducked = True
            self.state.ambience.last_command_id = command_id
        return self._update(True, command_dict, ",".join(sorted(lanes)), "ducked_audio")

    def _update(
        self,
        applied: bool,
        command_dict: dict[str, Any],
        lane: str,
        reason: str,
    ) -> dict[str, Any]:
        return {
            "applied": applied,
            "type": command_dict.get("type"),
            "lane": lane,
            "reason": reason,
            "state": self.snapshot(),
        }

    def _normalize_command(
        self,
        command: PlayerCommand | dict[str, Any],
    ) -> dict[str, Any]:
        if isinstance(command, PlayerCommand):
            return command_to_dict(command)
        return dict(command)

    def _playback_item(self, command_dict: dict[str, Any]) -> dict[str, Any]:
        payload = self._payload(command_dict)
        return {
            "command_id": command_dict.get("command_id"),
            "type": command_dict.get("type"),
            "payload": dict(payload),
            "timestamp_ms": command_dict.get("timestamp_ms"),
            "metadata": dict(command_dict.get("metadata", {})),
            "priority": self._payload_priority(payload),
            "event": payload.get("event"),
            "spatial": payload.get("spatial"),
        }

    def _queue_item(
        self,
        command_dict: dict[str, Any],
        item: dict[str, Any],
        lane: str | None,
    ) -> PlaybackQueueItem:
        return PlaybackQueueItem(
            command_id=str(command_dict.get("command_id", "")),
            type=str(command_dict.get("type", "")),
            payload=dict(item.get("payload", {})),
            priority=self._priority(item),
            lane=lane,
            metadata=dict(command_dict.get("metadata", {})),
        )

    def _payload(self, command_dict: dict[str, Any]) -> dict[str, Any]:
        payload = command_dict.get("payload", {})
        return dict(payload) if isinstance(payload, dict) else {}

    def _priority(self, item: dict[str, Any]) -> int:
        return self._payload_priority(item.get("payload", item))

    def _payload_priority(self, payload: dict[str, Any]) -> int:
        value = payload.get("priority")
        if value is None and isinstance(payload.get("original_decision"), dict):
            value = payload["original_decision"].get("priority")
        try:
            return int(value)
        except (TypeError, ValueError):
            return 50

    def _sfx_item_matches(self, item: dict[str, Any], target: str) -> bool:
        payload = item.get("payload", {})
        if not isinstance(payload, dict):
            return False
        candidates = {
            item.get("command_id"),
            payload.get("asset_id"),
            payload.get("event"),
            payload.get("proposal_id"),
        }
        return target in {str(candidate) for candidate in candidates if candidate}


class MockPlayerHarness:
    def __init__(self, player: MockPlayerRuntime | None = None) -> None:
        self.player = player or MockPlayerRuntime()

    def run_commands(self, commands: list[PlayerCommand | dict[str, Any]]) -> dict[str, Any]:
        updates = self.player.apply_commands(commands)
        return {
            "commands_applied": len(updates),
            "playback_state": self.player.snapshot(),
            "updates": updates,
        }

    async def run_debug_scenario(self, scenario_name: str) -> dict[str, Any]:
        from runtime.debug_session_runner import DebugSessionRunner, result_to_json_dict

        runner = DebugSessionRunner()
        scenario = runner.build_scenario(scenario_name)
        debug_result = await runner.run_scenario(scenario)
        if self.player.state.session_id == "debug-session":
            self.player.state.session_id = debug_result.session_id
        harness_result = self.run_commands(debug_result.player_commands)
        return {
            "scenario": scenario_name,
            "debug_result": result_to_json_dict(debug_result),
            "player_commands": debug_result.player_commands,
            **harness_result,
        }

    def run_debug_scenario_sync(self, scenario_name: str) -> dict[str, Any]:
        return asyncio.run(self.run_debug_scenario(scenario_name))
