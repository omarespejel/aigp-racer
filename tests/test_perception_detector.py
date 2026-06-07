from __future__ import annotations

from perception.detector import Round1ColorGateDetector


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

    observation = Round1ColorGateDetector(min_pixels=10).detect(image, sim_time_ns=44)

    assert observation is not None
    assert observation.sim_time_ns == 44
    assert observation.source == "round1_color_bbox"
    assert observation.corners[0].u_px == 4.0
    assert observation.corners[0].v_px == 3.0
    assert observation.corners[2].u_px == 10.0
    assert observation.corners[2].v_px == 8.0
    assert observation.confidence > 0.0


def test_round1_color_detector_ignores_dark_frame() -> None:
    assert Round1ColorGateDetector().detect(black_image()) is None


def test_round1_color_detector_rejects_tiny_highlight() -> None:
    image = black_image()
    image[4][4] = (255, 0, 255)

    assert Round1ColorGateDetector(min_pixels=2).detect(image) is None
