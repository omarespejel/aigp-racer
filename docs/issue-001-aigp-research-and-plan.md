# AI Grand Prix 2026 Strategy: Verified Research, Winning Stack, AutoRaceEvolve, And First 10 Hours

## Summary

This issue is the durable research and execution handoff for `aigp-racer`.

We looked at the AI Grand Prix 2026 competition, autonomous drone-racing SOTA, the official AI Grand Prix technical specification, the Elodin practice harness, Claude research notes, Codex verification, AGIBOT World Challenge alternatives, and the Go2 Air ControlBench dataset.

The conclusion:

- AI Grand Prix is still a serious and active AI robotics challenge.
- AGIBOT-next is probably the better long-term WorldForge-native challenge, but AGIBOT 2026 is already past its submission phase.
- This repo should focus on the AI Grand Prix runtime and first valid runs.
- WorldForge should stay offline as the evaluation, DecisionTrace, replay, regression, and AutoRaceEvolve lab.
- The live flight stack should be hard real-time, low-latency, and small: camera + telemetry, detector, estimator, planner, tiny CTBR controller, MAVLink commands.
- No LLM, VLM, giant video model, or learned world model belongs in the live control path.

## Repository Decision

This repository, `omarespejel/aigp-racer`, is for:

- AI Grand Prix simulator and official SDK integration.
- UDP JPEG vision stream handling.
- MAVLink telemetry and command smoke tests.
- Gate detection and PnP pose estimation.
- State estimation and gate-relative drift correction.
- Conservative valid-run baseline.
- Speed-phase learned CTBR controller.
- Offline AutoRaceEvolve optimization harness.
- WorldForge bridge for replay, DecisionTrace, and evaluation.

This repository is not for:

- AGIBOT challenge implementation.
- General-purpose WorldForge core changes.
- Publishing claims about AGIBOT, Go2, or DecisionTrace that are not backed by artifacts.
- Running LLM agents in the drone flight loop.

## Official AI Grand Prix Facts

Sources:

- AI Grand Prix site and FAQ: https://www.theaigrandprix.com/
- Official rules: https://www.theaigrandprix.com/official-rules/
- Technical specification PDF: https://www.theaigrandprix.com/wp-content/uploads/2026/05/260508_Technical_Spec_0002.pdf

Verified facts:

- The competition is founded by Anduril in partnership with Drone Champions League, Neros Technologies, and JobsOhio.
- It is a software/autonomy competition: no human pilots and no hardware modifications.
- Competitors use standardized Neros drones in the physical stages.
- Prize pool is listed as USD 500,000.
- Exact prize allocation beyond top-team rules is not fully finalized in the rules and must be rechecked before external claims.
- Teams can be individuals or teams up to 8.
- Virtual qualification runs May to July 2026 according to the current FAQ.
- Physical qualifier is planned for September 2026 in Southern California.
- Final is planned for November 2026 in Ohio.
- Top 10 at the Ohio final are guaranteed at least USD 5,000 according to the FAQ.
- Participants retain ownership of their algorithms and source code.
- Participants must disclose FLOSS and generative AI use.
- Human interaction during timed autonomous runs is disqualifying.
- Use of communications to pilot the physical drone is disqualifying.
- Physical-stage eligibility and citizenship/export restrictions must be checked early, especially for team composition.

## Official Virtual Qualifier Technical Spec

Source: VADR-TS-002, Issue 00.02, dated 2026-05-08.

Important values:

- Physics simulation rate: 120 Hz.
- Command rate: less than 100 Hz.
- Minimum heartbeat: 2 Hz.
- Camera: 30 Hz, 640 x 360.
- Camera model: pinhole, no lens distortion.
- Intrinsics: `cx=320`, `cy=180`, `fx=320`, `fy=320`.
- Vertical FoV: 90 degrees.
- Camera tilt: +20 degrees upward from body frame.
- Coordinate convention: NED.
- `MAV_FRAME_LOCAL_NED`: origin is the fixed physical ground point where the drone armed.
- `MAV_FRAME_BODY_NED`: X forward, Y right, Z down.
- Body to IMU transform: identity.
- GPS: not available.
- Absolute global position: not exposed.
- Gate outer dimensions: 2700 mm x 2700 mm x 260 mm.
- Gate inner opening: 1500 mm x 1500 mm x 260 mm.
- Drone chassis: 280 mm x 280 mm x 160 mm.
- MAVLink2 via MAVSDK over UDP.
- Supported simulator to client messages include `ATTITUDE`, `HIGHRES_IMU`, `TIMESYNC`.
- Supported client to simulator control messages include `SET_ATTITUDE_TARGET` and `SET_POSITION_TARGET_LOCAL_NED`.
- Vision stream uses UDP port 5600.
- Vision packets are chunked JPEG frames with little-endian 24-byte header:
  - `frame_id`
  - `chunk_id`
  - `total_chunks`
  - `jpeg_size`
  - `payload_size`
  - `sim_time_ns`
