# Ten-Hour First-Runtime Bootstrap

Japan start time: `2026-06-08 02:06:04 JST`.

GitHub issue: https://github.com/omarespejel/aigp-racer/issues/2

## Scope

This block moves the repository from process-only bootstrap toward first-runtime
foundations:

- simulator and SDK access inventory;
- Elodin harness clone and interface inventory;
- official-spec UDP JPEG reassembler;
- MAVLink telemetry and velocity probe skeleton;
- camera intrinsics and gate geometry;
- Round 1 detector baseline;
- timestamp sync and minimal state estimation;
- conservative command-rate-guarded controller;
- RaceEpisode and DecisionTrace fixtures.

## Hour 0-1 Access Inventory

Public search found:

- Official site and FAQ: https://www.theaigrandprix.com/
- Official team portal: https://teams.theaigrandprix.com/login
- Official technical spec PDF: https://www.theaigrandprix.com/wp-content/uploads/2026/05/260508_Technical_Spec_0002.pdf
- Elodin harness: https://github.com/elodin-sys/ai-grand-prix

No public DCL simulator/SDK package URL was found through public search. Current
working assumption: official simulator access is team-portal-gated.

Non-claim: this does not prove the official simulator is unavailable to a
registered team.

## Elodin Harness Inventory

Cloned repository:

```text
external/elodin-ai-grand-prix
```

Elodin commit:

```text
13f9f9e3d5a3130f0ce0b65500d9f309cc1e11b2
```

Relevant findings:

- Elodin matches the AI Grand Prix camera assumptions: 640 x 360, `fx=fy=320`,
  `cx=320`, `cy=180`, +20 degree upward tilt, 30 Hz.
- Elodin includes a 3-gate practice course and Betaflight SITL.
- Elodin exposes an in-process solver API with raw RGBA frames.
- Elodin does **not** implement the official chunked JPEG vision UDP stream.
- Elodin does **not** implement the official MAVLink 2 interface.
- Elodin explicitly warns its solver boundary is ENU today, while AI Grand Prix
  MAVLink uses NED.

Decision:

- Use Elodin as a practice harness and fixture source.
- Do not depend on Elodin-only state or ENU solver semantics in the official
  runtime code.
- Build official-interface modules in this repo now: JPEG chunks, MAVLink-shaped
  telemetry, NED/body/camera geometry, and command-rate guards.

## Non-Claims

- No official simulator compatibility claim.
- No valid run claim.
- No speedup claim.
- No reliability claim.
- No physical-drone transfer claim.
- No learned-policy safety claim.

## Implemented Local Surfaces

- `vision.reassembler`: official-spec chunked JPEG reassembler.
- `mavlink.telemetry`: heartbeat, attitude, HIGHRES_IMU, TIMESYNC parsers and velocity probe.
- `perception.geometry`: AI GP intrinsics, gate dimensions, fronto-parallel PnP sanity fixture, camera ray to body NED.
- `perception.detector`: Round 1 high-contrast color detector baseline.
- `estimation.sync`: timestamp buffer and nearest-not-after alignment.
- `estimation.state`: minimal state estimator with explicit stale/no-gate/no-velocity states.
- `solver.baseline`: conservative controller and command intent.
- `solver.commands`: command-rate guard for less-than-100-Hz ceiling.
- `worldforge_bridge.schema`: offline RaceEpisode and DecisionTrace fixtures.

## Validation

Local gate:

```bash
./scripts/aigp_local_gate.sh
```

Current result:

```text
41 passed
```
