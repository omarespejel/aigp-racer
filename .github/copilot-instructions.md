# aigp-racer Coding Instructions

This repository builds an autonomous drone-racing stack for AI Grand Prix.

## Non-Negotiable Boundaries

- Keep the live flight path small, deterministic, and low-latency.
- Do not put LLMs, large video models, learned world-model rollouts, DecisionTrace generation, or WorldForge evaluation in the live control loop.
- Treat WorldForge as offline replay, evaluation, regression, DecisionTrace, and AutoRaceEvolve infrastructure.
- Prefer a conservative valid run before optimizing lap time.
- A policy promotion is not valid without logs, metrics, hashes, evaluator configuration, and a regression result.

## Runtime Priorities

- Respect the AI Grand Prix command-rate ceiling of less than 100 Hz.
- Preserve timestamps and frame IDs across camera, telemetry, estimation, and command logs.
- Treat NED/body/camera frame conversions as correctness-critical.
- Make stale telemetry, missing frames, lost gates, and low detector confidence explicit.
- Recovery behavior is part of the controller, not a later add-on.

## Evidence And Compliance

- Update `DISCLOSURE_LEDGER.md` when adding dependencies, generated-AI code, model weights, datasets, simulator sources, or competition-relevant external sources.
- Source docs claims about rules, specs, schedules, papers, and competition decisions.
- Keep generated artifacts, logs, datasets, videos, checkpoints, and model weights out of git unless deliberately reviewed.

