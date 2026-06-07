# AI Grand Prix Validation Policy

## Baseline Gate

Run:

```bash
./scripts/aigp_local_gate.sh
```

This currently checks:

- review configuration validity;
- research operating model validity;
- issue template parseability;
- Python lint and formatting;
- pytest.

## Future Surface-Specific Gates

Add these as implementation appears:

- `vision`: UDP JPEG reassembly tests for missing, duplicate, stale, and out-of-order chunks.
- `mavlink`: heartbeat, telemetry parsing, frame conventions, command-rate tests.
- `perception`: camera intrinsics, +20 degree tilt, gate dimensions, PnP sanity.
- `estimation`: timestamp sync, velocity ambiguity, stale-update rejection, gate-relative correction.
- `solver`: safe state machine, recovery, no-command-overrate, stale-input handling.
- `evolve`: frozen evaluator, hidden seeds, candidate artifact hashes, reward-hacking checks.
- `worldforge_bridge`: offline-only conversion, RaceEpisode schema, DecisionTrace schema.

## Promotion Rule

A result is not promoted because it is interesting. It is promoted only if its issue gate passes and the required artifacts are checked in.

