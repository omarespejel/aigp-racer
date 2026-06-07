# AI Review Guidelines

These guidelines are consumed by CodeRabbit and mirrored in Qodo instructions.

## Review Goal

The review goal is not generic Python polish. The review goal is to keep a future autonomous drone racing system correct, deterministic, low-latency, auditable, and competition-compliant.

## Highest-Priority Findings

Flag these as high priority:

- live runtime changes that can exceed the AI Grand Prix less-than-100-Hz command ceiling;
- stale telemetry or camera frames used without explicit freshness checks;
- camera/body/NED frame conversion ambiguity;
- unsafe behavior when gate confidence drops, gates are lost, or telemetry is delayed;
- world-model, LLM, DecisionTrace, or WorldForge code entering the live flight hot path;
- missing tests for UDP frame reassembly, PnP geometry, telemetry parsing, estimator sync, command-rate limiting, or evaluator promotion gates;
- learned policy promotion without reproducible artifact hashes, evaluator settings, held-out reliability metrics, and crash-regression results;
- competition, spec, paper, or schedule claims without current sources;
- missing disclosure ledger updates for dependencies, model weights, datasets, generated-AI usage, simulator sources, or submission-relevant artifacts.

## Lower-Priority Findings

Keep these concise and only raise them when they affect real maintainability:

- style preferences not enforced by Ruff or formatting checks;
- broad refactors unrelated to the PR objective;
- naming issues that do not obscure runtime behavior or evidence artifacts.

## Path-Specific Expectations

- `solver/`: command limits, recovery states, deterministic fallback, stale-data handling.
- `mavlink/`: message types, heartbeat, timestamping, NED/body frames, command isolation.
- `vision/`: UDP chunk reassembly, memory bounds, duplicate/missing chunks, JPEG timing.
- `perception/`: gate corners, uncertainty, PnP, intrinsics, +20 degree camera tilt.
- `estimation/`: IMU/attitude/velocity assumptions, sync, drift correction, covariance.
- `planning/`: reliability-first speed schedules, recovery, no raw-lap-time-only promotion.
- `policies/`: training/eval configs, artifacts, hashes, held-out reliability.
- `evolve/`: frozen evaluator, hidden seeds, anti-reward-hacking, reproducible candidates.
- `worldforge_bridge/`: offline-only DecisionTrace, replay, metrics, and evidence conversion.
- `docs/`: sources, dates, claim boundaries.

## Preferred Review Shape

Lead with bugs, risks, missing tests, or compliance gaps. Keep summaries short. Do not ask for broad rewrites when a local fix would solve the risk.

