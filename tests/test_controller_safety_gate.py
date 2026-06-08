from __future__ import annotations

import json
from pathlib import Path

from scripts import aigp_controller_safety_gate


def test_controller_safety_evidence_matches_generator() -> None:
    fixture_path = (
        Path(__file__).resolve().parents[1]
        / "docs"
        / "engineering"
        / "evidence"
        / "controller-safety-2026-06-08.json"
    )

    expected = aigp_controller_safety_gate.build_evidence()
    actual = json.loads(fixture_path.read_text(encoding="utf-8"))

    assert actual == expected
