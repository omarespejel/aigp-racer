# Minimal Loop Latency

Date: 2026-06-08
Issue: #24

## Thesis

A minimal assembled loop from camera bytes to command intent can expose real
integration and latency bottlenecks before the official simulator is available.

## Result

NARROW_CLAIM, with a pure-Python runtime NO-GO.

The loop runner in `scripts/aigp_minimal_loop_latency_gate.py` executes the
current local fixture path:

```text
chunked JPEG bytes
  -> JpegFrameReassembler
  -> Pillow JPEG decode and Python RGB row materialization
  -> Round1ColorGateDetector
  -> MinimalStateEstimator
  -> ConservativeController
  -> build_position_target_body_velocity_intent
```

That proves the modules can be assembled from camera bytes through command
intent without simulator-only state. It also shows that the current Pillow plus
pure-Python detector path is not a credible live runtime path for a 30 Hz camera
budget on this local fixture.

## Evidence

Measured artifact:

```text
docs/engineering/evidence/minimal-loop-latency-2026-06-08.json
```

Measured command:

```bash
uv run --python 3.14 --with pillow==12.2.0 \
  python scripts/aigp_minimal_loop_latency_gate.py \
  --decoder pillow \
  --iterations 100 \
  --warmup 5 \
  --fixture tests/fixtures/frame_640x360_synthetic.jpg \
  --write-json docs/engineering/evidence/minimal-loop-latency-2026-06-08.json
```

Budget source:

```text
AI Grand Prix Technical Specification VADR-TS-002, Issue 00.02, dated 2026-05-08:
camera 30 Hz and command rate <100 Hz.
https://www.theaigrandprix.com/wp-content/uploads/2026/05/260508_Technical_Spec_0002.pdf
```

Local measured result:

```text
decoder: Pillow 12.2.0
windows packaging: not evaluated in this local artifact; verify Windows 11 and Python 3.14 wheel availability before any runtime dependency decision
fixture: tests/fixtures/frame_640x360_synthetic.jpg
fixture sha256: 300317f992c7d4c90396af410c46832d58cc6efed480d229ffaff4b4239b9401
frame budget: 33.333333 ms
total p99: 59.090556 ms
decode p99: 30.814686 ms
detect p99: 28.244385 ms
decode + detect p99: 59.059071 ms
passes frame p99 budget: false
passes decode + detect p99 budget: false
control + intent p99: 0.013403 ms
passes command p99 budget: true
```

The last loop output is a reacquire command:

```text
detection_status: DETECTED
measurement_basis: OUTER_FRAME
state_status: GATE_WITHOUT_VELOCITY
command_kind: REACQUIRE
command_reason: gate confidence below threshold
message_name: SET_POSITION_TARGET_LOCAL_NED
```

This is acceptable for the latency assembly experiment because the issue asks
whether the module chain executes and where time is spent. It is not a valid-run
or tracking-controller result.

## Drift Policy

The timing JSON is measured evidence, not a deterministic generator output. The
local gate validates schema, fixture integrity, pinned config, decoder
provenance, source metadata, non-claims, and recomputed budget booleans with
`--check-json`, then asserts the checked-in artifact has no worktree drift.

The local gate does not regenerate p99 timing values on every run because normal
wall-clock jitter would rewrite the evidence artifact. Regeneration is an
explicit experiment step using the command above.

## Follow-Up

The NO-GO opened a focused compiled/vectorized vision issue:

```text
https://github.com/omarespejel/aigp-racer/issues/28
```

Issue #28 should benchmark OpenCV or PyTurboJPEG plus vectorized thresholding
against this same fixture and artifact schema before we spend more time polishing
the pure-Python detector path.

## Non-Claims

- Not official simulator latency evidence.
- Not a valid-run result.
- Not a lap-time, reliability, or win claim.
- Not proof that pure Python is sufficient for the final runtime.
- Not Windows packaging evidence.
- Not Round 2 detector evidence.

## Local Validation

```bash
uv run --python 3.14 --with pytest \
  python -m pytest tests/test_vision_reassembler.py tests/test_perception_detector.py tests/test_estimation.py tests/test_mavlink_command_intent.py tests/test_minimal_loop_latency_gate.py
uv run --python 3.14 --with pillow==12.2.0 \
  python scripts/aigp_minimal_loop_latency_gate.py \
  --decoder pillow \
  --iterations 100 \
  --warmup 5 \
  --fixture tests/fixtures/frame_640x360_synthetic.jpg \
  --write-json docs/engineering/evidence/minimal-loop-latency-2026-06-08.json
./scripts/aigp_local_gate.sh
```
