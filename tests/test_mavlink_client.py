from __future__ import annotations

import json
import socket
import subprocess
import sys
import threading
import time
from pathlib import Path

import pytest

from mavlink.client import (
    JsonTelemetryDecoder,
    TelemetryClientError,
    UdpTelemetryClient,
    iter_json_fixture_messages,
    run_telemetry_probe,
    telemetry_probe_to_json_dict,
    write_probe_json,
)

FIXTURE_PATH = Path(__file__).parent / "fixtures" / "telemetry_probe_spec_messages.json"
ROOT = Path(__file__).resolve().parents[1]


def test_json_telemetry_decoder_accepts_object_datagram() -> None:
    message = JsonTelemetryDecoder().decode(b'{"mavpackettype":"HEARTBEAT","system_status":4}')

    assert message == {"mavpackettype": "HEARTBEAT", "system_status": 4}


def test_json_telemetry_decoder_rejects_non_object_datagram() -> None:
    with pytest.raises(TelemetryClientError, match="must decode to an object"):
        JsonTelemetryDecoder().decode(b'["HEARTBEAT"]')


def test_json_telemetry_decoder_rejects_invalid_json() -> None:
    with pytest.raises(TelemetryClientError, match="invalid JSON telemetry datagram"):
        JsonTelemetryDecoder().decode(b"not-json")


def test_iter_json_fixture_messages_loads_spec_fixture() -> None:
    messages = list(iter_json_fixture_messages(FIXTURE_PATH))

    assert [message["mavpackettype"] for message in messages] == [
        "HEARTBEAT",
        "ATTITUDE",
        "HIGHRES_IMU",
        "TIMESYNC",
    ]
    assert [message["_frame_id"] for message in messages] == [
        "fixture-000000",
        "fixture-000001",
        "fixture-000002",
        "fixture-000003",
    ]


def test_iter_json_fixture_messages_wraps_json_lines_errors(tmp_path: Path) -> None:
    fixture = tmp_path / "bad-lines.jsonl"
    fixture.write_text('{"mavpackettype":"HEARTBEAT"}\nnot-json\n', encoding="utf-8")

    with pytest.raises(TelemetryClientError, match="fixture line 1"):
        list(iter_json_fixture_messages(fixture))


def test_iter_json_fixture_messages_wraps_array_errors(tmp_path: Path) -> None:
    fixture = tmp_path / "bad-array.json"
    fixture.write_text('[{"mavpackettype":"HEARTBEAT"},', encoding="utf-8")

    with pytest.raises(TelemetryClientError, match="invalid JSON telemetry fixture array"):
        list(iter_json_fixture_messages(fixture))


def test_run_telemetry_probe_emits_fixture_evidence_shape() -> None:
    run = run_telemetry_probe(
        iter_json_fixture_messages(FIXTURE_PATH),
        source="fixture:spec_messages",
    )
    payload = telemetry_probe_to_json_dict(run)

    assert payload["schema_version"] == "aigp.telemetry_probe.v0"
    assert payload["source"] == "fixture:spec_messages"
    assert payload["probe_end_monotonic_s"] == 0.03
    assert payload["message_count"] == 4
    assert payload["message_refs"][0] == {
        "index": 0,
        "message_type": "HEARTBEAT",
        "canonical_timestamp_s": 0.0,
        "timestamp_source": "_monotonic_s",
        "source_timestamp": 0.0,
        "canonical_frame_id": "fixture-000000",
        "frame_id_source": "_frame_id",
    }
    assert payload["message_refs"][-1]["canonical_frame_id"] == "fixture-000003"
    assert payload["transport_errors"] == ()
    assert payload["message_type_histogram"] == {
        "ATTITUDE": 1,
        "HEARTBEAT": 1,
        "HIGHRES_IMU": 1,
        "TIMESYNC": 1,
    }
    assert payload["parsed_counts"] == {
        "ATTITUDE": 1,
        "HEARTBEAT": 1,
        "HIGHRES_IMU": 1,
        "TIMESYNC": 1,
    }
    assert payload["parse_errors"] == ()
    assert payload["heartbeat_observed"] is True
    assert payload["heartbeat_fresh_at_end"] is True
    assert payload["velocity_report"]["status"] == "NOT_AVAILABLE"
    assert payload["velocity_report"]["candidates"] == []
    assert "not official simulator telemetry evidence" in payload["non_claims"]
    assert "not binary MAVLink decoding evidence" in payload["non_claims"]


