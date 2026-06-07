# Start Here

Read this file before relying on memory or previous chat context.

## Required Read Order

1. `AGENTS.md`
2. `.codex/START_HERE.md`
3. `.codex/research/north_star.yml`
4. `.codex/research/operating_model.yml`
5. `.codex/research/README.md`
6. `.codex/HANDOFF.md`
7. `docs/engineering/reproducibility.md`
8. `docs/engineering/hardening-policy.md`
9. `docs/security/threat-model.md`
10. `AIGP_RACER_LAB.md`
11. The current active issue.
12. `git status --short --branch`

## Current Posture

This repo is in bootstrap mode. The first useful success is not a fast drone.

The first useful success is:

> We can connect to a simulator, identify and reproduce where autonomous racing failures occur, and review improvements through deterministic artifacts and bot-reviewed PR discipline.

## Hot-Path Boundary

The live flight path is:

```text
camera/telemetry -> detector/estimator/planner/controller -> MAVLink command
```

The offline lab is:

```text
logs -> RaceEpisode -> DecisionTrace/EvalReport -> AutoRaceEvolve candidate selection
```

Do not cross these paths without an issue and explicit architecture review.

