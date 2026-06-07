from __future__ import annotations

from estimation.state import EstimatorInputs, MinimalStateEstimator
from estimation.sync import TimestampBuffer
from mavlink.telemetry import Attitude, HighresImu, LinearVelocity
from perception.detector import GateObservation
from perception.geometry import CameraPoseEstimate, project_frontoparallel_gate


def attitude() -> Attitude:
    return Attitude(
        time_boot_ms=1,
        roll_rad=0.0,
        pitch_rad=0.0,
        yaw_rad=0.0,
        rollspeed_rad_s=0.0,
        pitchspeed_rad_s=0.0,
        yawspeed_rad_s=0.0,
    )


def imu() -> HighresImu:
    return HighresImu(
        time_usec=1000,
        acceleration_m_s2=(0.0, 0.0, -9.8),
        gyro_rad_s=(0.0, 0.0, 0.0),
    )


def gate_observation() -> GateObservation:
    corners = project_frontoparallel_gate(
        CameraPoseEstimate(x_right_m=0.0, y_down_m=0.0, z_forward_m=3.0)
    )
    return GateObservation(
        corners=corners,
        confidence=0.5,
        sim_time_ns=10,
        source="test",
    )


def test_timestamp_buffer_returns_nearest_not_after() -> None:
    buffer: TimestampBuffer[str] = TimestampBuffer(max_samples=2)
    buffer.add(10, "old")
    buffer.add(20, "current")
    buffer.add(30, "new")

    match = buffer.nearest_not_after(25, max_age_ns=10)

    assert match is not None
    assert match.sample.value == "current"
    assert match.age_ns == 5
    assert buffer.sample_count == 2


def test_timestamp_buffer_rejects_stale_sample() -> None:
    buffer: TimestampBuffer[str] = TimestampBuffer()
    buffer.add(10, "old")

    assert buffer.nearest_not_after(25, max_age_ns=5) is None


def test_estimator_marks_missing_telemetry_stale() -> None:
    estimate = MinimalStateEstimator().estimate(
        EstimatorInputs(
            sim_time_ns=1,
            attitude=None,
            imu=None,
            velocity=None,
            gate_observation=None,
        )
    )

    assert estimate.stale
    assert estimate.status == "STALE_TELEMETRY"


def test_estimator_reports_gate_without_velocity() -> None:
    estimate = MinimalStateEstimator().estimate(
        EstimatorInputs(
            sim_time_ns=10,
            attitude=attitude(),
            imu=imu(),
            velocity=None,
            gate_observation=gate_observation(),
            telemetry_age_ns=20_000_000,
        )
    )

    assert not estimate.stale
    assert estimate.status == "GATE_WITHOUT_VELOCITY"
    assert estimate.gate_pose_camera is not None
    assert estimate.gate_pose_camera.z_forward_m == 3.0


def test_estimator_ready_when_velocity_exists() -> None:
    estimate = MinimalStateEstimator().estimate(
        EstimatorInputs(
            sim_time_ns=10,
            attitude=attitude(),
            imu=imu(),
            velocity=LinearVelocity((1.0, 0.0, 0.0), "LOCAL_POSITION_NED", ("vx", "vy", "vz")),
            gate_observation=gate_observation(),
            telemetry_age_ns=20_000_000,
        )
    )

    assert estimate.status == "READY"


def test_estimator_reports_no_gate() -> None:
    estimate = MinimalStateEstimator().estimate(
        EstimatorInputs(
            sim_time_ns=10,
            attitude=attitude(),
            imu=imu(),
            velocity=None,
            gate_observation=None,
            telemetry_age_ns=20_000_000,
        )
    )

    assert estimate.status == "NO_GATE"
