# Qodo And CodeRabbit Setup

Date: 2026-06-08.

This repo uses version-controlled review configuration for both Qodo and CodeRabbit.

## Sources Checked

- CodeRabbit configuration overview: https://docs.coderabbit.ai/guides/configuration-overview
- CodeRabbit YAML configuration: https://docs.coderabbit.ai/getting-started/yaml-configuration
- CodeRabbit configuration reference, last updated 2026-06-02: https://docs.coderabbit.ai/reference/configuration
- Qodo v2 code review overview: https://docs.qodo.ai/code-review
- Qodo `.pr_agent.toml` configuration: https://docs.qodo.ai/install-and-configure/configuration-overview/configuration-file
- Qodo configuration and command reference: https://docs.qodo.ai/install-and-configure/configuration-overview/configuration-and-command-reference

## What Was Added

- `.coderabbit.yaml`: CodeRabbit v2 YAML config with schema reference, path-specific robotics instructions, tool integrations, issue planning, and guideline file patterns.
- `.pr_agent.toml`: Qodo v2 Git integration config with `/agentic_describe`, `/agentic_review`, push-triggered review, CI feedback, severity thresholding, and drone-racing compliance guidelines.
- `.github/copilot-instructions.md`: shared repository instructions that CodeRabbit can use through its code-guidelines feature.
- `docs/review-guidelines.md`: explicit review criteria for runtime, perception, estimation, planning, policy, evaluator, and docs changes.
- `scripts/validate_review_configs.py`: local validation for TOML, YAML, and CodeRabbit schema compatibility.
- `.github/workflows/ci.yml`: first CI job for review-config validation, formatting/linting, and tests once implementation begins.

## Setup Steps Still Needed In GitHub

1. Install or enable the CodeRabbit GitHub app on `omarespejel/aigp-racer`.
2. Install or enable the Qodo Git integration on `omarespejel/aigp-racer`.
3. Confirm both tools can read repository config on a small test PR.
4. Add GitHub labels used by the configs:
   - `runtime`
   - `perception`
   - `estimation`
   - `offline-eval`
   - `compliance`
   - `docs`
   - `skip-review`
   - `generated-only`
5. Keep `request_changes_workflow` disabled until baseline CI and review behavior are proven on real PRs.

## Operating Policy

CodeRabbit should provide broad context, path-specific review, issue planning, and external-tool checks. Qodo should provide severity-gated issue/compliance review and CI failure feedback. If the two tools produce conflicting advice, keep the finding that is backed by source code, tests, logs, or official competition docs.

