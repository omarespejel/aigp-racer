"""Measure a minimal local camera-to-command loop."""

from __future__ import annotations

import argparse
import hashlib
import importlib.metadata
import json
import platform
import statistics
import sys
import time
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from io import BytesIO
from pathlib import Path
from typing import Any

from estimation.state import EstimatorInputs, MinimalStateEstimator
from mavlink.command_intent import build_position_target_body_velocity_intent
from mavlink.telemetry import Attitude, HighresImu
from perception.detector import RGBImage, Round1ColorGateDetector
from solver.baseline import ConservativeController
from vision.reassembler import JpegFrameReassembler, VisionChunkHeader, pack_header

SCHEMA_VERSION = "aigp.minimal_loop_latency.v0"
DEFAULT_ITERATIONS = 100
DEFAULT_WARMUP = 5
DEFAULT_CHUNK_COUNT = 4
DEFAULT_DECODER = "pillow"
EXPECTED_DECODER_VERSION = "12.2.0"
DEFAULT_FRAME_BUDGET_MS = 33.333333
DEFAULT_COMMAND_BUDGET_MS = 10.526316
DEFAULT_FIXTURE = Path("tests/fixtures/frame_640x360_synthetic.jpg")
DEFAULT_EVIDENCE = Path("docs/engineering/evidence/minimal-loop-latency-2026-06-08.json")
CLAIM_BOUNDARY = (
    "local fixture timing only; modules are assembled from frame reassembly through "
    "command intent, but no official simulator, UDP socket, or MAVLink send path is exercised"
)
TECHNICAL_SPEC_SOURCE = (
    "AI Grand Prix Technical Specification VADR-TS-002, Issue 00.02, 2026-05-08; "
    "camera 30 Hz and command rate <100 Hz"
)
TECHNICAL_SPEC_URL = (
    "https://www.theaigrandprix.com/wp-content/uploads/2026/05/260508_Technical_Spec_0002.pdf"
)
PILLOW_DEPENDENCY_NOTE = "Pillow JPEG decode plus Python RGB row materialization"
PILLOW_WINDOWS_PACKAGING_NOTE = (
    "not evaluated in this local artifact; verify Windows 11 and Python 3.14 "
    "wheel availability before any runtime dependency decision"
)
STAGES = ("reassemble", "decode", "detect", "estimate", "control", "intent")
NON_CLAIMS = (
    "not official simulator latency evidence",
    "not a valid-run result",
    "not a lap-time, reliability, or win claim",
    "not proof that pure Python is sufficient for the final runtime",
    "not Windows packaging evidence",
    "not Round 2 detector evidence",
)


class MinimalLoopError(ValueError):
    """Raised when the minimal loop cannot run or validate."""


@dataclass(frozen=True)
class LoopConfig:
    iterations: int = DEFAULT_ITERATIONS
    warmup: int = DEFAULT_WARMUP
    chunk_count: int = DEFAULT_CHUNK_COUNT
    frame_budget_ms: float = DEFAULT_FRAME_BUDGET_MS
    command_budget_ms: float = DEFAULT_COMMAND_BUDGET_MS

    def __post_init__(self) -> None:
        if self.iterations <= 0:
            raise MinimalLoopError("iterations must be positive")
        if self.warmup < 0:
            raise MinimalLoopError("warmup must be non-negative")
        if self.chunk_count <= 0:
            raise MinimalLoopError("chunk_count must be positive")
        if self.frame_budget_ms <= 0.0:
            raise MinimalLoopError("frame_budget_ms must be positive")
        if self.command_budget_ms <= 0.0:
            raise MinimalLoopError("command_budget_ms must be positive")


@dataclass(frozen=True)
class FrameDecoder:
    name: str
    decode: Callable[[bytes], RGBImage]
    dependency_note: str
    windows_packaging_note: str
    version: str | None = None


def discover_decoder(name: str) -> FrameDecoder:
    if name == "pillow":
        return _discover_pillow_decoder()
    if name == "synthetic_rgb":
        return FrameDecoder(
            name="synthetic_rgb",
            decode=lambda _: _synthetic_rgb_frame(),
            dependency_note="deterministic decoded-RGB fixture; does not decode JPEG bytes",
            windows_packaging_note="not a runtime decoder and not valid JPEG-decode evidence",
            version=None,
        )
    raise MinimalLoopError(f"unsupported decoder {name}")


