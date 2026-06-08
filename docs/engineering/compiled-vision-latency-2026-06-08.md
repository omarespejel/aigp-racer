# Compiled Vision Latency

Date: 2026-06-08
Issue: #28

## Thesis

A compiled or vectorized vision path can recover enough camera-frame budget for
the minimal loop by removing Python RGB materialization and Python per-pixel
threshold scanning.

## Result

GO, with a narrow claim.

The benchmark in `scripts/aigp_compiled_vision_gate.py` runs the same local
fixture and downstream estimator/controller/command-intent path as issue #24,
but replaces the Pillow plus pure-Python detector path with:

```text
OpenCV imdecode
  -> NumPy vectorized magenta/white threshold
  -> vectorized bbox extraction
  -> GateObservation(measurement_basis=OUTER_FRAME)
```

This clears the local fixture p99 budgets by a wide margin.

## Evidence

Measured artifact:

```text
docs/engineering/evidence/compiled-vision-latency-2026-06-08.json
```

Measured command:

```bash
uv run --python 3.14 --with opencv-python --with numpy \
  python scripts/aigp_compiled_vision_gate.py \
  --candidate opencv_vectorized \
  --iterations 1000 \
  --warmup 25 \
  --fixture tests/fixtures/frame_640x360_synthetic.jpg \
  --write-json docs/engineering/evidence/compiled-vision-latency-2026-06-08.json
```

Budget source:

```text
AI Grand Prix Technical Specification VADR-TS-002, Issue 00.02, dated 2026-05-08:
camera 30 Hz and command rate <100 Hz.
https://www.theaigrandprix.com/wp-content/uploads/2026/05/260508_Technical_Spec_0002.pdf
```

Local measured result:

```text
candidate: opencv_vectorized
opencv-python: 4.13.0.92
numpy: 2.4.6
fixture: tests/fixtures/frame_640x360_synthetic.jpg
total p99: 2.078857 ms
decode p99: 0.701588 ms
detect p99: 1.351726 ms
decode + detect p99: 2.053314 ms
control + intent p99: 0.006793 ms
passes frame p99 budget: true
passes decode + detect p99 budget: true
passes command p99 budget: true
```

The last output is still a reacquire command because the synthetic fixture has
low detector confidence:

```text
detection_status: DETECTED
measurement_basis: OUTER_FRAME
mask_pixels: 22318
gate_confidence: 0.096866
state_status: GATE_WITHOUT_VELOCITY
command_kind: REACQUIRE
command_reason: gate confidence below threshold
message_name: SET_POSITION_TARGET_LOCAL_NED
```

That is acceptable for this latency experiment. It is not valid-run evidence.

## Packaging Boundary

OpenCV and NumPy installed and imported under local macOS Python 3.14:

```text
opencv-python 4.13.0.92
numpy 2.4.6
```

This is not Windows 11 packaging proof. The official simulator host is Windows
11, so the same dependency pair must be verified on that host before becoming a
runtime dependency decision.

## Drift Policy

The timing JSON is measured evidence, not a deterministic generator output. The
local gate checks schema, fixture integrity, source metadata, pinned config,
candidate provenance, stage latency shape, recomputed budget booleans, and
non-claims with `--check-json`, then asserts the checked-in artifact has no
worktree drift. It does not regenerate p99 values on every run.

## Non-Claims

- Not official simulator latency evidence.
- Not official simulator frame evidence.
- Not a valid-run result.
- Not Round 2 detector evidence.
- Not a final runtime dependency decision.
- Not Windows packaging proof.

## Local Validation

```bash
uv run --python 3.14 --with pytest \
  python -m pytest tests/test_compiled_vision_gate.py tests/test_minimal_loop_latency_gate.py tests/test_perception_detector.py
uv run --python 3.14 \
  python scripts/aigp_compiled_vision_gate.py \
  --check-json docs/engineering/evidence/compiled-vision-latency-2026-06-08.json \
  --iterations 1000 \
  --warmup 25 \
  --fixture tests/fixtures/frame_640x360_synthetic.jpg
./scripts/aigp_local_gate.sh
```
