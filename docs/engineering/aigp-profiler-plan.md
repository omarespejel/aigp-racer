# AI Grand Prix Profiler Plan

The first profiler is not an optimization claim. It is a failure-attribution tool.

## Thesis

Autonomous racing failures should be attributable to concrete sections:

- camera packet assembly;
- frame decode;
- gate detection;
- PnP pose;
- telemetry parsing;
- state estimation;
- planning;
- control command emission;
- offline evidence conversion.

If we can emit deterministic profiles for these sections, we can decide whether future work should target perception latency, estimator drift, controller recovery, or offline policy search.

## Smallest Falsifying Experiment

Emit a deterministic fixture profile with section names, p50/p95/p99 placeholders, event counts, and non-claims. If this cannot be made deterministic, the profiling discipline is not ready.

## GO Gate

`scripts/aigp_profile_gate.py --write-json docs/engineering/evidence/aigp-profile-fixture-2026-06-08.json` emits stable JSON, and rerunning it produces no diff.

## NO-GO Gate

The fixture requires wall-clock timestamps, host-specific paths, random IDs, or simulator-only state before producing stable attribution.

## Non-Claims

- No speedup.
- No latency measurement.
- No reliability result.
- No official simulator compatibility.
- No physical-drone transfer.

