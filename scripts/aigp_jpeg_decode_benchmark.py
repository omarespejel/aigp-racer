"""Benchmark optional JPEG decode paths for the AI Grand Prix vision stream."""

from __future__ import annotations

import argparse
import hashlib
import importlib.metadata
import json
import platform
import statistics
import sys
import time
from collections.abc import Callable
from dataclasses import dataclass
from io import BytesIO
from pathlib import Path
from typing import Any

SCHEMA_VERSION = "aigp.jpeg_decode_benchmark.v0"
DEFAULT_WIDTH_PX = 640
DEFAULT_HEIGHT_PX = 360
DEFAULT_ITERATIONS = 1000
DEFAULT_WARMUP = 20
DEFAULT_VISION_P99_BUDGET_MS = 25.0
SUPPORTED_DECODERS = ("pillow", "opencv", "pyturbojpeg")


class JpegBenchmarkError(ValueError):
    """Raised when the benchmark cannot run with the requested configuration."""


@dataclass(frozen=True)
class DecoderCandidate:
    name: str
    decode: Callable[[bytes], tuple[int, int, int]]
    version: str
    dependency_note: str


@dataclass(frozen=True)
class BenchmarkConfig:
    iterations: int = DEFAULT_ITERATIONS
    warmup: int = DEFAULT_WARMUP
    vision_p99_budget_ms: float = DEFAULT_VISION_P99_BUDGET_MS

    def __post_init__(self) -> None:
        if self.iterations <= 0:
            raise JpegBenchmarkError("iterations must be positive")
        if self.warmup < 0:
            raise JpegBenchmarkError("warmup must be non-negative")
        if self.vision_p99_budget_ms <= 0.0:
            raise JpegBenchmarkError("vision_p99_budget_ms must be positive")


def generate_synthetic_fixture(path: Path) -> None:
    """Write a deterministic 640 x 360 JPEG fixture using Pillow when available."""

    try:
        from PIL import Image, ImageDraw
    except ImportError as exc:
        raise JpegBenchmarkError("Pillow is required to generate the JPEG fixture") from exc

    image = Image.new("RGB", (DEFAULT_WIDTH_PX, DEFAULT_HEIGHT_PX), (12, 12, 12))
    pixels = image.load()
    for y in range(DEFAULT_HEIGHT_PX):
        for x in range(DEFAULT_WIDTH_PX):
            pixels[x, y] = (
                (x * 5 + y * 2) % 256,
                (x * 2 + y * 3) % 256,
                (x + y * 4) % 256,
            )

    draw = ImageDraw.Draw(image)
    # Magenta gate-like square gives the fixture a high-contrast racing feature.
    draw.rectangle((220, 90, 420, 290), outline=(255, 0, 255), width=12)
    draw.rectangle((252, 122, 388, 258), fill=(18, 18, 18))
    path.parent.mkdir(parents=True, exist_ok=True)
    image.save(path, format="JPEG", quality=85, optimize=False, progressive=False)


def discover_decoder(name: str) -> DecoderCandidate | dict[str, Any]:
    if name == "pillow":
        return _discover_pillow()
    if name == "opencv":
        return _discover_opencv()
    if name == "pyturbojpeg":
        return _discover_pyturbojpeg()
    raise JpegBenchmarkError(f"unsupported decoder {name}")


