# Handoff

Last updated: 2026-06-08.

## Current State

- Repository initialized and pushed to `omarespejel/aigp-racer`.
- AI Grand Prix research summary captured in issue #1 and `docs/issue-001-aigp-research-and-plan.md`.
- Qodo and CodeRabbit review guardrails are configured.
- CI validates review configuration and Python smoke tests.
- This handoff adds research-lab operating discipline adapted from the `provable-transformer-vm` style: lanes, hypothesis issues, GO/NO-GO gates, no-claims, hardening policy, and local gates.

## Active Objective

Bootstrap the lab discipline before adding racing code.

Immediate next code objectives:

1. Simulator access inventory.
2. UDP JPEG reassembler.
3. MAVLink heartbeat and telemetry probe.
4. PnP gate geometry fixture.
5. Conservative valid-run baseline.

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

