from __future__ import annotations

import json

from tools import debug_session_runner


def test_debug_session_cli_runs_known_scenario(capsys) -> None:
    exit_code = debug_session_runner.main(["backchannel"])

    captured = capsys.readouterr()
    payload = json.loads(captured.out)
    assert exit_code == 0
    assert payload["scenario"] == "backchannel"
    assert payload["frames_processed"] > 0


def test_debug_session_cli_rejects_unknown_scenario(capsys) -> None:
    exit_code = debug_session_runner.main(["missing"])

    captured = capsys.readouterr()
    assert exit_code != 0
    assert "available scenarios" in captured.err
    assert "backchannel" in captured.err