def build_report(
    *,
    fixture_path: Path,
    decoder: FrameDecoder,
    config: LoopConfig,
    clock_ns: Callable[[], int] | None = None,
) -> dict[str, Any]:
    fixture_bytes = fixture_path.read_bytes()
    datagrams = tuple(
        _chunk_datagram(
            frame_id=1,
            sim_time_ns=33_333_333,
            chunk_id=index,
            total_chunks=config.chunk_count,
            jpeg_bytes=fixture_bytes,
        )
        for index in range(config.chunk_count)
    )

    stage_samples_ms: dict[str, list[float]] = {stage: [] for stage in STAGES}
    total_samples_ms: list[float] = []
    last_output: dict[str, Any] | None = None
    total_runs = config.warmup + config.iterations
    clock = time.perf_counter_ns if clock_ns is None else clock_ns
    for run_index in range(total_runs):
        output = _run_once(datagrams=datagrams, decoder=decoder, clock_ns=clock)
        if run_index >= config.warmup:
            for stage in STAGES:
                stage_samples_ms[stage].append(output["stage_latency_ms"][stage])
            total_samples_ms.append(output["total_latency_ms"])
            last_output = output["summary"]

    if last_output is None:
        raise MinimalLoopError("no measured loop outputs")

    stage_latency = {
        stage: _latency_summary(samples) for stage, samples in stage_samples_ms.items()
    }
    total_latency = _latency_summary(total_samples_ms)
    total_p99_ms = float(total_latency["p99"])
    detect_p99_ms = float(stage_latency["detect"]["p99"])
    decode_p99_ms = float(stage_latency["decode"]["p99"])
    control_p99_ms = float(stage_latency["control"]["p99"])
    intent_p99_ms = float(stage_latency["intent"]["p99"])
    return {
        "schema_version": SCHEMA_VERSION,
        "github_issue": "https://github.com/omarespejel/aigp-racer/issues/24",
        "claim_boundary": CLAIM_BOUNDARY,
        "fixture": {
            "path": str(fixture_path),
            "size_bytes": len(fixture_bytes),
            "sha256": hashlib.sha256(fixture_bytes).hexdigest(),
            "chunk_count": config.chunk_count,
        },
        "decoder": {
            "name": decoder.name,
            "version": decoder.version,
            "dependency_note": decoder.dependency_note,
            "windows_packaging_note": decoder.windows_packaging_note,
        },
        "environment": {
            "python_version": sys.version.split()[0],
            "platform": platform.platform(),
            "machine": platform.machine(),
            "processor": platform.processor(),
        },
        "config": {
            "iterations": config.iterations,
            "warmup": config.warmup,
            "frame_budget_ms": _format_decimal(config.frame_budget_ms),
            "command_budget_ms": _format_decimal(config.command_budget_ms),
            "budget_source": TECHNICAL_SPEC_SOURCE,
            "budget_source_url": TECHNICAL_SPEC_URL,
        },
        "stage_latency_ms": stage_latency,
        "total_latency_ms": total_latency,
        "passes_frame_p99_budget": total_p99_ms <= config.frame_budget_ms,
        "passes_decode_plus_detect_p99_budget": (
            decode_p99_ms + detect_p99_ms <= config.frame_budget_ms
        ),
        "passes_command_p99_budget": (control_p99_ms + intent_p99_ms <= config.command_budget_ms),
        "last_output": last_output,
        "non_claims": list(NON_CLAIMS),
    }


