# Telemetry Probe Fixture

This note records the first deterministic telemetry probe for issue #3.

Fixture input:

```text
tests/fixtures/telemetry_probe_spec_messages.json
```

Generated evidence:

```text
docs/engineering/evidence/telemetry-probe-fixture-2026-06-08.json
```

Command:

```bash
uv run --python 3.14 --with jsonschema --with pyyaml --with ruff --with pytest \
  python scripts/aigp_telemetry_probe.py \
  --fixture-json tests/fixtures/telemetry_probe_spec_messages.json \
  --source-label fixture:spec_messages \
  --write-json docs/engineering/evidence/telemetry-probe-fixture-2026-06-08.json
```

Outcome:

- heartbeat parsed and fresh at fixture end;
- `ATTITUDE`, `HIGHRES_IMU`, and `TIMESYNC` parsed without errors;
- per-message references preserve `_monotonic_s` and `_frame_id` for audit joins;
- `heartbeat_fresh_at_end` is computed against `probe_end_monotonic_s`, not only
  the last processed message timestamp;
- velocity probe reports `NOT_AVAILABLE` for the spec-message fixture.

Non-claims:

- not official simulator telemetry evidence;
- not binary MAVLink decoding evidence;
- not a velocity availability claim for the official simulator;
- not a latency benchmark.
