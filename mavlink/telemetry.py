"""Dependency-free MAVLink telemetry parsing and probe helpers."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any


class TelemetryError(ValueError):
    """Raised when an incoming MAVLink-like message cannot be parsed."""


class VelocityProbeStatus(StrEnum):
    AVAILABLE = "AVAILABLE"
    NOT_AVAILABLE = "NOT_AVAILABLE"
    AMBIGUOUS = "AMBIGUOUS"


@dataclass(frozen=True)
class Heartbeat:
    system_status: int | None = None
    mavlink_version: int | None = None


@dataclass(frozen=True)
class Attitude:
    time_boot_ms: int
    roll_rad: float
    pitch_rad: float
    yaw_rad: float
    rollspeed_rad_s: float
    pitchspeed_rad_s: float
    yawspeed_rad_s: float


@dataclass(frozen=True)
class HighresImu:
    time_usec: int
    acceleration_m_s2: tuple[float, float, float]
    gyro_rad_s: tuple[float, float, float]
    fields_updated: int | None = None


@dataclass(frozen=True)
class TimeSync:
    tc1: int
    ts1: int


@dataclass(frozen=True)
class LinearVelocity:
    velocity_m_s: tuple[float, float, float]
    source_message: str
    source_fields: tuple[str, str, str]


@dataclass(frozen=True)
class VelocityProbeReport:
    status: VelocityProbeStatus
    candidates: tuple[LinearVelocity, ...] = ()
    inspected_message_types: tuple[str, ...] = ()


@dataclass
class HeartbeatMonitor:
    """Track whether the simulator heartbeat is fresh enough to command."""

    timeout_s: float = 2.5
    last_heartbeat_s: float | None = None

    def observe(self, monotonic_s: float) -> None:
        self.last_heartbeat_s = monotonic_s

    def is_fresh(self, monotonic_s: float) -> bool:
        if self.last_heartbeat_s is None:
            return False
        return monotonic_s - self.last_heartbeat_s <= self.timeout_s


@dataclass
class TelemetryProbe:
    """Collect telemetry message types and probe for exposed linear velocity."""

    inspected_message_types: set[str] = field(default_factory=set)
    velocity_candidates: list[LinearVelocity] = field(default_factory=list)

    def observe(self, message: Any) -> None:
        message_type = message_type_name(message)
        self.inspected_message_types.add(message_type)
        velocity = extract_linear_velocity(message)
        if velocity is not None:
            self.velocity_candidates.append(velocity)

    def report(self) -> VelocityProbeReport:
        unique_candidates = tuple(_dedupe_velocity_candidates(self.velocity_candidates))
        if not unique_candidates:
            status = VelocityProbeStatus.NOT_AVAILABLE
        elif len({candidate.source_fields for candidate in unique_candidates}) == 1:
            status = VelocityProbeStatus.AVAILABLE
        else:
            status = VelocityProbeStatus.AMBIGUOUS
        return VelocityProbeReport(
            status=status,
            candidates=unique_candidates,
            inspected_message_types=tuple(sorted(self.inspected_message_types)),
        )


def message_type_name(message: Any) -> str:
    if isinstance(message, dict):
        return str(message.get("mavpackettype") or message.get("type") or "UNKNOWN")
    getter = getattr(message, "get_type", None)
    if callable(getter):
        return str(getter())
    return message.__class__.__name__


def parse_heartbeat(message: Any) -> Heartbeat:
    return Heartbeat(
        system_status=_optional_int(message, "system_status"),
        mavlink_version=_optional_int(message, "mavlink_version"),
    )


def parse_attitude(message: Any) -> Attitude:
    return Attitude(
        time_boot_ms=_required_int(message, "time_boot_ms"),
        roll_rad=_required_float(message, "roll"),
        pitch_rad=_required_float(message, "pitch"),
        yaw_rad=_required_float(message, "yaw"),
        rollspeed_rad_s=_required_float(message, "rollspeed"),
        pitchspeed_rad_s=_required_float(message, "pitchspeed"),
        yawspeed_rad_s=_required_float(message, "yawspeed"),
    )


def parse_highres_imu(message: Any) -> HighresImu:
    return HighresImu(
        time_usec=_required_int(message, "time_usec"),
        acceleration_m_s2=(
            _required_float(message, "xacc"),
            _required_float(message, "yacc"),
            _required_float(message, "zacc"),
        ),
        gyro_rad_s=(
            _required_float(message, "xgyro"),
            _required_float(message, "ygyro"),
            _required_float(message, "zgyro"),
        ),
        fields_updated=_optional_int(message, "fields_updated"),
    )


def parse_timesync(message: Any) -> TimeSync:
    return TimeSync(tc1=_required_int(message, "tc1"), ts1=_required_int(message, "ts1"))


def extract_linear_velocity(message: Any) -> LinearVelocity | None:
    field_sets = (
        ("vx", "vy", "vz"),
        ("velocity_x", "velocity_y", "velocity_z"),
        ("linear_velocity_x", "linear_velocity_y", "linear_velocity_z"),
        ("v_north", "v_east", "v_down"),
    )
    for fields in field_sets:
        if all(_has_field(message, field_name) for field_name in fields):
            return LinearVelocity(
                velocity_m_s=tuple(_required_float(message, field_name) for field_name in fields),
                source_message=message_type_name(message),
                source_fields=fields,
            )
    return None


def _dedupe_velocity_candidates(candidates: list[LinearVelocity]) -> list[LinearVelocity]:
    seen: set[tuple[str, tuple[str, str, str], tuple[float, float, float]]] = set()
    deduped: list[LinearVelocity] = []
    for candidate in candidates:
        key = (candidate.source_message, candidate.source_fields, candidate.velocity_m_s)
        if key in seen:
            continue
        seen.add(key)
        deduped.append(candidate)
    return deduped


def _has_field(message: Any, field_name: str) -> bool:
    if isinstance(message, dict):
        return field_name in message and message[field_name] is not None
    return hasattr(message, field_name) and getattr(message, field_name) is not None


def _required_float(message: Any, field_name: str) -> float:
    value = _get_field(message, field_name)
    if value is None:
        raise TelemetryError(f"missing required MAVLink field {field_name}")
    return float(value)


def _required_int(message: Any, field_name: str) -> int:
    value = _get_field(message, field_name)
    if value is None:
        raise TelemetryError(f"missing required MAVLink field {field_name}")
    return int(value)


def _optional_int(message: Any, field_name: str) -> int | None:
    value = _get_field(message, field_name)
    if value is None:
        return None
    return int(value)


def _get_field(message: Any, field_name: str) -> Any:
    if isinstance(message, dict):
        return message.get(field_name)
    return getattr(message, field_name, None)
