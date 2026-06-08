from __future__ import annotations

import json
from dataclasses import asdict
from pathlib import Path

from scripts import aigp_integrated_dry_run_gate

ROOT = Path(__file__).resolve().parents[1]


def test_integrated_dry_run_episode_matches_generator() -> None:
    fixture_path = (
        ROOT / "docs" / "engineering" / "evidence" / "integrated-dry-run-episode-2026-06-08.json"
    )

    expected = aigp_integrated_dry_run_gate._fixed_json_value(
        asdict(aigp_integrated_dry_run_gate.build_integrated_dry_run_episode())
    )
    actual = json.loads(fixture_path.read_text(encoding="utf-8"))

    assert actual == expected
    assert actual["events"][1]["event_type"] == "gate_detection_result"
    assert actual["events"][2]["payload"]["status"] == "GATE_WITHOUT_VELOCITY"
    assert actual["events"][3]["payload"]["kind"] == "BODY_VELOCITY"
    assert "not a valid-run result" in actual["non_claims"]


def test_integrated_dry_run_decision_trace_matches_generator() -> None:
    fixture_path = (
        ROOT
        / "docs"
        / "engineering"
        / "evidence"
        / "integrated-dry-run-decision-trace-2026-06-08.json"
    )

    expected = aigp_integrated_dry_run_gate._fixed_json_value(
        asdict(aigp_integrated_dry_run_gate.build_integrated_dry_run_decision_trace())
    )
    actual = json.loads(fixture_path.read_text(encoding="utf-8"))

    assert actual == expected
    assert actual["selected_action"]["command"]["kind"] == "BODY_VELOCITY"
    assert actual["selected_action"]["command_intent"]["mode"] == "TRACK_GATE"
    assert actual["reproducibility"]["issue"].endswith("/issues/21")
    candidate_ids = [action["id"] for action in actual["candidate_actions"]]
    score_ids = [score["action_id"] for score in actual["scores"]]
    assert candidate_ids == ["hold", "reacquire", "controller_output"]
    assert score_ids == candidate_ids
    assert len(candidate_ids) == len(set(candidate_ids))
    assert actual["selected_action"]["id"] == "controller_output"
