from __future__ import annotations

import logging

import pytest

from estimation.state import (
    EstimatorDiagnosticEvent,
    EstimatorInputs,
    GatePoseMeasurement,
    GatePoseMeasurementMode,
    MinimalStateEstimator,
    gate_measurement_from_labeled_corners,
    gate_measurement_from_observation,
)
from estimation.sync import TimestampBuffer
from mavlink.telemetry import Attitude, HighresImu, LinearVelocity
from perception.detector import GateObservation
from perception.geometry import (
    CameraPoseEstimate,
    ImagePoint,
    project_frontoparallel_gate,
    project_planar_gate,
)


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
        source_frame_id=7,
        source="test",
        corner_uncertainty_px=(2.0, 2.0, 2.0, 2.0),
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
    assert estimate.source_frame_id == 7
    assert estimate.gate_measurement is not None
    assert estimate.gate_measurement.mode == GatePoseMeasurementMode.SCREEN_SPACE_CENTER_DEPTH
    assert not estimate.gate_measurement.has_full_planar_pose
    assert estimate.gate_pose_camera is not None
    assert estimate.gate_pose_camera.z_forward_m == 3.0


def test_estimator_degrades_malformed_gate_observation_to_no_gate(
    caplog: pytest.LogCaptureFixture,
) -> None:
    malformed_gate = GateObservation(
        corners=(
            ImagePoint(10.0, 10.0),
            ImagePoint(10.0, 10.0),
            ImagePoint(10.0, 10.0),
            ImagePoint(10.0, 10.0),
        ),
        confidence=0.5,
        sim_time_ns=10,
        source_frame_id=7,
        source="test",
        corner_uncertainty_px=(2.0, 2.0, 2.0, 2.0),
    )

    with caplog.at_level(logging.WARNING, logger="estimation.state"):
        estimate = MinimalStateEstimator().estimate(
            EstimatorInputs(
                sim_time_ns=10,
                attitude=attitude(),
                imu=imu(),
                velocity=None,
                gate_observation=malformed_gate,
                telemetry_age_ns=20_000_000,
            )
        )

    assert len(caplog.records) == 1
    assert caplog.records[0].getMessage() == ("estimator degraded: MALFORMED_GATE_OBSERVATION")
    assert caplog.records[0].aigp_event_type == "estimator_degraded"
    assert caplog.records[0].aigp_status == "MALFORMED_GATE_OBSERVATION"
    assert caplog.records[0].aigp_source_frame_id == 7
    assert caplog.records[0].aigp_source == "test"
    assert estimate.diagnostics == (
        EstimatorDiagnosticEvent(
            event_type="estimator_degraded",
            status="MALFORMED_GATE_OBSERVATION",
            reason="malformed gate observation: gate image width must be positive",
            sim_time_ns=10,
            source_frame_id=7,
            source="test",
        ),
    )

    assert not estimate.stale
    assert estimate.status == "MALFORMED_GATE_OBSERVATION"
    assert estimate.gate_pose_camera is None
    assert estimate.gate_confidence is None
    assert estimate.source_frame_id == 7
    assert estimate.degraded_reason is not None
    assert "malformed gate observation" in estimate.degraded_reason


def test_estimator_degrades_bad_corner_types_without_crashing() -> None:
    malformed_gate = GateObservation(
        corners=((10.0, 10.0), (20.0, 10.0), (20.0, 20.0), (10.0, 20.0)),
        confidence=0.5,
        sim_time_ns=10,
        source_frame_id=7,
        source="test",
    )

    estimate = MinimalStateEstimator().estimate(
        EstimatorInputs(
            sim_time_ns=10,
            attitude=attitude(),
            imu=imu(),
            velocity=None,
            gate_observation=malformed_gate,
            telemetry_age_ns=20_000_000,
        )
    )

    assert not estimate.stale
    assert estimate.status == "MALFORMED_GATE_OBSERVATION"
    assert estimate.gate_pose_camera is None
    assert estimate.degraded_reason is not None


def test_estimator_degrades_missing_corner_uncertainty_without_pose() -> None:
    observation = gate_observation()
    gate_without_uncertainty = GateObservation(
        corners=observation.corners,
        confidence=observation.confidence,
        sim_time_ns=observation.sim_time_ns,
        source_frame_id=observation.source_frame_id,
        source=observation.source,
        corner_uncertainty_px=None,
    )

    estimate = MinimalStateEstimator().estimate(
        EstimatorInputs(
            sim_time_ns=10,
            attitude=attitude(),
            imu=imu(),
            velocity=None,
            gate_observation=gate_without_uncertainty,
            telemetry_age_ns=20_000_000,
        )
    )

    assert estimate.status == "MALFORMED_GATE_OBSERVATION"
    assert estimate.gate_measurement is None
    assert estimate.gate_pose_camera is None
    assert estimate.diagnostics[0].source_frame_id == 7
    assert "requires corner_uncertainty_px" in estimate.degraded_reason


