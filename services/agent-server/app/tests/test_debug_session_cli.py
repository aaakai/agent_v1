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


def test_debug_session_cli_runs_sfx_and_scene(capsys) -> None:
    sfx_code = debug_session_runner.main(["sfx"])
    sfx_payload = json.loads(capsys.readouterr().out)
    scene_code = debug_session_runner.main(["scene"])
    scene_payload = json.loads(capsys.readouterr().out)

    assert sfx_code == 0
    assert sfx_payload["scenario"] == "sfx"
    assert scene_code == 0
    assert scene_payload["final_state"]["scene"]["name"] == "rainy_alley"


def test_debug_session_cli_rejects_unknown_scenario(capsys) -> None:
    exit_code = debug_session_runner.main(["missing"])

    captured = capsys.readouterr()
    assert exit_code != 0
    assert "available scenarios" in captured.err
    assert "backchannel" in captured.err