def validate_report(
    report: object,
    *,
    fixture_path: Path,
    expected_config: LoopConfig | None = None,
) -> None:
    config_expectation = LoopConfig() if expected_config is None else expected_config
    if not isinstance(report, dict):
        raise MinimalLoopError("report root must be an object")
    if report.get("schema_version") != SCHEMA_VERSION:
        raise MinimalLoopError("schema_version drifted")
    if report.get("github_issue") != "https://github.com/omarespejel/aigp-racer/issues/24":
        raise MinimalLoopError("github_issue drifted")
    if report.get("claim_boundary") != CLAIM_BOUNDARY:
        raise MinimalLoopError("claim_boundary drifted")
    if report.get("non_claims") != list(NON_CLAIMS):
        raise MinimalLoopError("non_claims drifted")
    fixture = report.get("fixture")
    if not isinstance(fixture, dict):
        raise MinimalLoopError("fixture must be an object")
    fixture_bytes = fixture_path.read_bytes()
    if fixture.get("sha256") != hashlib.sha256(fixture_bytes).hexdigest():
        raise MinimalLoopError("fixture sha256 drifted")
    if type(fixture.get("size_bytes")) is not int or fixture.get("size_bytes") != len(
        fixture_bytes
    ):
        raise MinimalLoopError("fixture size drifted")
    if fixture.get("path") != str(fixture_path):
        raise MinimalLoopError("fixture path drifted")
    if (
        type(fixture.get("chunk_count")) is not int
        or fixture.get("chunk_count") != config_expectation.chunk_count
    ):
        raise MinimalLoopError("fixture chunk_count drifted")
    decoder = report.get("decoder")
    if not isinstance(decoder, dict):
        raise MinimalLoopError("decoder must be an object")
    if decoder.get("name") != DEFAULT_DECODER:
        raise MinimalLoopError("decoder.name drifted")
    if decoder.get("version") != EXPECTED_DECODER_VERSION:
        raise MinimalLoopError("decoder.version drifted")
    if decoder.get("dependency_note") != PILLOW_DEPENDENCY_NOTE:
        raise MinimalLoopError("decoder.dependency_note drifted")
    if decoder.get("windows_packaging_note") != PILLOW_WINDOWS_PACKAGING_NOTE:
        raise MinimalLoopError("decoder.windows_packaging_note drifted")
    config = report.get("config")
    if not isinstance(config, dict):
        raise MinimalLoopError("config must be an object")
    if config.get("budget_source") != TECHNICAL_SPEC_SOURCE:
        raise MinimalLoopError("config.budget_source drifted")
    if config.get("budget_source_url") != TECHNICAL_SPEC_URL:
        raise MinimalLoopError("config.budget_source_url drifted")
    iterations = config.get("iterations")
    if type(iterations) is not int or iterations != config_expectation.iterations:
        raise MinimalLoopError("config.iterations drifted")
    warmup = config.get("warmup")
    if type(warmup) is not int or warmup != config_expectation.warmup:
        raise MinimalLoopError("config.warmup drifted")
    frame_budget_ms = _fixed_decimal_to_float(
        config.get("frame_budget_ms"), "config.frame_budget_ms"
    )
    if config.get("frame_budget_ms") != _format_decimal(config_expectation.frame_budget_ms):
        raise MinimalLoopError("config.frame_budget_ms drifted")
    command_budget_ms = _fixed_decimal_to_float(
        config.get("command_budget_ms"), "config.command_budget_ms"
    )
    if config.get("command_budget_ms") != _format_decimal(config_expectation.command_budget_ms):
        raise MinimalLoopError("config.command_budget_ms drifted")
    stage_latency = report.get("stage_latency_ms")
    if not isinstance(stage_latency, dict):
        raise MinimalLoopError("stage_latency_ms must be an object")
    for stage in STAGES:
        if stage not in stage_latency:
            raise MinimalLoopError(f"missing stage latency for {stage}")
        _validate_latency_summary(stage_latency[stage], f"stage_latency_ms.{stage}")
    _validate_latency_summary(report.get("total_latency_ms"), "total_latency_ms")
    total_latency = report["total_latency_ms"]
    expected_frame = (
        _fixed_decimal_to_float(total_latency["p99"], "total_latency_ms.p99") <= frame_budget_ms
    )
    expected_decode_detect = (
        _fixed_decimal_to_float(stage_latency["decode"]["p99"], "stage_latency_ms.decode.p99")
        + _fixed_decimal_to_float(stage_latency["detect"]["p99"], "stage_latency_ms.detect.p99")
        <= frame_budget_ms
    )
    expected_command = (
        _fixed_decimal_to_float(stage_latency["control"]["p99"], "stage_latency_ms.control.p99")
        + _fixed_decimal_to_float(stage_latency["intent"]["p99"], "stage_latency_ms.intent.p99")
        <= command_budget_ms
    )
    _validate_budget_bool(
        report=report,
        key="passes_frame_p99_budget",
        expected=expected_frame,
    )
    _validate_budget_bool(
        report=report,
        key="passes_decode_plus_detect_p99_budget",
        expected=expected_decode_detect,
    )
    _validate_budget_bool(
        report=report,
        key="passes_command_p99_budget",
        expected=expected_command,
    )
    last_output = report.get("last_output")
    if not isinstance(last_output, dict):
        raise MinimalLoopError("last_output must be an object")
    if last_output.get("message_name") != "SET_POSITION_TARGET_LOCAL_NED":
        raise MinimalLoopError("message name drifted")
    if last_output.get("detection_status") != "DETECTED":
        raise MinimalLoopError("detection status drifted")


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _run_once(
    *,
    datagrams: tuple[bytes, ...],
    decoder: FrameDecoder,
    clock_ns: Callable[[], int],
) -> dict[str, Any]:
    reassembler = JpegFrameReassembler()
    stage_latency: dict[str, float] = {}

    frame = None
    loop_start_ns = clock_ns()
    start_ns = clock_ns()
    for datagram in datagrams:
        frame = reassembler.add_datagram(datagram)
    end_ns = clock_ns()
    if frame is None:
        raise MinimalLoopError("fixture datagrams did not produce a complete frame")
    stage_latency["reassemble"] = _elapsed_ms(start_ns, end_ns)

    start_ns = clock_ns()
    image = decoder.decode(frame.jpeg)
    end_ns = clock_ns()
    stage_latency["decode"] = _elapsed_ms(start_ns, end_ns)

    detector = Round1ColorGateDetector()
    start_ns = clock_ns()
    detection = detector.analyze(
        image,
        sim_time_ns=frame.sim_time_ns,
        source_frame_id=frame.frame_id,
    )
    end_ns = clock_ns()
    stage_latency["detect"] = _elapsed_ms(start_ns, end_ns)

    estimator = MinimalStateEstimator()
    start_ns = clock_ns()
    state = estimator.estimate(
        EstimatorInputs(
            sim_time_ns=frame.sim_time_ns,
            attitude=_attitude(),
            imu=_imu(),
            velocity=None,
            gate_observation=detection.observation,
            telemetry_age_ns=0,
        )
    )
    end_ns = clock_ns()
    stage_latency["estimate"] = _elapsed_ms(start_ns, end_ns)

    controller = ConservativeController()
    start_ns = clock_ns()
    command = controller.command(state)
    end_ns = clock_ns()
    stage_latency["control"] = _elapsed_ms(start_ns, end_ns)

    start_ns = clock_ns()
    intent = build_position_target_body_velocity_intent(command)
    end_ns = clock_ns()
    stage_latency["intent"] = _elapsed_ms(start_ns, end_ns)

    return {
        "stage_latency_ms": stage_latency,
        "total_latency_ms": _elapsed_ms(loop_start_ns, end_ns),
        "summary": {
            "frame_id": frame.frame_id,
            "sim_time_ns": frame.sim_time_ns,
            "detection_status": detection.status.value,
            "detected": detection.detected,
            "measurement_basis": None
            if detection.observation is None
            else detection.observation.measurement_basis.value,
            "state_status": state.status,
            "gate_confidence": None
            if state.gate_confidence is None
            else _format_decimal(state.gate_confidence),
            "gate_z_forward_m": None
            if state.gate_pose_camera is None
            else _format_decimal(state.gate_pose_camera.z_forward_m),
            "command_kind": command.kind.value,
            "command_reason": command.reason,
            "message_name": intent.message_name,
            "intent_mode": intent.mode,
        },
    }


