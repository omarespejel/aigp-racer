# Conservative Controller Safety

Issue: #19.

## Decision

Harden the conservative valid-run controller so it only tracks a visible gate
when the estimator state is commandable, the detector confidence is explicit and
above a conservative threshold, the gate depth is inside a bounded range, and
the gate center is not too far from the camera centerline.

This keeps the first valid-run path conservative while simulator access remains
blocked. It does not optimize speed.

## Boundary

The controller may emit `BODY_VELOCITY` only for:

- `READY`;
- `GATE_WITHOUT_VELOCITY`.

It emits non-tracking commands for:

- stale telemetry;
- missing gate pose;
- malformed or degraded estimator states;
- missing, invalid, or low gate confidence;
- non-finite or non-positive gate pose;
- gate depth outside the configured tracking range;
- gate center offset above the configured ratio.

## Evidence

Generated artifact:

```text
docs/engineering/evidence/controller-safety-2026-06-08.json
sha256 7a3134ba12a30564a49cdfa1e0eb50e03efee4331a913f0531c48541e3c268d8
```

The artifact records deterministic state-to-command-to-intent examples. It does
not execute tests or claim pass/fail status; pass/fail evidence comes from the
local/CI commands below.

Validation:

```bash
uv run --python 3.14 --with pytest python -m pytest tests/test_solver_baseline.py tests/test_mavlink_command_intent.py tests/test_controller_safety_gate.py
uv run --python 3.14 --with ruff python -m ruff check solver/baseline.py solver/commands.py scripts/aigp_controller_safety_gate.py tests/test_solver_baseline.py tests/test_controller_safety_gate.py
uv run --python 3.14 --with ruff python -m ruff format --check solver/baseline.py solver/commands.py scripts/aigp_controller_safety_gate.py tests/test_solver_baseline.py tests/test_controller_safety_gate.py
./scripts/aigp_local_gate.sh
```

Focused result:

```text
66 passed
```

## GO Evidence

- `test_controller_holds_on_stale_state`
- `test_controller_reacquires_when_gate_missing`
- `test_controller_tracks_visible_gate_conservatively`
- `test_controller_tracks_gate_without_velocity_status`
- `test_controller_reacquires_on_non_commandable_status`
- `test_controller_reacquires_on_missing_gate_confidence`
- `test_controller_reacquires_on_low_gate_confidence`
- `test_controller_reacquires_on_invalid_gate_confidence`
- `test_controller_reacquires_on_non_positive_gate_depth`
- `test_controller_reacquires_outside_conservative_tracking_range`
- `test_controller_reacquires_on_non_finite_gate_pose`
- `test_controller_rejects_invalid_safety_thresholds`
- `test_controller_safety_evidence_matches_generator`

## Non-Claims

- not an official simulator run;
- not an Elodin practice run;
- not a valid-run result;
- not latency, lap-time, or reliability evidence;
- not a learned-policy or AutoRaceEvolve result;
- not proof that `SET_POSITION_TARGET_LOCAL_NED` is sufficient for Round 1.
