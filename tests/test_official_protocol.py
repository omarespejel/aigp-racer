from __future__ import annotations

import struct

import pytest

from mavlink.official_protocol import (
    ENCAPSULATED_RACE_STATUS_MSG_ID,
    ENCAPSULATED_TRACK_INFO_MSG_ID,
    MAVLINK_CMD_SIM_RESET,
    OfficialProtocolError,
    parse_race_status_payload,
    parse_track_data_packet_payload,
    parse_track_info_payload,
)


def test_parse_race_status_payload_accepts_official_layout_and_padding() -> None:
    payload = struct.pack(
        "<BQqqIq",
        ENCAPSULATED_RACE_STATUS_MSG_ID,
        1_500,
        1_000,
        -1,
        3,
        42_000_000,
    )

    status = parse_race_status_payload(payload + b"\x00" * 16)

    assert status.sim_boot_time_ms == 1_500
    assert status.race_start_boot_time_ms == 1_000
    assert status.race_finish_time_ns == -1
    assert status.active_gate_index == 3
    assert status.last_gate_race_time_raw == 42_000_000


def test_parse_race_status_payload_rejects_wrong_type() -> None:
    payload = struct.pack("<BQqqIq", 99, 1, -1, -1, 0, -1)

    with pytest.raises(OfficialProtocolError, match="data_type"):
        parse_race_status_payload(payload)


def test_parse_track_data_packet_payload_preserves_chunk_bytes() -> None:
    packet = struct.pack("<BH", ENCAPSULATED_TRACK_INFO_MSG_ID, 7) + b"chunk"

    parsed = parse_track_data_packet_payload(packet)

    assert parsed.data_type == ENCAPSULATED_TRACK_INFO_MSG_ID
    assert parsed.transfer_id == 7
    assert parsed.chunk_payload == b"chunk"


def test_parse_track_data_packet_payload_rejects_short_packet() -> None:
    with pytest.raises(OfficialProtocolError, match="shorter"):
        parse_track_data_packet_payload(b"\x02")


def test_parse_track_info_payload_decodes_gate_records() -> None:
    payload = struct.pack("<H", 2)
    payload += struct.pack(
        "<Hfffffffff",
        0,
        1.0,
        2.0,
        -0.5,
        1.0,
        0.0,
        0.0,
        0.0,
        1.5,
        1.5,
    )
    payload += struct.pack(
        "<Hfffffffff",
        1,
        3.0,
        4.0,
        -0.75,
        0.707,
        0.0,
        0.707,
        0.0,
        2.7,
        2.7,
    )

    track = parse_track_info_payload(payload)

    assert len(track.gates) == 2
    assert track.gates[0].gate_id == 0
    assert track.gates[0].position_ned_m == (1.0, 2.0, -0.5)
    assert track.gates[0].orientation_ned_wxyz == (1.0, 0.0, 0.0, 0.0)
    assert track.gates[1].width_m == pytest.approx(2.7)
    assert track.gates[1].height_m == pytest.approx(2.7)


def test_parse_track_info_payload_rejects_trailing_bytes_unless_allowed() -> None:
    payload = struct.pack("<H", 0) + b"padding"

    with pytest.raises(OfficialProtocolError, match="trailing"):
        parse_track_info_payload(payload)

    assert parse_track_info_payload(payload, allow_trailing_padding=True).gates == ()


def test_parse_track_info_payload_rejects_non_positive_gate_size() -> None:
    payload = struct.pack("<H", 1)
    payload += struct.pack("<Hfffffffff", 0, 0.0, 0.0, 0.0, 1.0, 0.0, 0.0, 0.0, 0.0, 1.5)

    with pytest.raises(OfficialProtocolError, match="positive"):
        parse_track_info_payload(payload)


def test_official_reset_command_constant_matches_template() -> None:
    assert MAVLINK_CMD_SIM_RESET == 31_000
