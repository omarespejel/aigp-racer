#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

uv run --python 3.14 --with jsonschema --with pyyaml --with ruff --with pytest \
  python scripts/validate_review_configs.py

uv run --python 3.14 --with jsonschema --with pyyaml --with ruff --with pytest \
  python scripts/aigp_profile_gate.py \
  --write-json docs/engineering/evidence/aigp-profile-fixture-2026-06-08.json

uv run --python 3.14 --with jsonschema --with pyyaml --with ruff --with pytest \
  python scripts/aigp_fixture_gate.py

uv run --python 3.14 --with jsonschema --with pyyaml --with ruff --with pytest \
  python scripts/aigp_telemetry_probe.py \
  --fixture-json tests/fixtures/telemetry_probe_spec_messages.json \
  --source-label fixture:spec_messages \
  --write-json docs/engineering/evidence/telemetry-probe-fixture-2026-06-08.json

uv run --python 3.14 --with jsonschema --with pyyaml --with ruff --with pytest \
  python scripts/aigp_sim_access_probe.py \
  --write-json docs/engineering/evidence/sim-access-probe-2026-06-08.json

uv run --python 3.14 --with jsonschema --with pyyaml --with ruff --with pytest \
  python scripts/aigp_official_package_probe.py \
  --check-json docs/engineering/evidence/official-sim-package-probe-2026-06-08.json

uv run --python 3.14 --with jsonschema --with pyyaml --with ruff --with pytest \
  python scripts/aigp_official_packet_capture.py \
  --fixture \
  --write-json docs/engineering/evidence/official-packet-capture-fixture-2026-06-08.json \
  --check-json docs/engineering/evidence/official-packet-capture-fixture-2026-06-08.json

uv run --python 3.14 --with jsonschema --with pyyaml --with ruff --with pytest \
  python scripts/aigp_command_intent_gate.py \
  --write-json docs/engineering/evidence/command-intent-envelope-2026-06-08.json

uv run --python 3.14 --with jsonschema --with pyyaml --with ruff --with pytest \
  python scripts/aigp_jpeg_decode_benchmark.py \
  --check-json docs/engineering/evidence/jpeg-decode-benchmark-2026-06-08.json \
  --fixture tests/fixtures/frame_640x360_synthetic.jpg

uv run --python 3.14 --with jsonschema --with pyyaml --with ruff --with pytest \
  python scripts/aigp_practice_adapter_gate.py \
  --write-json docs/engineering/evidence/practice-adapter-2026-06-08.json

uv run --python 3.14 --with jsonschema --with pyyaml --with ruff --with pytest \
  python scripts/aigp_gate_measurement_boundary_gate.py \
  --write-json docs/engineering/evidence/gate-measurement-boundary-2026-06-08.json

uv run --python 3.14 --with jsonschema --with pyyaml --with ruff --with pytest \
  python scripts/aigp_controller_safety_gate.py \
  --write-json docs/engineering/evidence/controller-safety-2026-06-08.json

uv run --python 3.14 --with jsonschema --with pyyaml --with ruff --with pytest \
  python scripts/aigp_integrated_dry_run_gate.py \
  --write-json

uv run --python 3.14 --with jsonschema --with pyyaml --with ruff --with pytest \
  python scripts/aigp_minimal_loop_latency_gate.py \
  --check-json docs/engineering/evidence/minimal-loop-latency-2026-06-08.json \
  --fixture tests/fixtures/frame_640x360_synthetic.jpg

uv run --python 3.14 --with jsonschema --with pyyaml --with ruff --with pytest \
  python scripts/aigp_compiled_vision_gate.py \
  --check-json docs/engineering/evidence/compiled-vision-latency-2026-06-08.json \
  --iterations 1000 \
  --warmup 25 \
  --fixture tests/fixtures/frame_640x360_synthetic.jpg

uv run --python 3.14 --with jsonschema --with pyyaml --with ruff --with pytest \
  python scripts/aigp_compiled_vision_gate.py \
  --candidate fixture_step \
  --iterations 2 \
  --warmup 0 \
  --fixture tests/fixtures/frame_640x360_synthetic.jpg \
  --deterministic-clock-step-ns 1000000 \
  --deterministic-environment \
  --write-json docs/engineering/evidence/compiled-vision-latency-drift-check-2026-06-08.json

uv run --python 3.14 --with jsonschema --with pyyaml --with ruff --with pytest \
  python scripts/aigp_compiled_vision_gate.py \
  --candidate fixture_step \
  --iterations 2 \
  --warmup 0 \
  --fixture tests/fixtures/frame_640x360_synthetic.jpg \
  --deterministic-clock-step-ns 1000000 \
  --deterministic-environment \
  --check-json docs/engineering/evidence/compiled-vision-latency-drift-check-2026-06-08.json

uv run --python 3.14 --with jsonschema --with pyyaml --with ruff --with pytest \
  python scripts/aigp_packaging_probe.py \
  --fixture tests/fixtures/frame_640x360_synthetic.jpg \
  --check-json docs/engineering/evidence/opencv-numpy-packaging-probe-2026-06-08.json

uv run --python 3.14 --with jsonschema --with pyyaml --with ruff --with pytest \
  python -m ruff check .

uv run --python 3.14 --with jsonschema --with pyyaml --with ruff --with pytest \
  python -m ruff format --check .

uv run --python 3.14 --with jsonschema --with pyyaml --with ruff --with pytest \
  python -m pytest

git diff --check
git diff --exit-code docs/engineering/evidence/aigp-profile-fixture-2026-06-08.json
git diff --exit-code docs/engineering/evidence/race-episode-fixture-2026-06-08.json
git diff --exit-code docs/engineering/evidence/decision-trace-fixture-2026-06-08.json
git diff --exit-code docs/engineering/evidence/telemetry-probe-fixture-2026-06-08.json
git diff --exit-code docs/engineering/evidence/pnp-uncertainty-2026-06-08.json
git diff --exit-code docs/engineering/evidence/sim-access-probe-2026-06-08.json
git diff --exit-code docs/engineering/evidence/official-sim-package-probe-2026-06-08.json
git diff --exit-code docs/engineering/evidence/official-packet-capture-fixture-2026-06-08.json
git diff --exit-code docs/engineering/evidence/command-intent-envelope-2026-06-08.json
git diff --exit-code docs/engineering/evidence/jpeg-decode-benchmark-2026-06-08.json
git diff --exit-code docs/engineering/evidence/practice-adapter-2026-06-08.json
git diff --exit-code docs/engineering/evidence/gate-measurement-boundary-2026-06-08.json
git diff --exit-code docs/engineering/evidence/controller-safety-2026-06-08.json
git diff --exit-code docs/engineering/evidence/integrated-dry-run-episode-2026-06-08.json
git diff --exit-code docs/engineering/evidence/integrated-dry-run-decision-trace-2026-06-08.json
git diff --exit-code docs/engineering/evidence/minimal-loop-latency-2026-06-08.json
git diff --exit-code docs/engineering/evidence/compiled-vision-latency-2026-06-08.json
git diff --exit-code docs/engineering/evidence/compiled-vision-latency-drift-check-2026-06-08.json
git diff --exit-code docs/engineering/evidence/opencv-numpy-packaging-probe-2026-06-08.json
