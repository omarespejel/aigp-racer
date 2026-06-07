# Handoff

Last updated: 2026-06-08.

## Current State

- Repository initialized and pushed to `omarespejel/aigp-racer`.
- AI Grand Prix research summary captured in issue #1 and `docs/issue-001-aigp-research-and-plan.md`.
- Qodo and CodeRabbit review guardrails are configured.
- CI validates review configuration and Python smoke tests.
- Research-lab operating discipline is checked in: lanes, hypothesis issues, GO/NO-GO gates, no-claims, hardening policy, and local gates.
- First runtime fixtures are checked in for UDP JPEG reassembly, PnP sanity, estimator sync, conservative solver commands, RaceEpisode, and DecisionTrace.
- Active branch `codex/aigp-telemetry-probe-2026-06-08` adds a decoded-message telemetry probe for issue #3. It supports deterministic JSON fixtures and local UDP JSON smoke testing only; it does not decode official binary MAVLink 2 packets.

## Active Objective

Resolve the first MAVLink telemetry unknown without overclaiming official simulator behavior.

Immediate next code objectives:

1. Land issue #3 telemetry-probe fixture evidence and tests.
2. Resolve issue #4 simulator/team-portal access.
3. Capture real official simulator packet examples once access exists.
4. Choose and gate a binary MAVLink decoder only after packet evidence exists.
5. Continue issue #5 full PnP and detector uncertainty path.

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
