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
uv run --python 3.14 --with pytest python -m pytest tests/test_mavlink_telemetry.py
```

Non-claim: this fixture does not prove official simulator behavior.

