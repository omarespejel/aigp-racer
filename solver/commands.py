"""Command intent types and rate limiting."""

from __future__ import annotations

import math
from dataclasses import dataclass
from enum import StrEnum
from numbers import Real

_RATE_BOUND_ERROR = "max_rate_hz must be a finite real number greater than 0 and less than 100"
_RATE_INTERVAL_ERROR = "max_rate_hz is too small to compute a finite interval"


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
class WallClockCommandRateLimiter:
    """Wall-clock send-layer guard for the command-rate ceiling documented in
    AI Grand Prix Technical Specification VADR-TS-002, Issue 00.02
    (2026-05-08), mirrored in docs/engineering/spec-notes.md.

    Deterministic replay should use ``SimTimeCommandRateLimiter`` so command
    decisions are keyed to recorded simulator timestamps instead of host
    scheduling jitter.
    """

    max_rate_hz: float = 95.0
    last_emit_monotonic_s: float | None = None

    def __post_init__(self) -> None:
        self._validate_rate()

    @property
    def min_interval_s(self) -> float:
        rate_hz = self._validated_rate_hz()
        return 1.0 / rate_hz

    def allow(self, monotonic_s: float) -> bool:
        self._validate_rate()
        if not math.isfinite(monotonic_s):
            return False
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
        self._validated_rate_hz()

    def _validated_rate_hz(self) -> float:
        return _validated_rate_hz(self.max_rate_hz)


@dataclass
class SimTimeCommandRateLimiter:
    """Deterministic command limiter keyed by simulator nanoseconds."""

    max_rate_hz: float = 95.0
    last_emit_sim_time_ns: int | None = None

    def __post_init__(self) -> None:
        self._validate_rate()

    @property
    def min_interval_ns(self) -> int:
        rate_hz = self._validated_rate_hz()
        return math.ceil(1_000_000_000 / rate_hz)

    def allow(self, sim_time_ns: int) -> bool:
        self._validate_rate()
        if not _valid_sim_time_ns(sim_time_ns):
            return False
        if self.last_emit_sim_time_ns is None:
            self.last_emit_sim_time_ns = sim_time_ns
            return True
        if sim_time_ns < self.last_emit_sim_time_ns:
            return False
        if sim_time_ns - self.last_emit_sim_time_ns < self.min_interval_ns:
            return False
        self.last_emit_sim_time_ns = sim_time_ns
        return True

    def _validate_rate(self) -> None:
        self._validated_rate_hz()

    def _validated_rate_hz(self) -> float:
        return _validated_rate_hz(self.max_rate_hz)


def _valid_sim_time_ns(sim_time_ns: int) -> bool:
    return type(sim_time_ns) is int and sim_time_ns >= 0


def _validated_rate_hz(max_rate_hz: object) -> float:
    if isinstance(max_rate_hz, bool) or not isinstance(max_rate_hz, Real):
        raise ValueError(_RATE_BOUND_ERROR)
    rate_hz = float(max_rate_hz)
    if not math.isfinite(rate_hz) or not 0.0 < rate_hz < 100.0:
        raise ValueError(_RATE_BOUND_ERROR)
    try:
        interval_ns = 1_000_000_000.0 / rate_hz
    except OverflowError as exc:
        raise ValueError(_RATE_INTERVAL_ERROR) from exc
    if not math.isfinite(interval_ns):
        raise ValueError(_RATE_INTERVAL_ERROR)
    return rate_hz
