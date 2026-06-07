from __future__ import annotations

import json
from pathlib import Path

import pytest

from scripts import aigp_jpeg_decode_benchmark as bench


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
        candidate=bench.DecoderCandidate(
            name="fake",
            decode=decode,
            version="1.0",
            dependency_note="test fake",
        ),
        config=bench.BenchmarkConfig(iterations=3, warmup=1, vision_p99_budget_ms=4.0),
        clock_ns=lambda: next(clock_values),
    )

    assert decode_calls == 4
    assert result["available"] is True
    assert result["decoded_shape_hwc"] == [360, 640, 3]
    assert result["latency_ms"]["min"] == 1.0
    assert result["latency_ms"]["median"] == 2.0
    assert result["latency_ms"]["p99"] == 2.98
    assert result["passes_vision_p99_budget"] is True


def test_build_report_records_available_and_unavailable_candidates(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fixture = tmp_path / "frame.jpg"
    fixture.write_bytes(b"jpeg")

    def fake_discover(name: str) -> bench.DecoderCandidate | dict[str, object]:
        if name == "available":
            return bench.DecoderCandidate(
                name="available",
                decode=lambda _: (360, 640, 3),
                version="1.0",
                dependency_note="test fake",
            )
        return {"name": name, "available": False, "reason": "missing"}

    clock_values = iter([0, 1_000_000])
    monkeypatch.setattr(bench, "discover_decoder", fake_discover)
    monkeypatch.setattr(bench.time, "perf_counter_ns", lambda: next(clock_values))

    report = bench.build_report(
        fixture_path=fixture,
        decoder_names=("available", "missing"),
        config=bench.BenchmarkConfig(iterations=1, warmup=0),
    )

    assert report["schema_version"] == "aigp.jpeg_decode_benchmark.v0"
    assert report["fixture"]["size_bytes"] == 4
    assert report["results"][0]["available"] is True
    assert report["results"][1] == {"name": "missing", "available": False, "reason": "missing"}
    assert "not a runtime dependency decision" in report["non_claims"]


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
