"""Practice-only frame adapters for non-official simulator harnesses."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from typing import Final

from perception.detector import RGBImage

AGP_CAMERA_WIDTH_PX: Final = 640
AGP_CAMERA_HEIGHT_PX: Final = 360
ELODIN_PRACTICE_FRAME_SOURCE: Final = "elodin_practice_rgba"

RGBATuple = tuple[int, int, int, int]
RGBTuple = tuple[int, int, int]
RGBAImage = Sequence[Sequence[Sequence[int]]]


class PracticeFrameAdapterError(ValueError):
    """Raised when a practice frame cannot be adapted safely."""


@dataclass(frozen=True)
class DetectorFrame:
    """Detector-compatible RGB frame with explicit source metadata."""

    rgb: tuple[tuple[RGBTuple, ...], ...]
    sim_time_ns: int | None
    source_frame_id: int | None
    source: str
    claim_boundary: str


@dataclass(frozen=True)
class ElodinRgbaFrameAdapter:
    """Convert Elodin practice RGBA frames into detector-compatible RGB frames.

    This adapter is deliberately practice-only. It does not decode official UDP
    JPEG packets and does not imply official simulator compatibility.
    """

    expected_width_px: int = AGP_CAMERA_WIDTH_PX
    expected_height_px: int = AGP_CAMERA_HEIGHT_PX

    def __post_init__(self) -> None:
        if self.expected_width_px <= 0:
            raise ValueError("expected_width_px must be positive")
        if self.expected_height_px <= 0:
            raise ValueError("expected_height_px must be positive")

    def adapt(
        self,
        frame_rgba: RGBAImage,
        *,
        sim_time_ns: int | None = None,
        source_frame_id: int | None = None,
    ) -> DetectorFrame:
        """Strip alpha and return a validated detector frame."""

        _validate_optional_int("sim_time_ns", sim_time_ns)
        _validate_optional_int("source_frame_id", source_frame_id)

        frame_height = _safe_len(frame_rgba, "RGBA frame must be a sequence of rows")
        if frame_height != self.expected_height_px:
            raise PracticeFrameAdapterError("RGBA frame height does not match expected height")

        rows: list[tuple[RGBTuple, ...]] = []
        for row_index, row in enumerate(frame_rgba):
            row_width = _safe_len(
                row,
                f"RGBA frame row {row_index} must be a sequence of pixels",
            )
            if row_width != self.expected_width_px:
                raise PracticeFrameAdapterError(
                    f"RGBA frame row {row_index} width does not match expected width"
                )
            try:
                rows.append(tuple(_rgba_to_rgb(pixel) for pixel in row))
            except TypeError as exc:
                raise PracticeFrameAdapterError(
                    f"RGBA frame row {row_index} must be iterable"
                ) from exc

        return DetectorFrame(
            rgb=tuple(rows),
            sim_time_ns=sim_time_ns,
            source_frame_id=source_frame_id,
            source=ELODIN_PRACTICE_FRAME_SOURCE,
            claim_boundary=(
                "practice-only Elodin RGBA adapter; not official UDP JPEG compatibility evidence"
            ),
        )


def detector_rgb_image(frame: DetectorFrame) -> RGBImage:
    """Return the RGB image for detector call sites."""

    return frame.rgb


def _rgba_to_rgb(pixel: Sequence[int]) -> RGBTuple:
    pixel_len = _safe_len(pixel, "Elodin practice frame pixels must be RGBA sequences")
    if pixel_len != 4:
        raise PracticeFrameAdapterError("Elodin practice frame pixels must be RGBA")
    try:
        red, green, blue, alpha = pixel
    except (TypeError, ValueError) as exc:
        raise PracticeFrameAdapterError("Elodin practice frame pixels must be RGBA") from exc
    for channel_name, channel in (
        ("red", red),
        ("green", green),
        ("blue", blue),
        ("alpha", alpha),
    ):
        if not isinstance(channel, int) or channel < 0 or channel > 255:
            raise PracticeFrameAdapterError(
                f"RGBA {channel_name} channel must be an integer in [0, 255]"
            )
    return (red, green, blue)


def _safe_len(value: object, message: str) -> int:
    try:
        return len(value)  # type: ignore[arg-type]
    except TypeError as exc:
        raise PracticeFrameAdapterError(message) from exc


def _validate_optional_int(name: str, value: int | None) -> None:
    if value is not None and type(value) is not int:
        raise PracticeFrameAdapterError(f"{name} must be an integer when provided")
