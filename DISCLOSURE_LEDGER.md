# Disclosure Ledger

This file tracks competition-relevant disclosure material for AI Grand Prix work.

## Generative AI Use

- 2026-06-08: Initial strategy issue and repository scaffolding drafted with Codex using user-provided Claude research excerpts and independently verified public sources.
- 2026-06-08: Qodo and CodeRabbit configuration, review guidelines, CI validation harness, and setup notes drafted with Codex after checking current vendor documentation.
- 2026-06-08: Research-lab operating model, Codex handoff docs, GitHub issue forms, PR template, hardening policy, no-claims policy, threat model, and local gates drafted with Codex from user-provided `provable-transformer-vm` operating-system notes plus current GitHub/Qodo/CodeRabbit documentation.

## FLOSS Dependencies

- Qodo Git integration configuration: `.pr_agent.toml`; service must be installed separately.
- CodeRabbit configuration: `.coderabbit.yaml`; service must be installed separately.
- Python dev-only validation dependencies:
  - `jsonschema`
  - `pytest`
  - `pyyaml`
  - `ruff`
- GitHub issue forms and PR template are repository-native GitHub features; no runtime dependency.
- `scripts/aigp_local_gate.sh` and `scripts/aigp_profile_gate.py` are local validation scripts.

Runtime dependencies remain pending. Add every runtime, training, evaluation, and simulation dependency before submission.

## Models And Weights

Pending. Record source, license, checkpoint hash, training data, and whether the artifact is used in the flight runtime or only offline.

## Data Sources

- AI Grand Prix official rules: https://www.theaigrandprix.com/official-rules/
- AI Grand Prix technical specification VADR-TS-002: https://www.theaigrandprix.com/wp-content/uploads/2026/05/260508_Technical_Spec_0002.pdf
- Elodin AI Grand Prix harness: https://www.elodin.systems/post/elodin-ai-grand-prix-race-sim-harness
- AGIBOT World Challenge dataset: https://huggingface.co/datasets/agibot-world/AgiBotWorldChallenge-2026
- Go2 Air ControlBench public preview: https://huggingface.co/datasets/espejelomar/go2-air-controlbench-v1
- CodeRabbit configuration overview: https://docs.coderabbit.ai/guides/configuration-overview
- CodeRabbit YAML configuration: https://docs.coderabbit.ai/getting-started/yaml-configuration
- CodeRabbit configuration reference: https://docs.coderabbit.ai/reference/configuration
- Qodo v2 code review overview: https://docs.qodo.ai/code-review
- Qodo `.pr_agent.toml` configuration: https://docs.qodo.ai/install-and-configure/configuration-overview/configuration-file
- Qodo configuration and command reference: https://docs.qodo.ai/install-and-configure/configuration-overview/configuration-and-command-reference
- GitHub issue forms syntax: https://docs.github.com/en/communities/using-templates-to-encourage-useful-issues-and-pull-requests/syntax-for-issue-forms
- GitHub PR template docs: https://docs.github.com/en/repositories/managing-your-repositorys-settings-and-features/customizing-your-repository/creating-a-pull-request-template-for-your-repository