- Runtime: Python 3.14.2 is known to work.
- Other environments are allowed.
- Simulator runs on Windows 11 and a standard PC with about 8 GB VRAM.
- Linux simulator support is not currently provided.
- Round 1 environment is deterministic: same course geometry, same physics parameters, deterministic environmental conditions.
- Round 1 maximum run duration: 8 minutes.

Spec ambiguity to resolve on day one:

- Section 4.5 says telemetry includes linear velocities.
- The explicit message table lists `ATTITUDE` and `HIGHRES_IMU`.
- `HIGHRES_IMU` does not carry linear velocity.
- Therefore the first simulator probe must confirm whether clean velocity telemetry is actually exposed.

Why this matters:

- If velocity telemetry is available, the first estimator can be much lighter.
- If velocity telemetry is not available, we need IMU integration plus gate-relative pose corrections, closer to the A2RL hard-mode literature.

## Elodin Harness

Sources:

- Blog: https://www.elodin.systems/post/elodin-ai-grand-prix-race-sim-harness
- GitHub: https://github.com/elodin-sys/ai-grand-prix

Why it matters:

- It exists now and appears aligned with the AI Grand Prix virtual spec.
- It provides a practical starting environment before or alongside the official simulator.
- It models drone physics, motor dynamics, camera intrinsics, and racing gates.
- It includes Betaflight SITL and a solver/autopilot contract.
- It supports CSV and video export for regression analysis.

Constraint:

- Treat Elodin as a development harness, not the final authority.
- The official DCL simulator and official SDK are the competition contract.
- Do not use simulator-only state that will not be exposed in the official interface.

## Autonomous Drone Racing SOTA Sources

Primary papers and references to keep in scope:

- Swift, UZH, Nature 2023: https://www.nature.com/articles/s41586-023-06419-4
- AlphaPilot / UZH RPG, arXiv 2005.12813: https://arxiv.org/abs/2005.12813
- Autonomous Drone Racing survey, arXiv 2301.01755: https://arxiv.org/abs/2301.01755
- Time-Optimal Spatial ILC, arXiv 2306.15992: https://arxiv.org/abs/2306.15992
- MonoRace, TU Delft MAVLab, arXiv 2601.15222: https://arxiv.org/abs/2601.15222
- Drift-Corrected Monocular VIO and Perception-Aware Planning, arXiv 2512.20475: https://arxiv.org/abs/2512.20475
- ADR-VINS, arXiv 2603.02742: https://arxiv.org/abs/2603.02742
- Dream to Fly, arXiv 2501.14377: https://arxiv.org/abs/2501.14377
- SkyDreamer, arXiv 2510.14783: https://arxiv.org/abs/2510.14783

Resolved citation dispute:

- Claude's first deep-research pass flagged some arXiv IDs as likely fabricated because they were not found in that run.
- Direct verification showed those claims were wrong.
- `2603.02742` resolves to the KAIST tightly-coupled filter-based monocular VIO drone-racing paper.
- `2512.20475` resolves to the drift-corrected monocular VIO and perception-aware planning paper.
- `2501.14377` resolves to Dream to Fly.
- The AI Grand Prix technical spec PDF also directly verifies the latency and sensor numbers.

Lesson:

- Treat multi-agent search output as useful but not authoritative.
- For load-bearing claims, verify against primary sources or direct API/PDF reads.

## SOTA Interpretation

What actually wins:

- Not giant pixel-to-motor systems.
- Not LLMs in the loop.
- Not a large online world model.
- The strongest systems are hybrid:
  - learned gate/corner detection;
  - classical or filter-based state estimation;
  - gate-map drift correction;
  - time-optimal or perception-aware planning;
  - fast control, increasingly learned at the limit.

Important nuance:

