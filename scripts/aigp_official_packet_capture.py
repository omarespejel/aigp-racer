"""Capture bounded official-simulator UDP packet summaries.

This script is intentionally a capture scaffold, not a live solver. It does not
send MAVLink commands, decode images, or depend on pymavlink. The first goal is
to preserve small, sanitized evidence that the official simulator emits packets
matching the observed sample-client contracts.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import select
import socket
import sys
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from vision.reassembler import VisionPacketError, parse_datagram  # noqa: E402

SCHEMA_VERSION = "aigp.official_packet_capture.v0"
ISSUE_URL = "https://github.com/omarespejel/aigp-racer/issues/35"

DEFAULT_VISION_HOST = "0.0.0.0"
DEFAULT_VISION_PORT = 5600
DEFAULT_MAVLINK_HOST = "127.0.0.1"
DEFAULT_MAVLINK_PORT = 14550
DEFAULT_DURATION_S = 10.0
DEFAULT_MAX_DATAGRAMS_PER_STREAM = 64
DEFAULT_MAX_TOTAL_BYTES = 10 * 1024 * 1024
DEFAULT_MAX_DATAGRAM_BYTES = 65_535
FORBIDDEN_RAW_PAYLOAD_KEYS = {
    "payload",
    "raw_payload",
    "jpeg",
    "jpeg_bytes",
    "mavlink_payload",
    "raw_mavlink_payload",
}

NON_CLAIMS = (
    "not a successful official simulator run",
    "not decoded binary MAVLink support",
    "not velocity availability evidence until a live run is attached",
    "not valid-run, latency, reliability, lap-time, or controller evidence",
    "not permission to use raw actuator control",
)

MAVLINK_V1_STX = 0xFE
MAVLINK_V2_STX = 0xFD
MAVLINK_V2_SIGNED_FLAG = 0x01

MAVLINK_MESSAGE_NAMES = {
    0: "HEARTBEAT",
    30: "ATTITUDE",
    32: "LOCAL_POSITION_NED",
    105: "HIGHRES_IMU",
    111: "TIMESYNC",
    130: "DATA_TRANSMISSION_HANDSHAKE",
    131: "ENCAPSULATED_DATA",
    247: "COLLISION",
    331: "ODOMETRY",
    375: "ACTUATOR_OUTPUT_STATUS",
}


class PacketCaptureError(ValueError):
    """Raised when packet capture configuration or evidence is invalid."""


@dataclass(frozen=True)
class UdpStreamConfig:
    name: str
    host: str
    port: int
    parser: str
    max_datagram_bytes: int = DEFAULT_MAX_DATAGRAM_BYTES


def build_default_streams(
    *,
    vision_host: str = DEFAULT_VISION_HOST,
    vision_port: int = DEFAULT_VISION_PORT,
    mavlink_host: str = DEFAULT_MAVLINK_HOST,
    mavlink_port: int = DEFAULT_MAVLINK_PORT,
) -> tuple[UdpStreamConfig, ...]:
    return (
        UdpStreamConfig(
            name="vision",
            host=vision_host,
            port=vision_port,
            parser="official_chunked_jpeg_header",
        ),
        UdpStreamConfig(
            name="mavlink",
            host=mavlink_host,
            port=mavlink_port,
            parser="mavlink_frame_header_only",
        ),
    )


def build_fixture_report() -> dict[str, Any]:
    """Build deterministic packet summaries for local validation."""

    vision_payload = bytes([0xFF, 0xD8, 0xFF, 0xD9])
    vision_datagram = (
        (1).to_bytes(4, "little")
        + (0).to_bytes(2, "little")
        + (1).to_bytes(2, "little")
        + len(vision_payload).to_bytes(4, "little")
        + len(vision_payload).to_bytes(4, "little")
        + (33_333_333).to_bytes(8, "little")
        + vision_payload
    )
    mavlink_payload = b""
    mavlink_datagram = _build_mavlink2_fixture_frame(
        msgid=0,
        seq=7,
        sysid=1,
        compid=1,
        payload=mavlink_payload,
    )
    streams = build_default_streams()
    datagrams = (
        summarize_datagram(
            stream=streams[0],
            datagram=vision_datagram,
            remote_address=("127.0.0.1", 49000),
            received_monotonic_s=1.0,
            index=0,
        ),
        summarize_datagram(
            stream=streams[1],
            datagram=mavlink_datagram,
            remote_address=("127.0.0.1", 49001),
            received_monotonic_s=1.001,
            index=0,
        ),
    )
    return build_report(
        mode="fixture",
        source="deterministic local packet-capture fixture",
        duration_s=0.0,
        streams=streams,
        datagrams=datagrams,
        max_datagrams_per_stream=DEFAULT_MAX_DATAGRAMS_PER_STREAM,
        max_total_bytes=DEFAULT_MAX_TOTAL_BYTES,
    )


def capture_live_report(
    *,
    streams: tuple[UdpStreamConfig, ...],
    duration_s: float,
    max_datagrams_per_stream: int,
    max_total_bytes: int,
) -> dict[str, Any]:
    _validate_capture_limits(
        duration_s=duration_s,
        max_datagrams_per_stream=max_datagrams_per_stream,
        max_total_bytes=max_total_bytes,
    )
    _validate_runtime_stream_configs(streams)
    sockets: dict[socket.socket, UdpStreamConfig] = {}
    stream_counts = {stream.name: 0 for stream in streams}
    total_bytes = 0
    datagrams: list[dict[str, Any]] = []
    deadline = time.monotonic() + duration_s

    try:
        for stream in streams:
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            sock.setblocking(False)
            try:
                sock.bind((stream.host, stream.port))
            except OSError as exc:
                raise PacketCaptureError(
                    f"failed to bind {stream.name} UDP socket to {stream.host}:{stream.port}: {exc}"
                ) from exc
            sockets[sock] = stream

        while time.monotonic() < deadline:
            if all(count >= max_datagrams_per_stream for count in stream_counts.values()):
                break
            timeout_s = max(0.0, min(0.1, deadline - time.monotonic()))
            readable, _, _ = select.select(tuple(sockets), (), (), timeout_s)
            for sock in readable:
                stream = sockets[sock]
                if stream_counts[stream.name] >= max_datagrams_per_stream:
                    continue
                datagram, remote_address = sock.recvfrom(stream.max_datagram_bytes)
                total_bytes += len(datagram)
                if total_bytes > max_total_bytes:
                    raise PacketCaptureError("capture exceeded max_total_bytes")
                datagrams.append(
                    summarize_datagram(
                        stream=stream,
                        datagram=datagram,
                        remote_address=remote_address,
                        received_monotonic_s=time.monotonic(),
                        index=stream_counts[stream.name],
                    )
                )
                stream_counts[stream.name] += 1
    finally:
        for sock in sockets:
            sock.close()

    return build_report(
        mode="live",
        source="official simulator UDP capture scaffold",
        duration_s=duration_s,
        streams=streams,
        datagrams=tuple(datagrams),
        max_datagrams_per_stream=max_datagrams_per_stream,
        max_total_bytes=max_total_bytes,
    )


def summarize_datagram(
    *,
    stream: UdpStreamConfig,
    datagram: bytes,
    remote_address: tuple[str, int],
    received_monotonic_s: float,
    index: int,
) -> dict[str, Any]:
    if not math.isfinite(received_monotonic_s):
        raise PacketCaptureError("received_monotonic_s must be finite")
    if index < 0:
        raise PacketCaptureError("index must be non-negative")

    summary: dict[str, Any] = {
        "stream": stream.name,
        "index": index,
        "local_bind": {"host": stream.host, "port": stream.port},
        "remote": {"host": remote_address[0], "port": remote_address[1]},
        "received_monotonic_s": _fixed_float(received_monotonic_s),
        "size_bytes": len(datagram),
        "sha256_16": hashlib.sha256(datagram).hexdigest()[:16],
    }
    if stream.parser == "official_chunked_jpeg_header":
        summary["vision"] = summarize_vision_datagram(datagram)
    elif stream.parser == "mavlink_frame_header_only":
        summary["mavlink"] = summarize_mavlink_datagram(datagram)
    else:
        raise PacketCaptureError(f"unknown stream parser {stream.parser}")
    return summary


def summarize_vision_datagram(datagram: bytes) -> dict[str, Any]:
    try:
        chunk = parse_datagram(datagram)
    except VisionPacketError as exc:
        return {"parse_status": "ERROR", "error": str(exc)}
    header = chunk.header
    return {
        "parse_status": "OK",
        "frame_id": header.frame_id,
        "chunk_id": header.chunk_id,
        "total_chunks": header.total_chunks,
        "jpeg_size_bytes": header.jpeg_size,
        "payload_size_bytes": header.payload_size,
        "sim_time_ns": header.sim_time_ns,
        "is_complete_single_chunk_frame": header.total_chunks == 1,
    }


def summarize_mavlink_datagram(datagram: bytes) -> dict[str, Any]:
    if not datagram:
        return {"parse_status": "ERROR", "error": "empty datagram"}
    first = datagram[0]
    if first == MAVLINK_V2_STX:
        return _summarize_mavlink2(datagram)
    if first == MAVLINK_V1_STX:
        return _summarize_mavlink1(datagram)
    return {
        "parse_status": "UNKNOWN_MAGIC",
        "magic": first,
        "note": "not recognized as MAVLink v1 or v2 frame start",
    }


def build_report(
    *,
    mode: str,
    source: str,
    duration_s: float,
    streams: tuple[UdpStreamConfig, ...],
    datagrams: tuple[dict[str, Any], ...],
    max_datagrams_per_stream: int,
    max_total_bytes: int,
) -> dict[str, Any]:
    stream_counts = {stream.name: 0 for stream in streams}
    stream_bytes = {stream.name: 0 for stream in streams}
    for datagram in datagrams:
        stream_name = str(datagram["stream"])
        stream_counts[stream_name] = stream_counts.get(stream_name, 0) + 1
        stream_bytes[stream_name] = stream_bytes.get(stream_name, 0) + int(datagram["size_bytes"])
    report = {
        "schema_version": SCHEMA_VERSION,
        "issue": ISSUE_URL,
        "mode": mode,
        "source": source,
        "duration_s": _fixed_float(duration_s),
        "limits": {
            "max_datagrams_per_stream": max_datagrams_per_stream,
            "max_total_bytes": max_total_bytes,
            "raw_payload_bytes_recorded": False,
        },
        "streams": [asdict(stream) for stream in streams],
        "stream_counts": stream_counts,
        "stream_bytes": stream_bytes,
        "datagrams": list(datagrams),
        "non_claims": list(NON_CLAIMS),
    }
    validate_report(report)
    return report


def validate_report(report: dict[str, Any]) -> None:
    if report.get("schema_version") != SCHEMA_VERSION:
        raise PacketCaptureError("unexpected schema_version")
    if report.get("issue") != ISSUE_URL:
        raise PacketCaptureError("unexpected issue URL")
    if report.get("non_claims") != list(NON_CLAIMS):
        raise PacketCaptureError("unexpected non_claims")
    if report.get("mode") not in {"fixture", "live"}:
        raise PacketCaptureError("mode must be fixture or live")
    _validate_fixed_non_negative_float(report.get("duration_s"), "duration_s")
    limits = report.get("limits")
    if not isinstance(limits, dict):
        raise PacketCaptureError("limits must be an object")
    if limits.get("raw_payload_bytes_recorded") is not False:
        raise PacketCaptureError("raw payload bytes must not be recorded")
    max_datagrams_per_stream = int(limits.get("max_datagrams_per_stream", 0))
    max_total_bytes = int(limits.get("max_total_bytes", 0))
    if max_datagrams_per_stream <= 0 or max_total_bytes <= 0:
        raise PacketCaptureError("capture limits must be positive")
    datagrams = report.get("datagrams")
    if not isinstance(datagrams, list):
        raise PacketCaptureError("datagrams must be a list")
    streams = report.get("streams")
    stream_names = _validate_stream_entries(streams)
    total_bytes = 0
    counts: dict[str, int] = {}
    stream_bytes = {stream_name: 0 for stream_name in stream_names}
    for datagram in datagrams:
        if not isinstance(datagram, dict):
            raise PacketCaptureError("datagram entries must be objects")
        _reject_forbidden_raw_payload_keys(datagram)
        stream = str(datagram.get("stream"))
        if stream not in stream_names:
            raise PacketCaptureError(f"datagram references unknown stream {stream}")
        counts[stream] = counts.get(stream, 0) + 1
        if counts[stream] > max_datagrams_per_stream:
            raise PacketCaptureError("datagram count exceeds max_datagrams_per_stream")
        size_bytes = int(datagram.get("size_bytes", -1))
        if size_bytes < 0:
            raise PacketCaptureError("size_bytes must be non-negative")
        total_bytes += size_bytes
        stream_bytes[stream] += size_bytes
    if total_bytes > max_total_bytes:
        raise PacketCaptureError("total datagram bytes exceed max_total_bytes")
    expected_counts = {stream_name: counts.get(stream_name, 0) for stream_name in stream_names}
    if report.get("stream_counts") != expected_counts:
        raise PacketCaptureError("stream_counts do not match datagrams")
    if report.get("stream_bytes") != stream_bytes:
        raise PacketCaptureError("stream_bytes do not match datagrams")


def write_json(path: Path, report: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def check_json(path: Path, report: dict[str, Any]) -> None:
    actual = json.loads(path.read_text(encoding="utf-8"))
    validate_report(actual)
    if actual != report:
        raise PacketCaptureError(f"{path} does not match regenerated packet-capture fixture")


def _summarize_mavlink2(datagram: bytes) -> dict[str, Any]:
    if len(datagram) < 12:
        return {"parse_status": "ERROR", "error": "MAVLink v2 datagram too short"}
    payload_len = datagram[1]
    incompat_flags = datagram[2]
    signature_len = 13 if incompat_flags & MAVLINK_V2_SIGNED_FLAG else 0
    frame_size = 10 + payload_len + 2 + signature_len
    if len(datagram) < frame_size:
        return {
            "parse_status": "ERROR",
            "error": "MAVLink v2 datagram shorter than declared frame size",
            "declared_frame_size_bytes": frame_size,
        }
    msgid = datagram[7] | (datagram[8] << 8) | (datagram[9] << 16)
    return {
        "parse_status": "OK",
        "version": 2,
        "payload_length": payload_len,
        "incompat_flags": incompat_flags,
        "compat_flags": datagram[3],
        "seq": datagram[4],
        "sysid": datagram[5],
        "compid": datagram[6],
        "msgid": msgid,
        "message_name": MAVLINK_MESSAGE_NAMES.get(msgid, "UNKNOWN"),
        "signed": bool(signature_len),
        "frame_size_bytes": frame_size,
        "trailing_bytes": len(datagram) - frame_size,
    }


def _summarize_mavlink1(datagram: bytes) -> dict[str, Any]:
    if len(datagram) < 8:
        return {"parse_status": "ERROR", "error": "MAVLink v1 datagram too short"}
    payload_len = datagram[1]
    frame_size = 6 + payload_len + 2
    if len(datagram) < frame_size:
        return {
            "parse_status": "ERROR",
            "error": "MAVLink v1 datagram shorter than declared frame size",
            "declared_frame_size_bytes": frame_size,
        }
    msgid = datagram[5]
    return {
        "parse_status": "OK",
        "version": 1,
        "payload_length": payload_len,
        "seq": datagram[2],
        "sysid": datagram[3],
        "compid": datagram[4],
        "msgid": msgid,
        "message_name": MAVLINK_MESSAGE_NAMES.get(msgid, "UNKNOWN"),
        "frame_size_bytes": frame_size,
        "trailing_bytes": len(datagram) - frame_size,
    }


def _build_mavlink2_fixture_frame(
    *,
    msgid: int,
    seq: int,
    sysid: int,
    compid: int,
    payload: bytes,
) -> bytes:
    if not 0 <= msgid <= 0xFFFFFF:
        raise ValueError("msgid must fit in 24 bits")
    header = bytes(
        [
            MAVLINK_V2_STX,
            len(payload),
            0,
            0,
            seq,
            sysid,
            compid,
            msgid & 0xFF,
            (msgid >> 8) & 0xFF,
            (msgid >> 16) & 0xFF,
        ]
    )
    checksum_placeholder = b"\x00\x00"
    return header + payload + checksum_placeholder


def _validate_capture_limits(
    *,
    duration_s: float,
    max_datagrams_per_stream: int,
    max_total_bytes: int,
) -> None:
    if duration_s <= 0.0 or not math.isfinite(duration_s):
        raise PacketCaptureError("duration_s must be positive and finite")
    if max_datagrams_per_stream <= 0:
        raise PacketCaptureError("max_datagrams_per_stream must be positive")
    if max_total_bytes <= 0:
        raise PacketCaptureError("max_total_bytes must be positive")


def _validate_stream_entries(streams: Any) -> tuple[str, ...]:
    if not isinstance(streams, list):
        raise PacketCaptureError("streams must be a list")
    stream_names: list[str] = []
    for stream in streams:
        if not isinstance(stream, dict):
            raise PacketCaptureError("stream entries must be objects")
        name = stream.get("name")
        if not isinstance(name, str) or not name:
            raise PacketCaptureError("stream name must be a non-empty string")
        if name in stream_names:
            raise PacketCaptureError(f"duplicate stream name {name}")
        host = stream.get("host")
        if not isinstance(host, str) or not host:
            raise PacketCaptureError(f"stream {name} host must be a non-empty string")
        port = stream.get("port")
        if not isinstance(port, int) or not 0 < port <= 65_535:
            raise PacketCaptureError(f"stream {name} port must be in 1..65535")
        parser = stream.get("parser")
        if parser not in {"official_chunked_jpeg_header", "mavlink_frame_header_only"}:
            raise PacketCaptureError(f"stream {name} has unknown parser")
        max_datagram_bytes = stream.get("max_datagram_bytes")
        if max_datagram_bytes != DEFAULT_MAX_DATAGRAM_BYTES:
            raise PacketCaptureError(
                f"stream {name} max_datagram_bytes must be {DEFAULT_MAX_DATAGRAM_BYTES}"
            )
        stream_names.append(name)
    return tuple(stream_names)


def _validate_runtime_stream_configs(streams: tuple[UdpStreamConfig, ...]) -> None:
    _validate_stream_entries([asdict(stream) for stream in streams])


def _reject_forbidden_raw_payload_keys(value: Any, *, path: str = "datagram") -> None:
    if isinstance(value, dict):
        for key, nested_value in value.items():
            key_text = str(key)
            if key_text in FORBIDDEN_RAW_PAYLOAD_KEYS:
                raise PacketCaptureError(f"forbidden raw payload key at {path}.{key_text}")
            _reject_forbidden_raw_payload_keys(nested_value, path=f"{path}.{key_text}")
    elif isinstance(value, list):
        for index, nested_value in enumerate(value):
            _reject_forbidden_raw_payload_keys(nested_value, path=f"{path}[{index}]")


def _validate_fixed_non_negative_float(value: Any, name: str) -> None:
    if not isinstance(value, str):
        raise PacketCaptureError(f"{name} must be a fixed float string")
    try:
        parsed = float(value)
    except ValueError as exc:
        raise PacketCaptureError(f"{name} must be a finite non-negative float") from exc
    if not math.isfinite(parsed) or parsed < 0.0:
        raise PacketCaptureError(f"{name} must be a finite non-negative float")


def _fixed_float(value: float) -> str:
    if not math.isfinite(value):
        raise PacketCaptureError("float values must be finite")
    return f"{value:.6f}"


def _build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser()
    mode_group = parser.add_mutually_exclusive_group(required=True)
    mode_group.add_argument("--fixture", action="store_true")
    mode_group.add_argument("--live", action="store_true")
    parser.add_argument("--vision-host", default=DEFAULT_VISION_HOST)
    parser.add_argument("--vision-port", type=int, default=DEFAULT_VISION_PORT)
    parser.add_argument("--mavlink-host", default=DEFAULT_MAVLINK_HOST)
    parser.add_argument("--mavlink-port", type=int, default=DEFAULT_MAVLINK_PORT)
    parser.add_argument("--duration-s", type=float, default=DEFAULT_DURATION_S)
    parser.add_argument(
        "--max-datagrams-per-stream", type=int, default=DEFAULT_MAX_DATAGRAMS_PER_STREAM
    )
    parser.add_argument("--max-total-bytes", type=int, default=DEFAULT_MAX_TOTAL_BYTES)
    parser.add_argument("--write-json", type=Path)
    parser.add_argument("--check-json", type=Path)
    return parser


def main() -> int:
    parser = _build_arg_parser()
    args = parser.parse_args()
    try:
        if args.fixture:
            report = build_fixture_report()
        else:
            if args.check_json is not None:
                parser.error(
                    "--live cannot be used with --check-json because live captures are runtime data"
                )
            report = capture_live_report(
                streams=build_default_streams(
                    vision_host=args.vision_host,
                    vision_port=args.vision_port,
                    mavlink_host=args.mavlink_host,
                    mavlink_port=args.mavlink_port,
                ),
                duration_s=args.duration_s,
                max_datagrams_per_stream=args.max_datagrams_per_stream,
                max_total_bytes=args.max_total_bytes,
            )
        if args.write_json is not None:
            write_json(args.write_json, report)
        else:
            print(json.dumps(report, indent=2, sort_keys=True))
        if args.check_json is not None:
            check_json(args.check_json, report)
    except PacketCaptureError as exc:
        print(str(exc), file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
