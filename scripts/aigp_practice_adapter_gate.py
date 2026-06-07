"""Regenerate practice-frame adapter evidence for issue #11."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


def build_evidence() -> dict[str, Any]:
    test_records = [
        {
            "path": "tests/test_practice_adapter.py",
            "name": "test_elodin_rgba_frame_adapter_feeds_round1_detector",
            "purpose": "verify practice RGBA frames can enter the existing detector boundary",
        },
        {
            "path": "tests/test_practice_adapter.py",
            "name": "test_elodin_rgba_frame_adapter_rejects_wrong_dimensions",
            "purpose": "verify frame dimensions are explicit and validated",
        },
        {
            "path": "tests/test_practice_adapter.py",
            "name": "test_elodin_rgba_frame_adapter_rejects_malformed_pixels",
            "purpose": "verify malformed pixels fail before perception",
        },
        {
            "path": "tests/test_practice_adapter.py",
            "name": "test_elodin_rgba_frame_adapter_normalizes_non_sequence_errors",
            "purpose": (
                "verify malformed frame containers, rows, and pixels fail with "
                "PracticeFrameAdapterError"
            ),
        },
        {
            "path": "tests/test_practice_adapter.py",
            "name": "test_elodin_rgba_frame_adapter_validates_frame_metadata_types",
            "purpose": "verify frame timestamps and source ids stay typed at the boundary",
        },
        {
            "path": "tests/test_practice_adapter.py",
            "name": "test_elodin_rgba_frame_adapter_validates_expected_dimensions",
            "purpose": "verify adapter configuration is bounded",
        },
        {
            "path": "tests/test_practice_adapter.py",
            "name": "test_practice_adapter_evidence_matches_generator",
            "purpose": "verify evidence artifact stays deterministic",
        },
    ]
    return {
        "schema_version": "aigp.practice_adapter.v0",
        "github_issue": "https://github.com/omarespejel/aigp-racer/issues/11",
        "claim_boundary": (
            "deterministic fixture evidence only; practice-only Elodin RGBA adapter, "
            "not official UDP JPEG compatibility"
        ),
        "adapter": {
            "module": "vision/practice_adapter.py",
            "input": "Elodin-style RGBA frame sequence",
            "output": "DetectorFrame.rgb plus sim_time_ns, source_frame_id, and source tag",
            "source_tag": "elodin_practice_rgba",
            "default_expected_resolution_px": [640, 360],
        },
        "go_gate_evidence": {
            "accepts_deterministic_rgba_fixture": True,
            "feeds_existing_round1_detector": True,
            "preserves_sim_time_ns": True,
            "preserves_source_frame_id": True,
            "normalizes_malformed_input_errors": True,
            "validates_frame_metadata_types": True,
            "requires_elodin_runtime_in_ci": False,
            "tags_practice_only_source": True,
        },
        "known_boundaries": [
            {
                "surface": "official_vision",
                "boundary": "does not decode UDP chunked JPEG",
            },
            {
                "surface": "official_simulator",
                "boundary": "does not prove official simulator compatibility",
            },
            {
                "surface": "frame_semantics",
                "boundary": (
                    "strips alpha only; does not perform camera calibration or color conversion"
                ),
            },
        ],
        "tests": test_records,
        "commands": [
            "uv run --python 3.14 --with jsonschema --with pyyaml --with ruff --with pytest "
            "python -m pytest tests/test_practice_adapter.py tests/test_perception_detector.py",
            "./scripts/aigp_local_gate.sh",
        ],
        "validation": {
            "generator_executes_tests": False,
            "listed_go_gate_test_count": len(test_records),
            "status_source": "external local or CI gate; this generator only writes evidence",
        },
        "non_claims": [
            "not official simulator compatibility evidence",
            "not an Elodin fidelity claim",
            "not a valid-run result",
            "not a latency, speed, or reliability claim",
            "not a replacement for the official UDP JPEG receiver",
        ],
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--write-json", type=Path, required=True)
    args = parser.parse_args()

    args.write_json.parent.mkdir(parents=True, exist_ok=True)
    args.write_json.write_text(
        json.dumps(build_evidence(), indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