- "End-to-end" needs to be split into two different meanings.
- Pixel-to-motor end-to-end is still too risky as the main competition path.
- State-to-control or state-to-motor learned control is proven useful.
- MonoRace used a small G&CNet policy that outputs motor commands at 500 Hz on embedded hardware.
- AI Grand Prix virtual qualifiers do not expose raw motor control at 500 Hz, so the transferable idea is not the raw motor interface. The transferable idea is a small learned policy.
- For AI Grand Prix, the learned policy should output body-rate plus thrust style commands through `SET_ATTITUDE_TARGET`, or a closely related control target, at about 80 to 95 Hz.

Key competition lesson:

- Reliability beats pure speed early.
- A valid finish is worth more than an aggressive policy that crashes.
- Human-vs-AI racing results and A2RL outcomes show that a gate strike or recovery failure can decide finals.

## Architecture Decision

Live runtime:

```text
UDP JPEG camera + MAVLink telemetry
    -> timestamp sync and packet assembly
    -> gate detector and corner uncertainty
    -> PnP / partial-corner pose update
    -> state estimator and gate-relative drift correction
    -> planner / speed schedule
    -> tiny CTBR policy or conservative controller
    -> MAVLink SET_ATTITUDE_TARGET or SET_POSITION_TARGET_LOCAL_NED
```

Rates:

- Vision: 30 Hz.
- Hot estimator/controller loop: 80 to 95 Hz target, under the official less-than-100-Hz command ceiling.
- Planner: 10 to 30 Hz.
- Offline optimizer: asynchronous only.

Design latency targets:

- Hot loop p99 <= 8 ms.
- Vision p99 <= 25 ms.

These are engineering targets, not official spec requirements.

Controller plan:

- Phase 1: conservative baseline using `SET_POSITION_TARGET_LOCAL_NED` or a simple geometric/PID controller to finish Round 1.
- Phase 2: CTBR policy through `SET_ATTITUDE_TARGET`.
- Phase 3: tiny PPO-trained MLP, likely 3x64 or 4x128.
- Phase 4: maintain safe, normal, and aggressive policies and switch based on confidence, drift, and recovery state.

Perception plan:

- Round 1: start with color/geometry/OpenCV detector because gates are highlighted and the environment is desaturated.
- Round 2 and physical stages: train a tiny corner heatmap or segmentation model.
- Output per-corner uncertainty, not just boxes.
- Use known intrinsics and gate dimensions for PnP.

Estimation plan:

- First probe velocity telemetry.
- If velocity exists, start with attitude + velocity + gate pose drift correction.
- If velocity does not exist, integrate IMU and correct using gate-relative observations.
- PnP when 4+ corners are visible.
- Use ADR-VINS style direct corner reprojection when only 2 or 3 corners are visible.
- Avoid spending weeks on generic OpenVINS/VINS-Mono as the core.

Planning plan:

- Generate a valid gate sequence first.
- Use known gate geometry for relative pose.
- Add a time-optimal line after reliable finish.
- Use Spatial ILC / line refinement for repeated deterministic runs.
- Keep speed schedule conservative until finish reliability is high.

World model plan:

- Do not run a world model in the flight path.
- Use the simulator as the world model for evaluation and training.
- If a learned world model is explored, keep it offline as a hypothesis to validate, not a load-bearing runtime dependency.

## WorldForge Role

WorldForge is the offline evidence engine:

- replay logs;
- emit DecisionTrace;
- compare candidate actions;
- calculate regret;
- track run-level metrics;
- regression-test failures;
- curate crash corpora;
- drive AutoRaceEvolve candidate evaluation;
- produce reproducible artifacts for every promoted policy.

WorldForge is not:

- the live pilot;
- an online predictive model in the hot loop;
- a replacement for low-latency controller engineering.

Suggested data contracts:

- `RaceEpisode`
- `TelemetrySample`
- `FramePacket`
- `GateObservation`
- `StateEstimate`
- `PlannerState`
- `CandidateAction`
- `PolicyDecision`
- `ControlCommand`
- `RaceOutcome`
- `DecisionTrace`
- `CandidateGenome`
- `EvalReport`

Key metrics:

- valid finish rate;
- lap time;
- missed gates;
- gate strikes;
- crash cause;
- detector confidence;
- estimator drift;
- command latency;
- vision latency;
- controller saturation;
- recovery success;
- policy aggression level;
- regression corpus pass/fail.

## AutoRaceEvolve

Sources:

