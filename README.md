# aigp-racer

Autonomous drone-racing research and implementation repo for the AI Grand Prix.

The working thesis is:

- win the runtime with a low-latency perception, estimation, planning, and CTBR-control stack;
- keep large models, LLMs, and world-model search out of the flight hot path;
- use WorldForge offline for replay, DecisionTrace evidence, regression tests, policy search, and AutoRaceEvolve-style optimization.

The first durable handoff is in [docs/issue-001-aigp-research-and-plan.md](docs/issue-001-aigp-research-and-plan.md).

