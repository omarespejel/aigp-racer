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
REQUIRED_DOCS = (
    "AGENTS.md",
    ".codex/START_HERE.md",
    ".codex/HANDOFF.md",
    ".codex/research/README.md",
    ".codex/research/north_star.yml",
    ".codex/research/operating_model.yml",
    ".github/pull_request_template.md",
    ".github/ISSUE_TEMPLATE/research-frontier.yml",
    ".github/ISSUE_TEMPLATE/hardening-followup.yml",
    ".github/ISSUE_TEMPLATE/paper-claim.yml",
    ".github/instructions/trusted-core.instructions.md",
    "docs/engineering/reproducibility.md",
    "docs/engineering/hardening-policy.md",
    "docs/security/threat-model.md",
    "AIGP_RACER_LAB.md",
)
ISSUE_FORM_REQUIRED_TOP_LEVEL_KEYS = {"name", "description", "body"}
RESEARCH_REQUIRED_FIELDS = {
    "thesis",
    "why_it_matters_for_ai_grand_prix",
    "smallest_falsifying_experiment",
    "go_gate",
    "no_go_gate",
    "required_artifacts",
    "non_claims",
    "local_validation_plan",
}
RESEARCH_ALLOWED_OUTCOMES = {"GO", "NO_GO", "NARROW_CLAIM", "FOLLOWUP_ISSUE", "KILL"}


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


def validate_required_docs() -> None:
    missing = [path for path in REQUIRED_DOCS if not (ROOT / path).exists()]
    if missing:
        raise AssertionError(f"Missing required lab docs: {missing}")


def validate_issue_forms() -> None:
    issue_template_dir = ROOT / ".github" / "ISSUE_TEMPLATE"
    forms = sorted(
        path for path in issue_template_dir.glob("*.yml") if path.name not in {"config.yml"}
    )
    if not forms:
        raise AssertionError("No GitHub issue forms found")

    for form_path in forms:
        form = load_yaml(form_path)
        if not isinstance(form, dict):
            raise AssertionError(f"{form_path} must parse as a YAML mapping")
        missing = ISSUE_FORM_REQUIRED_TOP_LEVEL_KEYS.difference(form)
        if missing:
            raise AssertionError(f"{form_path} missing top-level keys: {sorted(missing)}")
        body = form["body"]
        if not isinstance(body, list) or not body:
            raise AssertionError(f"{form_path} body must be a non-empty list")
        for index, item in enumerate(body):
            if not isinstance(item, dict) or "type" not in item:
                raise AssertionError(f"{form_path} body item {index} must define a type")


def validate_research_operating_model() -> None:
    model = load_yaml(ROOT / ".codex" / "research" / "operating_model.yml")
    unit = model.get("unit_of_work", {})
    required_fields = set(unit.get("required_fields", []))
    missing_fields = RESEARCH_REQUIRED_FIELDS.difference(required_fields)
    if missing_fields:
        raise AssertionError(
            f"operating_model.yml missing required issue fields: {sorted(missing_fields)}"
        )

    allowed_outcomes = set(unit.get("allowed_outcomes", []))
    missing_outcomes = RESEARCH_ALLOWED_OUTCOMES.difference(allowed_outcomes)
    if missing_outcomes:
        raise AssertionError(
            f"operating_model.yml missing allowed outcomes: {sorted(missing_outcomes)}"
        )

    review_policy = model.get("review_bot_policy", {})
    quiet_window = review_policy.get("required_quiet_window_minutes")
    if quiet_window != 5:
        raise AssertionError("review_bot_policy.required_quiet_window_minutes must be 5")


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
    validate_required_docs()
    validate_coderabbit()
    validate_qodo()
    validate_workflow_yaml()
    validate_issue_forms()
    validate_research_operating_model()
    validate_ruff()
    print("AI review and research-lab configuration validation passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