def test_write_probe_json_uses_fixed_float_format(tmp_path: Path) -> None:
    run = run_telemetry_probe(
        [{"mavpackettype": "HEARTBEAT", "_monotonic_s": 0.000001, "_frame_id": "heartbeat-0"}],
        source="fixture:fixed_float",
    )
    evidence_path = tmp_path / "probe.json"

    write_probe_json(evidence_path, run)
    text = evidence_path.read_text(encoding="utf-8")

    assert "1e-06" not in text
    assert '"canonical_timestamp_s": 0.000001' in text
    assert '"probe_end_monotonic_s": 0.000001' in text


def test_run_telemetry_probe_uses_probe_end_for_heartbeat_freshness() -> None:
    run = run_telemetry_probe(
        [{"mavpackettype": "HEARTBEAT", "_monotonic_s": 0.0, "_frame_id": "heartbeat-0"}],
        source="fixture:stale_heartbeat",
        heartbeat_timeout_s=2.5,
        probe_end_monotonic_s=3.0,
    )

    assert run.heartbeat_observed is True
    assert run.heartbeat_fresh_at_end is False
    assert run.probe_end_monotonic_s == 3.0


def test_run_telemetry_probe_marks_out_of_order_heartbeat_stale() -> None:
    run = run_telemetry_probe(
        [
            {"mavpackettype": "HEARTBEAT", "_monotonic_s": 10.0, "_frame_id": "heartbeat-10"},
            {
                "mavpackettype": "ATTITUDE",
                "_monotonic_s": 9.0,
                "_frame_id": "attitude-9",
                "time_boot_ms": 9000,
                "roll": 0.0,
                "pitch": 0.0,
                "yaw": 0.0,
                "rollspeed": 0.0,
                "pitchspeed": 0.0,
                "yawspeed": 0.0,
            },
        ],
        source="fixture:out_of_order",
        heartbeat_timeout_s=2.5,
    )

    assert run.heartbeat_observed is True
    assert run.probe_end_monotonic_s == 9.0
    assert run.heartbeat_fresh_at_end is False


def test_run_telemetry_probe_can_use_wall_clock_probe_end() -> None:
    heartbeat_s = time.monotonic() - 3.0
    run = run_telemetry_probe(
        [{"mavpackettype": "HEARTBEAT", "_monotonic_s": heartbeat_s, "_frame_id": "heartbeat-0"}],
        source="udp-json:test",
        heartbeat_timeout_s=2.5,
        use_wall_clock_probe_end=True,
    )

    assert run.probe_end_monotonic_s >= heartbeat_s
    assert run.heartbeat_fresh_at_end is False


def test_run_telemetry_probe_rejects_conflicting_probe_end_modes() -> None:
    with pytest.raises(ValueError, match="mutually exclusive"):
        run_telemetry_probe(
            [{"mavpackettype": "HEARTBEAT", "_monotonic_s": 0.0, "_frame_id": "heartbeat-0"}],
            source="fixture:bad_end",
            probe_end_monotonic_s=1.0,
            use_wall_clock_probe_end=True,
        )


def test_run_telemetry_probe_records_parser_errors_without_stopping() -> None:
    run = run_telemetry_probe(
        [
            {"mavpackettype": "HEARTBEAT", "_monotonic_s": 0.0},
            {"mavpackettype": "ATTITUDE", "_monotonic_s": 0.01, "time_boot_ms": 1},
        ],
        source="fixture:bad_attitude",
    )

    assert run.message_count == 2
    assert run.parsed_counts["HEARTBEAT"] == 1
    assert run.parsed_counts["ATTITUDE"] == 0
    assert run.parse_errors == (
        {
            "index": 1,
            "message_type": "ATTITUDE",
            "canonical_frame_id": "ATTITUDE:000001",
            "canonical_timestamp_s": 0.01,
            "timestamp_source": "_monotonic_s",
            "error": "missing required MAVLink field roll",
        },
    )


def test_run_telemetry_probe_records_velocity_probe_errors_without_stopping() -> None:
    run = run_telemetry_probe(
        [
            {
                "mavpackettype": "LOCAL_POSITION_NED",
                "_monotonic_s": 0.0,
                "_frame_id": "bad-velocity",
                "vx": "not-a-float",
                "vy": 0.0,
                "vz": 0.0,
            },
            {"mavpackettype": "HEARTBEAT", "_monotonic_s": 0.01, "_frame_id": "heartbeat-0"},
        ],
        source="fixture:bad_velocity",
    )

    assert run.message_count == 2
    assert run.heartbeat_observed is True
    assert run.parse_errors == (
        {
            "index": 0,
            "message_type": "LOCAL_POSITION_NED",
            "stage": "velocity_probe",
            "canonical_frame_id": "bad-velocity",
            "canonical_timestamp_s": 0.0,
            "timestamp_source": "_monotonic_s",
            "error": "invalid MAVLink field vx: could not convert string to float: 'not-a-float'",
        },
    )


