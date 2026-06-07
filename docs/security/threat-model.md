# Threat Model

This is a research repository, but it still handles artifacts and code that can affect competition behavior.

## Assets

- competition solver code;
- simulator interface assumptions;
- model and policy weights;
- run logs and RaceEpisode artifacts;
- DecisionTrace and EvalReport artifacts;
- AutoRaceEvolve evaluator settings;
- hidden holdout seeds;
- disclosure and license records;
- private raw videos or robot logs if introduced later.

## Trust Boundaries

- Official AI Grand Prix simulator and SDK are external dependencies.
- Elodin harness is a practice harness, not the competition contract.
- WorldForge is offline infrastructure.
- Qodo and CodeRabbit are advisory reviewers, not authorities.
- Generated-AI code must be disclosed and reviewed like other code.

## Main Risks

- A live runtime accidentally depends on simulator-only state.
- A policy overfits deterministic canaries and is promoted as reliable.
- A stale or malformed UDP frame is treated as fresh perception.
- MAVLink commands exceed rate limits or use wrong frames.
- Generated evidence drifts silently.
- AutoRaceEvolve mutates code or rewards to exploit the evaluator.
- A public claim exceeds the actual evidence.
- A raw log or video with sensitive information is committed.

## Mitigations

- Keep hot-path and offline paths separate.
- Use local gates and targeted tests.
- Record exact commands and artifacts.
- Use hidden holdout seeds for promotion decisions.
- Update `DISCLOSURE_LEDGER.md`.
- Keep large/raw artifacts out of git unless deliberately reviewed.
- Use Qodo and CodeRabbit as adversarial reviewers.

