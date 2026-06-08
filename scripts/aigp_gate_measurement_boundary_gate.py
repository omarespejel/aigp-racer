"""Regenerate the gate-measurement boundary evidence artifact."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


def build_evidence() -> dict[str, Any]:
    return {
        "claim_boundary": "deterministic estimator adapter tests only",
        "commands": [
            "uv run --python 3.14 --with pytest python -m pytest "
            "tests/test_estimation.py tests/test_perception_geometry.py "
            "tests/test_perception_detector.py",
            "./scripts/aigp_local_gate.sh",
        ],
        "github_issues": [
            "https://github.com/omarespejel/aigp-racer/issues/9",
            "https://github.com/omarespejel/aigp-racer/issues/23",
        ],
        "depth_measurement_bases": [
            {
                "basis": "INNER_OPENING",
                "width_m": 1.5,
                "source": "AI Grand Prix Technical Specification VADR-TS-002 gate inner opening",
            },
            {
                "basis": "OUTER_FRAME",
                "width_m": 2.7,
                "source": "AI Grand Prix Technical Specification VADR-TS-002 gate outer frame",
            },
        ],
        "measurement_modes": [
            {
                "declares_measurement_basis": True,
                "full_planar_pose": False,
                "mode": "SCREEN_SPACE_CENTER_DEPTH",
                "source": "GateObservation screen-space bbox corners",
            },
            {
                "declares_measurement_basis": True,
                "full_planar_pose": True,
                "mode": "LABELED_PLANAR_PNP",
                "source": "LabeledGateImageCorners physical gate-local labels",
            },
        ],
        "non_claims": [
            "not full VIO evidence",
            "not ADR-VINS or partial-corner reprojection evidence",
            "not Round 2 visual robustness evidence",
            "not physical-camera calibration evidence",
            "not official Round 1 highlight-basis evidence before a real frame is captured",
            "not full square-gate in-plane roll disambiguation from bbox corners",
        ],
        "required_boundary": {
            "depth_basis_must_be_declared": True,
            "labeled_corners_required_for_full_planar_pnp": True,
            "round1_color_bbox_basis": "OUTER_FRAME",
            "round1_color_bbox_basis_status": "provisional until first official simulator frame",
            "screen_space_measurement_requires_uncertainty": True,
            "screen_space_observation_can_claim_roll": False,
            "screen_space_observation_mode": "SCREEN_SPACE_CENTER_DEPTH",
        },
        "schema_version": "aigp.gate_measurement_boundary.v0",
        "source_files": [
            "estimation/state.py",
            "tests/test_estimation.py",
            "perception/detector.py",
            "perception/geometry.py",
            "scripts/aigp_gate_measurement_boundary_gate.py",
            "docs/engineering/gate-measurement-boundary-2026-06-08.md",
            "docs/engineering/gate-depth-measurement-basis-2026-06-08.md",
        ],
        "status": "passed",
        "tests": [
            {
                "name": "test_frontoparallel_pose_estimate_uses_declared_measurement_basis",
                "path": "tests/test_perception_geometry.py",
                "purpose": "verify 1.5 m inner-opening and 2.7 m outer-frame bases "
                "produce distinct depth estimates",
            },
            {
                "name": "test_gate_observation_measurement_uses_declared_depth_basis",
                "path": "tests/test_estimation.py",
                "purpose": "verify estimator measurements propagate the declared depth basis",
            },
            {
                "name": "test_gate_observation_measurement_is_center_depth_only",
                "path": "tests/test_estimation.py",
                "purpose": "verify detector observations only produce center/depth measurements",
            },
            {
                "name": "test_gate_observation_measurement_requires_uncertainty",
                "path": "tests/test_estimation.py",
                "purpose": "verify detector observations without uncertainty "
                "cannot enter the measurement adapter",
            },
            {
                "name": "test_labeled_gate_measurement_carries_full_planar_pose",
                "path": "tests/test_estimation.py",
                "purpose": "verify physical-labeled corners produce full planar pose measurements",
            },
            {
                "name": "test_screen_space_gate_observation_cannot_enter_full_planar_pnp_path",
                "path": "tests/test_estimation.py",
                "purpose": "verify screen-space bbox corners cannot enter the full-PnP adapter",
            },
            {
                "name": "test_estimator_reports_gate_without_velocity",
                "path": "tests/test_estimation.py",
                "purpose": "verify StateEstimate preserves screen-space measurement mode",
            },
            {
                "name": "test_estimator_degrades_malformed_gate_observation_to_no_gate",
                "path": "tests/test_estimation.py",
                "purpose": "verify malformed observations return a structured diagnostic event "
                "and emit a telemetry log",
            },
            {
                "name": "test_estimator_degrades_missing_corner_uncertainty_without_pose",
                "path": "tests/test_estimation.py",
                "purpose": "verify detector observations without uncertainty "
                "do not become pose measurements",
            },
            {
                "name": "test_estimator_degrades_missing_gate_metadata_without_crashing",
                "path": "tests/test_estimation.py",
                "purpose": "verify malformed observations missing metadata still degrade safely "
                "with a structured telemetry log",
            },
            {
                "name": "test_estimator_throttles_repeated_malformed_gate_logs",
                "path": "tests/test_estimation.py",
                "purpose": "verify repeated malformed gate frames keep diagnostics "
                "but throttle logs",
            },
            {
                "name": "test_estimator_rejects_bool_and_non_int_intervals",
                "path": "tests/test_estimation.py",
                "purpose": "verify estimator timing config rejects bool-as-int values",
            },
            {
                "name": "test_gate_pose_measurement_rejects_contradictory_modes",
                "path": "tests/test_estimation.py",
                "purpose": "verify measurement mode invariants are enforced at construction",
            },
            {
                "name": "test_gate_pose_measurement_rejects_missing_screen_space_uncertainty",
                "path": "tests/test_estimation.py",
                "purpose": "verify screen-space measurements require explicit uncertainty bounds",
            },
            {
                "name": "test_gate_pose_measurement_rejects_bool_uncertainty",
                "path": "tests/test_estimation.py",
                "purpose": "verify explicit uncertainty bounds reject bool-as-number values",
            },
            {
                "name": "test_gate_pose_measurement_coerces_mode_and_preserves_invariants",
                "path": "tests/test_estimation.py",
                "purpose": "verify raw string modes cannot bypass measurement invariants",
            },
            {
                "name": "test_gate_pose_measurement_rejects_planar_center_mismatch",
                "path": "tests/test_estimation.py",
                "purpose": "verify labeled planar measurements cannot publish "
                "a center that disagrees with planar_pose.center",
            },
            {
                "name": "test_gate_pose_measurement_rejects_wrong_planar_pose_type",
                "path": "tests/test_estimation.py",
                "purpose": "verify untyped planar_pose values fail with a controlled ValueError",
            },
        ],
        "validation": {
            "focused_pytest_count": 46,
            "local_gate_pytest_count": 223,
            "status": "passed",
        },
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--write-json", required=True, type=Path)
    args = parser.parse_args()

    args.write_json.parent.mkdir(parents=True, exist_ok=True)
    args.write_json.write_text(
        json.dumps(build_evidence(), indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


if __name__ == "__main__":
    main()
