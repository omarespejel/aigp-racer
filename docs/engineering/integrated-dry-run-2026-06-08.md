# Integrated Dry-Run Evidence

Date: 2026-06-08

Issue: https://github.com/omarespejel/aigp-racer/issues/21

## Thesis

A deterministic local dry run can connect the current Round 1 detector,
gate-measurement estimator boundary, conservative controller, and MAVLink
command-intent envelope into offline RaceEpisode and DecisionTrace evidence
without putting WorldForge in the live flight hot path.

## Result

GO, with a narrow claim.

The generator in `scripts/aigp_integrated_dry_run_gate.py` creates one synthetic
highlighted gate frame and runs the actual module chain:

```text
Round1ColorGateDetector
  -> MinimalStateEstimator
  -> ConservativeController
  -> build_position_target_body_velocity_intent
  -> RaceEpisode / DecisionTrace artifacts
```

This proves the current modules can be serialized into offline replay evidence.
It does not prove official simulator compatibility or runtime latency.

## Evidence

- `docs/engineering/evidence/integrated-dry-run-episode-2026-06-08.json`
- `docs/engineering/evidence/integrated-dry-run-decision-trace-2026-06-08.json`
- `tests/test_integrated_dry_run_gate.py`

After issue #23, the dry-run artifacts also serialize the detector and estimator
`measurement_basis`. The synthetic Round 1 bbox path currently records
`OUTER_FRAME`; this is still not official frame-calibration evidence.

## Follow-Ups

- First-frame official simulator depth-basis calibration:
  https://github.com/omarespejel/aigp-racer/issues/23
- Simulator-time command-rate replay determinism:
  https://github.com/omarespejel/aigp-racer/issues/22
- Minimal assembled hot-loop latency:
  https://github.com/omarespejel/aigp-racer/issues/24

## Non-Claims

- Not official simulator compatibility evidence.
- Not a valid-run result.
- Not a lap-time, latency, or reliability claim.
- Not a learned-policy result.
- Not physical-drone transfer evidence.
- Not proof that screen-space detector corners are physical gate-corner labels.
- Not proof that official Round 1 highlighted pixels align with the outer frame.

## Local Validation

```bash
uv run --python 3.14 python scripts/aigp_integrated_dry_run_gate.py --write-json
uv run --python 3.14 --with pytest python -m pytest tests/test_worldforge_bridge.py tests/test_integrated_dry_run_gate.py
./scripts/aigp_local_gate.sh
```
