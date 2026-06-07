# Repository Instructions

- Keep the flight runtime small, deterministic, and low-latency.
- Do not put LLMs, large video models, or learned world-model rollouts in the live control path.
- Treat WorldForge as the offline replay, evaluation, DecisionTrace, and optimization lab.
- Preserve competition compliance evidence from day one: FLOSS dependencies, generated-AI usage, model weights, data sources, and license notes.
- Prefer reproducible artifacts over claims: every promoted controller or policy should have logs, metrics, hashes, and a regression result.
- Before changing architecture, update the relevant issue or handoff doc under `docs/`.

