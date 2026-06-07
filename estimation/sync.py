"""Timestamp synchronization helpers."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Timestamped[T]:
    sim_time_ns: int
    value: T


@dataclass(frozen=True)
class SyncMatch[T]:
    sample: Timestamped[T]
    age_ns: int

    @property
    def age_s(self) -> float:
        return self.age_ns / 1_000_000_000.0


class TimestampBuffer[T]:
    """Small sorted timestamp buffer for telemetry/frame alignment."""

    def __init__(self, max_samples: int = 128) -> None:
        if max_samples <= 0:
            raise ValueError("max_samples must be positive")
        self.max_samples = max_samples
        self._samples: list[Timestamped[T]] = []

    def add(self, sim_time_ns: int, value: T) -> None:
        sample = Timestamped(sim_time_ns=sim_time_ns, value=value)
        self._samples.append(sample)
        self._samples.sort(key=lambda item: item.sim_time_ns)
        if len(self._samples) > self.max_samples:
            self._samples = self._samples[-self.max_samples :]

    def nearest_not_after(self, sim_time_ns: int, *, max_age_ns: int) -> SyncMatch[T] | None:
        best: Timestamped[T] | None = None
        for sample in self._samples:
            if sample.sim_time_ns <= sim_time_ns:
                best = sample
            else:
                break
        if best is None:
            return None
        age_ns = sim_time_ns - best.sim_time_ns
        if age_ns > max_age_ns:
            return None
        return SyncMatch(sample=best, age_ns=age_ns)

    @property
    def sample_count(self) -> int:
        return len(self._samples)