def test_run_telemetry_probe_ignores_velocity_from_timestamp_invalid_frames() -> None:
    run = run_telemetry_probe(
        [
            {
                "mavpackettype": "LOCAL_POSITION_NED",
                "_frame_id": "missing-time-velocity",
                "vx": 1.0,
                "vy": 2.0,
                "vz": 3.0,
            }
        ],
        source="fixture:invalid_velocity_time",
    )

    assert run.message_refs == ()
    assert run.velocity_report["status"] == "NOT_AVAILABLE"
    assert run.velocity_report["candidates"] == []
    assert run.parse_errors == (
        {
            "index": 0,
            "message_type": "LOCAL_POSITION_NED",
            "stage": "timestamp",
            "canonical_frame_id": "missing-time-velocity",
            "timestamp_source": "missing",
            "error": "telemetry message 0 must include _monotonic_s or a MAVLink time field",
        },
    )


def test_run_telemetry_probe_rejects_non_finite_velocity_without_json_crash(
    tmp_path: Path,
) -> None:
    run = run_telemetry_probe(
        [
            {
                "mavpackettype": "LOCAL_POSITION_NED",
                "_monotonic_s": 0.0,
                "_frame_id": "nan-velocity",
                "vx": "nan",
                "vy": 0.0,
                "vz": 0.0,
            }
        ],
        source="fixture:nan_velocity",
    )
    evidence_path = tmp_path / "nan-velocity.json"

    write_probe_json(evidence_path, run)

    assert run.velocity_report["status"] == "NOT_AVAILABLE"
    assert run.velocity_report["candidates"] == []
    assert run.parse_errors == (
        {
            "index": 0,
            "message_type": "LOCAL_POSITION_NED",
            "stage": "velocity_probe",
            "canonical_frame_id": "nan-velocity",
            "canonical_timestamp_s": 0.0,
            "timestamp_source": "_monotonic_s",
            "error": "MAVLink field vx must be finite",
        },
    )
    assert '"candidates": []' in evidence_path.read_text(encoding="utf-8")


def test_run_telemetry_probe_records_invalid_monotonic_time() -> None:
    run = run_telemetry_probe(
        [{"mavpackettype": "HEARTBEAT", "_monotonic_s": -1.0, "_frame_id": "bad-time"}],
        source="fixture:bad_time",
    )

    assert run.heartbeat_observed is False
    assert run.parse_errors == (
        {
            "index": 0,
            "message_type": "HEARTBEAT",
            "stage": "timestamp",
            "canonical_frame_id": "bad-time",
            "timestamp_source": "_monotonic_s",
            "error": "_monotonic_s must be finite and non-negative",
        },
    )


def test_run_telemetry_probe_records_missing_message_timestamp() -> None:
    run = run_telemetry_probe(
        [{"mavpackettype": "HEARTBEAT"}],
        source="fixture:missing_time",
    )

    assert run.parse_errors == (
        {
            "index": 0,
            "message_type": "HEARTBEAT",
            "stage": "timestamp",
            "canonical_frame_id": "HEARTBEAT:000000",
            "timestamp_source": "missing",
            "error": "telemetry message 0 must include _monotonic_s or a MAVLink time field",
        },
    )
    assert run.message_refs == ()


def test_run_telemetry_probe_records_non_numeric_time_usec() -> None:
    run = run_telemetry_probe(
        [{"mavpackettype": "HIGHRES_IMU", "time_usec": "bad", "_frame_id": "bad-time-usec"}],
        source="fixture:bad_time_usec",
    )

    assert run.parse_errors == (
        {
            "index": 0,
            "message_type": "HIGHRES_IMU",
            "stage": "timestamp",
            "canonical_frame_id": "bad-time-usec",
            "timestamp_source": "time_usec",
            "error": "invalid time_usec timestamp for telemetry message 0: "
            "could not convert string to float: 'bad'",
        },
    )