def run_benchmark(
    *,
    fixture_bytes: bytes,
    candidate: DecoderCandidate,
    config: BenchmarkConfig,
    clock_ns: Callable[[], int] = time.perf_counter_ns,
) -> dict[str, Any]:
    decoded_shape = None
    for _ in range(config.warmup):
        decoded_shape = candidate.decode(fixture_bytes)

    samples_ms: list[float] = []
    for _ in range(config.iterations):
        start_ns = clock_ns()
        decoded_shape = candidate.decode(fixture_bytes)
        end_ns = clock_ns()
        samples_ms.append((end_ns - start_ns) / 1_000_000.0)

    if decoded_shape is None:
        raise JpegBenchmarkError("decoder did not produce a decoded frame")

    p50_ms = _percentile(samples_ms, 50)
    p95_ms = _percentile(samples_ms, 95)
    p99_ms = _percentile(samples_ms, 99)
    return {
        "name": candidate.name,
        "available": True,
        "version": candidate.version,
        "dependency_note": candidate.dependency_note,
        "decoded_shape_hwc": list(decoded_shape),
        "iterations": config.iterations,
        "warmup": config.warmup,
        "latency_ms": {
            "min": round(min(samples_ms), 6),
            "median": round(statistics.median(samples_ms), 6),
            "p50": round(p50_ms, 6),
            "p95": round(p95_ms, 6),
            "p99": round(p99_ms, 6),
            "max": round(max(samples_ms), 6),
        },
        "passes_vision_p99_budget": p99_ms <= config.vision_p99_budget_ms,
    }


def build_report(
    *,
    fixture_path: Path,
    decoder_names: tuple[str, ...],
    config: BenchmarkConfig,
) -> dict[str, Any]:
    fixture_bytes = fixture_path.read_bytes()
    results: list[dict[str, Any]] = []
    for decoder_name in decoder_names:
        candidate = discover_decoder(decoder_name)
        if isinstance(candidate, DecoderCandidate):
            try:
                results.append(
                    run_benchmark(
                        fixture_bytes=fixture_bytes,
                        candidate=candidate,
                        config=config,
                    )
                )
            except Exception as exc:
                results.append(_unavailable_decoder(decoder_name, str(exc)))
        else:
            results.append(candidate)

    return {
        "schema_version": SCHEMA_VERSION,
        "github_issue": "https://github.com/omarespejel/aigp-racer/issues/17",
        "claim_boundary": (
            "local JPEG decode benchmark only; not official simulator frame, full vision "
            "pipeline, or Windows packaging evidence"
        ),
        "fixture": _fixture_metadata(fixture_path, fixture_bytes),
        "environment": {
            "python_version": sys.version.split()[0],
            "platform": platform.platform(),
            "machine": platform.machine(),
            "processor": platform.processor(),
        },
        "config": {
            "iterations": config.iterations,
            "warmup": config.warmup,
            "vision_p99_budget_ms": config.vision_p99_budget_ms,
            "decoder_names": list(decoder_names),
        },
        "results": results,
        "promotion_rule": (
            "A decoder is eligible for runtime consideration only if it is available, "
            "fits the p99 budget on representative frames, and has a documented "
            "Windows/Python 3.14 packaging path."
        ),
        "non_claims": [
            "not a runtime dependency decision",
            "not official simulator frame evidence",
            "not detector latency evidence",
            "not full vision-pipeline p99 evidence",
            "not Windows packaging proof until run on the official Windows host",
        ],
    }


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _discover_pillow() -> DecoderCandidate | dict[str, Any]:
    try:
        from PIL import Image
    except ImportError as exc:
        return _unavailable_decoder("pillow", str(exc))

    def decode(data: bytes) -> tuple[int, int, int]:
        with Image.open(BytesIO(data)) as image:
            rgb = image.convert("RGB")
            rgb.load()
            width, height = rgb.size
        return (height, width, 3)

    return DecoderCandidate(
        name="pillow",
        decode=decode,
        version=_package_version("Pillow"),
        dependency_note="Pillow fallback decoder; simple packaging path, not assumed speed winner",
    )


def _discover_opencv() -> DecoderCandidate | dict[str, Any]:
    try:
        import cv2
        import numpy as np
    except ImportError as exc:
        return _unavailable_decoder("opencv", str(exc))

    def decode(data: bytes) -> tuple[int, int, int]:
        array = np.frombuffer(data, dtype=np.uint8)
        image = cv2.imdecode(array, cv2.IMREAD_COLOR)
        if image is None:
            raise JpegBenchmarkError("OpenCV failed to decode JPEG")
        height, width, channels = image.shape
        return (int(height), int(width), int(channels))

    return DecoderCandidate(
        name="opencv",
        decode=decode,
        version=_package_version("opencv-python"),
        dependency_note="OpenCV fallback decoder; heavier dependency than dedicated JPEG path",
    )


