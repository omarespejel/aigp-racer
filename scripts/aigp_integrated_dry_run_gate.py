"""Regenerate integrated dry-run RaceEpisode and DecisionTrace evidence."""

from __future__ import annotations

import argparse
import json
from dataclasses import asdict
from pathlib import Path
from typing import Any

from estimation.state import EstimatorInputs, MinimalStateEstimator, StateEstimate
from mavlink.command_intent import build_position_target_body_velocity_intent
from mavlink.telemetry import Attitude, HighresImu
from perception.detector import GateDetectionResult, Round1ColorGateDetector
from solver.baseline import ConservativeController
from solver.commands import CommandKind, ControlCommand
from worldforge_bridge.schema import DecisionTrace, EpisodeEvent, RaceEpisode

ROOT = Path(__file__).resolve().parents[1]
EPISODE_PATH = (
    ROOT / "docs" / "engineering" / "evidence" / "integrated-dry-run-episode-2026-06-08.json"
)
TRACE_PATH = (
    ROOT / "docs" / "engineering" / "evidence" / "integrated-dry-run-decision-trace-2026-06-08.json"
)

SIM_TIME_NS = 33_333_333
SOURCE_FRAME_ID = 1
IMAGE_WIDTH_PX = 640
IMAGE_HEIGHT_PX = 360

NON_CLAIMS = (
    "not official simulator compatibility evidence",
    "not a valid-run result",
    "not a lap-time, latency, or reliability claim",
    "not a learned-policy result",
    "not physical-drone transfer evidence",
    "not proof that screen-space detector corners are physical gate-corner labels",
)


def build_integrated_dry_run_episode() -> RaceEpisode:
    chain = _run_chain()
    return RaceEpisode(
        schema_version="aigp.race_episode.v0",
        episode_id="integrated-dry-run-2026-06-08",
        source="deterministic local synthetic frame",
        claim_boundary=(
            "offline dry-run fixture only; detector, estimator, controller, and command-intent "
            "modules are real, but no simulator or MAVLink transport is exercised"
        ),
        non_claims=NON_CLAIMS,
        events=(
            EpisodeEvent(
                event_type="synthetic_frame",
                sim_time_ns=SIM_TIME_NS,
                source_frame_id=SOURCE_FRAME_ID,
                payload={
                    "image_size_px": [IMAGE_WIDTH_PX, IMAGE_HEIGHT_PX],
                    "gate_highlight_bbox_px": [240, 100, 400, 260],
                    "pixel_contract": "RGB rows; magenta rectangle on black background",
                },
            ),
            EpisodeEvent(
                event_type="gate_detection_result",
                sim_time_ns=SIM_TIME_NS,
                source_frame_id=SOURCE_FRAME_ID,
                payload=_detection_summary(chain["detection"]),
            ),
            EpisodeEvent(
                event_type="state_estimate",
                sim_time_ns=SIM_TIME_NS,
                source_frame_id=SOURCE_FRAME_ID,
                payload=_state_summary(chain["state"]),
            ),
            EpisodeEvent(
                event_type="control_command",
                sim_time_ns=SIM_TIME_NS,
                source_frame_id=SOURCE_FRAME_ID,
                payload=_command_summary(chain["command"]),
            ),
            EpisodeEvent(
                event_type="command_intent",
                sim_time_ns=SIM_TIME_NS,
                source_frame_id=SOURCE_FRAME_ID,
                payload=chain["intent"].as_dict(),
            ),
        ),
    )


def build_integrated_dry_run_decision_trace() -> DecisionTrace:
    chain = _run_chain()
    command = chain["command"]
    intent = chain["intent"]
    selected_action = _identified_action("controller_output", _command_summary(command))
    hold_action = _identified_action(
        "hold",
        _command_summary(
            ControlCommand(
                sim_time_ns=SIM_TIME_NS,
                kind=CommandKind.HOLD,
                source_frame_id=SOURCE_FRAME_ID,
                reason="candidate baseline hold",
            )
        ),
    )
    reacquire_action = _identified_action(
        "reacquire",
        _command_summary(
            ControlCommand(
                sim_time_ns=SIM_TIME_NS,
                kind=CommandKind.REACQUIRE,
                source_frame_id=SOURCE_FRAME_ID,
                yaw_rate_rad_s=0.2,
                reason="candidate reacquire",
            )
        ),
    )
    return DecisionTrace(
        schema_version="decision_trace.v1-draft",
        trace_id="integrated-dry-run-control-decision-2026-06-08",
        episode_id="integrated-dry-run-2026-06-08",
        observation={
            "detector": _detection_summary(chain["detection"]),
            "state": _state_summary(chain["state"]),
        },
        goal={
            "objective": "conservative first valid-run bootstrap",
            "local_goal": "emit a bounded command toward a detected centered gate",
        },
        candidate_actions=(hold_action, reacquire_action, selected_action),
        scores=(
            {"action_id": "hold", "score": 0.1, "reason": "safe but no gate progress"},
            {"action_id": "reacquire", "score": 0.2, "reason": "unnecessary with detected gate"},
            {
                "action_id": "controller_output",
                "score": 0.6,
                "reason": "actual controller output for commandable dry-run state",
            },
        ),
        selected_action={
            "id": "controller_output",
            "command": selected_action,
            "command_intent": intent.as_dict(),
        },
        predicted_outcome={
            "source": "analytic dry-run",
            "expected_behavior": "move toward visible gate center without speed claim",
        },
        measured_or_analytic_outcome={
            "source": "module-chain dry-run",
            "detected": chain["detection"].detected,
            "state_status": chain["state"].status,
            "command_kind": command.kind.value,
            "intent_mode": intent.mode,
        },
        reproducibility={
            "generator": "scripts/aigp_integrated_dry_run_gate.py",
            "issue": "https://github.com/omarespejel/aigp-racer/issues/21",
            "followup_depth_basis_issue": "https://github.com/omarespejel/aigp-racer/issues/23",
            "followup_latency_issue": "https://github.com/omarespejel/aigp-racer/issues/24",
        },
        non_claims=NON_CLAIMS,
    )


