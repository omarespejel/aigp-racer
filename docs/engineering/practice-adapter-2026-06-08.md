# Practice Frame Adapter

Issue: #11.

## Decision

Add a practice-only adapter for Elodin-style raw RGBA frames. The adapter strips
alpha, validates shape and pixel channels, preserves `sim_time_ns` and
`source_frame_id`, and tags the output as `elodin_practice_rgba`.

This keeps Elodin useful for iteration without creating an Elodin-only detector
or implying official simulator compatibility.

## Boundary

The adapter accepts:

```text
Sequence[height][width][RGBA channel]
```

It emits:

```text
DetectorFrame(rgb, sim_time_ns, source_frame_id, source, claim_boundary)
```

Default expected dimensions are 640 x 360 to match the AI Grand Prix camera
resolution documented in VADR-TS-002, Issue 00.02, dated 2026-05-08
(https://www.theaigrandprix.com/wp-content/uploads/2026/05/260508_Technical_Spec_0002.pdf).
Tests use a smaller fixture to keep CI cheap.

## Evidence

Generated artifact:

```text
docs/engineering/evidence/practice-adapter-2026-06-08.json
sha256 631fe81af32ba869a57bb24b83adb4603ce044d9bb75b98f1cc9d24fb503adca
```

Validation:

```bash
uv run --python 3.14 --with jsonschema --with pyyaml --with ruff --with pytest \
  python -m pytest tests/test_practice_adapter.py tests/test_perception_detector.py
./scripts/aigp_local_gate.sh
```

## GO Evidence

- `test_elodin_rgba_frame_adapter_feeds_round1_detector`
- `test_elodin_rgba_frame_adapter_rejects_wrong_dimensions`
- `test_elodin_rgba_frame_adapter_rejects_malformed_pixels`
- `test_elodin_rgba_frame_adapter_normalizes_non_sequence_errors`
- `test_elodin_rgba_frame_adapter_validates_frame_metadata_types`
- `test_elodin_rgba_frame_adapter_validates_expected_dimensions`
- `test_practice_adapter_evidence_matches_generator`

## Non-Claims

- not official simulator compatibility evidence;
- not an Elodin fidelity claim;
- not a valid-run result;
- not a latency, speed, or reliability claim;
- not a replacement for the official UDP JPEG receiver.
