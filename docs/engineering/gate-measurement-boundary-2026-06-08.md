# Gate Measurement Boundary

Issue: #9.

## Decision

Keep detector-derived screen-space corners on the conservative center/depth
path. Full planar PnP is only available when the input carries physical
gate-local corner labels.

## Scope

- `GateObservation` from the Round 1 bbox detector uses screen-space
  top-left, top-right, bottom-right, bottom-left corners.
- Screen-space bbox corners produce `SCREEN_SPACE_CENTER_DEPTH` measurements.
- `LabeledGateImageCorners` produce `LABELED_PLANAR_PNP` measurements.
- `StateEstimate` preserves the measurement mode so downstream code can branch
  without assuming that bbox corners observed full square-gate roll.

## GO Evidence

The estimator now records the pose-measurement source mode and preserves the
full-PnP boundary in tests.

Tests:

- `test_gate_observation_measurement_is_center_depth_only`
- `test_gate_observation_measurement_requires_uncertainty`
- `test_labeled_gate_measurement_carries_full_planar_pose`
- `test_screen_space_gate_observation_cannot_enter_full_planar_pnp_path`
- `test_estimator_reports_gate_without_velocity`
- `test_estimator_degrades_malformed_gate_observation_to_no_gate`
- `test_estimator_degrades_missing_corner_uncertainty_without_pose`
- `test_estimator_degrades_missing_gate_metadata_without_crashing`
- `test_gate_pose_measurement_rejects_contradictory_modes`
- `test_gate_pose_measurement_rejects_missing_screen_space_uncertainty`
- `test_gate_pose_measurement_coerces_mode_and_preserves_invariants`
- `test_gate_pose_measurement_rejects_planar_center_mismatch`

Validation:

```bash
uv run --python 3.14 --with pytest python -m pytest tests/test_estimation.py tests/test_perception_geometry.py tests/test_perception_detector.py
./scripts/aigp_local_gate.sh
```

Machine-readable evidence:

```text
docs/engineering/evidence/gate-measurement-boundary-2026-06-08.json
sha256 c6a0b4b089d84fa0e61b179f776834bc1d7808b0e94f6e6e78fa7a902d47590a
```

## Non-Claims

- No full VIO claim.
- No ADR-VINS or partial-corner reprojection claim.
- No Round 2 visual robustness claim.
- No physical-camera calibration claim.
- No full square-gate in-plane roll disambiguation from bbox corners.
