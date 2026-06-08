# Handoff

Last updated: 2026-06-08.

## Current State

- Repository initialized and pushed to `omarespejel/aigp-racer`.
- AI Grand Prix research summary captured in issue #1 and `docs/issue-001-aigp-research-and-plan.md`.
- Qodo and CodeRabbit review guardrails are configured.
- CI validates review configuration and Python smoke tests.
- Research-lab operating discipline is checked in: lanes, hypothesis issues, GO/NO-GO gates, no-claims, hardening policy, and local gates.
- First runtime fixtures are checked in for UDP JPEG reassembly, PnP sanity, estimator sync, conservative solver commands, RaceEpisode, and DecisionTrace.
- PR #7 merged issue #3. The decoded-message telemetry probe supports deterministic JSON fixtures and local UDP JSON smoke testing only; it does not decode official binary MAVLink 2 packets.
- Issue #4 is blocked on team-portal credentials or an official package link. Public and local search found no unauthenticated simulator/SDK package URL; evidence is recorded in https://github.com/omarespejel/aigp-racer/issues/4#issuecomment-4643872137.
- PR #8 merged issue #5. Full planar PnP is available only for physical-labeled, front-facing gate corners; detector bbox corners remain screen-space observations.
- PR #10 merged issue #9. Detector observations now bridge into estimator measurements through an explicit `GatePoseMeasurement` boundary without overclaiming full planar PnP from screen-space bbox corners.
- PR #20 merged issue #19. Conservative valid-run commands now gate tracking on confidence, range, status, and center offset.
- Active branch `codex/aigp-integrated-dry-run-2026-06-08` works issue #21: emit integrated dry-run RaceEpisode and DecisionTrace evidence from the actual detector -> estimator -> controller -> command-intent module chain.

## Active Objective

Prove the current runtime modules can produce offline replay evidence through one deterministic integrated dry run, without claiming official simulator compatibility or latency.

Immediate next code objectives:

1. Land issue #21 integrated dry-run evidence.
2. Recheck issue #4 once team-portal credentials or an official package link are available.
3. Capture real official simulator packet examples once access exists.
4. Resolve depth measurement basis/calibration in issue #23.
5. Move command-rate replay decisions to simulator time in issue #22.
6. Assemble and measure a minimal hot loop in issue #24.

## Current Known Unknowns

- Whether official simulator access is already available through team login.
- Whether telemetry actually exposes clean linear velocity.
- Whether `SET_POSITION_TARGET_LOCAL_NED` is sufficient for a conservative first valid run.
- Whether final submission allows compiled inference or only pure Python.
- Whether physical-stage team eligibility imposes constraints on team composition.

## Merge Policy Reminder

For PR work, use:

```bash
./scripts/aigp_local_gate.sh
```

Then wait for Qodo/CodeRabbit/human quiet window before rebase merge.
