from __future__ import annotations

from pathlib import Path

import pytest

from perception.detector import GateDetectionResult, GateDetectionStatus, GateObservation
from perception.geometry import GateMeasurementBasis, ImagePoint
from scripts import aigp_compiled_vision_gate as gate


def test_build_report_runs_compiled_candidate_with_injected_clock(tmp_path: Path) -> None:
    fixture = tmp_path / "frame.jpg"
    fixture.write_bytes(b"jpeg fixture bytes")
    config = gate.CompiledVisionConfig(iterations=2, warmup=0)

    report = gate.build_report(
        fixture_path=fixture,
        candidate=_fake_candidate(),
        config=config,
        clock_ns=_StepClock(step_ns=1_000_000),
        reproduction_command=_test_command(),
    )

    assert report["schema_version"] == gate.SCHEMA_VERSION
    assert report["candidate"]["name"] == gate.DEFAULT_CANDIDATE
    assert report["stage_latency_ms"]["decode"]["p50"] == "1.000000"
    assert report["combined_latency_ms"]["decode_plus_detect"]["p99"] == "2.000000"
    assert report["combined_latency_ms"]["command"]["p99"] == "2.000000"
    assert report["total_latency_ms"]["p99"] == "12.000000"
    assert report["passes_frame_p99_budget"] is True
    assert report["passes_decode_plus_detect_p99_budget"] is True
    assert report["passes_command_p99_budget"] is True
    assert report["last_output"]["detection_status"] == "DETECTED"
    assert report["last_output"]["measurement_basis"] == "OUTER_FRAME"
    assert report["last_output"]["message_name"] == "SET_POSITION_TARGET_LOCAL_NED"


def test_validate_report_accepts_checked_artifact_shape(tmp_path: Path) -> None:
    fixture = tmp_path / "frame.jpg"
    fixture.write_bytes(b"jpeg fixture bytes")
    config = gate.CompiledVisionConfig(iterations=1, warmup=0)
    report = gate.build_report(
        fixture_path=fixture,
        candidate=_fake_candidate(),
        config=config,
        clock_ns=_StepClock(step_ns=1_000_000),
        reproduction_command=_test_command(),
    )

    gate.validate_report(report, fixture_path=fixture, expected_config=config)


def test_validate_report_rejects_non_object_root(tmp_path: Path) -> None:
    fixture = tmp_path / "frame.jpg"
    fixture.write_bytes(b"jpeg fixture bytes")

    with pytest.raises(gate.CompiledVisionGateError, match="report root"):
        gate.validate_report([], fixture_path=fixture)


def test_validate_report_rejects_candidate_drift(tmp_path: Path) -> None:
    fixture = tmp_path / "frame.jpg"
    fixture.write_bytes(b"jpeg fixture bytes")
    config = gate.CompiledVisionConfig(iterations=1, warmup=0)
    report = gate.build_report(
        fixture_path=fixture,
        candidate=_fake_candidate(),
        config=config,
        clock_ns=_StepClock(step_ns=1_000_000),
        reproduction_command=_test_command(),
    )
    report["candidate"]["name"] = "pillow"

    with pytest.raises(gate.CompiledVisionGateError, match=r"candidate\.name"):
        gate.validate_report(report, fixture_path=fixture, expected_config=config)


def test_validate_report_rejects_tampered_budget_result(tmp_path: Path) -> None:
    fixture = tmp_path / "frame.jpg"
    fixture.write_bytes(b"jpeg fixture bytes")
    config = gate.CompiledVisionConfig(iterations=1, warmup=0)
    report = gate.build_report(
        fixture_path=fixture,
        candidate=_fake_candidate(),
        config=config,
        clock_ns=_StepClock(step_ns=1_000_000),
        reproduction_command=_test_command(),
    )
    report["passes_decode_plus_detect_p99_budget"] = False

    with pytest.raises(gate.CompiledVisionGateError, match="passes_decode_plus_detect"):
        gate.validate_report(report, fixture_path=fixture, expected_config=config)


