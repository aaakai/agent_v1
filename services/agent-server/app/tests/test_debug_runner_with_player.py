from __future__ import annotations

import json

from tools import debug_session_runner, mock_player_harness


def test_mock_player_harness_cli_runs_sfx(capsys) -> None:
    exit_code = mock_player_harness.main(["sfx"])

    payload = json.loads(capsys.readouterr().out)
    assert exit_code == 0
    assert payload["scenario"] == "sfx"
    assert payload["playback_state"]["sfx"]["active"]


def test_mock_player_harness_cli_state_only(capsys) -> None:
    exit_code = mock_player_harness.main(["sfx", "--state-only"])

    payload = json.loads(capsys.readouterr().out)
    assert exit_code == 0
    assert "sfx" in payload
    assert "debug_result" not in payload


def test_mock_player_harness_cli_commands(capsys) -> None:
    exit_code = mock_player_harness.main(["sfx", "--commands"])

    payload = json.loads(capsys.readouterr().out)
    assert exit_code == 0
    assert payload["player_commands"]
    assert payload["playback_state"]["sfx"]["active"]


def test_mock_player_harness_cli_rejects_unknown(capsys) -> None:
    exit_code = mock_player_harness.main(["missing"])

    captured = capsys.readouterr()
    assert exit_code != 0
    assert "available scenarios" in captured.err


def test_debug_session_runner_cli_with_player(capsys) -> None:
    exit_code = debug_session_runner.main(["sfx", "--with-player"])

    payload = json.loads(capsys.readouterr().out)
    assert exit_code == 0
    assert payload["commands_applied"] == len(payload["player_commands"])
    assert payload["playback_state"]["sfx"]["active"]
