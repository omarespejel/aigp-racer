"""Regenerate command-intent evidence for issue #14."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from mavlink.command_intent import build_position_target_body_velocity_intent
from solver.commands import CommandKind, ControlCommand


def build_evidence() -> dict[str, Any]:
    sample_intents = [
        build_position_target_body_velocity_intent(
            ControlCommand(
                sim_time_ns=120,
                kind=CommandKind.BODY_VELOCITY,
                source_frame_id=9,
                forward_m_s=1.25,
                right_m_s=-0.25,
                down_m_s=0.1,
                yaw_rate_rad_s=0.05,
                reason="tracking visible gate",
            )
        ).as_dict(),
        build_position_target_body_velocity_intent(
            ControlCommand(
                sim_time_ns=121,
                kind=CommandKind.HOLD,
                source_frame_id=9,
                reason="stale telemetry",
            )
        ).as_dict(),
        build_position_target_body_velocity_intent(
            ControlCommand(
                sim_time_ns=122,
                kind=CommandKind.REACQUIRE,
                source_frame_id=10,
                yaw_rate_rad_s=0.2,
                reason="no gate observation",
            )
        ).as_dict(),
    ]
    test_records = [
        "test_body_velocity_command_maps_to_official_message_intent",
        "test_hold_command_zeroes_velocity_and_yaw_rate",
        "test_reacquire_command_preserves_conservative_yaw_intent",
        "test_command_intent_rejects_non_finite_control_fields",
        "test_command_intent_rejects_bool_control_fields",
        "test_command_intent_rejects_invalid_timestamps",
        "test_command_intent_rejects_bool_source_frame_id",
        "test_command_intent_evidence_uses_fixed_float_strings",
        "test_command_intent_evidence_writer_formats_raw_floats",
        "test_command_intent_as_dict_is_stable_and_json_shaped",
    ]
    return _fixed_float_evidence(
        {
            "schema_version": "aigp.command_intent_evidence.v1",
            "github_issue": "https://github.com/omarespejel/aigp-racer/issues/14",
            "claim_boundary": (
                "deterministic command-intent fixture only; not binary MAVLink, MAVSDK, "
                "or official simulator compatibility evidence"
            ),
            "official_spec_reference": {
                "name": "VADR-TS-002",
                "issue": "00.02",
                "date": "2026-05-08",
                "url": (
                    "https://www.theaigrandprix.com/wp-content/uploads/2026/05/"
                    "260508_Technical_Spec_0002.pdf"
                ),
            },
            "mapping": {
                "source_module": "solver/commands.py",
                "intent_module": "mavlink/command_intent.py",
                "message_name": "SET_POSITION_TARGET_LOCAL_NED",
                "frame": "MAV_FRAME_BODY_NED",
                "intent_profile": "body_ned_velocity_plus_yaw_rate",
                "serialized_by_this_artifact": False,
                "float_format": "six_decimal_strings_for_evidence_only",
            },
            "sample_intents": sample_intents,
            "go_gate_evidence": {
                "body_velocity_maps_to_message_intent": True,
                "hold_zeroes_velocity_and_yaw": True,
                "reacquire_preserves_yaw_intent": True,
                "rejects_non_finite_control_fields": True,
                "rejects_bool_control_fields": True,
                "rejects_invalid_timestamps": True,
                "requires_live_mavsdk": False,
                "requires_official_simulator": False,
            },
            "tests": [
                {"path": "tests/test_mavlink_command_intent.py", "name": name}
                for name in test_records
            ],
            "commands": [
                "uv run --python 3.14 --with jsonschema --with pyyaml --with ruff --with pytest "
                "python -m pytest tests/test_mavlink_command_intent.py "
                "tests/test_solver_baseline.py",
                "./scripts/aigp_local_gate.sh",
            ],
            "validation": {
                "generator_executes_tests": False,
                "listed_go_gate_test_count": len(test_records),
                "status_source": "external local or CI gate; this generator only writes evidence",
            },
            "non_claims": [
                "not binary MAVLink serialization evidence",
                "not MAVSDK integration evidence",
                "not official simulator compatibility evidence",
                "not a valid-run result",
                "not latency, lap-time, or reliability evidence",
                "not proof that SET_POSITION_TARGET_LOCAL_NED is the final racing command path",
            ],
        }
    )


def _fixed_float_evidence(value: Any) -> Any:
    if isinstance(value, float):
        return f"{value:.6f}"
    if isinstance(value, list):
        return [_fixed_float_evidence(item) for item in value]
    if isinstance(value, dict):
        return {key: _fixed_float_evidence(item) for key, item in value.items()}
    return value


def write_evidence_json(path: Path, payload: dict[str, Any]) -> None:
    fixed_payload = _fixed_float_evidence(payload)
    _reject_float_values(fixed_payload)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(fixed_payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def _reject_float_values(value: Any, path: str = "$") -> None:
    if isinstance(value, float):
        raise ValueError(f"evidence contains unformatted float at {path}")
    if isinstance(value, list):
        for index, item in enumerate(value):
            _reject_float_values(item, f"{path}[{index}]")
    elif isinstance(value, dict):
        for key, item in value.items():
            _reject_float_values(item, f"{path}.{key}")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--write-json", type=Path, required=True)
    args = parser.parse_args()

    write_evidence_json(args.write_json, build_evidence())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