def test_validate_report_uses_combined_p99_for_budget(tmp_path: Path) -> None:
    fixture = tmp_path / "frame.jpg"
    fixture.write_bytes(b"jpeg fixture bytes")
    config = gate.CompiledVisionConfig(iterations=1, warmup=0, decode_detect_budget_ms=1.5)
    report = gate.build_report(
        fixture_path=fixture,
        candidate=_fake_candidate(),
        config=config,
        clock_ns=_StepClock(step_ns=1_000_000),
        reproduction_command=_test_command(),
    )
    report["passes_decode_plus_detect_p99_budget"] = True

    with pytest.raises(gate.CompiledVisionGateError, match="passes_decode_plus_detect"):
        gate.validate_report(report, fixture_path=fixture, expected_config=config)


def test_validate_report_rejects_numeric_type_drift(tmp_path: Path) -> None:
    fixture = tmp_path / "frame.jpg"
    fixture.write_bytes(b"jpeg fixture bytes")
    config = gate.CompiledVisionConfig(iterations=1, warmup=0)
    report = gate.build_report(
        fixture_path=fixture,
        candidate=_fake_candidate(),
        config=config,
        clock_ns=_StepClock(step_ns=1_000_000),
        reproduction_command=_test_command(),
    )
    report["fixture"]["chunk_count"] = float(config.chunk_count)

    with pytest.raises(gate.CompiledVisionGateError, match="chunk_count"):
        gate.validate_report(report, fixture_path=fixture, expected_config=config)


@pytest.mark.parametrize(
    "kwargs",
    [
        {"iterations": 0},
        {"warmup": -1},
        {"chunk_count": 0},
        {"frame_budget_ms": 0.0},
        {"decode_detect_budget_ms": 0.0},
        {"command_budget_ms": 0.0},
    ],
)
def test_config_rejects_invalid_values(kwargs: dict[str, object]) -> None:
    with pytest.raises(gate.CompiledVisionGateError):
        gate.CompiledVisionConfig(**kwargs)


def test_discover_candidate_rejects_unknown_name() -> None:
    with pytest.raises(gate.CompiledVisionGateError, match="unsupported candidate"):
        gate.discover_candidate("unknown")


class _StepClock:
    def __init__(self, *, step_ns: int) -> None:
        self.step_ns = step_ns
        self.calls = -1

    def __call__(self) -> int:
        self.calls += 1
        return self.calls * self.step_ns


def _fake_candidate() -> gate.VisionCandidate:
    return gate.VisionCandidate(
        name=gate.DEFAULT_CANDIDATE,
        decode=lambda data: {"bytes": data},
        detect=lambda _decoded, sim_time_ns, source_frame_id: _fake_detection(
            sim_time_ns,
            source_frame_id,
        ),
        dependency_note="OpenCV imdecode plus NumPy vectorized color threshold and bbox extraction",
        windows_packaging_note="Windows 11 wheel availability must be verified",
        opencv_version=gate.EXPECTED_OPENCV_VERSION,
        numpy_version=gate.EXPECTED_NUMPY_VERSION,
    )


def _test_command() -> str:
    return "uv run --python 3.14 python scripts/aigp_compiled_vision_gate.py --write-json test.json"


def _fake_detection(sim_time_ns: int, source_frame_id: int) -> GateDetectionResult:
    observation = GateObservation(
        corners=(
            ImagePoint(0.0, 0.0),
            ImagePoint(639.0, 0.0),
            ImagePoint(639.0, 359.0),
            ImagePoint(0.0, 359.0),
        ),
        confidence=0.1,
        sim_time_ns=sim_time_ns,
        source_frame_id=source_frame_id,
        source="opencv_vectorized_color_bbox",
        measurement_basis=GateMeasurementBasis.OUTER_FRAME,
        corner_uncertainty_px=(1.0, 1.0, 1.0, 1.0),
    )
    return GateDetectionResult(
        status=GateDetectionStatus.DETECTED,
        observation=observation,
        sim_time_ns=sim_time_ns,
        source_frame_id=source_frame_id,
        source="opencv_vectorized_color_bbox",
        mask_pixels=20_000,
        confidence=0.1,
    )
