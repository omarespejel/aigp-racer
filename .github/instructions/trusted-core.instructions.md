# Trusted-Core Instructions

Apply these instructions to trusted-core paths:

- `solver/**`
- `mavlink/**`
- `vision/**`
- `perception/**`
- `estimation/**`
- `planning/**`
- `policies/**`
- `evolve/**`
- `worldforge_bridge/**`
- `scripts/**`
- `.github/workflows/**`
- `docs/engineering/**`
- `docs/security/**`

## Review Focus

- runtime correctness before speed;
- deterministic behavior before cleverness;
- timestamp and freshness checks;
- NED/body/camera frame correctness;
- command-rate compliance;
- safe recovery on lost gates or stale telemetry;
- offline-only WorldForge and DecisionTrace boundary;
- reproducible evidence before claims;
- disclosure ledger completeness.

## Do Not Suggest

- LLMs in the live control path;
- online learned world-model rollouts;
- public speed or reliability claims without evidence;
- broad refactors unrelated to the issue hypothesis;
- style-only churn that does not affect correctness, safety, or evidence quality.

