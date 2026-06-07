# Simulator Access Probe

Issue: #4.

## Decision

Keep official simulator access as a hardening blocker, but continue advancing
practice-only work through deterministic fixtures and the Elodin harness.

The current state is:

- public unauthenticated search has not found an official simulator or SDK
  package URL;
- team-portal credentials are still required before we can record an official
  package version or run official telemetry;
- repo fixtures already cover the official UDP vision header, decoded-message
  telemetry probe shape, conservative command intent, and offline RaceEpisode /
  DecisionTrace schemas;
- Elodin is useful now as a practice harness, but it is not the official wire
  protocol.

## Source Refresh

Primary sources checked:

- AI Grand Prix Technical Specification VADR-TS-002, Issue 00.02:
  https://www.theaigrandprix.com/wp-content/uploads/2026/05/260508_Technical_Spec_0002.pdf
- AI Grand Prix public site:
  https://www.theaigrandprix.com/
- Elodin AI Grand Prix harness announcement:
  https://www.elodin.systems/post/elodin-ai-grand-prix-race-sim-harness
- Elodin practice harness repo:
  https://github.com/elodin-sys/ai-grand-prix

Important refreshed facts:

- official vision stream is UDP chunked JPEG on port 5600, 30 Hz, 640 x 360,
  with a 24-byte little-endian header;
- official MAVLink side is MAVLink 2 over UDP, with a command rate below 100 Hz
  and minimum heartbeat rate of 2 Hz;
- official telemetry velocity availability remains ambiguous until the official
  simulator is probed;
- Elodin uses raw RGBA frames, ENU practice state, and a Betaflight FDM/RC/PWM
  bridge, so it needs an explicit practice adapter.

## Evidence

Generated artifact:

```text
docs/engineering/evidence/sim-access-probe-2026-06-08.json
sha256 fa764428a3534a58bb0fd3f648605cb0836d54310ccaee1fcdb044d504460e90
```

Command:

```bash
uv run --python 3.14 --with jsonschema --with pyyaml --with ruff --with pytest \
  python scripts/aigp_sim_access_probe.py \
  --write-json docs/engineering/evidence/sim-access-probe-2026-06-08.json
```

## Next Gate

`GO`: team portal yields official simulator or SDK package; record version and
run the day-one telemetry probe.

`NARROW_CLAIM`: no credentials or no package yet; continue with Elodin
practice-only adapter work and official-spec fixtures.

`NO_GO`: official package exists but telemetry or vision cannot be decoded after
heartbeat; open a focused MAVLink or vision hardening issue.

## Non-Claims

- not official simulator access evidence;
- not official SDK compatibility evidence;
- not a successful simulator run;
- not binary MAVLink decoding evidence;
- not a velocity availability claim;
- not an Elodin fidelity claim;
- not a speed, reliability, or latency claim.
