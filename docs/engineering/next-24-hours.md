# Next 24 Hours

Decision after the 10-hour bootstrap block:

> Continue toward official simulator access and first valid run if the team can provide portal access. If not, harden the fixture stack and wire it into Elodin practice runs without relying on Elodin-only state.

## Priority 1: Official Access

- Confirm AI Grand Prix registration/team status.
- Log into https://teams.theaigrandprix.com/login.
- Download official simulator/SDK if available.
- Record exact package/version and update `docs/engineering/spec-notes.md`.
- Run the telemetry velocity probe from `docs/engineering/day-one-telemetry-probe.md`.

## Priority 2: Official Interface Smoke

- Bind UDP port 5600.
- Receive and reassemble real chunked JPEG frames.
- Decode JPEG into RGB image.
- Log p50/p95/p99 frame assembly and decode timing.
- Parse MAVLink heartbeat, attitude, high-rate IMU, and timesync.
- Verify command-rate guard against the official simulator.

## Priority 3: Elodin Practice Harness

- Build Betaflight SITL if official simulator access remains blocked.
- Run Elodin baseline.
- Add an adapter from Elodin raw RGBA frames into the same perception/estimation/controller path.
- Keep the adapter marked practice-only because Elodin is not the official wire protocol.

## Priority 4: First Valid-Run Path

- Convert detector output to gate pose.
- Feed pose into `MinimalStateEstimator`.
- Feed estimate into `ConservativeController`.
- Emit RaceEpisode and DecisionTrace from an actual practice or official run.
- Do not optimize speed until the valid-run path is stable.

## Priority 5: Follow-Up Issues

- Resolve official simulator access blocker.
- Implement binary MAVLink socket client around the telemetry parser.
- Replace fronto-parallel sanity pose with full PnP when OpenCV or another solver is introduced.
- Add JPEG decode path once real frames or JPEG fixtures exist.

