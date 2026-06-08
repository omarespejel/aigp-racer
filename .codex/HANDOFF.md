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
- PR #25 merged issue #21. Integrated dry-run RaceEpisode and DecisionTrace evidence now exercises the detector -> estimator -> controller -> command-intent module chain without claiming simulator compatibility or latency.
- PR #26 merged issue #22. Simulator-time replay command gating is split from wall-clock send-layer gating.
- Active branch `codex/aigp-gate-depth-basis-2026-06-08` works issue #23: make screen-space gate depth basis explicit and first-frame calibratable.

## Active Objective

Make screen-space gate depth conversion explicit by declaring whether bbox width uses the 1.5 m inner opening or 2.7 m outer frame, while preserving the first-frame calibration caveat.

Immediate next code objectives:

1. Land issue #23 gate depth measurement-basis hardening.
2. Recheck issue #4 once team-portal credentials or an official package link are available.
3. Capture real official simulator packet examples once access exists.
4. Calibrate Round 1 highlight basis from the first official simulator frame.
5. Assemble and measure a minimal hot loop in issue #24.

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
