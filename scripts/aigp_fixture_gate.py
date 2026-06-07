"""Regenerate deterministic first-runtime evidence fixtures."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from worldforge_bridge.schema import (  # noqa: E402
    build_bootstrap_decision_trace,
    build_bootstrap_episode,
    write_json,
)

EPISODE_PATH = ROOT / "docs" / "engineering" / "evidence" / "race-episode-fixture-2026-06-08.json"
TRACE_PATH = ROOT / "docs" / "engineering" / "evidence" / "decision-trace-fixture-2026-06-08.json"


def main() -> int:
    write_json(EPISODE_PATH, build_bootstrap_episode())
    write_json(TRACE_PATH, build_bootstrap_decision_trace())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
