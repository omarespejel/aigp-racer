"""Emit deterministic AI Grand Prix profile fixtures."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

SECTIONS = (
    "udp_jpeg_reassembly",
    "telemetry_parse",
    "gate_detection",
    "pnp_pose",
    "state_estimation",
    "planning",
    "control_command_emission",
    "offline_evidence_conversion",
)


def build_fixture_profile() -> dict[str, Any]:
    empty_section = {
        "event_count": 0,
        "p50_ms": None,
        "p95_ms": None,
        "p99_ms": None,
    }
    return {
        "schema_version": "aigp.profile.v0",
        "source": "scripts/aigp_profile_gate.py fixture mode",
        "claim_boundary": (
            "deterministic fixture only; no simulator run, no latency measurement, no speedup claim"
        ),
        "non_claims": [
            "not official simulator compatibility evidence",
            "not a latency benchmark",
            "not a reliability result",
            "not a speedup claim",
            "not physical-drone transfer evidence",
        ],
        "profile": {section: dict(empty_section) for section in SECTIONS},
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

    write_json(args.write_json, build_fixture_profile())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
