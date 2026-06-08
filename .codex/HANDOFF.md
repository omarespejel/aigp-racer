# Handoff

Last updated: 2026-06-08.

## Current State

- Repository initialized and pushed to `omarespejel/aigp-racer`.
- AI Grand Prix research summary captured in issue #1 and `docs/issue-001-aigp-research-and-plan.md`.
- Qodo and CodeRabbit review guardrails are configured.
- CI validates review configuration and Python smoke tests.
- Research-lab operating discipline is checked in: lanes, hypothesis issues, GO/NO-GO gates, no-claims, hardening policy, and local gates.
- First runtime fixtures are checked in for UDP JPEG reassembly, PnP sanity, estimator sync, conservative solver commands, RaceEpisode, and DecisionTrace.
- PR #7 merged issue #3. The decoded-message telemetry probe supports deterministic JSON fixtures and local UDP JSON smoke testing only; it does not decode official binary MAVLink 2 packets.
- Issue #4 is blocked on team-portal credentials or an official package link. Public and local search found no unauthenticated simulator/SDK package URL; evidence is recorded in https://github.com/omarespejel/aigp-racer/issues/4#issuecomment-4643872137.
- PR #8 merged issue #5. Full planar PnP is available only for physical-labeled, front-facing gate corners; detector bbox corners remain screen-space observations.
- PR #10 merged issue #9. Detector observations now bridge into estimator measurements through an explicit `GatePoseMeasurement` boundary without overclaiming full planar PnP from screen-space bbox corners.
- PR #20 merged issue #19. Conservative valid-run commands now gate tracking on confidence, range, status, and center offset.
- PR #25 merged issue #21. Integrated dry-run RaceEpisode and DecisionTrace evidence now exercises the detector -> estimator -> controller -> command-intent module chain without claiming simulator compatibility or latency.
- PR #26 merged issue #22. Simulator-time replay command gating is split from wall-clock send-layer gating.
- PR #27 merged issue #23. Screen-space gate depth conversion now carries an explicit inner-opening versus outer-frame measurement basis and preserves the first-frame calibration caveat.
- PR #29 merged issue #24. The minimal local camera-bytes-to-command-intent loop is measured; the Pillow plus pure-Python detector path is a local p99 NO-GO and was routed to issue #28.
- PR #30 merged issue #28. The OpenCV/NumPy compiled-vectorized path is a local fixture latency GO with a measured combined decode+detect p99 of 2.020049 ms, but it remains a non-claim for Windows packaging and official simulator compatibility.
- PR #32 merged issue #31. OpenCV/NumPy import/decode packaging evidence is local macOS only; Windows 11 simulator-host packaging remains open.
- Official simulator package `AI-GP Simulator v1.0.3364.zip` is now locally present outside git. Evidence is recorded in `docs/engineering/evidence/official-sim-package-probe-2026-06-08.json`.
- The official package probe confirms the outer archive contains `AIGP_3364.zip`, `PyAIPilotExample.zip`, and `README.md`; the nested simulator tree is extracted locally but the Windows executable has not been run.
- Extracted simulator tree facts: `FlightSim.exe`, `FlightSim/Binaries/Win64/DCGame-Win64-Shipping.exe`, `FlightSim/Content/Paks/FlightSim-WindowsNoEditor.pak`, 64 files, 4,755,012,758 bytes.
- The official Python template adds useful protocol evidence beyond the PDF: MAVLink UDP port 14550, vision UDP port 5600, `LOCAL_POSITION_NED`, `ODOMETRY`, `ACTUATOR_OUTPUT_STATUS`, `COLLISION`, race status, track-info chunks, reset command `31000`, and a sample raw actuator command path at `CONTROL_HZ = 250`.

## Active Objective

Add a packaging probe for the OpenCV/NumPy dependency pair so the compiled
vision path cannot silently become a runtime dependency before Windows 11
simulator-host evidence exists.

Immediate next code objectives:

1. Extract/run `AIGP_3364.zip` on a Windows 10/11 simulator host once enough disk and account access are ready.
2. Capture real official simulator packet examples: one JPEG frame sequence and one decoded telemetry/race/track sample.
3. Run the velocity telemetry probe against live `LOCAL_POSITION_NED` / `ODOMETRY` / `HIGHRES_IMU` traffic.
4. Calibrate Round 1 highlight basis from the first official simulator frame.
5. Investigate whether the sample raw actuator command path is legal/useful before adding any raw motor command intent.

## Current Known Unknowns

- Whether the local official simulator package can be extracted and launched on the Windows host.
- Whether official simulator account login is available.
- Whether telemetry actually exposes clean linear velocity.
- Whether `SET_POSITION_TARGET_LOCAL_NED` is sufficient for a conservative first valid run.
- Whether raw actuator control is legal, stable, and rate-compatible for the virtual qualifier.
- Whether final submission allows compiled inference or only pure Python.
- Whether physical-stage team eligibility imposes constraints on team composition.

## Merge Policy Reminder

For PR work, use:

```bash
./scripts/aigp_local_gate.sh
```

Then wait for Qodo/CodeRabbit/human quiet window before rebase merge.
