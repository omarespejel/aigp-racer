from __future__ import annotations

import json
from pathlib import Path

import pytest

from scripts import aigp_official_packet_capture as capture

ROOT = Path(__file__).resolve().parents[1]


def test_fixture_report_has_bounded_summaries_without_raw_payloads() -> None:
    report = capture.build_fixture_report()

    assert report["schema_version"] == capture.SCHEMA_VERSION
    assert report["mode"] == "fixture"
    assert report["limits"]["raw_payload_bytes_recorded"] is False
    assert report["stream_counts"] == {"mavlink": 1, "vision": 1}
    assert len(report["datagrams"]) == 2
    assert "raw_payload" not in json.dumps(report["datagrams"])
    assert "not decoded binary MAVLink support" in report["non_claims"]


def test_fixture_report_matches_checked_evidence() -> None:
    fixture_path = (
        ROOT
        / "docs"
        / "engineering"
        / "evidence"
        / "official-packet-capture-fixture-2026-06-08.json"
    )
    actual = json.loads(fixture_path.read_text(encoding="utf-8"))

    assert actual == capture.build_fixture_report()


def test_vision_summary_parses_official_header() -> None:
    payload = b"abc"
    datagram = (
        (42).to_bytes(4, "little")
        + (1).to_bytes(2, "little")
        + (3).to_bytes(2, "little")
        + (9).to_bytes(4, "little")
        + len(payload).to_bytes(4, "little")
        + (123_456).to_bytes(8, "little")
        + payload
    )

    summary = capture.summarize_vision_datagram(datagram)

    assert summary["parse_status"] == "OK"
    assert summary["frame_id"] == 42
    assert summary["chunk_id"] == 1
    assert summary["total_chunks"] == 3
    assert summary["sim_time_ns"] == 123_456
    assert summary["is_complete_single_chunk_frame"] is False


def test_vision_summary_records_parse_errors_without_throwing() -> None:
    summary = capture.summarize_vision_datagram(b"short")

    assert summary["parse_status"] == "ERROR"
    assert "shorter than 24-byte header" in summary["error"]


def test_mavlink2_summary_parses_header_without_pymavlink() -> None:
    datagram = capture._build_mavlink2_fixture_frame(
        msgid=32,
        seq=9,
        sysid=2,
        compid=3,
        payload=b"\x01\x02\x03",
    )

    summary = capture.summarize_mavlink_datagram(datagram)

    assert summary["parse_status"] == "OK"
    assert summary["version"] == 2
    assert summary["payload_length"] == 3
    assert summary["seq"] == 9
    assert summary["sysid"] == 2
    assert summary["compid"] == 3
    assert summary["msgid"] == 32
    assert summary["message_name"] == "LOCAL_POSITION_NED"
    assert summary["trailing_bytes"] == 0


def test_mavlink1_summary_parses_header_without_pymavlink() -> None:
    payload = b"\x01"
    datagram = bytes([capture.MAVLINK_V1_STX, len(payload), 4, 1, 1, 30]) + payload + b"\x00\x00"

    summary = capture.summarize_mavlink_datagram(datagram)

    assert summary["parse_status"] == "OK"
    assert summary["version"] == 1
    assert summary["msgid"] == 30
    assert summary["message_name"] == "ATTITUDE"


def test_mavlink_summary_records_unknown_magic() -> None:
    summary = capture.summarize_mavlink_datagram(b"\x00abc")

    assert summary["parse_status"] == "UNKNOWN_MAGIC"
    assert summary["magic"] == 0


def test_report_validation_rejects_payload_leakage() -> None:
    report = capture.build_fixture_report()
    report["datagrams"][0]["raw_payload"] = "ff00"

    with pytest.raises(capture.PacketCaptureError, match="raw payload"):
        capture.validate_report(report)


def test_report_validation_rejects_nested_payload_leakage() -> None:
    report = capture.build_fixture_report()
    report["datagrams"][0]["vision"]["payload"] = "ff00"

    with pytest.raises(capture.PacketCaptureError, match="forbidden raw payload key"):
        capture.validate_report(report)


def test_report_validation_allows_payload_size_metadata() -> None:
    report = capture.build_fixture_report()

    capture.validate_report(report)

    assert "payload_size_bytes" in report["datagrams"][0]["vision"]
    assert "payload_length" in report["datagrams"][1]["mavlink"]


def test_report_validation_rejects_unbounded_stream_counts() -> None:
    report = capture.build_fixture_report()
    report["limits"]["max_datagrams_per_stream"] = 1
    report["datagrams"].append(dict(report["datagrams"][0]))

    with pytest.raises(capture.PacketCaptureError, match="max_datagrams_per_stream"):
        capture.validate_report(report)


def test_report_validation_rejects_incorrect_aggregates() -> None:
    report = capture.build_fixture_report()
    report["stream_counts"]["vision"] = 99

    with pytest.raises(capture.PacketCaptureError, match="stream_counts"):
        capture.validate_report(report)


def test_report_validation_rejects_incorrect_stream_bytes() -> None:
    report = capture.build_fixture_report()
    report["stream_bytes"]["mavlink"] = 99

    with pytest.raises(capture.PacketCaptureError, match="stream_bytes"):
        capture.validate_report(report)


def test_report_validation_rejects_fixed_metadata_drift() -> None:
    report = capture.build_fixture_report()
    report["issue"] = "https://example.invalid/wrong"

    with pytest.raises(capture.PacketCaptureError, match="issue URL"):
        capture.validate_report(report)


def test_report_validation_rejects_duration_drift() -> None:
    report = capture.build_fixture_report()
    report["duration_s"] = "-1.000000"

    with pytest.raises(capture.PacketCaptureError, match="duration_s"):
        capture.validate_report(report)


def test_report_validation_rejects_unknown_stream() -> None:
    report = capture.build_fixture_report()
    report["datagrams"][0]["stream"] = "unknown"

    with pytest.raises(capture.PacketCaptureError, match="unknown stream"):
        capture.validate_report(report)


def test_check_json_rejects_drift(tmp_path: Path) -> None:
    path = tmp_path / "capture.json"
    report = capture.build_fixture_report()
    capture.write_json(path, report)
    drifted = json.loads(path.read_text(encoding="utf-8"))
    drifted["stream_counts"]["vision"] = 99
    path.write_text(json.dumps(drifted, sort_keys=True), encoding="utf-8")

    with pytest.raises(capture.PacketCaptureError, match="stream_counts"):
        capture.check_json(path, report)
