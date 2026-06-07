from __future__ import annotations

import json
from collections.abc import Callable
from pathlib import Path

import pytest

from scripts import aigp_jpeg_decode_benchmark as bench


def _fake_candidate(
    *,
    name: str = "pillow",
    decode: Callable[[bytes], tuple[int, int, int]],
    version: str = "1.0",
    dependency_note: str = "test fake",
) -> bench.DecoderCandidate:
    metadata = bench._decoder_metadata(name)
    return bench.DecoderCandidate(
        name=name,
        decode=decode,
        version=version,
        dependency_note=dependency_note,
        **metadata,
    )


def test_percentile_interpolates_sorted_values() -> None:
    assert bench._percentile([1.0, 2.0, 3.0, 4.0], 50) == 2.5
    assert bench._percentile([1.0, 2.0, 3.0, 4.0], 100) == 4.0


def test_benchmark_config_rejects_invalid_values() -> None:
    with pytest.raises(bench.JpegBenchmarkError, match="iterations"):
        bench.BenchmarkConfig(iterations=0)

    with pytest.raises(bench.JpegBenchmarkError, match="warmup"):
        bench.BenchmarkConfig(warmup=-1)

    with pytest.raises(bench.JpegBenchmarkError, match="vision_p99_budget"):
        bench.BenchmarkConfig(vision_p99_budget_ms=0.0)


def test_run_benchmark_records_latency_stats_with_injected_clock() -> None:
    clock_values = iter(
        [
            0,
            1_000_000,
            1_000_000,
            3_000_000,
            3_000_000,
            6_000_000,
        ]
    )
    decode_calls = 0

    def decode(data: bytes) -> tuple[int, int, int]:
        nonlocal decode_calls
        assert data == b"jpeg"
        decode_calls += 1
        return (360, 640, 3)

    result = bench.run_benchmark(
        fixture_bytes=b"jpeg",
        candidate=_fake_candidate(decode=decode),
        config=bench.BenchmarkConfig(iterations=3, warmup=1, vision_p99_budget_ms=4.0),
        clock_ns=lambda: next(clock_values),
    )

    assert decode_calls == 4
    assert result["availability"] == "available"
    assert result["available"] is True
    assert result["benchmark_ok"] is True
    assert result["decoded_shape_hwc"] == [360, 640, 3]
    assert result["latency_ms"]["min"] == "1.000000"
    assert result["latency_ms"]["median"] == "2.000000"
    assert result["latency_ms"]["p99"] == "2.980000"
    assert result["passes_vision_p99_budget"] is True


def test_run_benchmark_uses_current_default_clock(monkeypatch: pytest.MonkeyPatch) -> None:
    clock_values = iter([0, 2_000_000])
    monkeypatch.setattr(bench.time, "perf_counter_ns", lambda: next(clock_values))

    result = bench.run_benchmark(
        fixture_bytes=b"jpeg",
        candidate=_fake_candidate(decode=lambda _: (360, 640, 3)),
        config=bench.BenchmarkConfig(iterations=1, warmup=0),
    )

    assert result["latency_ms"]["p99"] == "2.000000"


