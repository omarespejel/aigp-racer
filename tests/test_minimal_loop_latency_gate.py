from __future__ import annotations

from pathlib import Path

import pytest

from scripts import aigp_minimal_loop_latency_gate as loop


def test_build_report_runs_minimal_loop_with_injected_clock(tmp_path: Path) -> None:
    fixture = tmp_path / "frame.jpg"
    fixture.write_bytes(b"jpeg fixture bytes")
    clock = _StepClock(step_ns=1_000_000)

    report = loop.build_report(
        fixture_path=fixture,
        decoder=loop.discover_decoder("synthetic_rgb"),
        config=loop.LoopConfig(iterations=2, warmup=0),
        clock_ns=clock,
    )

    assert report["schema_version"] == loop.SCHEMA_VERSION
    assert report["decoder"]["name"] == "synthetic_rgb"
    assert report["stage_latency_ms"]["reassemble"]["p99"] == "1.000000"
    assert report["stage_latency_ms"]["decode"]["p50"] == "1.000000"
    assert report["total_latency_ms"]["p99"] == "12.000000"
    assert report["passes_frame_p99_budget"] is True
    assert report["passes_command_p99_budget"] is True
    assert report["last_output"]["detection_status"] == "DETECTED"
    assert report["last_output"]["measurement_basis"] == "OUTER_FRAME"
    assert report["last_output"]["message_name"] == "SET_POSITION_TARGET_LOCAL_NED"
    assert report["last_output"]["intent_mode"] == "REACQUIRE"
    assert report["last_output"]["command_reason"] == "gate confidence below threshold"


def test_validate_report_accepts_checked_minimal_loop_artifact(tmp_path: Path) -> None:
    fixture = tmp_path / "frame.jpg"
    fixture.write_bytes(b"jpeg fixture bytes")
    config = loop.LoopConfig(iterations=1, warmup=0)
    report = loop.build_report(
        fixture_path=fixture,
        decoder=_fake_pillow_decoder(),
        config=config,
        clock_ns=_StepClock(step_ns=1_000_000),
    )

    loop.validate_report(report, fixture_path=fixture, expected_config=config)


def test_validate_report_rejects_non_object_json_root(tmp_path: Path) -> None:
    fixture = tmp_path / "frame.jpg"
    fixture.write_bytes(b"jpeg fixture bytes")
    config = loop.LoopConfig(iterations=1, warmup=0)

    with pytest.raises(loop.MinimalLoopError, match="report root"):
        loop.validate_report([], fixture_path=fixture, expected_config=config)


def test_validate_report_rejects_missing_stage_latency(tmp_path: Path) -> None:
    fixture = tmp_path / "frame.jpg"
    fixture.write_bytes(b"jpeg fixture bytes")
    config = loop.LoopConfig(iterations=1, warmup=0)
    report = loop.build_report(
        fixture_path=fixture,
        decoder=_fake_pillow_decoder(),
        config=config,
        clock_ns=_StepClock(step_ns=1_000_000),
    )
    del report["stage_latency_ms"]["detect"]

    with pytest.raises(loop.MinimalLoopError, match="detect"):
        loop.validate_report(report, fixture_path=fixture, expected_config=config)


def test_validate_report_rejects_non_bool_budget_result(tmp_path: Path) -> None:
    fixture = tmp_path / "frame.jpg"
    fixture.write_bytes(b"jpeg fixture bytes")
    config = loop.LoopConfig(iterations=1, warmup=0)
    report = loop.build_report(
        fixture_path=fixture,
        decoder=_fake_pillow_decoder(),
        config=config,
        clock_ns=_StepClock(step_ns=1_000_000),
    )
    report["passes_frame_p99_budget"] = "false"

    with pytest.raises(loop.MinimalLoopError, match="passes_frame_p99_budget"):
        loop.validate_report(report, fixture_path=fixture, expected_config=config)


def test_validate_report_rejects_tampered_budget_result(tmp_path: Path) -> None:
    fixture = tmp_path / "frame.jpg"
    fixture.write_bytes(b"jpeg fixture bytes")
    config = loop.LoopConfig(iterations=1, warmup=0)
    report = loop.build_report(
        fixture_path=fixture,
        decoder=_fake_pillow_decoder(),
        config=config,
        clock_ns=_StepClock(step_ns=1_000_000),
    )
    report["passes_command_p99_budget"] = False

    with pytest.raises(loop.MinimalLoopError, match="passes_command_p99_budget"):
        loop.validate_report(report, fixture_path=fixture, expected_config=config)


