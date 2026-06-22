# AGENTS.md

Project-level guidance for Codex and other coding agents working on this repo.

## 1. Project Overview

This project is the Lulula Agentic 3D Voice Runtime.

The core goal is to build a realtime voice agent runtime that can:

- accept browser / LiveKit user audio,
- extract audio features for VAD, backchannel, and turn-final detection,
- run ASR through mock or pluggable providers,
- support interrupt and backchannel behavior,
- arbitrate assistant speech, SFX, ambience, and spatial metadata,
- emit player-facing commands for a frontend or mock player,
- stay observable through debug runners and web debug pages.

The current architecture prioritizes:

- mock-only testability,
- low coupling between layers,
- graceful degradation when SDKs or API keys are missing,
- clear observability and debug snapshots,
- incremental integration of real services.

Current primary chain:

```text
Browser / LiveKit audio
-> LiveKitAudioTrackReader
-> AudioFrame
-> RawAudioRouter
-> BackchannelTrigger / ASRTrigger / ASRFlushTrigger
-> RuntimeCoordinator
-> Agents
-> AudioOrchestrator
-> PlayerCommand
-> Player Sink / Mock Player / Debug Panel
```

## 2. Core Architecture Rules

- `RawAudioRouter` only fans out `AudioFrame` instances to consumers.
- `RawAudioRouter` must not make business decisions.
- `BackchannelTrigger` owns audio feature extraction, VAD state, and backchannel opportunity events.
- `ASRTrigger` sends `AudioFrame` data to an ASR adapter and converts `ASRResult` into `ASR_PARTIAL` / `ASR_FINAL` events.
- `ASRFlushTrigger` and `TurnDetector` own turn-final and silence-flush timing decisions.
- `RuntimeCoordinator` receives events, updates `SessionState`, calls agents, applies state updates, and sends outputs to the orchestrator.
- Agents only produce `OutputProposal`, `ControlAction`, or `StateUpdate`.
- Agents must not play audio directly.
- `AudioOrchestrator` is the only output arbitration module.
- `PlayerCommand` is the backend-to-player protocol.
- `MockPlayerRuntime` only simulates frontend playback state.
- `MockPlayerRuntime` must not make agent or orchestrator decisions.
- `web_debug` is for debug UI and API only.
- `web_debug` must not change core runtime decision behavior.

## 3. Current Important Modules

### `services/agent-server/app/schemas/`

Pydantic runtime schemas and event type constants. Keep schema changes small and backward-compatible when possible.

### `services/agent-server/app/realtime/`

Event bus and session state manager. This layer stores current per-session state and event history.

### `services/agent-server/app/audio_input/`

Raw audio input primitives: `AudioFrame`, ring buffer, raw router, VAD, feature extractor, backchannel trigger, turn detector, and ASR flush trigger.

### `services/agent-server/app/asr/`

ASR abstractions, mock adapters, provider config/factory, diagnostics, provider skeletons, and OpenAI chunked transcription adapter.

### `services/agent-server/app/livekit/`

LiveKit config, token generation, debug state, room handler, audio track reader/publisher skeletons, room connection helpers, and backend agent worker loop.

### `services/agent-server/app/runtime/`

Coordinator, replay, simulator, latency helpers, and `DebugSessionRunner`. This is the main offline integration path.

### `services/agent-server/app/agents/`

Mock agents for backchannel, interrupt, dialogue, scene, SFX planning, spatial metadata, and safety policy.

### `services/agent-server/app/orchestrator/`

Audio arbitration lanes and `AudioOrchestrator`. This decides play, queue, stop, duck, replace, or reject behavior.

### `services/agent-server/app/audio_runtime/`

SFX DSL/retriever, ambience controller, spatial protocol, player protocol, player sinks, command recorder, playback state, playback queue, and mock player.

### `services/agent-server/app/web_debug/`

Framework-light debug API, FastAPI server wrapper, static debug UI, summary/narration builders, LiveKit debug API, and turn summary helpers.

### `services/agent-server/app/tools/`

CLI entry points for replay, simulation, debug sessions, mock player harness, LiveKit worker, latency report, and web debug server.

### `services/agent-server/app/tests/`

Pytest suite. Tests are intentionally mock-first and should remain independent of real external services.

## 4. Development Rules