def _chunk_datagram(
    *,
    frame_id: int,
    sim_time_ns: int,
    chunk_id: int,
    total_chunks: int,
    jpeg_bytes: bytes,
) -> bytes:
    chunk_size = (len(jpeg_bytes) + total_chunks - 1) // total_chunks
    start = chunk_id * chunk_size
    payload = jpeg_bytes[start : start + chunk_size]
    header = VisionChunkHeader(
        frame_id=frame_id,
        chunk_id=chunk_id,
        total_chunks=total_chunks,
        jpeg_size=len(jpeg_bytes),
        payload_size=len(payload),
        sim_time_ns=sim_time_ns,
    )
    return pack_header(header) + payload


def _discover_pillow_decoder() -> FrameDecoder:
    try:
        from PIL import Image
    except ImportError as exc:
        raise MinimalLoopError("Pillow is required for --decoder pillow") from exc

    def decode(data: bytes) -> RGBImage:
        with Image.open(BytesIO(data)) as image:
            rgb = image.convert("RGB")
            width, height = rgb.size
            pixels = rgb.tobytes()
        return [
            [
                (
                    pixels[(y * width + x) * 3],
                    pixels[(y * width + x) * 3 + 1],
                    pixels[(y * width + x) * 3 + 2],
                )
                for x in range(width)
            ]
            for y in range(height)
        ]

    return FrameDecoder(
        name="pillow",
        decode=decode,
        dependency_note=PILLOW_DEPENDENCY_NOTE,
        windows_packaging_note=PILLOW_WINDOWS_PACKAGING_NOTE,
        version=_package_version("Pillow"),
    )


def _synthetic_rgb_frame() -> list[list[tuple[int, int, int]]]:
    width_px = 640
    height_px = 360
    image = [[(12, 12, 12) for _ in range(width_px)] for _ in range(height_px)]
    for v_px in range(90, 291):
        for u_px in range(220, 421):
            on_top_or_bottom = v_px < 102 or v_px > 278
            on_left_or_right = u_px < 232 or u_px > 408
            if on_top_or_bottom or on_left_or_right:
                image[v_px][u_px] = (255, 0, 255)
    return image


