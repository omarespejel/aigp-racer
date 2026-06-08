# Command-Rate Replay Determinism

Date: 2026-06-08
Issue: #22

## Thesis

Command-rate decisions used in replay and AutoRaceEvolve-style offline evaluation
must be keyed to simulator time, not host wall-clock scheduling.

## Change

`solver.commands` now separates two boundaries:

- `WallClockCommandRateLimiter`: wall-clock send-layer guard for live transport deadlines.
- `SimTimeCommandRateLimiter`: deterministic replay guard using `sim_time_ns`.

AI Grand Prix Technical Specification VADR-TS-002, Issue 00.02, dated
2026-05-08, states the command-rate ceiling; this source is mirrored in
`docs/engineering/spec-notes.md`. The simulator-time limiter computes the
minimum safe interval as integer nanoseconds with `ceil(1e9 / max_rate_hz)`.
At the default 95 Hz guard this is `10_526_316 ns`, so a command one nanosecond
earlier is rejected and a command at the exact boundary is allowed.

## GO Gate

- First simulator-time command is allowed.
- Too-fast command is rejected.
- Exact-boundary command is allowed.
- Backward, negative, bool, float, and string timestamps are rejected without
  rewinding limiter state.
- Invalid or late-mutated rates are rejected, including booleans, non-real
  values, non-finite values, values greater than or equal to 100 Hz, and values
  too small to compute a finite nanosecond interval.

## Non-Claims

- Not proof of official command delivery timing.
- Not a latency result.
- Not a valid-run result.
- Not binary MAVLink or MAVSDK evidence.
- Not a claim that wall-clock transport deadlines are unnecessary.

## Local Validation

```bash
uv run --python 3.14 --with pytest python -m pytest tests/test_mavlink_command_intent.py tests/test_solver_baseline.py
./scripts/aigp_local_gate.sh
```