def test_estimator_degrades_missing_gate_metadata_without_crashing(
    caplog: pytest.LogCaptureFixture,
) -> None:
    class GateObservationWithoutMetadata:
        corners = project_frontoparallel_gate(
            CameraPoseEstimate(x_right_m=0.0, y_down_m=0.0, z_forward_m=3.0)
        )
        confidence = 0.5
        sim_time_ns = 10
        corner_uncertainty_px = (2.0, 2.0, 2.0, 2.0)

    with caplog.at_level(logging.WARNING, logger="estimation.state"):
        estimate = MinimalStateEstimator().estimate(
            EstimatorInputs(
                sim_time_ns=10,
                attitude=attitude(),
                imu=imu(),
                velocity=None,
                gate_observation=GateObservationWithoutMetadata(),  # type: ignore[arg-type]
                telemetry_age_ns=20_000_000,
            )
        )

    assert estimate.status == "MALFORMED_GATE_OBSERVATION"
    assert estimate.degraded_reason is not None
    assert "source_frame_id" in estimate.degraded_reason
    assert estimate.source_frame_id is None
    assert estimate.diagnostics[0].source_frame_id is None
    assert estimate.diagnostics[0].source is None
    assert len(caplog.records) == 1
    assert caplog.records[0].aigp_status == "MALFORMED_GATE_OBSERVATION"
    assert caplog.records[0].aigp_source_frame_id is None
    assert caplog.records[0].aigp_source is None


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


def test_gate_observation_measurement_is_center_depth_only() -> None:
    measurement = gate_measurement_from_observation(gate_observation())

    assert measurement.mode == GatePoseMeasurementMode.SCREEN_SPACE_CENTER_DEPTH
    assert measurement.center_camera.z_forward_m == 3.0
    assert measurement.confidence == 0.5
    assert measurement.source_frame_id == 7
    assert measurement.corner_uncertainty_px == (2.0, 2.0, 2.0, 2.0)
    assert measurement.planar_pose is None
    assert not measurement.has_full_planar_pose


def test_gate_observation_measurement_requires_uncertainty() -> None:
    observation = gate_observation()
    gate_without_uncertainty = GateObservation(
        corners=observation.corners,
        confidence=observation.confidence,
        sim_time_ns=observation.sim_time_ns,
        source_frame_id=observation.source_frame_id,
        source=observation.source,
        corner_uncertainty_px=None,
    )

    with pytest.raises(ValueError, match="requires corner_uncertainty_px"):
        gate_measurement_from_observation(gate_without_uncertainty)


def test_labeled_gate_measurement_carries_full_planar_pose() -> None:
    pose = CameraPoseEstimate(x_right_m=0.2, y_down_m=-0.1, z_forward_m=3.25)
    corners = project_planar_gate(
        pose,
        (
            (1.0, 0.0, 0.0),
            (0.0, 1.0, 0.0),
            (0.0, 0.0, 1.0),
        ),
    )

    measurement = gate_measurement_from_labeled_corners(
        corners,
        confidence=0.9,
        sim_time_ns=99,
        source_frame_id=3,
        source="test_labeled_fixture",
    )

    assert measurement.mode == GatePoseMeasurementMode.LABELED_PLANAR_PNP
    assert measurement.has_full_planar_pose
    assert measurement.planar_pose is not None
    assert measurement.center_camera.x_right_m == pytest.approx(pose.x_right_m)
    assert measurement.center_camera.y_down_m == pytest.approx(pose.y_down_m)
    assert measurement.center_camera.z_forward_m == pytest.approx(pose.z_forward_m)
    assert measurement.confidence == 0.9
    assert measurement.source == "test_labeled_fixture"


def test_gate_pose_measurement_rejects_contradictory_modes() -> None:
    pose = CameraPoseEstimate(x_right_m=0.0, y_down_m=0.0, z_forward_m=3.0)
    planar = gate_measurement_from_labeled_corners(
        project_planar_gate(
            pose,
            (
                (1.0, 0.0, 0.0),
                (0.0, 1.0, 0.0),
                (0.0, 0.0, 1.0),
            ),
        )
    ).planar_pose

    with pytest.raises(ValueError, match="SCREEN_SPACE_CENTER_DEPTH"):
        GatePoseMeasurement(
            mode=GatePoseMeasurementMode.SCREEN_SPACE_CENTER_DEPTH,
            center_camera=pose,
            confidence=None,
            sim_time_ns=None,
            source_frame_id=None,
            source="bad_fixture",
            planar_pose=planar,
        )

    with pytest.raises(ValueError, match="LABELED_PLANAR_PNP"):
        GatePoseMeasurement(
            mode=GatePoseMeasurementMode.LABELED_PLANAR_PNP,
            center_camera=pose,
            confidence=None,
            sim_time_ns=None,
            source_frame_id=None,
            source="bad_fixture",
        )


