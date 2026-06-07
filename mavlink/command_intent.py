"""Transport-independent command intents for official MAVLink command surfaces."""

from __future__ import annotations

import math
from dataclasses import dataclass
from enum import StrEnum
from numbers import Real
from typing import Any

from solver.commands import CommandKind, ControlCommand

SCHEMA_VERSION = "aigp.command_intent.v0"
CLAIM_BOUNDARY = "transport-independent command intent only; not binary MAVLink or MAVSDK evidence"


class CommandIntentError(ValueError):
    """Raised when a solver command cannot be mapped safely."""


class MavlinkMessageName(StrEnum):
    """Official command message names used as intent labels."""

    SET_POSITION_TARGET_LOCAL_NED = "SET_POSITION_TARGET_LOCAL_NED"


class MavFrameName(StrEnum):
    """MAVLink frame names used as intent labels."""

    MAV_FRAME_BODY_NED = "MAV_FRAME_BODY_NED"


class CommandIntentMode(StrEnum):
    """Mode labels preserved across the solver-to-transport boundary."""

    HOLD = "HOLD"
    REACQUIRE = "REACQUIRE"
    TRACK_GATE = "TRACK_GATE"


@dataclass(frozen=True)
class MavlinkCommandIntent:
    """Validated, deterministic command intent before binary MAVLink serialization."""

    schema_version: str
    source_command_kind: str
    message_name: str
    frame: str
    intent_profile: str
    mode: str
    sim_time_ns: int
    source_frame_id: int | None
    velocity_body_ned_m_s: tuple[float, float, float]
    yaw_rate_rad_s: float
    ignored_setpoint_groups: tuple[str, ...]
    reason: str
    claim_boundary: str

    def as_dict(self) -> dict[str, Any]:
        """Return a stable JSON-serializable representation."""

        return {
            "schema_version": self.schema_version,
            "source_command_kind": self.source_command_kind,
            "message_name": self.message_name,
            "frame": self.frame,
            "intent_profile": self.intent_profile,
            "mode": self.mode,
            "sim_time_ns": self.sim_time_ns,
            "source_frame_id": self.source_frame_id,
            "velocity_body_ned_m_s": list(self.velocity_body_ned_m_s),
            "yaw_rate_rad_s": self.yaw_rate_rad_s,
            "ignored_setpoint_groups": list(self.ignored_setpoint_groups),
            "reason": self.reason,
            "claim_boundary": self.claim_boundary,
        }


def build_position_target_body_velocity_intent(command: ControlCommand) -> MavlinkCommandIntent:
    """Map a solver command to a body-NED velocity command intent."""

    _validate_timestamp(command.sim_time_ns)
    _validate_optional_source_frame_id(command.source_frame_id)

    if command.kind == CommandKind.HOLD:
        mode = CommandIntentMode.HOLD
        velocity = (0.0, 0.0, 0.0)
        yaw_rate_rad_s = 0.0
    elif command.kind == CommandKind.REACQUIRE:
        mode = CommandIntentMode.REACQUIRE
        velocity = _validated_velocity(command)
        yaw_rate_rad_s = _finite_float("yaw_rate_rad_s", command.yaw_rate_rad_s)
    elif command.kind == CommandKind.BODY_VELOCITY:
        mode = CommandIntentMode.TRACK_GATE
        velocity = _validated_velocity(command)
        yaw_rate_rad_s = _finite_float("yaw_rate_rad_s", command.yaw_rate_rad_s)
    else:
        raise CommandIntentError(f"unsupported command kind {command.kind!r}")

    return MavlinkCommandIntent(
        schema_version=SCHEMA_VERSION,
        source_command_kind=command.kind.value,
        message_name=MavlinkMessageName.SET_POSITION_TARGET_LOCAL_NED.value,
        frame=MavFrameName.MAV_FRAME_BODY_NED.value,
        intent_profile="body_ned_velocity_plus_yaw_rate",
        mode=mode.value,
        sim_time_ns=command.sim_time_ns,
        source_frame_id=command.source_frame_id,
        velocity_body_ned_m_s=velocity,
        yaw_rate_rad_s=yaw_rate_rad_s,
        ignored_setpoint_groups=("position", "acceleration", "yaw_angle"),
        reason=command.reason,
        claim_boundary=CLAIM_BOUNDARY,
    )


def _validated_velocity(command: ControlCommand) -> tuple[float, float, float]:
    return (
        _finite_float("forward_m_s", command.forward_m_s),
        _finite_float("right_m_s", command.right_m_s),
        _finite_float("down_m_s", command.down_m_s),
    )


def _finite_float(name: str, value: float) -> float:
    if not isinstance(value, Real) or isinstance(value, bool):
        raise CommandIntentError(f"{name} must be a finite real number")
    parsed = float(value)
    if not math.isfinite(parsed):
        raise CommandIntentError(f"{name} must be finite")
    return parsed


def _validate_timestamp(sim_time_ns: int) -> None:
    if type(sim_time_ns) is not int or sim_time_ns < 0:
        raise CommandIntentError("sim_time_ns must be a non-negative integer")


def _validate_optional_source_frame_id(source_frame_id: int | None) -> None:
    if source_frame_id is not None and type(source_frame_id) is not int:
        raise CommandIntentError("source_frame_id must be an integer when provided")