- Do not perform broad refactors unless the task explicitly asks for them.
- Do not delete, skip, or weaken existing tests to make changes pass.
- Every new feature should add or update focused tests.
- By default, all tests must be mock-only.
- Real external service integration must gracefully degrade.
- SDK imports must be delayed until runtime paths that actually need them.
- Project imports and tests must not fail when SDKs, API keys, or network are missing.
- Never log API keys, secrets, raw tokens, or credentials.
- Never return API keys or secrets to frontend/debug responses.
- Safe config and debug status must mask secrets.
- Do not write raw PCM into diagnostics, debug snapshots, or web API responses.
- Do not introduce React, Vite, npm, or frontend build tooling unless explicitly requested.
- Do not implement real TTS, assistant audio publishing, SFX playback, or 3D rendering unless explicitly requested.
- Debug UI changes must not alter `RuntimeCoordinator`, agent, or `AudioOrchestrator` behavior.
- Keep changes scoped to the module boundary implied by the task.
- Prefer existing Pydantic/model patterns and local helper APIs.
- Preserve backward-compatible fields when debug or protocol structures are already tested.

## 5. Testing

Default test command:

```bash
python -m pytest -q
```

Run it before handing off completed work.

If a change is localized, it is fine to run targeted tests first, then run the full suite.

Testing principles:

- Tests must not require real LiveKit Cloud.
- Tests must not require real OpenAI, Deepgram, FunASR, or SenseVoice.
- Tests must not require a real microphone.
- Tests must not require real network access.
- Use fake clients, mock adapters, local fixtures, and monkeypatching.
- Provider skeleton tests should assert safe import, clear errors, and masked config.
- OpenAI chunked ASR tests must use fake clients and must not call the network.

## 6. Secrets / Environment Variables

Common LiveKit variables:

- `LIVEKIT_URL`
- `LIVEKIT_API_KEY`
- `LIVEKIT_API_SECRET`
- `LIVEKIT_ROOM`
- `LIVEKIT_AGENT_IDENTITY`

Common ASR variables:

- `ASR_PROVIDER`
- `ASR_LANGUAGE`
- `ASR_MODEL`
- `ASR_CHUNK_DURATION_MS`
- `ASR_SILENCE_FLUSH_MS`
- `OPENAI_API_KEY`
- `DEEPGRAM_API_KEY`
- `FUNASR_ENDPOINT`

Rules:

- Secrets are backend-only.
- Frontend code must never receive API secrets.
- Frontend LiveKit access must go through the backend token API.
- Safe config and debug status must mask secret values.
- Do not print secrets in CLI output, logs, exceptions, or snapshots.

## 7. LiveKit Rules

- LiveKit is only the realtime audio transport layer.
- Browser clients get room tokens from the backend token API.
- The backend worker joins a room and subscribes to remote participant audio tracks.
- The backend must not open its own microphone.
- The current focus is the user audio input chain.
- Do not implement assistant audio publishing unless explicitly requested.
- Do not implement real TTS output unless explicitly requested.
- Real LiveKit SDK use must be delayed import and optional.
- Tests must use mock rooms, mock tracks, and mock readers.

## 8. ASR Rules

- ASR providers are created through the ASR factory.
- Default ASR behavior should be `mock` or `disabled`.
- Real providers must not be required for imports or tests.
- OpenAI ASR is currently chunked final transcription, not realtime partial streaming.
- ASR flush can be triggered by silence, `USER_SPEECH_END`, `force_turn_end`, or max turn duration.
- `ASRTrigger.flush(reason=...)` must preserve `flush_reason` and `turn_final` metadata.
- Flush diagnostics should include counts, reasons, timestamps, and final text.
- Diagnostics must not store raw PCM.
- Diagnostics and debug status must not expose provider keys.
- Provider errors should become diagnostics/debug data, not router-wide crashes.

## 9. Debug / Observability Rules

- `DebugSessionRunner` is the main offline debug entry point.
- Web Debug Panel should default to simplified summary, narration, lanes, turn summary, and key decisions.
- Advanced JSON can remain available, but should not be the primary reading path.
- LiveKit Debug page should show config status, worker status, ASR status, and turn flush status.
- Debug summaries should be human-readable and tolerant of missing fields.
- Debug code must not move or duplicate core runtime decision logic.
- Debug snapshots must avoid secrets and raw PCM.

## 10. When Adding a New Feature

Use this checklist:

1. Read the relevant module and its tests first.
2. Identify the correct module boundary.
3. Keep business decisions out of routers, UI, sinks, and mock player code.
4. Add focused tests for the new behavior.
5. Keep external services mocked in tests.
6. Preserve secret masking and graceful degradation.
7. Run targeted tests if useful.
8. Run `python -m pytest -q`.
9. Summarize changed files, behavior, and test results.

## 11. What Not To Do

- Do not hardcode real credentials.
- Do not print secrets.
- Do not call real external services in tests.
- Do not remove existing tests to make CI pass.
- Do not move core decision logic into UI, player, sink, or debug modules.
- Do not make `RawAudioRouter` decide business behavior.
- Do not make agents directly play audio.
- Do not make `AudioOrchestrator` call ASR or TTS providers.
- Do not make Web Debug change runtime decisions.
- Do not store raw PCM in diagnostics or debug responses.
- Do not introduce heavy dependencies without an explicit request.
