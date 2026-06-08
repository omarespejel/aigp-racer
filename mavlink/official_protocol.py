"""Dependency-free parsers for official AI-GP sample MAVLink payload layouts."""

from __future__ import annotations

import math
import struct
from dataclasses import dataclass

ENCAPSULATED_RACE_STATUS_MSG_ID = 1
ENCAPSULATED_TRACK_INFO_MSG_ID = 2
MAVLINK_CMD_SIM_RESET = 31_000

RACE_STATUS_STRUCT = struct.Struct("<BQqqIq")
TRACK_DATA_PACKET_HEADER_STRUCT = struct.Struct("<BH")
TRACK_GATE_COUNT_STRUCT = struct.Struct("<H")
TRACK_GATE_STRUCT = struct.Struct("<Hfffffffff")


class OfficialProtocolError(ValueError):
    """Raised when an official sample payload cannot be parsed safely."""


@dataclass(frozen=True)
class RaceStatus:
    """Race status carried in an ENCAPSULATED_DATA payload."""

    data_type: int
    sim_boot_time_ms: int
    race_start_boot_time_ms: int
    race_finish_time_ns: int
    active_gate_index: int
    last_gate_race_time_raw: int


@dataclass(frozen=True)
class TrackDataPacket:
    """One chunk of official track-info payload data."""

    data_type: int
    transfer_id: int
    chunk_payload: bytes


@dataclass(frozen=True)
class GateInfo:
    """One gate from the official track-info payload."""

    gate_id: int
    position_ned_m: tuple[float, float, float]
    orientation_ned_wxyz: tuple[float, float, float, float]
    width_m: float
    height_m: float


@dataclass(frozen=True)
class TrackInfo:
    """Decoded official track-info payload."""

    gates: tuple[GateInfo, ...]


def parse_race_status_payload(payload: bytes) -> RaceStatus:
    """Parse the official sample's race-status payload.

    The sample uses `struct.unpack_from`, so this parser accepts MAVLink padding
    after the fixed status structure while still validating the leading type ID.
    """

    _require_minimum_length(payload, RACE_STATUS_STRUCT.size, "race status")
    values = RACE_STATUS_STRUCT.unpack_from(payload)
    status = RaceStatus(
        data_type=int(values[0]),
        sim_boot_time_ms=int(values[1]),
        race_start_boot_time_ms=int(values[2]),
        race_finish_time_ns=int(values[3]),
        active_gate_index=int(values[4]),
        last_gate_race_time_raw=int(values[5]),
    )
    if status.data_type != ENCAPSULATED_RACE_STATUS_MSG_ID:
        raise OfficialProtocolError("race-status payload has unexpected data_type")
    return status


def parse_track_data_packet_payload(payload: bytes) -> TrackDataPacket:
    """Parse the official sample's track-data packet header and chunk bytes."""

    _require_minimum_length(payload, TRACK_DATA_PACKET_HEADER_STRUCT.size, "track data packet")
    data_type, transfer_id = TRACK_DATA_PACKET_HEADER_STRUCT.unpack_from(payload)
    if int(data_type) != ENCAPSULATED_TRACK_INFO_MSG_ID:
        raise OfficialProtocolError("track-data packet has unexpected data_type")
    return TrackDataPacket(
        data_type=int(data_type),
        transfer_id=int(transfer_id),
        chunk_payload=payload[TRACK_DATA_PACKET_HEADER_STRUCT.size :],
    )


def parse_track_info_payload(payload: bytes, *, allow_trailing_padding: bool = False) -> TrackInfo:
    """Parse the reassembled official track-info payload."""

    _require_minimum_length(payload, TRACK_GATE_COUNT_STRUCT.size, "track info")
    (num_gates,) = TRACK_GATE_COUNT_STRUCT.unpack_from(payload)
    expected_size = TRACK_GATE_COUNT_STRUCT.size + int(num_gates) * TRACK_GATE_STRUCT.size
    _require_minimum_length(payload, expected_size, "track info")
    if len(payload) != expected_size and not allow_trailing_padding:
        raise OfficialProtocolError("track-info payload has trailing bytes")

    gates = []
    offset = TRACK_GATE_COUNT_STRUCT.size
    for _ in range(int(num_gates)):
        values = TRACK_GATE_STRUCT.unpack_from(payload, offset)
        gate = GateInfo(
            gate_id=int(values[0]),
            position_ned_m=_finite_tuple(values[1:4], "position_ned_m"),
            orientation_ned_wxyz=_finite_tuple(values[4:8], "orientation_ned_wxyz"),
            width_m=_finite_float(values[8], "width_m"),
            height_m=_finite_float(values[9], "height_m"),
        )
        if gate.width_m <= 0.0 or gate.height_m <= 0.0:
            raise OfficialProtocolError("gate width and height must be positive")
        gates.append(gate)
        offset += TRACK_GATE_STRUCT.size
    return TrackInfo(gates=tuple(gates))


def _require_minimum_length(payload: bytes, required: int, label: str) -> None:
    if len(payload) < required:
        raise OfficialProtocolError(f"{label} payload is shorter than {required} bytes")


def _finite_tuple(values: tuple[float, ...], label: str) -> tuple[float, ...]:
    return tuple(_finite_float(value, label) for value in values)


def _finite_float(value: float, label: str) -> float:
    parsed = float(value)
    if not math.isfinite(parsed):
        raise OfficialProtocolError(f"{label} must be finite")
    return parsed