- AlphaEvolve blog: https://deepmind.google/blog/alphaevolve-a-gemini-powered-coding-agent-for-designing-advanced-algorithms/
- FHE optimization paper, arXiv 2605.14718: https://arxiv.org/abs/2605.14718
- Eureka reward design, arXiv 2310.12931: https://arxiv.org/abs/2310.12931
- DrEureka sim-to-real, arXiv 2406.01967: https://arxiv.org/abs/2406.01967

Interpretation:

- The "autoresearch improving crypto" analogy is valid.
- AlphaEvolve-style loops improve code or algorithms by combining LLM-proposed candidates with automatic scoring and evolutionary selection.
- The FHE paper is a direct example in crypto-kernel latency.
- Drone racing has an unusually good automatic scorer: deterministic simulator runs.

AutoRaceEvolve tier ladder:

1. Parameter search.
   - Detector thresholds.
   - EKF noise parameters.
   - Controller gains.
   - Speed schedule.
   - Gate approach offsets.
   - Tools: Optuna, CMA-ES, Bayesian/TPE search.

2. Racing-line optimization.
   - Gate entry and exit points.
   - Curvature and speed constraints.
   - Spatial ILC style repeated-run improvements.

3. Reward and domain-randomization evolution.
   - Eureka and DrEureka style.
   - LLM proposes reward components or randomization ranges.
   - Simulator decides what survives.

4. Policy search.
   - PPO over tiny CTBR MLP policies.
   - Safe, normal, aggressive variants.
   - Promotion gated by reliability, not reward alone.

5. Code evolution.
   - AlphaEvolve-style planner/controller diffs.
   - Only after evaluator is frozen and trusted.
   - Must be sandboxed and fully disclosed under competition rules.

Promotion rules:

- Never optimize raw lap time alone.
- Require valid finish rate before speed gains count.
- Candidate must pass deterministic canaries.
- Candidate must pass randomized stress tests.
- Candidate must pass failure-regression corpus.
- Candidate must not violate latency budget.
- Candidate must not increase missed-gate or gate-strike risk beyond threshold.
- Final promotion is based on held-out evaluator, not evolved reward.

Guardrails:

- Frozen evaluator hash.
- Hidden holdout seeds.
- Artifact hashes for code, model, and config.
- Full logs for every promoted policy.
- Disclosure ledger update for LLM-generated code or model artifacts.

## AGIBOT And Go2 Context

Sources:

- AGIBOT 2026 challenge launch: https://www.agibot.com/article/231/detail/45.html
- AGIBOT ICRA 2026 competition listing: https://2026.ieee-icra.org/program/competitions/
- AGIBOT dataset: https://huggingface.co/datasets/agibot-world/AgiBotWorldChallenge-2026
- AGIBOT World Model baseline: https://github.com/AgibotTech/AgiBotWorldChallengeICRA2026-WorldModelBaseline
- Go2 Air ControlBench public preview: https://huggingface.co/datasets/espejelomar/go2-air-controlbench-v1

Decision:

- AGIBOT-next is probably the better strategic target for WorldForge as a world-model/planning/evaluation system.
- AI Grand Prix is still the better active high-signal challenge for immediate execution in this repo.
- AGIBOT 2026 submission deadlines are already past, so use AGIBOT as a study target and future-cycle preparation target.
- Do not mix AGIBOT implementation into `aigp-racer`.

AGIBOT dataset comparison:

- AGIBOT is much stronger as a training and competition dataset.
- It includes multi-task embodied manipulation, sim and real robot tracks, multi-camera and depth variants, Genie Sim linkage, EWMBench, and large video/model-training shards.
- AGIBOT WorldModel train split is roughly 38 GB, and individual Reasoning2Action video shards can be very large.
- It is the right substrate for foundation-model and embodied-world-model work.

Go2 dataset comparison:

- `go2-air-controlbench-v1` is not trying to compete with AGIBOT on scale.
- It is a compact, auditable command-to-outcome benchmark.
- It includes combined normalized trials, baseline reports, inverse-command regret, DecisionTrace examples, bounded ArUco evidence, figures, and audit notes.
- It is stronger as a proof of the WorldForge and DecisionTrace philosophy: predicted outcome, selected command, measured outcome, counterfactual candidates, and regret.

How to use both:

- Use AGIBOT as the future large upstream benchmark.
- Use the Go2 dataset as the small sharp prototype for auditable control evidence.
- Apply the Go2-style DecisionTrace layer to AI Grand Prix logs and eventually to AGIBOT episodes.

