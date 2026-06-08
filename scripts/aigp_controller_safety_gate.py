"""Regenerate conservative-controller safety evidence for issue #19."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from estimation.state import StateEstimate
from mavlink.command_intent import build_position_target_body_velocity_intent
from mavlink.telemetry import Attitude, HighresImu
from perception.geometry import CameraPoseEstimate
from solver.baseline import ConservativeController
from solver.commands import ControlCommand


def build_evidence() -> dict[str, Any]:
    controller = ConservativeController()
    scenarios = [
        _scenario(
            "nominal_centered_track",
            controller,
            _state(gate_pose=CameraPoseEstimate(0.0, 0.0, 3.0), status="READY"),
        ),
        _scenario(
            "gate_without_velocity_track",
            controller,
            _state(
                gate_pose=CameraPoseEstimate(0.0, 0.0, 3.0),
                status="GATE_WITHOUT_VELOCITY",
            ),
        ),
        _scenario(
            "stale_telemetry_hold",
            controller,
            _state(
                stale=True,
                gate_pose=CameraPoseEstimate(0.0, 0.0, 3.0),
                status="STALE_TELEMETRY",
            ),
        ),
        _scenario(
            "low_confidence_reacquire",
            controller,
            _state(
                gate_pose=CameraPoseEstimate(0.0, 0.0, 3.0),
                gate_confidence=0.1,
                status="READY",
            ),
        ),
        _scenario(
            "too_far_reacquire",
            controller,
            _state(gate_pose=CameraPoseEstimate(0.0, 0.0, 9.0), status="READY"),
        ),
        _scenario(
            "off_center_reacquire",
            controller,
            _state(gate_pose=CameraPoseEstimate(2.0, 0.0, 3.0), status="READY"),
        ),
        _scenario(
            "malformed_status_reacquire",
            controller,
            _state(
                gate_pose=CameraPoseEstimate(0.0, 0.0, 3.0),
                status="MALFORMED_GATE_OBSERVATION",
            ),
        ),
    ]
    tests = [
        "test_controller_holds_on_stale_state",
        "test_controller_reacquires_when_gate_missing",
        "test_controller_tracks_visible_gate_conservatively",
        "test_controller_tracks_gate_without_velocity_status",
        "test_controller_reacquires_on_non_commandable_status",
        "test_controller_reacquires_on_missing_gate_confidence",
        "test_controller_reacquires_on_low_gate_confidence",
        "test_controller_reacquires_on_invalid_gate_confidence",
        "test_controller_reacquires_on_non_positive_gate_depth",
        "test_controller_reacquires_outside_conservative_tracking_range",
        "test_controller_reacquires_on_non_finite_gate_pose",
        "test_controller_rejects_invalid_safety_thresholds",
    ]
    return _fixed_float_evidence(
        {
            "schema_version": "aigp.controller_safety_evidence.v0",
            "github_issue": "https://github.com/omarespejel/aigp-racer/issues/19",
            "claim_boundary": (
                "deterministic controller fixture only; not a simulator run, "
                "valid-run result, latency result, or reliability claim"
            ),
            "controller": {
                "module": "solver/baseline.py",
                "class": "ConservativeController",
                "min_gate_confidence": controller.min_gate_confidence,
                "min_track_depth_m": controller.min_track_depth_m,
                "max_track_depth_m": controller.max_track_depth_m,
                "max_center_offset_ratio": controller.max_center_offset_ratio,
                "max_forward_m_s": controller.max_forward_m_s,
                "max_lateral_m_s": controller.max_lateral_m_s,
                "max_vertical_m_s": controller.max_vertical_m_s,
            },
            "scenarios": scenarios,
            "go_gate_evidence": {
                "stale_state_holds": True,
                "degraded_state_reacquires": True,
                "missing_or_low_confidence_reacquires": True,
                "out_of_range_depth_reacquires": True,
                "off_center_gate_reacquires": True,
                "nominal_centered_gate_tracks": True,
                "command_intent_mapping_remains_valid": True,
            },
            "tests": [{"path": "tests/test_solver_baseline.py", "name": name} for name in tests],
            "commands": [
                "uv run --python 3.14 --with pytest python -m pytest "
                "tests/test_solver_baseline.py tests/test_mavlink_command_intent.py",
                "./scripts/aigp_local_gate.sh",
            ],
            "validation": {
                "generator_executes_tests": False,
                "listed_go_gate_test_count": len(tests),
                "status_source": "external local or CI gate; this generator only writes evidence",
            },
            "non_claims": [
                "not an official simulator run",
                "not an Elodin practice run",
                "not a valid-run result",
                "not latency, lap-time, or reliability evidence",
                "not a learned-policy or AutoRaceEvolve result",
                "not proof that SET_POSITION_TARGET_LOCAL_NED is sufficient for Round 1",
            ],
        }
    )


def _state(
    *,
    gate_pose: CameraPoseEstimate | None,
    gate_confidence: float | None = 0.8,
    stale: bool = False,
    status: str,
) -> StateEstimate:
    return StateEstimate(
        sim_time_ns=100,
        source_frame_id=7,
        attitude=Attitude(1, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0),
        imu=HighresImu(1, (0.0, 0.0, -9.8), (0.0, 0.0, 0.0)),
        velocity=None,
        gate_pose_camera=gate_pose,
        gate_confidence=gate_confidence if gate_pose else None,
        stale=stale,
        status=status,
    )


def _scenario(
    name: str,
    controller: ConservativeController,
    state: StateEstimate,
) -> dict[str, Any]:
    command = controller.command(state)
    intent = build_position_target_body_velocity_intent(command)
    return {
        "name": name,
        "state": _state_summary(state),
        "command": _command_summary(command),
        "command_intent": intent.as_dict(),
    }


def _state_summary(state: StateEstimate) -> dict[str, Any]:
    return {
        "sim_time_ns": state.sim_time_ns,
        "source_frame_id": state.source_frame_id,
        "status": state.status,
        "stale": state.stale,
        "gate_confidence": state.gate_confidence,
        "gate_pose_camera_m": (
            None
            if state.gate_pose_camera is None
            else {
                "x_right_m": state.gate_pose_camera.x_right_m,
                "y_down_m": state.gate_pose_camera.y_down_m,
                "z_forward_m": state.gate_pose_camera.z_forward_m,
            }
        ),
    }


def _command_summary(command: ControlCommand) -> dict[str, Any]:
    return {
        "sim_time_ns": command.sim_time_ns,
        "kind": command.kind.value,
        "source_frame_id": command.source_frame_id,
        "forward_m_s": command.forward_m_s,
        "right_m_s": command.right_m_s,
        "down_m_s": command.down_m_s,
        "yaw_rate_rad_s": command.yaw_rate_rad_s,
        "reason": command.reason,
    }


def _fixed_float_evidence(value: Any) -> Any:
    if isinstance(value, float):
        return f"{value:.6f}"
    if isinstance(value, list):
        return [_fixed_float_evidence(item) for item in value]
    if isinstance(value, tuple):
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
