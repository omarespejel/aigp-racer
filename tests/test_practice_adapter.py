from __future__ import annotations

import json
from pathlib import Path

import pytest

from perception.detector import Round1ColorGateDetector
from scripts import aigp_practice_adapter_gate
from vision.practice_adapter import (
    ELODIN_PRACTICE_FRAME_SOURCE,
    ElodinRgbaFrameAdapter,
    PracticeFrameAdapterError,
    detector_rgb_image,
)


def black_rgba_image(width: int = 16, height: int = 12) -> list[list[tuple[int, int, int, int]]]:
    return [[(0, 0, 0, 255) for _ in range(width)] for _ in range(height)]


def highlighted_gate_rgba_image() -> list[list[tuple[int, int, int, int]]]:
    image = black_rgba_image()
    for v in range(3, 9):
        image[v][4] = (255, 0, 255, 255)
        image[v][10] = (255, 0, 255, 255)
    for u in range(4, 11):
        image[3][u] = (255, 0, 255, 255)
        image[8][u] = (255, 0, 255, 255)
    return image


def test_elodin_rgba_frame_adapter_feeds_round1_detector() -> None:
    adapter = ElodinRgbaFrameAdapter(expected_width_px=16, expected_height_px=12)
    frame = adapter.adapt(
        highlighted_gate_rgba_image(),
        sim_time_ns=44,
        source_frame_id=7,
    )

    observation = Round1ColorGateDetector(min_pixels=10).detect(
        detector_rgb_image(frame),
        sim_time_ns=frame.sim_time_ns,
        source_frame_id=frame.source_frame_id,
    )

    assert frame.source == ELODIN_PRACTICE_FRAME_SOURCE
    assert frame.claim_boundary.startswith("practice-only")
    assert frame.rgb[3][4] == (255, 0, 255)
    assert observation is not None
    assert observation.sim_time_ns == 44
    assert observation.source_frame_id == 7
    assert observation.corners[0].u_px == 4.0
    assert observation.corners[2].v_px == 8.0


def test_elodin_rgba_frame_adapter_rejects_wrong_dimensions() -> None:
    adapter = ElodinRgbaFrameAdapter(expected_width_px=16, expected_height_px=12)

    with pytest.raises(PracticeFrameAdapterError, match="height"):
        adapter.adapt(black_rgba_image(height=11))

    image = black_rgba_image()
    image[2].append((0, 0, 0, 255))

    with pytest.raises(PracticeFrameAdapterError, match="width"):
        adapter.adapt(image)


def test_elodin_rgba_frame_adapter_rejects_malformed_pixels() -> None:
    adapter = ElodinRgbaFrameAdapter(expected_width_px=1, expected_height_px=1)

    with pytest.raises(PracticeFrameAdapterError, match="RGBA"):
        adapter.adapt([[(0, 0, 0)]])  # type: ignore[list-item]

    with pytest.raises(PracticeFrameAdapterError, match="integer"):
        adapter.adapt([[(-1, 0, 0, 255)]])

    with pytest.raises(PracticeFrameAdapterError, match="integer"):
        adapter.adapt([[(0, 0, 0, 256)]])


def test_elodin_rgba_frame_adapter_normalizes_non_sequence_errors() -> None:
    adapter = ElodinRgbaFrameAdapter(expected_width_px=1, expected_height_px=1)

    with pytest.raises(PracticeFrameAdapterError, match="sequence of rows"):
        adapter.adapt(object())  # type: ignore[arg-type]

    with pytest.raises(PracticeFrameAdapterError, match="sequence of pixels"):
        adapter.adapt([object()])  # type: ignore[list-item]

    with pytest.raises(PracticeFrameAdapterError, match="RGBA sequences"):
        adapter.adapt([[object()]])  # type: ignore[list-item]


def test_elodin_rgba_frame_adapter_validates_frame_metadata_types() -> None:
    adapter = ElodinRgbaFrameAdapter(expected_width_px=1, expected_height_px=1)

    with pytest.raises(PracticeFrameAdapterError, match="sim_time_ns"):
        adapter.adapt([[(0, 0, 0, 255)]], sim_time_ns="1")  # type: ignore[arg-type]

    with pytest.raises(PracticeFrameAdapterError, match="source_frame_id"):
        adapter.adapt([[(0, 0, 0, 255)]], source_frame_id=True)


def test_elodin_rgba_frame_adapter_validates_expected_dimensions() -> None:
    with pytest.raises(ValueError, match="expected_width_px"):
        ElodinRgbaFrameAdapter(expected_width_px=0)

    with pytest.raises(ValueError, match="expected_height_px"):
        ElodinRgbaFrameAdapter(expected_height_px=0)


def test_practice_adapter_evidence_matches_generator() -> None:
    fixture_path = (
        Path(__file__).resolve().parents[1]
        / "docs"
        / "engineering"
        / "evidence"
        / "practice-adapter-2026-06-08.json"
    )
    expected = aigp_practice_adapter_gate.build_evidence()
    actual = json.loads(fixture_path.read_text(encoding="utf-8"))

    assert actual == expected
