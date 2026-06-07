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
git diff --exit-code docs/engineering/evidence/command-intent-envelope-2026-06-08.json
git diff --exit-code docs/engineering/evidence/jpeg-decode-benchmark-2026-06-08.json
git diff --exit-code docs/engineering/evidence/practice-adapter-2026-06-08.json
git diff --exit-code docs/engineering/evidence/gate-measurement-boundary-2026-06-08.json
