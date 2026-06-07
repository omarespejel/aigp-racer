"""Telemetry probe client surfaces for decoded MAVLink-like messages."""

from __future__ import annotations

import json
import math
import socket
import time
from collections import Counter
from collections.abc import Callable, Iterable, Iterator
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from mavlink.telemetry import (
    HeartbeatMonitor,
    TelemetryError,
    TelemetryProbe,
    VelocityProbeReport,
    message_type_name,
    parse_attitude,
    parse_heartbeat,
    parse_highres_imu,
    parse_timesync,
)

DEFAULT_UDP_PORT = 5600
DEFAULT_MAX_DATAGRAM_BYTES = 65535
DEFAULT_MAX_DECODE_ERRORS = 1000

RECOGNIZED_MESSAGE_TYPES = (
    "HEARTBEAT",
    "ATTITUDE",
    "HIGHRES_IMU",
    "TIMESYNC",
)


class TelemetryClientError(ValueError):
    """Raised when a telemetry source cannot produce decoded messages."""


@dataclass(frozen=True)
class TelemetryProbeRun:
    schema_version: str
    source: str
    input_contract: str
    probe_end_monotonic_s: float
    message_count: int
    message_refs: tuple[dict[str, Any], ...]
    transport_errors: tuple[dict[str, Any], ...]
    message_type_histogram: dict[str, int]
    parsed_counts: dict[str, int]
    parse_errors: tuple[dict[str, Any], ...]
    heartbeat_observed: bool
    heartbeat_fresh_at_end: bool
    velocity_report: dict[str, Any]
    non_claims: tuple[str, ...]