## Risks

Technical risks:

- Official simulator behavior may differ from Elodin.
- Velocity telemetry ambiguity could change estimator complexity.
- UDP frame reassembly can create silent vision bugs.
- Windows scheduling and async timing can make deterministic runs non-deterministic at the stack level.
- Trained controller may overfit Round 1.
- Reward evolution can produce fast but reckless policies.
- Compute budget may block Tier 2+ AutoRaceEvolve.

Competition risks:

- Registration or team changes may have deadlines.
- FLOSS and generative-AI disclosure must be complete.
- Physical qualifier eligibility and export restrictions may affect team composition.
- Prize and job-offer details are not a reason to make external claims without rechecking rules.

Product risks:

- Over-investing in WorldForge runtime ideas can distract from the low-latency controller.
- Over-investing in AI Grand Prix can distract from AGIBOT-next, which is a better WorldForge thesis fit.
- Public positioning must separate "we are building a racing solver" from "WorldForge is a general evidence/evaluation layer."

## First Milestone

The first milestone is not "state of the art."

The first milestone is:

```text
Official or Elodin simulator launches
    -> solver connects
    -> heartbeat stable
    -> JPEG frames reassembled
    -> telemetry parsed
    -> at least one gate detected
    -> PnP returns plausible relative pose
    -> controller sends valid commands
    -> drone completes a conservative valid run
    -> logs become a RaceEpisode
    -> WorldForge emits a DecisionTrace / EvalReport
```

Acceptance criteria:

- Repo has runnable smoke test for packet assembly.
- Repo has MAVLink smoke test or documented official-SDK blocker.
- Repo has camera/PnP sanity fixture.
- Repo has conservative baseline.
- Repo has logging schema.
- Repo has first `RaceEpisode` fixture.
- Repo has first issue-driven regression checklist.

## First 10 Hours Execution Plan

### Hour 0 to 1: repo and compliance foundation

- Create initial repo.
- Add `README.md`, `AGENTS.md`, `DISCLOSURE_LEDGER.md`, and this issue source.
- Create GitHub issue from this document.
- Confirm GitHub remote and default branch.
- Confirm whether registration/team setup is complete.
- Add placeholders for official SDK paths and Elodin harness path.

Deliverable:

- Issue opened.
- Repo pushed.
- Compliance ledger started.

### Hour 1 to 2: pull official and practice environments

- Download or clone Elodin harness.
- Locate official simulator/SDK download if available through AI Grand Prix login.
- Record exact SDK version, simulator version, and spec PDF version.
- Create a `docs/spec-notes.md` file with observed interface facts.
- Do not download massive unrelated assets yet.

Deliverable:

- Environment inventory.
- Exact blocker list if official simulator access requires login.

### Hour 2 to 3: vision UDP packet reassembler

- Implement UDP JPEG chunk reassembly against the official 24-byte header.
- Validate:
  - out-of-order chunks;
  - missing chunk;
  - duplicate chunk;
  - frame ID rollover if relevant;
  - payload size and JPEG size mismatch;
  - `sim_time_ns` timestamp preservation.
- Add unit tests with synthetic JPEG bytes.

Deliverable:

- `vision/reassembler.py`
- `tests/test_reassembler.py`
- p99 reassembly timing on synthetic frames.

### Hour 3 to 4: MAVLink and telemetry probe

- Implement minimal MAVLink client wrapper.
- Maintain heartbeat.
- Parse `ATTITUDE`, `HIGHRES_IMU`, and `TIMESYNC`.
- Try to detect whether linear velocity appears anywhere in the actual messages.
- Log raw message names and selected fields.
- Smoke test `SET_ATTITUDE_TARGET` and `SET_POSITION_TARGET_LOCAL_NED` if simulator is available.

Deliverable:

- `mavlink/client.py`
- `docs/day-one-telemetry-probe.md`
- clear answer: velocity yes/no/ambiguous.

### Hour 4 to 5: camera and PnP sanity

- Encode AI GP intrinsics:
  - resolution 640 x 360;
  - `fx=fy=320`;
  - `cx=320`, `cy=180`;
  - no distortion;
  - +20 degree camera tilt.
- Encode gate geometry:
  - inner square 1.5 m x 1.5 m;
  - outer square 2.7 m x 2.7 m;
  - depth 0.26 m.