def test_run_telemetry_probe_reports_fallback_timestamp_source() -> None:
    run = run_telemetry_probe(
        [
            {
                "mavpackettype": "HEARTBEAT",
                "_monotonic_s": None,
                "time_usec": 1000,
                "_frame_id": "heartbeat-time-usec",
            }
        ],
        source="fixture:fallback_timestamp",
    )

    assert run.parse_errors == ()
    assert run.message_refs[0]["canonical_timestamp_s"] == 0.001
    assert run.message_refs[0]["timestamp_source"] == "time_usec"
    assert run.message_refs[0]["source_timestamp"] == 1000


def test_udp_json_client_receives_local_smoke_message() -> None:
    port = _unused_udp_port()
    client = UdpTelemetryClient(host="127.0.0.1", port=port, socket_timeout_s=0.02)
    stop_sender = threading.Event()
    sender = threading.Thread(
        target=_send_udp_json_after_bind,
        args=(
            port,
            {"mavpackettype": "HEARTBEAT", "system_status": 4},
            stop_sender,
        ),
    )
    sender.start()

    messages = list(client.iter_messages(duration_s=1.0, max_messages=1))
    stop_sender.set()
    sender.join(timeout=2.0)

    assert not sender.is_alive()
    assert messages[0]["mavpackettype"] == "HEARTBEAT"
    assert messages[0]["system_status"] == 4
    assert isinstance(messages[0]["_monotonic_s"], float)
    assert messages[0]["_monotonic_s"] == messages[0]["_received_monotonic_s"]
    assert messages[0]["_frame_id"] == "udp-json:000000"


def test_udp_json_client_defaults_to_loopback() -> None:
    client = UdpTelemetryClient()

    assert client.host == "127.0.0.1"


def test_udp_json_client_skips_bad_datagram() -> None:
    port = _unused_udp_port()
    client = UdpTelemetryClient(host="127.0.0.1", port=port, socket_timeout_s=0.02)
    stop_sender = threading.Event()
    sender = threading.Thread(
        target=_send_udp_payloads_after_bind,
        args=(
            port,
            [
                b"not-json",
                json.dumps(
                    {"mavpackettype": "HEARTBEAT", "system_status": 4, "_monotonic_s": 0.01}
                ).encode("utf-8"),
            ],
            stop_sender,
        ),
    )
    sender.start()

    messages = list(client.iter_messages(duration_s=0.3))
    stop_sender.set()
    sender.join(timeout=2.0)

    assert not sender.is_alive()
    assert any(message["mavpackettype"] == "HEARTBEAT" for message in messages)
    assert client.transport_errors()[0]["stage"] == "udp_json_decode"
    assert client.transport_errors()[0]["canonical_frame_id"] == "udp-json-drop:000000"
    assert "invalid JSON telemetry datagram" in client.transport_errors()[0]["error"]


def test_udp_json_client_resets_decode_errors_between_captures() -> None:
    port = _unused_udp_port()
    client = UdpTelemetryClient(host="127.0.0.1", port=port, socket_timeout_s=0.02)
    stop_sender = threading.Event()
    sender = threading.Thread(
        target=_send_udp_payloads_after_bind,
        args=(port, [b"not-json"], stop_sender),
    )
    sender.start()

    assert list(client.iter_messages(duration_s=0.2)) == []
    stop_sender.set()
    sender.join(timeout=2.0)
    assert client.transport_errors()

    assert list(client.iter_messages(duration_s=0.02)) == []
    assert client.transport_errors() == ()


def test_udp_json_client_caps_decode_error_records() -> None:
    port = _unused_udp_port()
    client = UdpTelemetryClient(
        host="127.0.0.1",
        port=port,
        max_decode_errors=1,
        socket_timeout_s=0.02,
    )
    stop_sender = threading.Event()
    sender = threading.Thread(
        target=_send_udp_payloads_after_bind,
        args=(port, [b"not-json"], stop_sender),
    )
    sender.start()

    assert list(client.iter_messages(duration_s=0.3)) == []
    stop_sender.set()
    sender.join(timeout=2.0)
    transport_errors = client.transport_errors()
    detail_errors = [error for error in transport_errors if error["stage"] == "udp_json_decode"]
    summary_errors = [
        error for error in transport_errors if error["stage"] == "udp_json_decode_summary"
    ]

    assert not sender.is_alive()
    assert len(detail_errors) == 1
    assert len(summary_errors) == 1
    assert summary_errors[0]["decode_error_count_total"] > 1
    assert summary_errors[0]["decode_error_count_recorded"] == 1
    assert summary_errors[0]["decode_error_count_dropped"] > 0