class JsonTelemetryDecoder:
    """Decode one UDP datagram containing one JSON MAVLink-like message."""

    def decode(self, datagram: bytes) -> dict[str, Any]:
        try:
            payload = json.loads(datagram.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise TelemetryClientError(f"invalid JSON telemetry datagram: {exc}") from exc
        if not isinstance(payload, dict):
            raise TelemetryClientError("JSON telemetry datagram must decode to an object")
        return payload


class UdpTelemetryClient:
    """Receive decoded JSON telemetry messages from a UDP socket.

    This is a local smoke-test transport. It does not decode binary MAVLink 2 packets.
    """

    def __init__(
        self,
        host: str = "127.0.0.1",
        port: int = DEFAULT_UDP_PORT,
        *,
        decoder: JsonTelemetryDecoder | None = None,
        max_datagram_bytes: int = DEFAULT_MAX_DATAGRAM_BYTES,
        max_decode_errors: int = DEFAULT_MAX_DECODE_ERRORS,
        socket_timeout_s: float = 0.1,
    ) -> None:
        if not 0 < port <= 65535:
            raise ValueError("port must be in 1..65535")
        if max_datagram_bytes <= 0:
            raise ValueError("max_datagram_bytes must be positive")
        if max_decode_errors <= 0:
            raise ValueError("max_decode_errors must be positive")
        if socket_timeout_s <= 0.0:
            raise ValueError("socket_timeout_s must be positive")
        self.host = host
        self.port = port
        self.decoder = decoder or JsonTelemetryDecoder()
        self.max_datagram_bytes = max_datagram_bytes
        self.max_decode_errors = max_decode_errors
        self.socket_timeout_s = socket_timeout_s
        self.decode_errors: list[dict[str, Any]] = []
        self.decode_error_count_total = 0

    def iter_messages(
        self,
        *,
        duration_s: float,
        max_messages: int | None = None,
    ) -> Iterator[dict[str, Any]]:
        if duration_s <= 0.0 or not math.isfinite(duration_s):
            raise ValueError("duration_s must be positive and finite")
        if max_messages is not None and max_messages <= 0:
            raise ValueError("max_messages must be positive when provided")

        deadline = time.monotonic() + duration_s
        emitted = 0
        self.decode_errors.clear()
        self.decode_error_count_total = 0
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
            sock.settimeout(self.socket_timeout_s)
            try:
                sock.bind((self.host, self.port))
            except OSError as exc:
                raise TelemetryClientError(
                    f"failed to bind UDP socket to {self.host}:{self.port}: {exc}"
                ) from exc
            while time.monotonic() < deadline:
                if max_messages is not None and emitted >= max_messages:
                    return
                remaining_s = deadline - time.monotonic()
                if remaining_s <= 0.0:
                    return
                sock.settimeout(min(self.socket_timeout_s, remaining_s))
                try:
                    datagram, _ = sock.recvfrom(self.max_datagram_bytes)
                except TimeoutError:
                    continue
                except OSError as exc:
                    raise TelemetryClientError(
                        f"UDP recvfrom failed on {self.host}:{self.port}: {exc}"
                    ) from exc
                try:
                    message = self.decoder.decode(datagram)
                except TelemetryClientError as exc:
                    error_index = self.decode_error_count_total
                    self.decode_error_count_total += 1
                    if len(self.decode_errors) < self.max_decode_errors:
                        self.decode_errors.append(
                            {
                                "stage": "udp_json_decode",
                                "canonical_frame_id": f"udp-json-drop:{error_index:06d}",
                                "canonical_timestamp_s": time.monotonic(),
                                "payload_size_bytes": len(datagram),
                                "error": str(exc),
                            }
                        )
                    continue
                received_monotonic_s = time.monotonic()
                message.setdefault("_received_monotonic_s", received_monotonic_s)
                if message.get("_monotonic_s") is None:
                    message["_monotonic_s"] = received_monotonic_s
                message.setdefault("_frame_id", f"udp-json:{emitted:06d}")
                yield message
                emitted += 1

    def transport_errors(self) -> tuple[dict[str, Any], ...]:
        errors = tuple(self.decode_errors)
        if self.decode_error_count_total <= len(self.decode_errors):
            return errors
        return (
            *errors,
            {
                "stage": "udp_json_decode_summary",
                "decode_error_count_total": self.decode_error_count_total,
                "decode_error_count_recorded": len(self.decode_errors),
                "decode_error_count_dropped": self.decode_error_count_total
                - len(self.decode_errors),
            },
        )


def iter_json_fixture_messages(path: Path) -> Iterator[dict[str, Any]]:
    """Read a JSON-array or JSON-lines fixture into decoded message dicts."""

    text = path.read_text(encoding="utf-8")
    stripped = text.strip()
    if not stripped:
        return
    if stripped.startswith("["):
        try:
            payload = json.loads(stripped)
        except json.JSONDecodeError as exc:
            raise TelemetryClientError(
                f"invalid JSON telemetry fixture array {path.name}: {exc}"
            ) from exc
        if not isinstance(payload, list):
            raise TelemetryClientError("JSON telemetry fixture array must contain messages")
        for index, item in enumerate(payload):
            yield _ensure_message_dict(item, index=index)
        return

    for index, line in enumerate(stripped.splitlines()):
        if not line.strip():
            continue
        try:
            payload = json.loads(line)
        except json.JSONDecodeError as exc:
            raise TelemetryClientError(
                f"invalid JSON telemetry fixture line {index}: {exc}"
            ) from exc
        yield _ensure_message_dict(payload, index=index)


def run_telemetry_probe(
    messages: Iterable[dict[str, Any]],
    *,
    source: str,
    heartbeat_timeout_s: float = 2.5,
    probe_end_monotonic_s: float | None = None,
    use_wall_clock_probe_end: bool = False,
    transport_error_provider: Callable[[], Iterable[dict[str, Any]]] | None = None,
) -> TelemetryProbeRun:
    if heartbeat_timeout_s <= 0.0:
        raise ValueError("heartbeat_timeout_s must be positive")
    if probe_end_monotonic_s is not None and use_wall_clock_probe_end:
        raise ValueError(
            "probe_end_monotonic_s and use_wall_clock_probe_end are mutually exclusive"
        )

    histogram: Counter[str] = Counter()
    parsed_counts: Counter[str] = Counter(
        {message_type: 0 for message_type in RECOGNIZED_MESSAGE_TYPES}
    )
    parse_errors: list[dict[str, Any]] = []
    velocity_probe = TelemetryProbe()
    heartbeat_monitor = HeartbeatMonitor(timeout_s=heartbeat_timeout_s)
    heartbeat_observed = False
    last_monotonic_s = 0.0
    message_refs: list[dict[str, Any]] = []
    message_count = 0

    for index, message in enumerate(messages):
        message_count += 1
        message_type = message_type_name(message)
        histogram[message_type] += 1
        try:
            last_monotonic_s = _message_monotonic_s(message, index=index)
        except TelemetryClientError as exc:
            parse_errors.append(
                {
                    "index": index,
                    "message_type": message_type,
                    "stage": "timestamp",
                    "canonical_frame_id": _best_effort_frame_id(
                        message,
                        index=index,
                        message_type=message_type,
                    ),
                    "timestamp_source": _best_effort_timestamp_source(message),
                    "error": str(exc),
                }
            )
            continue
        message_ref = _message_reference(
            message,
            index=index,
            message_type=message_type,
            monotonic_s=last_monotonic_s,
        )
        message_refs.append(message_ref)
        error_context = _parse_error_context(message_ref)
        try:
            velocity_probe.observe(message)
        except (TelemetryError, TypeError, ValueError) as exc:
            parse_errors.append(
                {
                    "index": index,
                    "message_type": message_type,
                    "stage": "velocity_probe",
                    **error_context,
                    "error": str(exc),
                }
            )

        try:
            if message_type == "HEARTBEAT":
                parse_heartbeat(message)
                heartbeat_monitor.observe(last_monotonic_s)
                heartbeat_observed = True
                parsed_counts[message_type] += 1
            elif message_type == "ATTITUDE":
                parse_attitude(message)
                parsed_counts[message_type] += 1
            elif message_type == "HIGHRES_IMU":
                parse_highres_imu(message)
                parsed_counts[message_type] += 1
            elif message_type == "TIMESYNC":
                parse_timesync(message)
                parsed_counts[message_type] += 1
        except (TelemetryError, TypeError, ValueError) as exc:
            parse_errors.append(
                {
                    "index": index,
                    "message_type": message_type,
                    **error_context,
                    "error": str(exc),
                }
            )

    probe_end_s = _probe_end_monotonic_s(
        probe_end_monotonic_s,
        last_message_monotonic_s=last_monotonic_s,
        use_wall_clock_probe_end=use_wall_clock_probe_end,
    )

    return TelemetryProbeRun(
        schema_version="aigp.telemetry_probe.v0",
        source=source,
        input_contract=(
            "decoded MAVLink-like dictionaries; UDP JSON mode is local smoke only and "
            "does not decode binary MAVLink 2 packets"
        ),
        probe_end_monotonic_s=probe_end_s,
        message_count=message_count,
        message_refs=tuple(message_refs),
        transport_errors=tuple(transport_error_provider() if transport_error_provider else ()),
        message_type_histogram=dict(sorted(histogram.items())),
        parsed_counts=dict(sorted(parsed_counts.items())),
        parse_errors=tuple(parse_errors),
        heartbeat_observed=heartbeat_observed,
        heartbeat_fresh_at_end=heartbeat_monitor.is_fresh(probe_end_s),
        velocity_report=_velocity_report_to_json(velocity_probe.report()),
        non_claims=(
            "not official simulator telemetry evidence",
            "not binary MAVLink decoding evidence",
            "not a velocity availability claim for the official simulator",
            "not a latency benchmark",
        ),
    )


def telemetry_probe_to_json_dict(run: TelemetryProbeRun) -> dict[str, Any]:
    return asdict(run)


def write_probe_json(path: Path, run: TelemetryProbeRun) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        _canonical_json_dumps(telemetry_probe_to_json_dict(run)) + "\n",
        encoding="utf-8",
    )


