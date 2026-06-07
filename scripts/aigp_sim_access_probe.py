"""Emit deterministic simulator-access and next-step evidence for issue #4."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


def build_fixture_probe() -> dict[str, Any]:
    return {
        "schema_version": "aigp.sim_access_probe.v0",
        "snapshot_date": "2026-06-08",
        "github_issue": "https://github.com/omarespejel/aigp-racer/issues/4",
        "claim_boundary": (
            "deterministic public-source and repo-state fixture only; no team-portal login "
            "and no official simulator run"
        ),
        "sources_checked": [
            {
                "kind": "official_technical_spec",
                "label": "AI Grand Prix Technical Specification VADR-TS-002 Issue 00.02",
                "url": (
                    "https://www.theaigrandprix.com/wp-content/uploads/2026/05/"
                    "260508_Technical_Spec_0002.pdf"
                ),
                "used_for": [
                    "official MAVLink-over-UDP and vision-stream contract",
                    "camera, timing, gate, and runtime constraints",
                ],
            },
            {
                "kind": "official_site",
                "label": "AI Grand Prix public site",
                "url": "https://www.theaigrandprix.com/",
                "used_for": ["public competition context and team-portal direction"],
            },
            {
                "kind": "practice_harness_blog",
                "label": "Elodin AI Grand Prix race sim harness announcement",
                "url": "https://www.elodin.systems/post/elodin-ai-grand-prix-race-sim-harness",
                "used_for": ["practice-harness scope and official-contract caveats"],
            },
            {
                "kind": "practice_harness_repo",
                "label": "elodin-sys/ai-grand-prix",
                "url": "https://github.com/elodin-sys/ai-grand-prix",
                "used_for": ["practice-harness setup and solver contract"],
            },
        ],
        "official_access_status": {
            "team_portal_url": "https://teams.theaigrandprix.com/login",
            "public_unauthenticated_package_url_found": False,
            "team_portal_credentials_required": True,
            "official_sdk_or_simulator_package_recorded": False,
            "current_outcome": "NO_GO_PUBLIC_UNAUTHENTICATED_ACCESS",
        },
        "repo_readiness": {
            "vision_udp_reassembler": "implemented_and_tested",
            "decoded_message_telemetry_probe": "implemented_fixture_only",
            "binary_mavlink_decoder": "not_implemented",
            "official_jpeg_fixture": "not_available",
            "official_simulator_run": "not_available",
            "worldforge_race_episode_fixture": "implemented_fixture_only",
            "conservative_controller": "implemented_fixture_only",
        },
        "official_interface_targets": {
            "vision": {
                "transport": "UDP",
                "port": 5600,
                "encoding": "chunked JPEG",
                "frame_rate_hz": 30,
                "resolution_px": [640, 360],
                "header_bytes": 24,
            },
            "mavlink": {
                "transport": "UDP",
                "protocol": "MAVLink 2",
                "min_heartbeat_hz": 2,
                "command_rate_hz": "<100",
                "expected_sim_to_client": [
                    "HEARTBEAT",
                    "ATTITUDE",
                    "HIGHRES_IMU",
                    "TIMESYNC",
                ],
                "expected_client_to_sim": [
                    "SET_ATTITUDE_TARGET",
                    "SET_POSITION_TARGET_LOCAL_NED",
                ],
            },
        },
        "practice_harness_status": {
            "name": "Elodin AI Grand Prix practice harness",
            "repo": "https://github.com/elodin-sys/ai-grand-prix",
            "pinned_clone_commit_from_spec_notes": "13f9f9e3d5a3130f0ce0b65500d9f309cc1e11b2",
            "local_clone_path": "external/elodin-ai-grand-prix",
            "local_clone_policy": (
                "ignored local simulator drop; not required for deterministic repo gate"
            ),
            "use_now": (
                "practice-only smoke and adapter development while official access is blocked"
            ),
        },
        "known_practice_vs_official_differences": [
            {
                "surface": "vision_transport",
                "official": "UDP chunked JPEG on port 5600",
                "elodin": "in-process raw RGBA frame on SensorUpdate",
                "repo_action": "build adapter that feeds both sources into the same detector API",
            },
            {
                "surface": "control_transport",
                "official": "MAVLink 2 SET_ATTITUDE_TARGET or SET_POSITION_TARGET_LOCAL_NED",
                "elodin": "Betaflight SITL FDM/RC/PWM bridge",
                "repo_action": "keep command intent separate from transport-specific emission",
            },
            {
                "surface": "world_frame",
                "official": "NED at MAVLink boundary",
                "elodin": "ENU practice solver state",
                "repo_action": "add explicit frame tags to any practice adapter output",
            },
            {
                "surface": "telemetry",
                "official": "ATTITUDE, HIGHRES_IMU, TIMESYNC; velocity text remains ambiguous",
                "elodin": "body-frame IMU, world pose, baro, mag, optional frame",
                "repo_action": (
                    "run velocity probe only against official or captured decoded messages"
                ),
            },
        ],
        "next_actions": [
            {
                "priority": 1,
                "action": (
                    "log into team portal and record official simulator or SDK package version"
                ),
                "gate": "official package/version path exists and is recorded outside git if large",
            },
            {
                "priority": 2,
                "action": (
                    "run day-one telemetry probe against official decoded telemetry "
                    "or a captured fixture"
                ),
                "gate": (
                    "velocity probe returns AVAILABLE, NOT_AVAILABLE, or AMBIGUOUS "
                    "with message evidence"
                ),
            },
            {
                "priority": 3,
                "action": (
                    "add practice-only Elodin frame adapter if official access remains blocked"
                ),
                "gate": (
                    "raw RGBA practice frames enter the same detector boundary without "
                    "official-compatibility claims"
                ),
            },
            {
                "priority": 4,
                "action": (
                    "add JPEG decode timing only after official or synthetic JPEG fixtures exist"
                ),
                "gate": "p50/p95/p99 decode metrics are fixture-scoped and non-claiming",
            },
        ],
        "non_claims": [
            "not official simulator access evidence",
            "not official SDK compatibility evidence",
            "not a successful simulator run",
            "not binary MAVLink decoding evidence",
            "not a velocity availability claim",
            "not an Elodin fidelity claim",
            "not a speed, reliability, or latency claim",
        ],
    }


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--write-json", type=Path, required=True)
    args = parser.parse_args()

    write_json(args.write_json, build_fixture_probe())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
