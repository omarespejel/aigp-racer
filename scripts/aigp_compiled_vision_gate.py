"""Measure a compiled/vectorized local vision path for the minimal loop."""

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
from pathlib import Path
from typing import Any

from estimation.state import EstimatorInputs, MinimalStateEstimator
from mavlink.command_intent import build_position_target_body_velocity_intent
from mavlink.telemetry import Attitude, HighresImu
from perception.detector import (
    GateDetectionResult,
    GateDetectionStatus,
    GateObservation,
)
from perception.geometry import GateMeasurementBasis, ImagePoint
from solver.baseline import ConservativeController
from vision.reassembler import JpegFrameReassembler, VisionChunkHeader, pack_header

SCHEMA_VERSION = "aigp.compiled_vision_latency.v0"
GITHUB_ISSUE = "https://github.com/omarespejel/aigp-racer/issues/28"
CLAIM_BOUNDARY = (
    "local fixture timing only; modules are assembled from frame reassembly through "
    "command intent, but no official simulator, UDP socket, or MAVLink send path is exercised"
)
DEFAULT_ITERATIONS = 1000
DEFAULT_WARMUP = 5
DEFAULT_CHUNK_COUNT = 4
DEFAULT_FIXTURE = Path("tests/fixtures/frame_640x360_synthetic.jpg")
DEFAULT_EVIDENCE = Path("docs/engineering/evidence/compiled-vision-latency-2026-06-08.json")
DEFAULT_CANDIDATE = "opencv_vectorized"
EXPECTED_OPENCV_VERSION = "4.13.0.92"
EXPECTED_NUMPY_VERSION = "2.4.6"
DEFAULT_FRAME_BUDGET_MS = 33.333333
DEFAULT_COMMAND_BUDGET_MS = 10.526316
TECHNICAL_SPEC_SOURCE = (
    "AI Grand Prix Technical Specification VADR-TS-002, Issue 00.02, 2026-05-08; "
    "camera 30 Hz and command rate <100 Hz"
)
TECHNICAL_SPEC_URL = (
    "https://www.theaigrandprix.com/wp-content/uploads/2026/05/260508_Technical_Spec_0002.pdf"
)
STAGES = ("reassemble", "decode", "detect", "estimate", "control", "intent")
NON_CLAIMS = (
    "not official simulator latency evidence",
    "not official simulator frame evidence",
    "not a valid-run result",
    "not Round 2 detector evidence",
    "not a final runtime dependency decision",
    "not Windows packaging proof",
)


class CompiledVisionGateError(ValueError):
    """Raised when compiled vision evidence cannot run or validate."""


@dataclass(frozen=True)
class CompiledVisionConfig:
    iterations: int = DEFAULT_ITERATIONS
    warmup: int = DEFAULT_WARMUP
    chunk_count: int = DEFAULT_CHUNK_COUNT
    frame_budget_ms: float = DEFAULT_FRAME_BUDGET_MS
    decode_detect_budget_ms: float = 25.0
    command_budget_ms: float = DEFAULT_COMMAND_BUDGET_MS

    def __post_init__(self) -> None:
        if self.iterations <= 0:
            raise CompiledVisionGateError("iterations must be positive")
        if self.warmup < 0:
            raise CompiledVisionGateError("warmup must be non-negative")
        if self.chunk_count <= 0:
            raise CompiledVisionGateError("chunk_count must be positive")
        if self.frame_budget_ms <= 0.0:
            raise CompiledVisionGateError("frame_budget_ms must be positive")
        if self.decode_detect_budget_ms <= 0.0:
            raise CompiledVisionGateError("decode_detect_budget_ms must be positive")
        if self.command_budget_ms <= 0.0:
            raise CompiledVisionGateError("command_budget_ms must be positive")


@dataclass(frozen=True)
class VisionCandidate:
    name: str
    decode: Callable[[bytes], object]
    detect: Callable[[object, int, int], GateDetectionResult]
    dependency_note: str
    windows_packaging_note: str
    opencv_version: str
    numpy_version: str


def discover_candidate(name: str) -> VisionCandidate:
    if name != DEFAULT_CANDIDATE:
        raise CompiledVisionGateError(f"unsupported candidate {name}")
    return _discover_opencv_candidate()