def _velocity_report_to_json(report: VelocityProbeReport) -> dict[str, Any]:
    return {
        "status": str(report.status),
        "inspected_message_types": list(report.inspected_message_types),
        "candidates": [
            {
                "source_message": candidate.source_message,
                "source_fields": list(candidate.source_fields),
                "velocity_m_s": list(candidate.velocity_m_s),
            }
            for candidate in report.candidates
        ],
    }


def _ensure_message_dict(value: Any, *, index: int) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise TelemetryClientError(f"telemetry fixture item {index} must be an object")
    return value


def _message_monotonic_s(message: dict[str, Any], *, index: int) -> float:
    value = message.get("_monotonic_s")
    timestamp_source = "_monotonic_s"
    if value is None and "time_usec" in message:
        timestamp_source = "time_usec"
        value = (
            _coerce_timestamp(
                message["time_usec"],
                index=index,
                timestamp_source=timestamp_source,
            )
            / 1_000_000.0
        )
    if value is None and "time_boot_ms" in message:
        timestamp_source = "time_boot_ms"
        value = (
            _coerce_timestamp(
                message["time_boot_ms"],
                index=index,
                timestamp_source=timestamp_source,
            )
            / 1_000.0
        )
    if value is None:
        raise TelemetryClientError(
            f"telemetry message {index} must include _monotonic_s or a MAVLink time field"
        )
    monotonic_s = _coerce_timestamp(value, index=index, timestamp_source=timestamp_source)
    if not math.isfinite(monotonic_s) or monotonic_s < 0.0:
        raise TelemetryClientError(f"{timestamp_source} must be finite and non-negative")
    return monotonic_s


def _coerce_timestamp(value: Any, *, index: int, timestamp_source: str) -> float:
    try:
        return float(value)
    except (TypeError, ValueError) as exc:
        raise TelemetryClientError(
            f"invalid {timestamp_source} timestamp for telemetry message {index}: {exc}"
        ) from exc


