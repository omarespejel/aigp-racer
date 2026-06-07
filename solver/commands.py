"""Command intent types and rate limiting."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


class CommandKind(StrEnum):
    HOLD = "HOLD"
    REACQUIRE = "REACQUIRE"
    BODY_VELOCITY = "BODY_VELOCITY"


@dataclass(frozen=True)
class ControlCommand:
    sim_time_ns: int
    kind: CommandKind
    source_frame_id: int | None = None
    forward_m_s: float = 0.0
    right_m_s: float = 0.0
    down_m_s: float = 0.0
    yaw_rate_rad_s: float = 0.0
    reason: str = ""


@dataclass
class CommandRateLimiter:
    """Guard command emission against the official <100 Hz ceiling."""

    max_rate_hz: float = 95.0
    last_emit_monotonic_s: float | None = None

    def __post_init__(self) -> None:
        self._validate_rate()

    @property
    def min_interval_s(self) -> float:
        self._validate_rate()
        return 1.0 / self.max_rate_hz

    def allow(self, monotonic_s: float) -> bool:
        if self.last_emit_monotonic_s is None:
            self.last_emit_monotonic_s = monotonic_s
            return True
        if monotonic_s < self.last_emit_monotonic_s:
            return False
        if monotonic_s - self.last_emit_monotonic_s < self.min_interval_s:
            return False
        self.last_emit_monotonic_s = monotonic_s
        return True

    def _validate_rate(self) -> None:
        if not 0.0 < self.max_rate_hz < 100.0:
            raise ValueError("max_rate_hz must be greater than 0 and less than 100")
