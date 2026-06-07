from __future__ import annotations

import json
from pathlib import Path

from scripts import aigp_profile_gate


def test_profile_fixture_matches_generator() -> None:
    fixture_path = (
        Path(__file__).resolve().parents[1]
        / "docs"
        / "engineering"
        / "evidence"
        / "aigp-profile-fixture-2026-06-08.json"
    )
    expected = aigp_profile_gate.build_fixture_profile()
    actual = json.loads(fixture_path.read_text(encoding="utf-8"))
    assert actual == expected
