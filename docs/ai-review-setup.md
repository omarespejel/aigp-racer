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
- `.github/instructions/trusted-core.instructions.md`: trusted-core review guidance for runtime, evaluator, and evidence-sensitive paths.
- `.github/ISSUE_TEMPLATE/*.yml`: GitHub issue forms for research-frontier, hardening, and claim-promotion issues.
- `.github/pull_request_template.md`: PR template that forces lane, validation, non-claims, and bot quiet-window discipline.
- `docs/review-guidelines.md`: explicit review criteria for runtime, perception, estimation, planning, policy, evaluator, and docs changes.
- `scripts/validate_review_configs.py`: local validation for TOML, YAML, and CodeRabbit schema compatibility.
- `scripts/aigp_local_gate.sh`: baseline local gate for review config, research operating model, deterministic fixture generation, lint, format, tests, and diff checks.
- `scripts/aigp_profile_gate.py`: deterministic profile fixture generator for the first no-claims evidence gate.
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
   - `research-frontier`
   - `hardening`
   - `claim`
5. Keep `request_changes_workflow` disabled until baseline CI and review behavior are proven on real PRs.

## Operating Policy

CodeRabbit should provide broad context, path-specific review, issue planning, and external-tool checks. Qodo should provide severity-gated issue/compliance review and CI failure feedback. If the two tools produce conflicting advice, keep the finding that is backed by source code, tests, logs, or official competition docs.

Use the bot findings as adversarial review signals:

- `must_fix`: fix before merge.
- `evidence_needed`: reproduce locally before merge.
- `stale_or_false_positive`: reply briefly with evidence.
- `followup_issue`: open a GO/NO-GO issue.
- `ignore`: style-only, no correctness/safety/research impact.

Wait 5 minutes after the latest Qodo, CodeRabbit, or human reviewer activity before merging.