def test_gate_pose_measurement_rejects_missing_screen_space_uncertainty() -> None:
    with pytest.raises(ValueError, match="corner_uncertainty_px"):
        GatePoseMeasurement(
            mode=GatePoseMeasurementMode.SCREEN_SPACE_CENTER_DEPTH,
            center_camera=CameraPoseEstimate(x_right_m=0.0, y_down_m=0.0, z_forward_m=3.0),
            confidence=None,
            sim_time_ns=None,
            source_frame_id=None,
            source="bad_fixture",
            corner_uncertainty_px=None,
        )

    with pytest.raises(ValueError, match="four non-negative"):
        GatePoseMeasurement(
            mode=GatePoseMeasurementMode.SCREEN_SPACE_CENTER_DEPTH,
            center_camera=CameraPoseEstimate(x_right_m=0.0, y_down_m=0.0, z_forward_m=3.0),
            confidence=None,
            sim_time_ns=None,
            source_frame_id=None,
            source="bad_fixture",
            corner_uncertainty_px=(1.0, -1.0, 1.0, 1.0),
        )


def test_gate_pose_measurement_coerces_mode_and_preserves_invariants() -> None:
    pose = CameraPoseEstimate(x_right_m=0.0, y_down_m=0.0, z_forward_m=3.0)
    planar = gate_measurement_from_labeled_corners(
        project_planar_gate(
            pose,
            (
                (1.0, 0.0, 0.0),
                (0.0, 1.0, 0.0),
                (0.0, 0.0, 1.0),
            ),
        )
    ).planar_pose

    measurement = GatePoseMeasurement(
        mode="SCREEN_SPACE_CENTER_DEPTH",  # type: ignore[arg-type]
        center_camera=pose,
        confidence=None,
        sim_time_ns=None,
        source_frame_id=None,
        source="raw_string_fixture",
        corner_uncertainty_px=(1.0, 1.0, 1.0, 1.0),
    )

    assert measurement.mode == GatePoseMeasurementMode.SCREEN_SPACE_CENTER_DEPTH

    with pytest.raises(ValueError, match="cannot carry planar_pose"):
        GatePoseMeasurement(
            mode="SCREEN_SPACE_CENTER_DEPTH",  # type: ignore[arg-type]
            center_camera=pose,
            confidence=None,
            sim_time_ns=None,
            source_frame_id=None,
            source="bad_raw_string_fixture",
            corner_uncertainty_px=(1.0, 1.0, 1.0, 1.0),
            planar_pose=planar,
        )

    with pytest.raises(ValueError, match="GatePoseMeasurement mode"):
        GatePoseMeasurement(
            mode="UNKNOWN_MODE",  # type: ignore[arg-type]
            center_camera=pose,
            confidence=None,
            sim_time_ns=None,
            source_frame_id=None,
            source="bad_raw_string_fixture",
            corner_uncertainty_px=(1.0, 1.0, 1.0, 1.0),
        )


def test_gate_pose_measurement_rejects_planar_center_mismatch() -> None:
    pose = CameraPoseEstimate(x_right_m=0.0, y_down_m=0.0, z_forward_m=3.0)
    planar = gate_measurement_from_labeled_corners(
        project_planar_gate(
            pose,
            (
                (1.0, 0.0, 0.0),
                (0.0, 1.0, 0.0),
                (0.0, 0.0, 1.0),
            ),
        )
    ).planar_pose

    with pytest.raises(ValueError, match="center_camera must match"):
        GatePoseMeasurement(
            mode=GatePoseMeasurementMode.LABELED_PLANAR_PNP,
            center_camera=CameraPoseEstimate(
                x_right_m=0.5,
                y_down_m=0.0,
                z_forward_m=3.0,
            ),
            confidence=None,
            sim_time_ns=None,
            source_frame_id=None,
            source="bad_planar_fixture",
            planar_pose=planar,
        )


def test_screen_space_gate_observation_cannot_enter_full_planar_pnp_path() -> None:
    with pytest.raises(TypeError, match="LabeledGateImageCorners"):
        gate_measurement_from_labeled_corners(gate_observation().corners)  # type: ignore[arg-type]