def test_validate_report_rejects_config_drift(tmp_path: Path) -> None:
    fixture = tmp_path / "frame.jpg"
    fixture.write_bytes(b"jpeg fixture bytes")
    config = loop.LoopConfig(iterations=1, warmup=0)
    report = loop.build_report(
        fixture_path=fixture,
        decoder=_fake_pillow_decoder(),
        config=config,
        clock_ns=_StepClock(step_ns=1_000_000),
    )
    report["config"]["iterations"] = 2

    with pytest.raises(loop.MinimalLoopError, match=r"config\.iterations"):
        loop.validate_report(report, fixture_path=fixture, expected_config=config)


def test_validate_report_accepts_expected_chunk_count(tmp_path: Path) -> None:
    fixture = tmp_path / "frame.jpg"
    fixture.write_bytes(b"jpeg fixture bytes")
    config = loop.LoopConfig(iterations=1, warmup=0, chunk_count=2)
    report = loop.build_report(
        fixture_path=fixture,
        decoder=_fake_pillow_decoder(),
        config=config,
        clock_ns=_StepClock(step_ns=1_000_000),
    )

    loop.validate_report(report, fixture_path=fixture, expected_config=config)


def test_validate_report_rejects_numeric_type_drift(tmp_path: Path) -> None:
    fixture = tmp_path / "frame.jpg"
    fixture.write_bytes(b"jpeg fixture bytes")
    config = loop.LoopConfig(iterations=1, warmup=0)
    report = loop.build_report(
        fixture_path=fixture,
        decoder=_fake_pillow_decoder(),
        config=config,
        clock_ns=_StepClock(step_ns=1_000_000),
    )
    report["config"]["iterations"] = 1.0

    with pytest.raises(loop.MinimalLoopError, match=r"config\.iterations"):
        loop.validate_report(report, fixture_path=fixture, expected_config=config)


def test_validate_report_rejects_decoder_metadata_drift(tmp_path: Path) -> None:
    fixture = tmp_path / "frame.jpg"
    fixture.write_bytes(b"jpeg fixture bytes")
    config = loop.LoopConfig(iterations=1, warmup=0)
    report = loop.build_report(
        fixture_path=fixture,
        decoder=_fake_pillow_decoder(),
        config=config,
        clock_ns=_StepClock(step_ns=1_000_000),
    )
    report["decoder"]["name"] = "synthetic_rgb"

    with pytest.raises(loop.MinimalLoopError, match=r"decoder\.name"):
        loop.validate_report(report, fixture_path=fixture, expected_config=config)


def test_cli_default_decoder_is_real_jpeg_decoder() -> None:
    assert loop.DEFAULT_DECODER == "pillow"


@pytest.mark.parametrize(
    "kwargs",
    [
        {"iterations": 0},
        {"warmup": -1},
        {"chunk_count": 0},
        {"frame_budget_ms": 0.0},
        {"command_budget_ms": 0.0},
    ],
)
def test_loop_config_rejects_invalid_values(kwargs: dict[str, object]) -> None:
    with pytest.raises(loop.MinimalLoopError):
        loop.LoopConfig(**kwargs)


def test_discover_decoder_rejects_unknown_name() -> None:
    with pytest.raises(loop.MinimalLoopError, match="unsupported decoder"):
        loop.discover_decoder("unknown")


class _StepClock:
    def __init__(self, *, step_ns: int) -> None:
        self.step_ns = step_ns
        self.calls = -1

    def __call__(self) -> int:
        self.calls += 1
        return self.calls * self.step_ns


def _fake_pillow_decoder() -> loop.FrameDecoder:
    return loop.FrameDecoder(
        name=loop.DEFAULT_DECODER,
        decode=lambda _: loop.discover_decoder("synthetic_rgb").decode(b""),
        dependency_note=loop.PILLOW_DEPENDENCY_NOTE,
        windows_packaging_note=loop.PILLOW_WINDOWS_PACKAGING_NOTE,
        version=loop.EXPECTED_DECODER_VERSION,
    )
