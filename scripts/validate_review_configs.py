"""Validate AI review configuration files."""

from __future__ import annotations

import json
import subprocess
import sys
import tomllib
import urllib.request
from pathlib import Path
from typing import Any

try:
    import jsonschema
    import yaml
except ImportError as exc:  # pragma: no cover - exercised by users without dev deps
    raise SystemExit(
        "Missing validation dependency. Install dev dependencies with "
        "`python -m pip install -e '.[dev]'`."
    ) from exc


ROOT = Path(__file__).resolve().parents[1]
CODERABBIT_SCHEMA_URL = "https://coderabbit.ai/integrations/schema.v2.json"


def load_yaml(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as handle:
        return yaml.safe_load(handle)


def load_toml(path: Path) -> dict[str, Any]:
    with path.open("rb") as handle:
        return tomllib.load(handle)


def fetch_coderabbit_schema() -> dict[str, Any]:
    with urllib.request.urlopen(CODERABBIT_SCHEMA_URL, timeout=15) as response:
        return json.loads(response.read().decode("utf-8"))


def validate_coderabbit() -> None:
    config = load_yaml(ROOT / ".coderabbit.yaml")
    schema = fetch_coderabbit_schema()
    jsonschema.Draft7Validator.check_schema(schema)
    jsonschema.validate(config, schema)


def validate_qodo() -> None:
    config = load_toml(ROOT / ".pr_agent.toml")
    required_sections = {"github_app", "review_agent", "checks", "config"}
    missing = required_sections.difference(config)
    if missing:
        raise AssertionError(f".pr_agent.toml missing sections: {sorted(missing)}")

    commands = config["github_app"].get("pr_commands", [])
    for command in ("/agentic_describe", "/agentic_review"):
        if command not in commands:
            raise AssertionError(f"Qodo github_app.pr_commands missing {command}")

    threshold = config["review_agent"].get("inline_comments_severity_threshold")
    if threshold not in {1, 2, 3}:
        raise AssertionError("Qodo inline_comments_severity_threshold must be 1, 2, or 3")


def validate_workflow_yaml() -> None:
    workflow = load_yaml(ROOT / ".github" / "workflows" / "ci.yml")
    if not isinstance(workflow, dict):
        raise AssertionError("CI workflow must parse as a YAML mapping")
    if "jobs" not in workflow:
        raise AssertionError("CI workflow must define jobs")


def validate_ruff() -> None:
    subprocess.run(
        [
            sys.executable,
            "-m",
            "ruff",
            "check",
            str(ROOT / "scripts" / "validate_review_configs.py"),
        ],
        check=True,
    )


def main() -> int:
    validate_coderabbit()
    validate_qodo()
    validate_workflow_yaml()
    validate_ruff()
    print("AI review configuration validation passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