- Create synthetic corner projection fixture.
- Recover pose with PnP.
- Validate coordinate-frame conversion from camera to body to NED.

Deliverable:

- `perception/pnp.py`
- `tests/test_pnp_geometry.py`
- one documented pose sanity result.

### Hour 5 to 6: Round 1 detector baseline

- Build a conservative OpenCV detector for highlighted/desaturated gates.
- Output:
  - candidate corners;
  - confidence;
  - image timestamp;
  - gate ID unknown/next candidate.
- Run against any available simulator frame or Elodin fixture.
- If no real frame exists, use synthetic/fixture image and keep blocker explicit.

Deliverable:

- `perception/gate_detector.py`
- first `GateObservation` schema.
- detector confidence contract.

### Hour 6 to 7: baseline estimator

- Implement minimal state estimate:
  - attitude from telemetry;
  - velocity if confirmed available;
  - otherwise IMU-integrated placeholder with clear error bounds;
  - gate-relative pose updates.
- Keep the estimator intentionally simple for first finish.
- Add timestamp sync between image and telemetry samples.

Deliverable:

- `estimation/state.py`
- `estimation/sync.py`
- `StateEstimate` dataclass/schema.

### Hour 7 to 8: conservative valid-run controller

- Implement safe control mode:
  - takeoff/arm readiness if simulator exposes it;
  - move toward visible gate center;
  - slow when detector confidence is low;
  - stop/hover/reacquire if gate lost;
  - never optimize speed yet.
- Prefer `SET_POSITION_TARGET_LOCAL_NED` for initial valid-run baseline if usable.
- Keep `SET_ATTITUDE_TARGET` interface ready for CTBR policy later.

Deliverable:

- `solver/baseline.py`
- first run command.
- controller state machine.

### Hour 8 to 9: RaceEpisode and WorldForge bridge

- Define minimal log schema:
  - telemetry samples;
  - frame metadata;
  - gate observations;
  - state estimates;
  - control commands;
  - outcome.
- Emit JSONL during a run.
- Convert one run or dry-run fixture into `RaceEpisode`.
- Emit a small `DecisionTrace` for one control decision.

Deliverable:

- `worldforge_bridge/schema.py`
- `runs/fixtures/first_episode.jsonl`
- `decision_traces/first_control_decision.json`

### Hour 9 to 10: regression and next planning gate

- Add smoke tests:
  - reassembler;
  - PnP;
  - telemetry parsing fixture;
  - baseline controller no-command-overrate check.
- Write `docs/next-24-hours.md`.
- Decide based on actual simulator access:
  - official sim available: chase first valid run;
  - official sim blocked: advance Elodin harness and unit fixtures;
  - velocity unavailable: prioritize estimator;
  - velocity available: prioritize detector/controller.

Deliverable:

- `pytest` or equivalent smoke result.
- first blocker list.
- next 24-hour work plan.

## Success Criteria For The First 10 Hours

Minimum success:

- Repo is live.
- GitHub issue exists.
- Spec notes and disclosure ledger exist.
- Packet reassembler design is started.
- PnP geometry is encoded.
- Official simulator access status is known.

Good success:

- UDP reassembler tests pass.
- PnP tests pass.
- MAVLink heartbeat works in a simulator or harness.
- Velocity telemetry ambiguity is resolved.
- Baseline controller can send commands.

Excellent success:

- Conservative baseline completes a simple gate course in Elodin or official sim.
- First RaceEpisode and DecisionTrace are emitted.
- We have a concrete path to first valid Round 1 finish.

## Open Questions

- Are we already registered and does the team have official simulator access?
- Is the official simulator downloadable now from the team login?
- Does telemetry actually include linear velocity?
- Does `SET_POSITION_TARGET_LOCAL_NED` behave well enough for a conservative first finish?
- Does the simulator enforce command-rate limits strictly?
- Can we run compiled extensions or ONNX/TensorRT in the final submission path?
- What are the exact submission packaging rules?
- What are the physical-stage eligibility constraints for every possible team member?

## Proposed Labels

- `research`
- `strategy`
- `architecture`
- `competition`
- `worldforge`
- `autoraceevolve`

## Final Decision

Proceed with AI Grand Prix implementation in this repo.

Keep AGIBOT-next as the better WorldForge-native strategic target, but do not let it block immediate AI Grand Prix progress.

The next concrete action is to spend 10 focused hours getting from repo seed to simulator interface probes and a conservative baseline path toward the first valid run.

