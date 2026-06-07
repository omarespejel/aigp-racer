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

    @property
    def min_interval_s(self) -> float:
        return 1.0 / self.max_rate_hz

    def allow(self, monotonic_s: float) -> bool:
        if self.last_emit_monotonic_s is None:
            self.last_emit_monotonic_s = monotonic_s
            return True
        if monotonic_s - self.last_emit_monotonic_s < self.min_interval_s:
            return False
        self.last_emit_monotonic_s = monotonic_s
        return True
