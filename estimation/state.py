"""Minimal state estimate for the first-runtime bootstrap."""

from __future__ import annotations

from dataclasses import dataclass

from mavlink.telemetry import Attitude, HighresImu, LinearVelocity
from perception.detector import GateObservation
from perception.geometry import CameraPoseEstimate, estimate_frontoparallel_gate_pose


@dataclass(frozen=True)
class StateEstimate:
    sim_time_ns: int
    source_frame_id: int | None
    attitude: Attitude | None
    imu: HighresImu | None
    velocity: LinearVelocity | None
    gate_pose_camera: CameraPoseEstimate | None
    gate_confidence: float | None
    stale: bool
    status: str


@dataclass(frozen=True)
class EstimatorInputs:
    sim_time_ns: int
    attitude: Attitude | None
    imu: HighresImu | None
    velocity: LinearVelocity | None
    gate_observation: GateObservation | None
    telemetry_age_ns: int | None = None


class MinimalStateEstimator:
    """First-pass estimator: attitude/IMU plus optional velocity and gate pose."""

    def __init__(self, max_telemetry_age_ns: int = 100_000_000) -> None:
        self.max_telemetry_age_ns = max_telemetry_age_ns

    def estimate(self, inputs: EstimatorInputs) -> StateEstimate:
        stale = (
            inputs.telemetry_age_ns is None
            or inputs.telemetry_age_ns > self.max_telemetry_age_ns
            or inputs.attitude is None
            or inputs.imu is None
        )
        gate_pose = None
        gate_confidence = None
        if inputs.gate_observation is not None:
            gate_pose = estimate_frontoparallel_gate_pose(inputs.gate_observation.corners)
            gate_confidence = inputs.gate_observation.confidence

        if stale:
            status = "STALE_TELEMETRY"
        elif gate_pose is None:
            status = "NO_GATE"
        elif inputs.velocity is None:
            status = "GATE_WITHOUT_VELOCITY"
        else:
            status = "READY"

        return StateEstimate(
            sim_time_ns=inputs.sim_time_ns,
            source_frame_id=(
                inputs.gate_observation.source_frame_id
                if inputs.gate_observation is not None
                else None
            ),
            attitude=inputs.attitude,
            imu=inputs.imu,
            velocity=inputs.velocity,
            gate_pose_camera=gate_pose,
            gate_confidence=gate_confidence,
            stale=stale,
            status=status,
        )