def _attitude() -> Attitude:
    return Attitude(
        time_boot_ms=33,
        roll_rad=0.0,
        pitch_rad=0.0,
        yaw_rad=0.0,
        rollspeed_rad_s=0.0,
        pitchspeed_rad_s=0.0,
        yawspeed_rad_s=0.0,
    )


def _imu() -> HighresImu:
    return HighresImu(
        time_usec=33_333,
        acceleration_m_s2=(0.0, 0.0, -9.8),
        gyro_rad_s=(0.0, 0.0, 0.0),
    )


def _latency_summary(samples_ms: Sequence[float]) -> dict[str, str]:
    if not samples_ms:
        raise MinimalLoopError("latency sample set is empty")
    return {
        "min": _format_decimal(min(samples_ms)),
        "p50": _format_decimal(_percentile(samples_ms, 50)),
        "median": _format_decimal(statistics.median(samples_ms)),
        "p95": _format_decimal(_percentile(samples_ms, 95)),
        "p99": _format_decimal(_percentile(samples_ms, 99)),
        "max": _format_decimal(max(samples_ms)),
    }


def _validate_latency_summary(value: object, path: str) -> None:
    if not isinstance(value, dict):
        raise MinimalLoopError(f"{path} must be an object")
    for key in ("min", "p50", "median", "p95", "p99", "max"):
        item = value.get(key)
        if not isinstance(item, str) or not _is_fixed_decimal(item):
            raise MinimalLoopError(f"{path}.{key} must be a fixed decimal string")


def _fixed_decimal_to_float(value: object, path: str) -> float:
    if not isinstance(value, str) or not _is_fixed_decimal(value):
        raise MinimalLoopError(f"{path} must be a fixed decimal string")
    return float(value)


def _validate_budget_bool(*, report: dict[str, Any], key: str, expected: bool) -> None:
    value = report.get(key)
    if not isinstance(value, bool):
        raise MinimalLoopError(f"{key} must be a bool")
    if value != expected:
        raise MinimalLoopError(f"{key} does not match reported p99 latencies")


def _percentile(values: Sequence[float], percentile: float) -> float:
    ordered = sorted(values)
    if len(ordered) == 1:
        return ordered[0]
    rank = (len(ordered) - 1) * percentile / 100.0
    lower = int(rank)
    upper = min(lower + 1, len(ordered) - 1)
    fraction = rank - lower
    return ordered[lower] * (1.0 - fraction) + ordered[upper] * fraction


def _elapsed_ms(start_ns: int, end_ns: int) -> float:
    if end_ns < start_ns:
        raise MinimalLoopError("clock moved backward")
    return (end_ns - start_ns) / 1_000_000.0


def _format_decimal(value: float) -> str:
    return f"{value:.6f}"


def _is_fixed_decimal(value: str) -> bool:
    parts = value.split(".")
    return len(parts) == 2 and parts[0].isdigit() and len(parts[1]) == 6 and parts[1].isdigit()


def _package_version(name: str) -> str:
    try:
        return importlib.metadata.version(name)
    except importlib.metadata.PackageNotFoundError:
        return "unknown"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--fixture", type=Path, default=DEFAULT_FIXTURE)
    parser.add_argument("--decoder", choices=("pillow", "synthetic_rgb"), default=DEFAULT_DECODER)
    parser.add_argument("--iterations", type=int, default=DEFAULT_ITERATIONS)
    parser.add_argument("--warmup", type=int, default=DEFAULT_WARMUP)
    parser.add_argument("--write-json", type=Path)
    parser.add_argument("--check-json", type=Path)
    args = parser.parse_args()
    if args.write_json is None and args.check_json is None:
        parser.error("one of --write-json or --check-json is required")

    if args.write_json is not None:
        report = build_report(
            fixture_path=args.fixture,
            decoder=discover_decoder(args.decoder),
            config=LoopConfig(
                iterations=args.iterations,
                warmup=args.warmup,
                chunk_count=DEFAULT_CHUNK_COUNT,
            ),
        )
        write_json(args.write_json, report)
    if args.check_json is not None:
        report = json.loads(args.check_json.read_text(encoding="utf-8"))
        validate_report(
            report,
            fixture_path=args.fixture,
            expected_config=LoopConfig(
                iterations=args.iterations,
                warmup=args.warmup,
                chunk_count=DEFAULT_CHUNK_COUNT,
            ),
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