def _run_chain() -> dict[str, Any]:
    detector = Round1ColorGateDetector()
    detection = detector.analyze(
        _synthetic_frame(),
        sim_time_ns=SIM_TIME_NS,
        source_frame_id=SOURCE_FRAME_ID,
    )
    estimator = MinimalStateEstimator()
    state = estimator.estimate(
        EstimatorInputs(
            sim_time_ns=SIM_TIME_NS,
            attitude=Attitude(
                time_boot_ms=33,
                roll_rad=0.0,
                pitch_rad=0.0,
                yaw_rad=0.0,
                rollspeed_rad_s=0.0,
                pitchspeed_rad_s=0.0,
                yawspeed_rad_s=0.0,
            ),
            imu=HighresImu(
                time_usec=33_333,
                acceleration_m_s2=(0.0, 0.0, -9.8),
                gyro_rad_s=(0.0, 0.0, 0.0),
            ),
            velocity=None,
            gate_observation=detection.observation,
            telemetry_age_ns=0,
        )
    )
    command = ConservativeController().command(state)
    intent = build_position_target_body_velocity_intent(command)
    return {
        "detection": detection,
        "state": state,
        "command": command,
        "intent": intent,
    }


def _synthetic_frame() -> list[list[tuple[int, int, int]]]:
    image = [[(0, 0, 0) for _ in range(IMAGE_WIDTH_PX)] for _ in range(IMAGE_HEIGHT_PX)]
    for v_px in range(100, 261):
        for u_px in range(240, 401):
            image[v_px][u_px] = (255, 0, 255)
    return image


def _detection_summary(detection: GateDetectionResult) -> dict[str, Any]:
    return {
        "status": detection.status.value,
        "source": detection.source,
        "detected": detection.detected,
        "mask_pixels": detection.mask_pixels,
        "confidence": detection.confidence,
        "observation": None
        if detection.observation is None
        else {
            "confidence": detection.observation.confidence,
            "source": detection.observation.source,
            "sim_time_ns": detection.observation.sim_time_ns,
            "source_frame_id": detection.observation.source_frame_id,
            "measurement_basis": detection.observation.measurement_basis.value,
            "corners_px": [
                {"u_px": point.u_px, "v_px": point.v_px} for point in detection.observation.corners
            ],
            "corner_uncertainty_px": list(detection.observation.corner_uncertainty_px or ()),
        },
    }


def _state_summary(state: StateEstimate) -> dict[str, Any]:
    return {
        "sim_time_ns": state.sim_time_ns,
        "source_frame_id": state.source_frame_id,
        "status": state.status,
        "stale": state.stale,
        "gate_confidence": state.gate_confidence,
        "gate_pose_camera_m": None
        if state.gate_pose_camera is None
        else {
            "x_right_m": state.gate_pose_camera.x_right_m,
            "y_down_m": state.gate_pose_camera.y_down_m,
            "z_forward_m": state.gate_pose_camera.z_forward_m,
        },
        "gate_measurement_mode": None
        if state.gate_measurement is None
        else state.gate_measurement.mode.value,
        "gate_measurement_basis": None
        if state.gate_measurement is None
        else state.gate_measurement.measurement_basis.value,
        "gate_measurement_has_full_planar_pose": None
        if state.gate_measurement is None
        else state.gate_measurement.has_full_planar_pose,
        "velocity_available": state.velocity is not None,
        "degraded_reason": state.degraded_reason,
        "diagnostic_count": len(state.diagnostics),
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


def _identified_action(action_id: str, command_summary: dict[str, Any]) -> dict[str, Any]:
    return {"id": action_id, **command_summary}


def _fixed_json_value(value: Any) -> Any:
    if isinstance(value, float):
        return f"{value:.6f}"
    if isinstance(value, tuple | list):
        return [_fixed_json_value(item) for item in value]
    if isinstance(value, dict):
        return {key: _fixed_json_value(item) for key, item in value.items()}
    return value


def _write_json(path: Path, value: RaceEpisode | DecisionTrace) -> None:
    payload = _fixed_json_value(asdict(value))
    _reject_float_values(payload)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _reject_float_values(value: Any, path: str = "$") -> None:
    if isinstance(value, float):
        raise ValueError(f"evidence contains unformatted float at {path}")
    if isinstance(value, list):
        for index, item in enumerate(value):
            _reject_float_values(item, f"{path}[{index}]")
    elif isinstance(value, dict):
        for key, item in value.items():
            _reject_float_values(item, f"{path}.{key}")


def write_evidence(*, episode_path: Path = EPISODE_PATH, trace_path: Path = TRACE_PATH) -> None:
    _write_json(episode_path, build_integrated_dry_run_episode())
    _write_json(trace_path, build_integrated_dry_run_decision_trace())


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--write-json", action="store_true")
    args = parser.parse_args()
    if not args.write_json:
        parser.error("--write-json is required")
    write_evidence()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
