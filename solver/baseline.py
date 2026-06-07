"""Conservative first-run controller."""

from __future__ import annotations

from dataclasses import dataclass

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

        pose = state.gate_pose_camera
        if pose.z_forward_m <= 0.0:
            return ControlCommand(
                sim_time_ns=state.sim_time_ns,
                kind=CommandKind.REACQUIRE,
                source_frame_id=state.source_frame_id,
                yaw_rate_rad_s=0.2,
                reason="gate depth non-positive",
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
