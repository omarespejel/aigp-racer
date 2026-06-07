from __future__ import annotations

import json
from pathlib import Path

from scripts import aigp_sim_access_probe


def test_sim_access_probe_fixture_matches_generator() -> None:
    fixture_path = (
        Path(__file__).resolve().parents[1]
        / "docs"
        / "engineering"
        / "evidence"
        / "sim-access-probe-2026-06-08.json"
    )
    expected = aigp_sim_access_probe.build_fixture_probe()
    actual = json.loads(fixture_path.read_text(encoding="utf-8"))
    assert actual == expected


def test_sim_access_probe_keeps_official_access_as_non_claim() -> None:
    probe = aigp_sim_access_probe.build_fixture_probe()

    assert (
        probe["official_access_status"]["current_outcome"] == "NO_GO_PUBLIC_UNAUTHENTICATED_ACCESS"
    )
    assert not probe["official_access_status"]["official_sdk_or_simulator_package_recorded"]
    assert "not official simulator access evidence" in probe["non_claims"]
    assert probe["repo_readiness"]["binary_mavlink_decoder"] == "not_implemented"


def test_sim_access_probe_records_practice_harness_divergences() -> None:
    probe = aigp_sim_access_probe.build_fixture_probe()
    differences = {
        difference["surface"]: difference
        for difference in probe["known_practice_vs_official_differences"]
    }

    assert differences["vision_transport"]["official"] == "UDP chunked JPEG on port 5600"
    assert differences["vision_transport"]["elodin"] == "in-process raw RGBA frame on SensorUpdate"
    assert differences["world_frame"]["official"] == "NED at MAVLink boundary"
    assert differences["world_frame"]["elodin"] == "ENU practice solver state"
