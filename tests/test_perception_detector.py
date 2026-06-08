from __future__ import annotations

import pytest

from perception.detector import GateDetectionStatus, Round1ColorGateDetector
from perception.geometry import GateMeasurementBasis


def black_image(width: int = 16, height: int = 12) -> list[list[tuple[int, int, int]]]:
    return [[(0, 0, 0) for _ in range(width)] for _ in range(height)]


def test_round1_color_detector_finds_highlighted_gate_bbox() -> None:
    image = black_image()
    for v in range(3, 9):
        image[v][4] = (255, 0, 255)
        image[v][10] = (255, 0, 255)
    for u in range(4, 11):
        image[3][u] = (255, 0, 255)
        image[8][u] = (255, 0, 255)

    observation = Round1ColorGateDetector(min_pixels=10).detect(
        image,
        sim_time_ns=44,
        source_frame_id=7,
    )

    assert observation is not None
    assert observation.sim_time_ns == 44
    assert observation.source_frame_id == 7
    assert observation.source == "round1_color_bbox"
    assert observation.measurement_basis == GateMeasurementBasis.OUTER_FRAME
    assert observation.corners[0].u_px == 4.0
    assert observation.corners[0].v_px == 3.0
    assert observation.corners[2].u_px == 10.0
    assert observation.corners[2].v_px == 8.0
    assert observation.confidence > 0.0
    assert observation.corner_uncertainty_px is not None
    assert observation.corner_uncertainty_px == pytest.approx(
        (5.0 / 3.0, 5.0 / 3.0, 5.0 / 3.0, 5.0 / 3.0),
        rel=0.0,
    )


def test_round1_color_detector_ignores_dark_frame() -> None:
    assert Round1ColorGateDetector().detect(black_image()) is None
    result = Round1ColorGateDetector().analyze(black_image(), sim_time_ns=44, source_frame_id=7)

    assert result.status == GateDetectionStatus.NO_HIGHLIGHT
    assert result.degraded
    assert result.sim_time_ns == 44
    assert result.source_frame_id == 7


def test_round1_color_detector_rejects_tiny_highlight() -> None:
    image = black_image()
    image[4][4] = (255, 0, 255)

    result = Round1ColorGateDetector(min_pixels=2).analyze(image)

    assert result.status == GateDetectionStatus.TOO_FEW_PIXELS
    assert result.observation is None


def test_round1_color_detector_reports_low_confidence_candidate() -> None:
    image = black_image()
    image[2][2] = (255, 0, 255)
    image[2][10] = (255, 0, 255)
    image[9][2] = (255, 0, 255)
    image[9][10] = (255, 0, 255)

    result = Round1ColorGateDetector(min_pixels=4, min_confidence=0.2).analyze(image)

    assert result.status == GateDetectionStatus.LOW_CONFIDENCE
    assert result.confidence is not None
    assert result.confidence < 0.2


def test_round1_color_detector_validates_thresholds() -> None:
    with pytest.raises(ValueError, match="min_pixels"):
        Round1ColorGateDetector(min_pixels=0)
    with pytest.raises(ValueError, match="min_confidence"):
        Round1ColorGateDetector(min_confidence=-0.1)
    with pytest.raises(ValueError, match="min_confidence"):
        Round1ColorGateDetector(min_confidence=1.1)
    with pytest.raises(ValueError, match="gate measurement basis"):
        Round1ColorGateDetector(measurement_basis="UNKNOWN")  # type: ignore[arg-type]
