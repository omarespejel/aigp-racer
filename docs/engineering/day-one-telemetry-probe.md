# Day-One Telemetry Probe

Purpose: resolve whether the official simulator exposes clean linear velocity.

## Why This Matters

If velocity telemetry is available, the first estimator can be simple:

```text
attitude + velocity + gate-relative pose correction
```

If velocity telemetry is not available, the estimator must rely more heavily on:

```text
IMU integration + gate-relative drift correction
```

## Probe Procedure

1. Start the official simulator.
2. Start the contestant client with telemetry logging enabled.
3. Record every MAVLink message type received for at least 10 seconds.
4. Feed the raw messages through `TelemetryProbe`.
5. Save:
   - message type histogram;
   - first example of each message type;
   - velocity probe report;
   - simulator package/version;
   - spec PDF version.

## Expected Outcomes

`GO`:

- `TelemetryProbe` reports `AVAILABLE`.
- A velocity source is identified, with fields and message type.
- The estimator can use velocity in the conservative baseline.

`NARROW_CLAIM`:

- `TelemetryProbe` reports `NOT_AVAILABLE`.
- Continue with IMU + gate-relative drift correction.

`NO_GO`:

- Telemetry cannot be received or decoded after heartbeat is established.
- Open a hardening issue for MAVLink transport or dialect mismatch.

## Current Local Fixture Command

```bash
uv run --python 3.14 --with jsonschema --with pyyaml --with ruff --with pytest \
  python scripts/aigp_telemetry_probe.py \
  --fixture-json tests/fixtures/telemetry_probe_spec_messages.json \
  --source-label fixture:spec_messages \
  --write-json docs/engineering/evidence/telemetry-probe-fixture-2026-06-08.json
```

The current implementation also has a local UDP JSON smoke path. That path is
only for decoded-message transport tests; it does not decode binary MAVLink 2.

Non-claims:

- this fixture does not prove official simulator behavior;
- this fixture does not prove binary MAVLink decoding;
- this fixture is not a latency benchmark;
- this fixture does not prove whether official velocity telemetry is available.
