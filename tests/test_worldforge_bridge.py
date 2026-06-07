from __future__ import annotations

import json
from pathlib import Path

from worldforge_bridge.schema import (
    build_bootstrap_decision_trace,
    build_bootstrap_episode,
    to_json_dict,
)

ROOT = Path(__file__).resolve().parents[1]


def test_bootstrap_episode_fixture_matches_generator() -> None:
    fixture_path = (
        ROOT / "docs" / "engineering" / "evidence" / "race-episode-fixture-2026-06-08.json"
    )
    actual = json.loads(fixture_path.read_text(encoding="utf-8"))
    expected = json.loads(json.dumps(to_json_dict(build_bootstrap_episode())))

    assert actual == expected
    assert "not a valid-run result" in actual["non_claims"]


def test_bootstrap_decision_trace_fixture_matches_generator() -> None:
    fixture_path = (
        ROOT / "docs" / "engineering" / "evidence" / "decision-trace-fixture-2026-06-08.json"
    )
    actual = json.loads(fixture_path.read_text(encoding="utf-8"))
    expected = json.loads(json.dumps(to_json_dict(build_bootstrap_decision_trace())))

    assert actual == expected
    assert "not generated in the live flight hot path" in actual["non_claims"]
