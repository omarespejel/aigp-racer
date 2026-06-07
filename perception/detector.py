"""Round 1 gate detector baseline."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from enum import StrEnum
from typing import Protocol

from perception.geometry import ImagePoint

RGBPixel = Sequence[int]
RGBImage = Sequence[Sequence[RGBPixel]]


class GateDetector(Protocol):
    def detect(
        self,
        image: RGBImage,
        *,
        sim_time_ns: int | None = None,
        source_frame_id: int | None = None,
    ) -> GateObservation | None:
        """Detect a gate candidate in an RGB image."""


class GateDetectionStatus(StrEnum):
    DETECTED = "DETECTED"
    NO_HIGHLIGHT = "NO_HIGHLIGHT"
    TOO_FEW_PIXELS = "TOO_FEW_PIXELS"
    DEGENERATE_BBOX = "DEGENERATE_BBOX"
    LOW_CONFIDENCE = "LOW_CONFIDENCE"


@dataclass(frozen=True)
class GateObservation:
    corners: tuple[ImagePoint, ImagePoint, ImagePoint, ImagePoint]
    confidence: float
    sim_time_ns: int | None
    source_frame_id: int | None
    source: str


@dataclass(frozen=True)
class GateDetectionResult:
    """Structured detector outcome for telemetry and offline audit traces."""

    status: GateDetectionStatus
    observation: GateObservation | None
    sim_time_ns: int | None
    source_frame_id: int | None
    source: str
    mask_pixels: int
    confidence: float | None = None

    @property
    def detected(self) -> bool:
        return self.observation is not None

    @property
    def degraded(self) -> bool:
        return self.status != GateDetectionStatus.DETECTED


@dataclass(frozen=True)
class Round1ColorGateDetector:
    """Conservative high-contrast detector for highlighted Round 1 gates.

    This is a bootstrap detector for desaturated/highlighted gates, not a Round 2
    visual-robustness model.
    """

    min_pixels: int = 12
    min_confidence: float = 0.05

    def __post_init__(self) -> None:
        if self.min_pixels <= 0:
            raise ValueError("min_pixels must be positive")
        if not 0.0 <= self.min_confidence <= 1.0:
            raise ValueError("min_confidence must be in [0.0, 1.0]")

    def analyze(
        self,
        image: RGBImage,
        *,
        sim_time_ns: int | None = None,
        source_frame_id: int | None = None,
    ) -> GateDetectionResult:
        """Return a structured outcome, including degraded/drop reasons."""

        min_u: int | None = None
        min_v: int | None = None
        max_u: int | None = None
        max_v: int | None = None
        mask_pixels = 0

        for v, row in enumerate(image):
            for u, pixel in enumerate(row):
                if not _is_gate_highlight(pixel):
                    continue
                mask_pixels += 1
                min_u = u if min_u is None else min(min_u, u)
                min_v = v if min_v is None else min(min_v, v)
                max_u = u if max_u is None else max(max_u, u)
                max_v = v if max_v is None else max(max_v, v)

        if min_u is None or min_v is None or max_u is None or max_v is None:
            return self._result(
                GateDetectionStatus.NO_HIGHLIGHT,
                sim_time_ns=sim_time_ns,
                source_frame_id=source_frame_id,
                mask_pixels=mask_pixels,
            )
        if mask_pixels < self.min_pixels:
            return self._result(
                GateDetectionStatus.TOO_FEW_PIXELS,
                sim_time_ns=sim_time_ns,
                source_frame_id=source_frame_id,
                mask_pixels=mask_pixels,
            )

        width = max_u - min_u + 1
        height = max_v - min_v + 1
        if width <= 1 or height <= 1:
            return self._result(
                GateDetectionStatus.DEGENERATE_BBOX,
                sim_time_ns=sim_time_ns,
                source_frame_id=source_frame_id,
                mask_pixels=mask_pixels,
            )

        confidence = mask_pixels / float(width * height)
        if confidence < self.min_confidence:
            return self._result(
                GateDetectionStatus.LOW_CONFIDENCE,
                sim_time_ns=sim_time_ns,
                source_frame_id=source_frame_id,
                mask_pixels=mask_pixels,
                confidence=confidence,
            )

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
            source="round1_color_bbox",
        )
        return GateDetectionResult(
            status=GateDetectionStatus.DETECTED,
            observation=observation,
            sim_time_ns=sim_time_ns,
            source_frame_id=source_frame_id,
            source="round1_color_bbox",
            mask_pixels=mask_pixels,
            confidence=confidence,
        )

    def detect(
        self,
        image: RGBImage,
        *,
        sim_time_ns: int | None = None,
        source_frame_id: int | None = None,
    ) -> GateObservation | None:
        return self.analyze(
            image,
            sim_time_ns=sim_time_ns,
            source_frame_id=source_frame_id,
        ).observation

    @staticmethod
    def _result(
        status: GateDetectionStatus,
        *,
        sim_time_ns: int | None,
        source_frame_id: int | None,
        mask_pixels: int,
        confidence: float | None = None,
    ) -> GateDetectionResult:
        return GateDetectionResult(
            status=status,
            observation=None,
            sim_time_ns=sim_time_ns,
            source_frame_id=source_frame_id,
            source="round1_color_bbox",
            mask_pixels=mask_pixels,
            confidence=confidence,
        )


def _is_gate_highlight(pixel: RGBPixel) -> bool:
    if len(pixel) < 3:
        return False
    red, green, blue = int(pixel[0]), int(pixel[1]), int(pixel[2])
    magenta = red >= 180 and blue >= 140 and green <= 130
    white = red >= 220 and green >= 220 and blue >= 220
    return magenta or white
