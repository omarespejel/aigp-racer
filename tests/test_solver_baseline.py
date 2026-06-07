from __future__ import annotations

from estimation.state import StateEstimate
from mavlink.telemetry import Attitude, HighresImu
from perception.geometry import CameraPoseEstimate
from solver.baseline import ConservativeController
from solver.commands import CommandKind, CommandRateLimiter


def state(*, stale: bool, gate_pose: CameraPoseEstimate | None) -> StateEstimate:
    return StateEstimate(
        sim_time_ns=100,
        attitude=Attitude(1, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0),
        imu=HighresImu(1, (0.0, 0.0, -9.8), (0.0, 0.0, 0.0)),
        velocity=None,
        gate_pose_camera=gate_pose,
        gate_confidence=0.8 if gate_pose else None,
        stale=stale,
        status="test",
    )


def test_controller_holds_on_stale_state() -> None:
    command = ConservativeController().command(state(stale=True, gate_pose=None))

    assert command.kind == CommandKind.HOLD
    assert command.forward_m_s == 0.0


def test_controller_reacquires_when_gate_missing() -> None:
    command = ConservativeController().command(state(stale=False, gate_pose=None))

    assert command.kind == CommandKind.REACQUIRE
    assert command.yaw_rate_rad_s > 0.0


def test_controller_tracks_visible_gate_conservatively() -> None:
    command = ConservativeController().command(
        state(stale=False, gate_pose=CameraPoseEstimate(0.5, -0.25, 4.0))
    )

    assert command.kind == CommandKind.BODY_VELOCITY
    assert command.forward_m_s == 1.0
    assert command.right_m_s == 0.2
    assert command.down_m_s == -0.1


def test_command_rate_limiter_keeps_below_100hz() -> None:
    limiter = CommandRateLimiter(max_rate_hz=95.0)

    assert limiter.allow(0.0)
    assert not limiter.allow(0.005)
    assert limiter.allow(0.011)
