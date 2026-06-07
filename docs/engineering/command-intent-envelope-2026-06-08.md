# Command Intent Envelope

Issue: #14.

## Decision

Add a transport-independent command-intent envelope between the conservative
solver and the future MAVSDK/binary MAVLink transport. The envelope maps
`ControlCommand` values into the official command-message naming surface without
claiming binary serialization or simulator compatibility.

The current mapping emits `SET_POSITION_TARGET_LOCAL_NED` intents with
`MAV_FRAME_BODY_NED` body-velocity semantics. This is grounded in VADR-TS-002,
Issue 00.02, dated 2026-05-08
(https://www.theaigrandprix.com/wp-content/uploads/2026/05/260508_Technical_Spec_0002.pdf),
which documents the command messages and MAVLink frames exposed by the virtual
qualifier interface.

## Boundary

The envelope accepts:

```text
ControlCommand(sim_time_ns, kind, source_frame_id, forward/right/down velocity, yaw_rate, reason)
```

It emits:

```text
MavlinkCommandIntent(
  message_name=SET_POSITION_TARGET_LOCAL_NED,
  frame=MAV_FRAME_BODY_NED,
  intent_profile=body_ned_velocity_plus_yaw_rate,
  velocity_body_ned_m_s,
  yaw_rate_rad_s,
  ignored_setpoint_groups
)
```

`HOLD` always zeroes velocity and yaw-rate intent. `REACQUIRE` preserves the
controller's conservative yaw-rate intent. `BODY_VELOCITY` preserves body-NED
velocity and yaw-rate values after finite-value validation.

## Evidence

Generated artifact:

```text
docs/engineering/evidence/command-intent-envelope-2026-06-08.json
sha256 3d2db37628d3ec2d79c52c6bc8ed27d084488fda89b214c62d4e37023f3d0291
```

The JSON fixture records the validation surface. It does not execute tests or
claim pass/fail status; pass/fail evidence comes from the local/CI commands
below.

Runtime intent values remain numeric. The evidence generator serializes float
values as six-decimal strings only in the checked-in evidence artifact to avoid
default JSON float-format drift.

Validation:

```bash
uv run --python 3.14 --with jsonschema --with pyyaml --with ruff --with pytest \
  python -m pytest tests/test_mavlink_command_intent.py tests/test_solver_baseline.py
./scripts/aigp_local_gate.sh
```

## GO Evidence

- `test_body_velocity_command_maps_to_official_message_intent`
- `test_hold_command_zeroes_velocity_and_yaw_rate`
- `test_reacquire_command_preserves_conservative_yaw_intent`
- `test_command_intent_rejects_non_finite_control_fields`
- `test_command_intent_rejects_bool_control_fields`
- `test_command_intent_rejects_invalid_timestamps`
- `test_command_intent_rejects_bool_source_frame_id`
- `test_command_intent_evidence_uses_fixed_float_strings`
- `test_command_intent_evidence_writer_formats_raw_floats`
- `test_command_intent_as_dict_is_stable_and_json_shaped`

## Non-Claims

- not binary MAVLink serialization evidence;
- not MAVSDK integration evidence;
- not official simulator compatibility evidence;
- not a valid-run result;
- not latency, lap-time, or reliability evidence;
- not proof that `SET_POSITION_TARGET_LOCAL_NED` is the final racing command path.
