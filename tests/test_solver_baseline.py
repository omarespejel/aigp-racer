from __future__ import annotations

import pytest

from estimation.state import StateEstimate
from mavlink.telemetry import Attitude, HighresImu
from perception.geometry import CameraPoseEstimate
from solver.baseline import ConservativeController
from solver.commands import CommandKind, CommandRateLimiter


def state(
    *,
    stale: bool,
    gate_pose: CameraPoseEstimate | None,
    gate_confidence: float | None = 0.8,
    status: str | None = None,
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
        status=status or ("STALE_TELEMETRY" if stale else "READY" if gate_pose else "NO_GATE"),
    )


def test_controller_holds_on_stale_state() -> None:
    command = ConservativeController().command(state(stale=True, gate_pose=None))

    assert command.kind == CommandKind.HOLD
    assert command.forward_m_s == 0.0
    assert command.source_frame_id == 7


def test_controller_reacquires_when_gate_missing() -> None:
    command = ConservativeController().command(state(stale=False, gate_pose=None))

    assert command.kind == CommandKind.REACQUIRE
    assert command.yaw_rate_rad_s > 0.0


def test_controller_tracks_visible_gate_conservatively() -> None:
    command = ConservativeController().command(
        state(stale=False, gate_pose=CameraPoseEstimate(0.5, -0.25, 4.0))
    )

    assert command.kind == CommandKind.BODY_VELOCITY
    assert command.source_frame_id == 7
    assert command.forward_m_s == 1.0
    assert command.right_m_s == 0.2
    assert command.down_m_s == -0.1


def test_controller_tracks_gate_without_velocity_status() -> None:
    command = ConservativeController().command(
        state(
            stale=False,
            gate_pose=CameraPoseEstimate(0.0, 0.0, 3.0),
            status="GATE_WITHOUT_VELOCITY",
        )
    )

    assert command.kind == CommandKind.BODY_VELOCITY
    assert command.forward_m_s > 0.0


@pytest.mark.parametrize(
    "status",
    [
        "MALFORMED_GATE_OBSERVATION",
        "NO_GATE",
    ],
)
def test_controller_reacquires_on_non_commandable_status(status: str) -> None:
    command = ConservativeController().command(
        state(
            stale=False,
            gate_pose=CameraPoseEstimate(0.0, 0.0, 3.0),
            status=status,
        )
    )

    assert command.kind == CommandKind.REACQUIRE
    assert command.reason == f"state not commandable: {status}"
    assert command.forward_m_s == 0.0


def test_controller_reacquires_on_missing_gate_confidence() -> None:
    command = ConservativeController().command(
        state(
            stale=False,
            gate_pose=CameraPoseEstimate(0.0, 0.0, 3.0),
            gate_confidence=None,
        )
    )

    assert command.kind == CommandKind.REACQUIRE
    assert command.reason == "gate confidence missing"
    assert command.forward_m_s == 0.0


@pytest.mark.parametrize("gate_confidence", [0.0, 0.34])
def test_controller_reacquires_on_low_gate_confidence(gate_confidence: float) -> None:
    command = ConservativeController().command(
        state(
            stale=False,
            gate_pose=CameraPoseEstimate(0.0, 0.0, 3.0),
            gate_confidence=gate_confidence,
        )
    )

    assert command.kind == CommandKind.REACQUIRE
    assert command.reason == "gate confidence below threshold"
    assert command.forward_m_s == 0.0


@pytest.mark.parametrize("gate_confidence", [float("nan"), float("inf"), -0.1, 1.1])
def test_controller_reacquires_on_invalid_gate_confidence(gate_confidence: float) -> None:
    command = ConservativeController().command(
        state(
            stale=False,
            gate_pose=CameraPoseEstimate(0.0, 0.0, 3.0),
            gate_confidence=gate_confidence,
        )
    )

    assert command.kind == CommandKind.REACQUIRE
    assert command.reason == "gate confidence invalid"
    assert command.forward_m_s == 0.0


def test_controller_reacquires_on_non_positive_gate_depth() -> None:
    command = ConservativeController().command(
        state(stale=False, gate_pose=CameraPoseEstimate(0.0, 0.0, 0.0))
    )

    assert command.kind == CommandKind.REACQUIRE
    assert command.forward_m_s == 0.0
    assert command.reason == "gate depth non-positive"