def _discover_pyturbojpeg() -> DecoderCandidate | dict[str, Any]:
    try:
        from turbojpeg import TurboJPEG
    except ImportError as exc:
        return _unavailable_decoder("pyturbojpeg", str(exc))

    try:
        jpeg = TurboJPEG()
    except Exception as exc:
        return _unavailable_decoder("pyturbojpeg", f"TurboJPEG init failed: {exc}")

    def decode(data: bytes) -> tuple[int, int, int]:
        image = jpeg.decode(data)
        height, width, channels = image.shape
        return (int(height), int(width), int(channels))

    return DecoderCandidate(
        name="pyturbojpeg",
        decode=decode,
        version=_package_version("PyTurboJPEG"),
        dependency_note=(
            "libjpeg-turbo-backed speed candidate; Windows native library path must be verified"
        ),
    )


def _fixture_metadata(path: Path, fixture_bytes: bytes) -> dict[str, Any]:
    return {
        "path": str(path),
        "size_bytes": len(fixture_bytes),
        "sha256": hashlib.sha256(fixture_bytes).hexdigest(),
    }


def _unavailable_decoder(name: str, reason: str) -> dict[str, Any]:
    return {
        "name": name,
        "available": False,
        "reason": reason,
    }


def _package_version(package_name: str) -> str:
    try:
        return importlib.metadata.version(package_name)
    except importlib.metadata.PackageNotFoundError:
        return "unknown"


def _percentile(values: list[float], percentile: int) -> float:
    if not values:
        raise JpegBenchmarkError("cannot compute percentile for empty sample")
    if not 0 <= percentile <= 100:
        raise JpegBenchmarkError("percentile must be in [0, 100]")
    sorted_values = sorted(values)
    if len(sorted_values) == 1:
        return sorted_values[0]
    rank = (len(sorted_values) - 1) * (percentile / 100.0)
    lower_index = int(rank)
    upper_index = min(lower_index + 1, len(sorted_values) - 1)
    fraction = rank - lower_index
    return sorted_values[lower_index] * (1.0 - fraction) + sorted_values[upper_index] * fraction


def _parse_decoders(value: str) -> tuple[str, ...]:
    decoders = tuple(item.strip() for item in value.split(",") if item.strip())
    if not decoders:
        raise JpegBenchmarkError("at least one decoder must be selected")
    unknown = [decoder for decoder in decoders if decoder not in SUPPORTED_DECODERS]
    if unknown:
        raise JpegBenchmarkError(f"unsupported decoder(s): {', '.join(unknown)}")
    return decoders


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--fixture", type=Path, required=True)
    parser.add_argument("--write-json", type=Path, required=True)
    parser.add_argument("--iterations", type=int, default=DEFAULT_ITERATIONS)
    parser.add_argument("--warmup", type=int, default=DEFAULT_WARMUP)
    parser.add_argument("--vision-p99-budget-ms", type=float, default=DEFAULT_VISION_P99_BUDGET_MS)
    parser.add_argument("--decoders", default=",".join(SUPPORTED_DECODERS))
    parser.add_argument("--generate-synthetic-fixture", action="store_true")
    args = parser.parse_args()

    if args.generate_synthetic_fixture:
        generate_synthetic_fixture(args.fixture)
    if not args.fixture.exists():
        raise JpegBenchmarkError(f"fixture does not exist: {args.fixture}")

    config = BenchmarkConfig(
        iterations=args.iterations,
        warmup=args.warmup,
        vision_p99_budget_ms=args.vision_p99_budget_ms,
    )
    report = build_report(
        fixture_path=args.fixture,
        decoder_names=_parse_decoders(args.decoders),
        config=config,
    )
    write_json(args.write_json, report)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