def test_build_report_records_available_and_unavailable_candidates(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fixture = tmp_path / "frame.jpg"
    fixture.write_bytes(b"jpeg")

    def fake_discover(name: str) -> bench.DecoderCandidate | dict[str, object]:
        if name == "pillow":
            return _fake_candidate(name="pillow", decode=lambda _: (360, 640, 3))
        return bench._unavailable_decoder(name, "missing")

    clock_values = iter([0, 1_000_000])
    monkeypatch.setattr(bench, "discover_decoder", fake_discover)
    monkeypatch.setattr(bench.time, "perf_counter_ns", lambda: next(clock_values))

    report = bench.build_report(
        fixture_path=fixture,
        decoder_names=("pillow", "opencv"),
        config=bench.BenchmarkConfig(iterations=1, warmup=0),
    )

    assert report["schema_version"] == "aigp.jpeg_decode_benchmark.v1"
    assert report["fixture"]["size_bytes"] == 4
    assert report["results"][0]["available"] is True
    assert report["results"][1]["availability"] == "missing_dependency"
    assert report["results"][1]["available"] is False
    assert report["results"][1]["benchmark_ok"] is False
    assert report["results"][1]["reason"] == "missing"
    assert (
        report["results"][1]["dependency_source_url"] == "https://pypi.org/project/opencv-python/"
    )
    assert "not a runtime dependency decision" in report["non_claims"]


def test_build_report_separates_benchmark_errors(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fixture = tmp_path / "frame.jpg"
    fixture.write_bytes(b"jpeg")

    def decode(_: bytes) -> tuple[int, int, int]:
        raise RuntimeError("decode failed")

    monkeypatch.setattr(bench, "discover_decoder", lambda _: _fake_candidate(decode=decode))

    report = bench.build_report(
        fixture_path=fixture,
        decoder_names=("pillow",),
        config=bench.BenchmarkConfig(iterations=1, warmup=0),
    )

    assert report["results"][0]["availability"] == "benchmark_error"
    assert report["results"][0]["available"] is True
    assert report["results"][0]["benchmark_ok"] is False
    assert report["results"][0]["reason"] == "decode failed"


def test_validate_report_accepts_checked_artifact_shape(tmp_path: Path) -> None:
    fixture = tmp_path / "frame.jpg"
    fixture.write_bytes(b"jpeg")
    fixture_metadata = bench._fixture_metadata(fixture, b"jpeg")
    report = {
        "schema_version": bench.SCHEMA_VERSION,
        "github_issue": "https://github.com/omarespejel/aigp-racer/issues/17",
        "fixture": fixture_metadata,
        "config": {
            "iterations": bench.DEFAULT_ITERATIONS,
            "warmup": bench.DEFAULT_WARMUP,
            "vision_p99_budget_ms": "25.000000",
            "decoder_names": list(bench.SUPPORTED_DECODERS),
        },
        "results": [
            {
                "name": "pillow",
                "availability": "available",
                "available": True,
                "benchmark_ok": True,
                "version": "12.2.0",
                "package_name": "Pillow",
                "dependency_note": "test",
                "dependency_source_url": "https://pypi.org/project/Pillow/",
                "dependency_docs_url": "https://pillow.readthedocs.io/_/downloads/en/stable/pdf/",
                "python_314_installability": "verified locally with uv on Python 3.14.3",
                "native_dependency": "wheel-managed; no separate native path checked",
                "decoded_shape_hwc": [360, 640, 3],
                "iterations": bench.DEFAULT_ITERATIONS,
                "warmup": bench.DEFAULT_WARMUP,
                "latency_ms": {
                    "min": "0.100000",
                    "median": "0.200000",
                    "p50": "0.200000",
                    "p95": "0.300000",
                    "p99": "0.400000",
                    "max": "0.500000",
                },
                "passes_vision_p99_budget": True,
            },
            bench._unavailable_decoder("opencv", "missing"),
            bench._unavailable_decoder("pyturbojpeg", "missing"),
        ],
        "non_claims": list(bench.REQUIRED_NON_CLAIMS),
    }

    bench.validate_report(report, fixture_path=fixture)


def test_validate_report_rejects_unfixed_latency_strings(tmp_path: Path) -> None:
    fixture = tmp_path / "frame.jpg"
    fixture.write_bytes(b"jpeg")
    report = {
        "schema_version": bench.SCHEMA_VERSION,
        "github_issue": "https://github.com/omarespejel/aigp-racer/issues/17",
        "fixture": bench._fixture_metadata(fixture, b"jpeg"),
        "config": {
            "iterations": bench.DEFAULT_ITERATIONS,
            "warmup": bench.DEFAULT_WARMUP,
            "vision_p99_budget_ms": "25.000000",
            "decoder_names": list(bench.SUPPORTED_DECODERS),
        },
        "results": [
            {
                "name": "pillow",
                "availability": "available",
                "available": True,
                "benchmark_ok": True,
                "version": "12.2.0",
                "package_name": "Pillow",
                "dependency_note": "test",
                "dependency_source_url": "https://pypi.org/project/Pillow/",
                "dependency_docs_url": "https://pillow.readthedocs.io/_/downloads/en/stable/pdf/",
                "python_314_installability": "verified locally with uv on Python 3.14.3",
                "native_dependency": "wheel-managed; no separate native path checked",
                "decoded_shape_hwc": [360, 640, 3],
                "iterations": bench.DEFAULT_ITERATIONS,
                "warmup": bench.DEFAULT_WARMUP,
                "latency_ms": {
                    "min": "0.1",
                    "median": "0.200000",
                    "p50": "0.200000",
                    "p95": "0.300000",
                    "p99": "0.400000",
                    "max": "0.500000",
                },
                "passes_vision_p99_budget": True,
            },
            bench._unavailable_decoder("opencv", "missing"),
            bench._unavailable_decoder("pyturbojpeg", "missing"),
        ],
        "non_claims": list(bench.REQUIRED_NON_CLAIMS),
    }

    with pytest.raises(bench.JpegBenchmarkError, match="fixed six-decimal"):
        bench.validate_report(report, fixture_path=fixture)


def test_write_json_sorts_keys(tmp_path: Path) -> None:
    path = tmp_path / "report.json"

    bench.write_json(path, {"z": 1, "a": 2})

    assert (
        path.read_text(encoding="utf-8")
        == json.dumps({"z": 1, "a": 2}, indent=2, sort_keys=True) + "\n"
    )


def test_parse_decoders_rejects_unknown_decoder() -> None:
    with pytest.raises(bench.JpegBenchmarkError, match="unsupported decoder"):
        bench._parse_decoders("pillow,unknown")
