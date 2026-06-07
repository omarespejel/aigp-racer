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
  python -m ruff check .

uv run --python 3.14 --with jsonschema --with pyyaml --with ruff --with pytest \
  python -m ruff format --check .

uv run --python 3.14 --with jsonschema --with pyyaml --with ruff --with pytest \
  python -m pytest

git diff --check

