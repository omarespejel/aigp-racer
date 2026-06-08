"""Conservative first-run controller."""

from __future__ import annotations

import math
from dataclasses import dataclass
from numbers import Real

from estimation.state import StateEstimate
from solver.commands import CommandKind, ControlCommand


@dataclass(frozen=True)
class ConservativeController:
    """Move cautiously toward the visible gate center."""

    max_forward_m_s: float = 1.0
    min_forward_m_s: float = 0.2
    lateral_gain: float = 0.4
    vertical_gain: float = 0.4
    max_lateral_m_s: float = 0.5
    max_vertical_m_s: float = 0.5
    min_gate_confidence: float = 0.35
    min_track_depth_m: float = 0.75
    max_track_depth_m: float = 8.0
    max_center_offset_ratio: float = 0.45

    def __post_init__(self) -> None:
        _require_positive_real("max_forward_m_s", self.max_forward_m_s)
        _require_positive_real("min_forward_m_s", self.min_forward_m_s)
        if self.min_forward_m_s > self.max_forward_m_s:
            raise ValueError("min_forward_m_s must be <= max_forward_m_s")
        _require_non_negative_real("lateral_gain", self.lateral_gain)
        _require_non_negative_real("vertical_gain", self.vertical_gain)
        _require_non_negative_real("max_lateral_m_s", self.max_lateral_m_s)
        _require_non_negative_real("max_vertical_m_s", self.max_vertical_m_s)
        _require_probability("min_gate_confidence", self.min_gate_confidence)
        _require_positive_real("min_track_depth_m", self.min_track_depth_m)
        _require_positive_real("max_track_depth_m", self.max_track_depth_m)
        if self.min_track_depth_m >= self.max_track_depth_m:
            raise ValueError("min_track_depth_m must be < max_track_depth_m")
        _require_positive_real("max_center_offset_ratio", self.max_center_offset_ratio)

    def command(self, state: StateEstimate) -> ControlCommand:
        if state.stale:
            return ControlCommand(
                sim_time_ns=state.sim_time_ns,
                kind=CommandKind.HOLD,
                source_frame_id=state.source_frame_id,
                reason="stale telemetry",
            )
        if state.gate_pose_camera is None:
            return ControlCommand(
                sim_time_ns=state.sim_time_ns,
                kind=CommandKind.REACQUIRE,
                source_frame_id=state.source_frame_id,
                yaw_rate_rad_s=0.2,
                reason="no gate observation",
            )
        if state.status not in {"READY", "GATE_WITHOUT_VELOCITY"}:
            return ControlCommand(
                sim_time_ns=state.sim_time_ns,
                kind=CommandKind.REACQUIRE,
                source_frame_id=state.source_frame_id,
                yaw_rate_rad_s=0.2,
                reason=f"state not commandable: {state.status}",
            )
        if state.gate_confidence is None:
            return ControlCommand(
                sim_time_ns=state.sim_time_ns,
                kind=CommandKind.REACQUIRE,
                source_frame_id=state.source_frame_id,
                yaw_rate_rad_s=0.2,
                reason="gate confidence missing",
            )
        if not _is_probability(state.gate_confidence):
            return ControlCommand(
                sim_time_ns=state.sim_time_ns,
                kind=CommandKind.REACQUIRE,
                source_frame_id=state.source_frame_id,
                yaw_rate_rad_s=0.2,
                reason="gate confidence invalid",
            )
        if state.gate_confidence < self.min_gate_confidence:
            return ControlCommand(
                sim_time_ns=state.sim_time_ns,
                kind=CommandKind.REACQUIRE,
                source_frame_id=state.source_frame_id,
                yaw_rate_rad_s=0.2,
                reason="gate confidence below threshold",
            )

        pose = state.gate_pose_camera
        if not all(
            math.isfinite(value) for value in (pose.x_right_m, pose.y_down_m, pose.z_forward_m)
        ):
            return ControlCommand(
                sim_time_ns=state.sim_time_ns,
                kind=CommandKind.REACQUIRE,
                source_frame_id=state.source_frame_id,
                yaw_rate_rad_s=0.2,
                reason="gate pose non-finite",
            )
        if pose.z_forward_m <= 0.0:
            return ControlCommand(
                sim_time_ns=state.sim_time_ns,
                kind=CommandKind.REACQUIRE,
                source_frame_id=state.source_frame_id,
                yaw_rate_rad_s=0.2,
                reason="gate depth non-positive",
            )
        if pose.z_forward_m < self.min_track_depth_m:
            return ControlCommand(
                sim_time_ns=state.sim_time_ns,
                kind=CommandKind.REACQUIRE,
                source_frame_id=state.source_frame_id,
                yaw_rate_rad_s=0.2,
                reason="gate depth below tracking range",
            )
        if pose.z_forward_m > self.max_track_depth_m:
            return ControlCommand(
                sim_time_ns=state.sim_time_ns,
                kind=CommandKind.REACQUIRE,
                source_frame_id=state.source_frame_id,
                yaw_rate_rad_s=0.2,
                reason="gate depth above tracking range",
            )
        if max(abs(pose.x_right_m), abs(pose.y_down_m)) / pose.z_forward_m > (
            self.max_center_offset_ratio
        ):
            return ControlCommand(
                sim_time_ns=state.sim_time_ns,
                kind=CommandKind.REACQUIRE,
                source_frame_id=state.source_frame_id,
                yaw_rate_rad_s=0.2,
                reason="gate center offset above tracking range",
            )
        forward = min(
            self.max_forward_m_s,
            max(self.min_forward_m_s, 0.25 * pose.z_forward_m),
        )
        right = _clamp(
            self.lateral_gain * pose.x_right_m,
            -self.max_lateral_m_s,
            self.max_lateral_m_s,
        )
        down = _clamp(
            self.vertical_gain * pose.y_down_m,
            -self.max_vertical_m_s,
            self.max_vertical_m_s,
        )
        return ControlCommand(
            sim_time_ns=state.sim_time_ns,
            kind=CommandKind.BODY_VELOCITY,
            source_frame_id=state.source_frame_id,
            forward_m_s=forward,
            right_m_s=right,
            down_m_s=down,
            reason="tracking visible gate",
        )


def _clamp(value: float, lower: float, upper: float) -> float:
    return max(lower, min(upper, value))


def _is_finite_real(value: object) -> bool:
    return not isinstance(value, bool) and isinstance(value, Real) and math.isfinite(float(value))


def _is_probability(value: object) -> bool:
    return _is_finite_real(value) and 0.0 <= float(value) <= 1.0


def _require_positive_real(name: str, value: object) -> None:
    if not _is_finite_real(value) or float(value) <= 0.0:
        raise ValueError(f"{name} must be a positive finite real")


def _require_non_negative_real(name: str, value: object) -> None:
    if not _is_finite_real(value) or float(value) < 0.0:
        raise ValueError(f"{name} must be a non-negative finite real")


def _require_probability(name: str, value: object) -> None:
    if not _is_probability(value):
        raise ValueError(f"{name} must be a probability in [0, 1]")
