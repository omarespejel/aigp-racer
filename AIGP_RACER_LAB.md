# AI Grand Prix Racer Lab

`aigp-racer` is an experimental autonomy lab for studying AI Grand Prix drone racing.

The upstream competition interface remains the contract. Early work focuses on:

- official simulator and SDK compatibility;
- low-latency telemetry, camera, and command handling;
- conservative valid-run behavior;
- deterministic replay artifacts;
- failure attribution;
- offline AutoRaceEvolve search;
- WorldForge evidence and DecisionTrace conversion.

No speedup, reliability, physical-transfer, production-readiness, or competition-winning claim is made until matched local evidence exists.

## First Useful Success

The first useful success is not:

> We made the drone fast.

The first useful success is:

> We can identify, reproduce, and review where autonomous racing failures occur inside the simulator, with deterministic artifacts and bot-reviewed PR discipline.

## Initial Public Posture

Use this language:

> `aigp-racer` is an experimental AI Grand Prix autonomy lab. It keeps the live control path small and low-latency while using offline replay, DecisionTrace, and AutoRaceEvolve-style evaluation to improve reliability and speed only after evidence gates pass.

Do not use:

- "winning stack" as a claim about our implementation;
- "state of the art" without a claim issue;
- "sim-to-real" without physical evidence;
- "world model runtime" for the live solver.

