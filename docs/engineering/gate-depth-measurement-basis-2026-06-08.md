# Gate Depth Measurement Basis

Date: 2026-06-08
Issue: #23

## Thesis

Screen-space bbox width cannot be converted into metric gate depth unless the
runtime declares which physical gate width the bbox represents.

AI Grand Prix Technical Specification VADR-TS-002, Issue 00.02, dated
2026-05-08, gives two relevant widths: 1.5 m for the inner opening and 2.7 m
for the outer frame. The same observed pixel width therefore changes estimated
depth by 1.8x depending on the selected basis.

## Change

`GateObservation` now carries `measurement_basis` with supported values:

- `INNER_OPENING`
- `OUTER_FRAME`

`estimate_frontoparallel_gate_pose` uses that declared basis when converting
image width to `z_forward_m`. `GatePoseMeasurement` preserves the basis so
WorldForge, DecisionTrace, and controller-side debug traces can distinguish a
center/depth estimate from an inner-opening interpretation versus an outer-frame
interpretation.

The Round 1 color bbox detector currently declares `OUTER_FRAME` because it
tracks highlighted pixels as a bbox around the visible gate frame. This is a
provisional runtime default, not official visual calibration evidence.

## GO Gate

- Detector observations declare a measurement basis.
- Estimator measurements preserve the declared basis.
- Geometry tests cover both 1.5 m and 2.7 m basis constants.
- Integrated dry-run evidence serializes the detection and state measurement
  basis.

## Follow-Up Calibration

When official simulator access is available, capture the first Round 1 frame and
record whether highlighted pixels align with the inner opening, outer frame, or
neither. If neither basis is stable, narrow the detector claim to screen-space
centering until a trained corner detector or calibrated thresholding path exists.

## Non-Claims

- Not official Round 1 visual calibration evidence.
- Not a full PnP validation.
- Not Round 2 visual robustness evidence.
- Not a claim that the official highlight always spans the outer frame.

## Local Validation

```bash
uv run --python 3.14 --with pytest python -m pytest tests/test_perception_geometry.py tests/test_perception_detector.py tests/test_estimation.py
./scripts/aigp_local_gate.sh
```
