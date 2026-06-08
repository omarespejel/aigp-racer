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
- Active branch `codex/aigp-controller-safety-2026-06-08` works issue #19: harden conservative valid-run commands with confidence, range, status, and offset guards.

## Active Objective

Harden the conservative valid-run controller so degraded, low-confidence, out-of-range, or far-off-center gate estimates do not emit tracking commands.

Immediate next code objectives:

1. Land issue #19 controller safety policy and evidence.
2. Recheck issue #4 once team-portal credentials or an official package link are available.
3. Capture real official simulator packet examples once access exists.
4. Choose and gate a binary MAVLink decoder only after packet evidence exists.
5. Emit RaceEpisode and DecisionTrace from an actual practice or official run.

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