def _probe_end_monotonic_s(
    probe_end_monotonic_s: float | None,
    *,
    last_message_monotonic_s: float,
    use_wall_clock_probe_end: bool,
) -> float:
    if use_wall_clock_probe_end:
        return time.monotonic()
    if probe_end_monotonic_s is None:
        return last_message_monotonic_s
    probe_end_s = float(probe_end_monotonic_s)
    if not math.isfinite(probe_end_s) or probe_end_s < 0.0:
        raise TelemetryClientError("probe_end_monotonic_s must be finite and non-negative")
    return probe_end_s


def _message_reference(
    message: dict[str, Any],
    *,
    index: int,
    message_type: str,
    monotonic_s: float,
) -> dict[str, Any]:
    timestamp_source, source_timestamp = _source_timestamp(
        message,
        fallback_monotonic_s=monotonic_s,
    )
    frame_id_source, frame_id = _source_frame_id(message, index=index, message_type=message_type)
    return {
        "index": index,
        "message_type": message_type,
        "canonical_timestamp_s": monotonic_s,
        "timestamp_source": timestamp_source,
        "source_timestamp": source_timestamp,
        "canonical_frame_id": frame_id,
        "frame_id_source": frame_id_source,
    }


def _parse_error_context(message_ref: dict[str, Any]) -> dict[str, Any]:
    return {
        "canonical_frame_id": message_ref["canonical_frame_id"],
        "canonical_timestamp_s": message_ref["canonical_timestamp_s"],
        "timestamp_source": message_ref["timestamp_source"],
    }


def _source_timestamp(
    message: dict[str, Any],
    *,
    fallback_monotonic_s: float,
) -> tuple[str, str | int | float | bool | None]:
    if message.get("_monotonic_s") is not None:
        return "_monotonic_s", _json_scalar(message["_monotonic_s"])
    if message.get("time_usec") is not None:
        return "time_usec", _json_scalar(message["time_usec"])
    if message.get("time_boot_ms") is not None:
        return "time_boot_ms", _json_scalar(message["time_boot_ms"])
    return "synthetic:index", fallback_monotonic_s


def _source_frame_id(
    message: dict[str, Any],
    *,
    index: int,
    message_type: str,
) -> tuple[str, str]:
    for field_name in ("_frame_id", "frame_id", "seq", "sequence"):
        value = message.get(field_name)
        if value is not None:
            return field_name, str(value)
    return "synthetic:index", f"{message_type}:{index:06d}"


def _best_effort_frame_id(message: dict[str, Any], *, index: int, message_type: str) -> str:
    _, frame_id = _source_frame_id(message, index=index, message_type=message_type)
    return frame_id


def _best_effort_timestamp_source(message: dict[str, Any]) -> str:
    for field_name in ("_monotonic_s", "time_usec", "time_boot_ms"):
        if field_name in message:
            return field_name
    return "missing"


def _json_scalar(value: Any) -> str | int | float | bool | None:
    if isinstance(value, str | int | float | bool) or value is None:
        return value
    return str(value)


def _canonical_json_dumps(value: Any) -> str:
    return _canonical_json_value(value, level=0)


def _canonical_json_value(value: Any, *, level: int) -> str:
    indent = "  "
    current_indent = indent * level
    next_indent = indent * (level + 1)
    if isinstance(value, dict):
        if not value:
            return "{}"
        lines = ["{"]
        for index, key in enumerate(sorted(value)):
            if not isinstance(key, str):
                raise TypeError("canonical JSON object keys must be strings")
            suffix = "," if index < len(value) - 1 else ""
            lines.append(
                f"{next_indent}{json.dumps(key)}: "
                f"{_canonical_json_value(value[key], level=level + 1)}{suffix}"
            )
        lines.append(f"{current_indent}}}")
        return "\n".join(lines)
    if isinstance(value, list | tuple):
        if not value:
            return "[]"
        lines = ["["]
        for index, item in enumerate(value):
            suffix = "," if index < len(value) - 1 else ""
            lines.append(f"{next_indent}{_canonical_json_value(item, level=level + 1)}{suffix}")
        lines.append(f"{current_indent}]")
        return "\n".join(lines)
    if isinstance(value, str):
        return json.dumps(value)
    if isinstance(value, bool):
        return "true" if value else "false"
    if value is None:
        return "null"
    if isinstance(value, int):
        return str(value)
    if isinstance(value, float):
        return _canonical_float(value)
    raise TypeError(f"unsupported canonical JSON value type: {type(value).__name__}")


def _canonical_float(value: float) -> str:
    if not math.isfinite(value):
        raise ValueError("canonical JSON floats must be finite")
    text = f"{value:.9f}".rstrip("0").rstrip(".")
    if text in ("", "-0"):
        text = "0"
    if "." not in text:
        text = f"{text}.0"
    return text
