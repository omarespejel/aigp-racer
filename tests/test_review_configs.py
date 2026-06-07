from __future__ import annotations

from scripts import validate_review_configs


def test_review_configs_are_valid() -> None:
    validate_review_configs.validate_required_docs()
    validate_review_configs.validate_coderabbit()
    validate_review_configs.validate_qodo()
    validate_review_configs.validate_workflow_yaml()
    validate_review_configs.validate_issue_forms()
    validate_review_configs.validate_research_operating_model()
