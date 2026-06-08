"""Minimal state estimate for the first-runtime bootstrap."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from enum import StrEnum
from math import isfinite
from numbers import Real

from mavlink.telemetry import Attitude, HighresImu, LinearVelocity
from perception.detector import GateObservation
from perception.geometry import (
    CameraPoseEstimate,
    GateMeasurementBasis,
    LabeledGateImageCorners,
    PlanarGatePoseEstimate,
    coerce_gate_measurement_basis,
    estimate_frontoparallel_gate_pose,
    estimate_planar_gate_pose,
)

LOGGER = logging.getLogger(__name__)


class GatePoseMeasurementMode(StrEnum):
    SCREEN_SPACE_CENTER_DEPTH = "SCREEN_SPACE_CENTER_DEPTH"
    LABELED_PLANAR_PNP = "LABELED_PLANAR_PNP"


@dataclass(frozen=True)
class GatePoseMeasurement:
    """Gate pose measurement with an explicit observation contract.

    Screen-space detector corners only support center/depth measurement. Full
    planar pose is reserved for image points labeled by physical gate-local
    corner identity.
    """

    mode: GatePoseMeasurementMode
    measurement_basis: GateMeasurementBasis
    center_camera: CameraPoseEstimate
    confidence: float | None
    sim_time_ns: int | None
    source_frame_id: int | None
    source: str
    corner_uncertainty_px: tuple[float, float, float, float] | None = None
    planar_pose: PlanarGatePoseEstimate | None = None

    def __post_init__(self) -> None:
        try:
            mode = (
                self.mode
                if isinstance(self.mode, GatePoseMeasurementMode)
                else GatePoseMeasurementMode(self.mode)
            )
        except (TypeError, ValueError) as exc:
            raise ValueError(
                "GatePoseMeasurement mode must be a GatePoseMeasurementMode value"
            ) from exc
        object.__setattr__(self, "mode", mode)
        object.__setattr__(
            self,
            "measurement_basis",
            coerce_gate_measurement_basis(self.measurement_basis),
        )

        if self.corner_uncertainty_px is not None:
            try:
                uncertainty = tuple(self.corner_uncertainty_px)
            except TypeError as exc:
                raise ValueError(
                    "GatePoseMeasurement corner_uncertainty_px must be four non-negative values"
                ) from exc
            if len(uncertainty) != 4 or any(
                not _is_non_negative_finite_real(value) for value in uncertainty
            ):
                raise ValueError(
                    "GatePoseMeasurement corner_uncertainty_px must be four non-negative values"
                )
            object.__setattr__(
                self,
                "corner_uncertainty_px",
                tuple(float(value) for value in uncertainty),
            )

        if (
            mode == GatePoseMeasurementMode.SCREEN_SPACE_CENTER_DEPTH
            and self.planar_pose is not None
        ):
            raise ValueError(
                "GatePoseMeasurement SCREEN_SPACE_CENTER_DEPTH cannot carry planar_pose"
            )
        if (
            mode == GatePoseMeasurementMode.SCREEN_SPACE_CENTER_DEPTH
            and self.corner_uncertainty_px is None
        ):
            raise ValueError(
                "GatePoseMeasurement SCREEN_SPACE_CENTER_DEPTH requires corner_uncertainty_px"
            )
        if mode == GatePoseMeasurementMode.LABELED_PLANAR_PNP and self.planar_pose is None:
            raise ValueError("GatePoseMeasurement LABELED_PLANAR_PNP requires planar_pose")
        if mode == GatePoseMeasurementMode.LABELED_PLANAR_PNP and not isinstance(
            self.planar_pose, PlanarGatePoseEstimate
        ):
            raise ValueError(
                "GatePoseMeasurement LABELED_PLANAR_PNP planar_pose must be "
                "a PlanarGatePoseEstimate"
            )
        if (
            mode == GatePoseMeasurementMode.LABELED_PLANAR_PNP
            and self.center_camera != self.planar_pose.center
        ):
            raise ValueError(
                "GatePoseMeasurement LABELED_PLANAR_PNP center_camera must match planar_pose.center"
            )
        if (
            mode == GatePoseMeasurementMode.LABELED_PLANAR_PNP
            and self.corner_uncertainty_px is not None
        ):
            raise ValueError(
                "GatePoseMeasurement LABELED_PLANAR_PNP cannot carry corner_uncertainty_px"
            )

    @property
    def has_full_planar_pose(self) -> bool:
        return self.planar_pose is not None


@dataclass(frozen=True)
class EstimatorDiagnosticEvent:
    """Structured estimator event for observability and replay traces."""

    event_type: str
    status: str
    reason: str
    sim_time_ns: int
    source_frame_id: int | None
    source: str | None


def _emit_diagnostic_event(diagnostic: EstimatorDiagnosticEvent) -> None:
    LOGGER.warning(
        "estimator degraded: %s",
        diagnostic.status,
        extra={
            "aigp_event_type": diagnostic.event_type,
            "aigp_status": diagnostic.status,
            "aigp_reason": diagnostic.reason,
            "aigp_sim_time_ns": diagnostic.sim_time_ns,
            "aigp_source_frame_id": diagnostic.source_frame_id,
            "aigp_source": diagnostic.source,
        },
    )


def _require_non_negative_int(name: str, value: int) -> int:
    if type(value) is not int or value < 0:
        raise ValueError(f"{name} must be a non-negative int")
    return value


def _is_non_negative_finite_real(value: object) -> bool:
    return (
        not isinstance(value, bool)
        and isinstance(value, Real)
        and isfinite(float(value))
        and float(value) >= 0.0
    )


def gate_measurement_from_observation(
    observation: GateObservation,
) -> GatePoseMeasurement:
    """Convert detector output to a bounded center/depth measurement only."""

    corner_uncertainty_px = observation.corner_uncertainty_px
    if corner_uncertainty_px is None:
        raise ValueError("GateObservation SCREEN_SPACE_CENTER_DEPTH requires corner_uncertainty_px")

    measurement_basis = observation.measurement_basis
    center_pose = estimate_frontoparallel_gate_pose(
        observation.corners,
        measurement_basis=measurement_basis,
    )
    return GatePoseMeasurement(
        mode=GatePoseMeasurementMode.SCREEN_SPACE_CENTER_DEPTH,
        measurement_basis=measurement_basis,
        center_camera=center_pose,
        confidence=observation.confidence,
        sim_time_ns=observation.sim_time_ns,
        source_frame_id=observation.source_frame_id,
        source=observation.source,
        corner_uncertainty_px=corner_uncertainty_px,
        planar_pose=None,
    )


def gate_measurement_from_labeled_corners(
    corners: LabeledGateImageCorners,
    *,
    confidence: float | None = None,
    sim_time_ns: int | None = None,
    source_frame_id: int | None = None,
    source: str = "labeled_planar_pnp_fixture",
) -> GatePoseMeasurement:
    """Convert physical-labeled corners to a full planar pose measurement."""

    planar_pose = estimate_planar_gate_pose(corners)
    return GatePoseMeasurement(
        mode=GatePoseMeasurementMode.LABELED_PLANAR_PNP,
        measurement_basis=GateMeasurementBasis.INNER_OPENING,
        center_camera=planar_pose.center,
        confidence=confidence,
        sim_time_ns=sim_time_ns,
        source_frame_id=source_frame_id,
        source=source,
        corner_uncertainty_px=None,
        planar_pose=planar_pose,
    )


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
    degraded_reason: str | None = None
    gate_measurement: GatePoseMeasurement | None = None
    diagnostics: tuple[EstimatorDiagnosticEvent, ...] = ()


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

    def __init__(
        self,
        max_telemetry_age_ns: int = 100_000_000,
        diagnostic_log_interval_ns: int = 250_000_000,
    ) -> None:
        self.max_telemetry_age_ns = _require_non_negative_int(
            "max_telemetry_age_ns",
            max_telemetry_age_ns,
        )
        self.diagnostic_log_interval_ns = _require_non_negative_int(
            "diagnostic_log_interval_ns",
            diagnostic_log_interval_ns,
        )
        self._last_diagnostic_log_key: tuple[str, str] | None = None
        self._last_diagnostic_log_time_ns: int | None = None

    def _maybe_emit_diagnostic_event(self, diagnostic: EstimatorDiagnosticEvent) -> None:
        diagnostic_key = (diagnostic.status, diagnostic.reason)
        should_emit = (
            self._last_diagnostic_log_key != diagnostic_key
            or self._last_diagnostic_log_time_ns is None
            or diagnostic.sim_time_ns < self._last_diagnostic_log_time_ns
            or diagnostic.sim_time_ns - self._last_diagnostic_log_time_ns
            >= self.diagnostic_log_interval_ns
        )
        if not should_emit:
            return

        _emit_diagnostic_event(diagnostic)
        self._last_diagnostic_log_key = diagnostic_key
        self._last_diagnostic_log_time_ns = diagnostic.sim_time_ns

    def estimate(self, inputs: EstimatorInputs) -> StateEstimate:
        stale = (
            inputs.telemetry_age_ns is None
            or inputs.telemetry_age_ns > self.max_telemetry_age_ns
            or inputs.attitude is None
            or inputs.imu is None
        )
        gate_pose = None
        gate_confidence = None
        gate_measurement = None
        diagnostics: tuple[EstimatorDiagnosticEvent, ...] = ()
        degraded_reason = None
        gate_source_frame_id = None
        gate_source = None
        if inputs.gate_observation is not None:
            gate_source_frame_id = getattr(inputs.gate_observation, "source_frame_id", None)
            gate_source = getattr(inputs.gate_observation, "source", None)
            try:
                gate_measurement = gate_measurement_from_observation(inputs.gate_observation)
                gate_pose = gate_measurement.center_camera
                gate_confidence = gate_measurement.confidence
            except (AttributeError, TypeError, ValueError) as exc:
                gate_pose = None
                gate_confidence = None
                gate_measurement = None
                degraded_reason = f"malformed gate observation: {exc}"
                diagnostic = EstimatorDiagnosticEvent(
                    event_type="estimator_degraded",
                    status="MALFORMED_GATE_OBSERVATION",
                    reason=degraded_reason,
                    sim_time_ns=inputs.sim_time_ns,
                    source_frame_id=gate_source_frame_id,
                    source=gate_source,
                )
                diagnostics = (diagnostic,)
                self._maybe_emit_diagnostic_event(diagnostic)

        if stale:
            status = "STALE_TELEMETRY"
        elif degraded_reason is not None:
            status = "MALFORMED_GATE_OBSERVATION"
        elif gate_pose is None:
            status = "NO_GATE"
        elif inputs.velocity is None:
            status = "GATE_WITHOUT_VELOCITY"
        else:
            status = "READY"

        return StateEstimate(
            sim_time_ns=inputs.sim_time_ns,
            source_frame_id=gate_source_frame_id,
            attitude=inputs.attitude,
            imu=inputs.imu,
            velocity=inputs.velocity,
            gate_measurement=gate_measurement,
            gate_pose_camera=gate_pose,
            gate_confidence=gate_confidence,
            stale=stale,
            status=status,
            degraded_reason=degraded_reason,
            diagnostics=diagnostics,
        )