@pytest.mark.parametrize(
    ("gate_pose", "reason"),
    [
        (CameraPoseEstimate(0.0, 0.0, 0.5), "gate depth below tracking range"),
        (CameraPoseEstimate(0.0, 0.0, 9.0), "gate depth above tracking range"),
        (CameraPoseEstimate(2.0, 0.0, 3.0), "gate center offset above tracking range"),
        (CameraPoseEstimate(0.0, -2.0, 3.0), "gate center offset above tracking range"),
    ],
)
def test_controller_reacquires_outside_conservative_tracking_range(
    gate_pose: CameraPoseEstimate,
    reason: str,
) -> None:
    command = ConservativeController().command(state(stale=False, gate_pose=gate_pose))

    assert command.kind == CommandKind.REACQUIRE
    assert command.forward_m_s == 0.0
    assert command.reason == reason


@pytest.mark.parametrize(
    "gate_pose",
    [
        CameraPoseEstimate(float("nan"), 0.0, 3.0),
        CameraPoseEstimate(0.0, float("inf"), 3.0),
        CameraPoseEstimate(0.0, 0.0, float("nan")),
    ],
)
def test_controller_reacquires_on_non_finite_gate_pose(gate_pose: CameraPoseEstimate) -> None:
    command = ConservativeController().command(state(stale=False, gate_pose=gate_pose))

    assert command.kind == CommandKind.REACQUIRE
    assert command.forward_m_s == 0.0
    assert command.reason == "gate pose non-finite"


@pytest.mark.parametrize(
    "kwargs",
    [
        {"max_forward_m_s": 0.0},
        {"min_forward_m_s": 0.0},
        {"min_forward_m_s": 2.0, "max_forward_m_s": 1.0},
        {"lateral_gain": -0.1},
        {"vertical_gain": -0.1},
        {"max_lateral_m_s": -0.1},
        {"max_vertical_m_s": -0.1},
        {"min_gate_confidence": -0.1},
        {"min_gate_confidence": 1.1},
        {"min_gate_confidence": True},
        {"min_track_depth_m": 0.0},
        {"max_track_depth_m": 0.0},
        {"min_track_depth_m": 2.0, "max_track_depth_m": 1.0},
        {"max_center_offset_ratio": 0.0},
    ],
)
def test_controller_rejects_invalid_safety_thresholds(kwargs: dict[str, object]) -> None:
    with pytest.raises(ValueError):
        ConservativeController(**kwargs)


def test_command_rate_limiter_keeps_below_100hz() -> None:
    limiter = CommandRateLimiter(max_rate_hz=95.0)

    assert limiter.allow(0.0)
    assert not limiter.allow(0.005)
    assert limiter.allow(0.011)


@pytest.mark.parametrize("max_rate_hz", [0.0, -1.0, 100.0, 120.0])
def test_command_rate_limiter_rejects_invalid_rates(max_rate_hz: float) -> None:
    with pytest.raises(ValueError, match="less than 100"):
        CommandRateLimiter(max_rate_hz=max_rate_hz)


def test_command_rate_limiter_catches_late_rate_mutation() -> None:
    limiter = CommandRateLimiter(max_rate_hz=95.0)
    limiter.max_rate_hz = 100.0

    with pytest.raises(ValueError, match="less than 100"):
        _ = limiter.min_interval_s


def test_command_rate_limiter_rejects_backward_time_without_rewind() -> None:
    limiter = CommandRateLimiter(max_rate_hz=95.0)

    assert limiter.allow(10.0)
    assert not limiter.allow(9.0)
    assert limiter.last_emit_monotonic_s == 10.0
    assert limiter.allow(10.011)


@pytest.mark.parametrize("monotonic_s", [float("nan"), float("inf"), float("-inf")])
def test_command_rate_limiter_rejects_non_finite_first_timestamp(monotonic_s: float) -> None:
    limiter = CommandRateLimiter(max_rate_hz=95.0)

    assert not limiter.allow(monotonic_s)
    assert limiter.last_emit_monotonic_s is None


@pytest.mark.parametrize("monotonic_s", [float("nan"), float("inf"), float("-inf")])
def test_command_rate_limiter_rejects_non_finite_later_timestamp(monotonic_s: float) -> None:
    limiter = CommandRateLimiter(max_rate_hz=95.0)

    assert limiter.allow(10.0)
    assert not limiter.allow(monotonic_s)
    assert limiter.last_emit_monotonic_s == 10.0
