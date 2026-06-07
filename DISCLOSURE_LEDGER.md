# Disclosure Ledger

This file tracks competition-relevant disclosure material for AI Grand Prix work.

## Generative AI Use

- 2026-06-08: Initial strategy issue and repository scaffolding drafted with Codex using user-provided Claude research excerpts and independently verified public sources.
- 2026-06-08: Qodo and CodeRabbit configuration, review guidelines, CI validation harness, and setup notes drafted with Codex after checking current vendor documentation.

## FLOSS Dependencies

- Qodo Git integration configuration: `.pr_agent.toml`; service must be installed separately.
- CodeRabbit configuration: `.coderabbit.yaml`; service must be installed separately.
- Python dev-only validation dependencies:
  - `jsonschema`
  - `pytest`
  - `pyyaml`
  - `ruff`

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