def build_report(
    *,
    fixture_path: Path,
    candidate: VisionCandidate,
    config: CompiledVisionConfig,
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
    clock = time.perf_counter_ns if clock_ns is None else clock_ns
    for index in range(config.warmup + config.iterations):
        output = _run_once(datagrams=datagrams, candidate=candidate, clock_ns=clock)
        if index >= config.warmup:
            for stage in STAGES:
                stage_samples_ms[stage].append(output["stage_latency_ms"][stage])
            total_samples_ms.append(output["total_latency_ms"])
            last_output = output["summary"]
    if last_output is None:
        raise CompiledVisionGateError("no measured loop outputs")

    stage_latency = {
        stage: _latency_summary(samples) for stage, samples in stage_samples_ms.items()
    }
    total_latency = _latency_summary(total_samples_ms)
    total_p99_ms = float(total_latency["p99"])
    decode_p99_ms = float(stage_latency["decode"]["p99"])
    detect_p99_ms = float(stage_latency["detect"]["p99"])
    control_p99_ms = float(stage_latency["control"]["p99"])
    intent_p99_ms = float(stage_latency["intent"]["p99"])
    return {
        "schema_version": SCHEMA_VERSION,
        "github_issue": GITHUB_ISSUE,
        "baseline_issue": "https://github.com/omarespejel/aigp-racer/issues/24",
        "claim_boundary": CLAIM_BOUNDARY,
        "fixture": {
            "path": fixture_path.as_posix(),
            "size_bytes": len(fixture_bytes),
            "sha256": hashlib.sha256(fixture_bytes).hexdigest(),
            "chunk_count": config.chunk_count,
        },
        "candidate": {
            "name": candidate.name,
            "opencv_version": candidate.opencv_version,
            "numpy_version": candidate.numpy_version,
            "dependency_note": candidate.dependency_note,
            "windows_packaging_note": candidate.windows_packaging_note,
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
            "decode_detect_budget_ms": _format_decimal(config.decode_detect_budget_ms),
            "command_budget_ms": _format_decimal(config.command_budget_ms),
            "budget_source": TECHNICAL_SPEC_SOURCE,
            "budget_source_url": TECHNICAL_SPEC_URL,
        },
        "stage_latency_ms": stage_latency,
        "total_latency_ms": total_latency,
        "passes_frame_p99_budget": total_p99_ms <= config.frame_budget_ms,
        "passes_decode_plus_detect_p99_budget": (
            decode_p99_ms + detect_p99_ms <= config.decode_detect_budget_ms
        ),
        "passes_command_p99_budget": (control_p99_ms + intent_p99_ms <= config.command_budget_ms),
        "last_output": last_output,
        "non_claims": list(NON_CLAIMS),
    }


def validate_report(
    report: object,
    *,
    fixture_path: Path,
    expected_config: CompiledVisionConfig | None = None,
) -> None:
    config_expectation = CompiledVisionConfig() if expected_config is None else expected_config
    if not isinstance(report, dict):
        raise CompiledVisionGateError("report root must be an object")
    if report.get("schema_version") != SCHEMA_VERSION:
        raise CompiledVisionGateError("schema_version drifted")
    if report.get("github_issue") != GITHUB_ISSUE:
        raise CompiledVisionGateError("github_issue drifted")
    if report.get("baseline_issue") != "https://github.com/omarespejel/aigp-racer/issues/24":
        raise CompiledVisionGateError("baseline_issue drifted")
    if report.get("claim_boundary") != CLAIM_BOUNDARY:
        raise CompiledVisionGateError("claim_boundary drifted")
    if report.get("non_claims") != list(NON_CLAIMS):
        raise CompiledVisionGateError("non_claims drifted")
    _validate_fixture(report.get("fixture"), fixture_path, config_expectation)
    _validate_candidate(report.get("candidate"))
    config = _validate_config(report.get("config"), config_expectation)
    stage_latency = report.get("stage_latency_ms")
    if not isinstance(stage_latency, dict):
        raise CompiledVisionGateError("stage_latency_ms must be an object")
    for stage in STAGES:
        if stage not in stage_latency:
            raise CompiledVisionGateError(f"missing stage latency for {stage}")
        _validate_latency_summary(stage_latency[stage], f"stage_latency_ms.{stage}")
    _validate_latency_summary(report.get("total_latency_ms"), "total_latency_ms")
    total_latency = report["total_latency_ms"]
    expected_frame = (
        _fixed_decimal_to_float(total_latency["p99"], "total_latency_ms.p99")
        <= config["frame_budget_ms"]
    )
    expected_decode_detect = (
        _fixed_decimal_to_float(stage_latency["decode"]["p99"], "stage_latency_ms.decode.p99")
        + _fixed_decimal_to_float(stage_latency["detect"]["p99"], "stage_latency_ms.detect.p99")
        <= config["decode_detect_budget_ms"]
    )
    expected_command = (
        _fixed_decimal_to_float(stage_latency["control"]["p99"], "stage_latency_ms.control.p99")
        + _fixed_decimal_to_float(stage_latency["intent"]["p99"], "stage_latency_ms.intent.p99")
        <= config["command_budget_ms"]
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


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


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


def _run_once(
    *,
    datagrams: tuple[bytes, ...],
    candidate: VisionCandidate,
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
        raise CompiledVisionGateError("fixture datagrams did not produce a complete frame")
    stage_latency["reassemble"] = _elapsed_ms(start_ns, end_ns)

    start_ns = clock_ns()
    decoded = candidate.decode(frame.jpeg)
    end_ns = clock_ns()
    stage_latency["decode"] = _elapsed_ms(start_ns, end_ns)

    start_ns = clock_ns()
    detection = candidate.detect(decoded, frame.sim_time_ns, frame.frame_id)
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
            "mask_pixels": detection.mask_pixels,
            "gate_confidence": None
            if state.gate_confidence is None
            else _format_decimal(state.gate_confidence),
            "gate_z_forward_m": None
            if state.gate_pose_camera is None
            else _format_decimal(state.gate_pose_camera.z_forward_m),
            "state_status": state.status,
            "command_kind": command.kind.value,
            "command_reason": command.reason,
            "message_name": intent.message_name,
            "intent_mode": intent.mode,
        },
    }


def _discover_opencv_candidate() -> VisionCandidate:
    try:
        import cv2
        import numpy as np
    except ImportError as exc:
        raise CompiledVisionGateError(
            "opencv-python and numpy are required for --candidate opencv_vectorized"
        ) from exc

    def decode(data: bytes) -> object:
        array = np.frombuffer(data, dtype=np.uint8)
        image = cv2.imdecode(array, cv2.IMREAD_COLOR)
        if image is None:
            raise CompiledVisionGateError("OpenCV could not decode JPEG fixture")
        return image

    def detect(decoded: object, sim_time_ns: int, source_frame_id: int) -> GateDetectionResult:
        image = decoded
        if not hasattr(image, "shape") or len(image.shape) != 3 or image.shape[2] != 3:
            raise CompiledVisionGateError("OpenCV decoded image must be HxWx3")
        blue = image[:, :, 0]
        green = image[:, :, 1]
        red = image[:, :, 2]
        mask = ((red >= 180) & (blue >= 140) & (green <= 130)) | (
            (red >= 220) & (green >= 220) & (blue >= 220)
        )
        ys, xs = np.nonzero(mask)
        mask_pixels = int(xs.size)
        if mask_pixels <= 0:
            return _result(
                GateDetectionStatus.NO_HIGHLIGHT,
                sim_time_ns=sim_time_ns,
                source_frame_id=source_frame_id,
                mask_pixels=0,
            )
        min_u = int(xs.min())
        max_u = int(xs.max())
        min_v = int(ys.min())
        max_v = int(ys.max())
        width = max_u - min_u + 1
        height = max_v - min_v + 1
        if width <= 1 or height <= 1:
            return _result(
                GateDetectionStatus.DEGENERATE_BBOX,
                sim_time_ns=sim_time_ns,
                source_frame_id=source_frame_id,
                mask_pixels=mask_pixels,
            )
        confidence = mask_pixels / float(width * height)
        observation = GateObservation(
            corners=(
                ImagePoint(float(min_u), float(min_v)),
                ImagePoint(float(max_u), float(min_v)),
                ImagePoint(float(max_u), float(max_v)),
                ImagePoint(float(min_u), float(max_v)),
            ),
            confidence=confidence,
            sim_time_ns=sim_time_ns,
            source_frame_id=source_frame_id,
            source="opencv_vectorized_color_bbox",
            measurement_basis=GateMeasurementBasis.OUTER_FRAME,
            corner_uncertainty_px=_bbox_corner_uncertainty(
                mask_pixels=mask_pixels,
                width_px=width,
                height_px=height,
            ),
        )
        return GateDetectionResult(
            status=GateDetectionStatus.DETECTED,
            observation=observation,
            sim_time_ns=sim_time_ns,
            source_frame_id=source_frame_id,
            source="opencv_vectorized_color_bbox",
            mask_pixels=mask_pixels,
            confidence=confidence,
        )

    return VisionCandidate(
        name=DEFAULT_CANDIDATE,
        decode=decode,
        detect=detect,
        dependency_note="OpenCV imdecode plus NumPy vectorized color threshold and bbox extraction",
        windows_packaging_note=(
            "Python 3.14 wheels installed in this macOS evidence run; Windows 11 wheel "
            "availability must be verified on the official simulator host"
        ),
        opencv_version=_package_version("opencv-python"),
        numpy_version=_package_version("numpy"),
    )


def _result(
    status: GateDetectionStatus,
    *,
    sim_time_ns: int,
    source_frame_id: int,
    mask_pixels: int,
) -> GateDetectionResult:
    return GateDetectionResult(
        status=status,
        observation=None,
        sim_time_ns=sim_time_ns,
        source_frame_id=source_frame_id,
        source="opencv_vectorized_color_bbox",
        mask_pixels=mask_pixels,
        confidence=None,
    )


def _bbox_corner_uncertainty(
    *,
    mask_pixels: int,
    width_px: int,
    height_px: int,
) -> tuple[float, float, float, float]:
    fill_ratio = mask_pixels / float(width_px * height_px)
    uncertainty_px = max(1.0, (1.0 - fill_ratio) * max(width_px, height_px) / 2.0)
    return (uncertainty_px, uncertainty_px, uncertainty_px, uncertainty_px)


def _latency_summary(samples_ms: Sequence[float]) -> dict[str, str]:
    if not samples_ms:
        raise CompiledVisionGateError("latency sample set is empty")
    return {
        "min": _format_decimal(min(samples_ms)),
        "p50": _format_decimal(_percentile(samples_ms, 50)),
        "median": _format_decimal(statistics.median(samples_ms)),
        "p95": _format_decimal(_percentile(samples_ms, 95)),
        "p99": _format_decimal(_percentile(samples_ms, 99)),
        "max": _format_decimal(max(samples_ms)),
    }


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
        raise CompiledVisionGateError("clock moved backward")
    return (end_ns - start_ns) / 1_000_000.0


def _format_decimal(value: float) -> str:
    return f"{value:.6f}"


def _is_fixed_decimal(value: str) -> bool:
    parts = value.split(".")
    return len(parts) == 2 and parts[0].isdigit() and len(parts[1]) == 6 and parts[1].isdigit()


def _fixed_decimal_to_float(value: object, path: str) -> float:
    if not isinstance(value, str) or not _is_fixed_decimal(value):
        raise CompiledVisionGateError(f"{path} must be a fixed decimal string")
    return float(value)


def _validate_fixture(
    value: object,
    fixture_path: Path,
    expected_config: CompiledVisionConfig,
) -> None:
    if not isinstance(value, dict):
        raise CompiledVisionGateError("fixture must be an object")
    fixture_bytes = fixture_path.read_bytes()
    if value.get("sha256") != hashlib.sha256(fixture_bytes).hexdigest():
        raise CompiledVisionGateError("fixture sha256 drifted")
    if type(value.get("size_bytes")) is not int or value.get("size_bytes") != len(fixture_bytes):
        raise CompiledVisionGateError("fixture size drifted")
    if Path(str(value.get("path"))).as_posix() != fixture_path.as_posix():
        raise CompiledVisionGateError("fixture path drifted")
    if (
        type(value.get("chunk_count")) is not int
        or value.get("chunk_count") != expected_config.chunk_count
    ):
        raise CompiledVisionGateError("fixture chunk_count drifted")


def _validate_candidate(value: object) -> None:
    if not isinstance(value, dict):
        raise CompiledVisionGateError("candidate must be an object")
    if value.get("name") != DEFAULT_CANDIDATE:
        raise CompiledVisionGateError("candidate.name drifted")
    if value.get("opencv_version") != EXPECTED_OPENCV_VERSION:
        raise CompiledVisionGateError("candidate.opencv_version drifted")
    if value.get("numpy_version") != EXPECTED_NUMPY_VERSION:
        raise CompiledVisionGateError("candidate.numpy_version drifted")
    if "OpenCV imdecode" not in str(value.get("dependency_note")):
        raise CompiledVisionGateError("candidate.dependency_note drifted")
    if "Windows 11" not in str(value.get("windows_packaging_note")):
        raise CompiledVisionGateError("candidate.windows_packaging_note drifted")


def _validate_config(
    value: object,
    expected_config: CompiledVisionConfig,
) -> dict[str, float]:
    if not isinstance(value, dict):
        raise CompiledVisionGateError("config must be an object")
    if type(value.get("iterations")) is not int or value.get("iterations") != (
        expected_config.iterations
    ):
        raise CompiledVisionGateError("config.iterations drifted")
    if type(value.get("warmup")) is not int or value.get("warmup") != expected_config.warmup:
        raise CompiledVisionGateError("config.warmup drifted")
    if value.get("budget_source") != TECHNICAL_SPEC_SOURCE:
        raise CompiledVisionGateError("config.budget_source drifted")
    if value.get("budget_source_url") != TECHNICAL_SPEC_URL:
        raise CompiledVisionGateError("config.budget_source_url drifted")
    frame_budget_ms = _fixed_decimal_to_float(
        value.get("frame_budget_ms"), "config.frame_budget_ms"
    )
    if value.get("frame_budget_ms") != _format_decimal(expected_config.frame_budget_ms):
        raise CompiledVisionGateError("config.frame_budget_ms drifted")
    decode_detect_budget_ms = _fixed_decimal_to_float(
        value.get("decode_detect_budget_ms"), "config.decode_detect_budget_ms"
    )
    if value.get("decode_detect_budget_ms") != _format_decimal(
        expected_config.decode_detect_budget_ms
    ):
        raise CompiledVisionGateError("config.decode_detect_budget_ms drifted")
    command_budget_ms = _fixed_decimal_to_float(
        value.get("command_budget_ms"), "config.command_budget_ms"
    )
    if value.get("command_budget_ms") != _format_decimal(expected_config.command_budget_ms):
        raise CompiledVisionGateError("config.command_budget_ms drifted")
    return {
        "frame_budget_ms": frame_budget_ms,
        "decode_detect_budget_ms": decode_detect_budget_ms,
        "command_budget_ms": command_budget_ms,
    }


def _validate_latency_summary(value: object, path: str) -> None:
    if not isinstance(value, dict):
        raise CompiledVisionGateError(f"{path} must be an object")
    for key in ("min", "p50", "median", "p95", "p99", "max"):
        item = value.get(key)
        if not isinstance(item, str) or not _is_fixed_decimal(item):
            raise CompiledVisionGateError(f"{path}.{key} must be a fixed decimal string")


def _validate_budget_bool(*, report: dict[str, Any], key: str, expected: bool) -> None:
    value = report.get(key)
    if not isinstance(value, bool):
        raise CompiledVisionGateError(f"{key} must be a bool")
    if value != expected:
        raise CompiledVisionGateError(f"{key} does not match reported p99 latencies")


def _package_version(name: str) -> str:
    try:
        return importlib.metadata.version(name)
    except importlib.metadata.PackageNotFoundError:
        return "unknown"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--fixture", type=Path, default=DEFAULT_FIXTURE)
    parser.add_argument("--candidate", choices=(DEFAULT_CANDIDATE,), default=DEFAULT_CANDIDATE)
    parser.add_argument("--iterations", type=int, default=DEFAULT_ITERATIONS)
    parser.add_argument("--warmup", type=int, default=DEFAULT_WARMUP)
    parser.add_argument("--write-json", type=Path)
    parser.add_argument("--check-json", type=Path)
    args = parser.parse_args()
    if args.write_json is None and args.check_json is None:
        parser.error("one of --write-json or --check-json is required")
    expected_config = CompiledVisionConfig(iterations=args.iterations, warmup=args.warmup)
    if args.write_json is not None:
        report = build_report(
            fixture_path=args.fixture,
            candidate=discover_candidate(args.candidate),
            config=expected_config,
        )
        write_json(args.write_json, report)
    if args.check_json is not None:
        report = json.loads(args.check_json.read_text(encoding="utf-8"))
        validate_report(report, fixture_path=args.fixture, expected_config=expected_config)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