def test_udp_json_client_caps_timeout_to_duration() -> None:
    port = _unused_udp_port()
    client = UdpTelemetryClient(host="127.0.0.1", port=port, socket_timeout_s=0.5)

    start_s = time.monotonic()
    messages = list(client.iter_messages(duration_s=0.02))
    elapsed_s = time.monotonic() - start_s

    assert messages == []
    assert elapsed_s < 0.2


def test_cli_fixture_source_defaults_to_basename() -> None:
    result = subprocess.run(
        [
            sys.executable,
            "scripts/aigp_telemetry_probe.py",
            "--fixture-json",
            str(FIXTURE_PATH),
        ],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    payload = json.loads(result.stdout)

    assert payload["source"] == "fixture:telemetry_probe_spec_messages.json"


def test_cli_rejects_udp_json_write_json(tmp_path: Path) -> None:
    result = subprocess.run(
        [
            sys.executable,
            "scripts/aigp_telemetry_probe.py",
            "--udp-json",
            "--write-json",
            str(tmp_path / "udp-probe.json"),
        ],
        cwd=ROOT,
        capture_output=True,
        text=True,
    )

    assert result.returncode != 0
    assert "--udp-json --write-json is disabled" in result.stderr


def test_cli_rejects_missing_fixture_path(tmp_path: Path) -> None:
    missing_fixture = tmp_path / "missing.json"

    result = subprocess.run(
        [
            sys.executable,
            "scripts/aigp_telemetry_probe.py",
            "--fixture-json",
            str(missing_fixture),
        ],
        cwd=ROOT,
        capture_output=True,
        text=True,
    )

    assert result.returncode != 0
    assert "--fixture-json must point to a readable file" in result.stderr


def test_cli_reports_malformed_fixture_without_traceback(tmp_path: Path) -> None:
    fixture = tmp_path / "bad-array.json"
    fixture.write_text('[{"mavpackettype":"HEARTBEAT"},', encoding="utf-8")

    result = subprocess.run(
        [
            sys.executable,
            "scripts/aigp_telemetry_probe.py",
            "--fixture-json",
            str(fixture),
        ],
        cwd=ROOT,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 2
    assert "invalid JSON telemetry fixture array bad-array.json" in result.stderr
    assert "Traceback" not in result.stderr


def test_cli_reports_udp_bind_failure_without_traceback() -> None:
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as occupied_socket:
        occupied_socket.bind(("127.0.0.1", 0))
        occupied_port = int(occupied_socket.getsockname()[1])

        result = subprocess.run(
            [
                sys.executable,
                "scripts/aigp_telemetry_probe.py",
                "--udp-json",
                "--udp-host",
                "127.0.0.1",
                "--udp-port",
                str(occupied_port),
                "--duration-s",
                "0.01",
            ],
            cwd=ROOT,
            capture_output=True,
            text=True,
        )

    assert result.returncode == 2
    assert "failed to bind UDP socket to 127.0.0.1" in result.stderr
    assert "Traceback" not in result.stderr


def test_run_telemetry_probe_includes_transport_errors() -> None:
    run = run_telemetry_probe(
        [{"mavpackettype": "HEARTBEAT", "_monotonic_s": 0.0, "_frame_id": "heartbeat-0"}],
        source="udp-json:test",
        transport_error_provider=lambda: (
            {
                "stage": "udp_json_decode",
                "canonical_frame_id": "udp-json-drop:000000",
                "canonical_timestamp_s": 1.0,
                "payload_size_bytes": 8,
            },
        ),
    )

    assert run.transport_errors == (
        {
            "stage": "udp_json_decode",
            "canonical_frame_id": "udp-json-drop:000000",
            "canonical_timestamp_s": 1.0,
            "payload_size_bytes": 8,
        },
    )


def _unused_udp_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


def _send_udp_json_after_bind(
    port: int,
    message: dict[str, object],
    stop_sender: threading.Event,
) -> None:
    payload = json.dumps(message, sort_keys=True).encode("utf-8")
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
        deadline_s = time.monotonic() + 1.2
        while time.monotonic() < deadline_s and not stop_sender.is_set():
            time.sleep(0.01)
            sock.sendto(payload, ("127.0.0.1", port))


def _send_udp_payloads_after_bind(
    port: int,
    payloads: list[bytes],
    stop_sender: threading.Event,
) -> None:
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
        deadline_s = time.monotonic() + 1.2
        index = 0
        while time.monotonic() < deadline_s and not stop_sender.is_set():
            time.sleep(0.01)
            sock.sendto(payloads[index % len(payloads)], ("127.0.0.1", port))
            index += 1
