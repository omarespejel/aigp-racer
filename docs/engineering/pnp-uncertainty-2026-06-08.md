# PnP And Detector Uncertainty Fixture

Issue: #5.

## Decision

Use an EXPERIMENTAL pure-Python planar homography decomposition for the first
full-PnP fixture. Do not add OpenCV until official runtime dependency policy is
known.

## Scope

- Four inner gate corners provided as physical gate-local labels: top-left,
  top-right, bottom-right, bottom-left.
- Known AI Grand Prix camera intrinsics and known gate dimensions.
  Source: AI Grand Prix Technical Specification VADR-TS-002, Issue 00.02,
  2026-05-08, mirrored in `docs/engineering/spec-notes.md`.
- Synthetic perspective-skewed gate projections.
- Detector outputs carry `corner_uncertainty_px` in the same screen-space order
  as the ordered corners: top-left, top-right, bottom-right, bottom-left. Each
  value is a non-negative pixel-radius bound for bbox-derived corners, not a
  statistical sigma; `None` means the detector did not estimate uncertainty.
  This lets downstream pose and evidence code distinguish precise corners from
  bbox-derived corners without treating the values as calibrated covariance.
  Screen-space bbox corners are not physical gate-corner labels for arbitrary
  in-plane roll.

## GO Evidence

The synthetic perspective-skewed gate test recovers gate center pose and
sub-pixel reprojection error using only checked-in code and fixtures.

Tests: `test_planar_pnp_recovers_perspective_skewed_gate_pose` and
`test_planar_pnp_recovers_rolled_gate_pose` in
`tests/test_perception_geometry.py`.

Pass criteria: center pose recovery within `1e-9` meters and mean/max
reprojection error below `1e-9` pixels.

Validation:

```bash
./scripts/aigp_local_gate.sh
```

Machine-readable evidence:

```text
docs/engineering/evidence/pnp-uncertainty-2026-06-08.json
sha256 ee8cba27acc0e68e535e489ce0f00d14d8c32178fa80286d1fed9a4fbd74a437
```

## Non-Claims

- No Round 2 visual robustness claim.
- No physical-camera calibration claim.
- No full VIO claim.
- No OpenCV availability claim.
- No partial-corner ADR-VINS claim.
- No back-facing gate pose claim.
- No unlabeled square-gate in-plane roll disambiguation claim.
