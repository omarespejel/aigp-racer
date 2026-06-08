# AI Grand Prix Spec Notes

Last checked: 2026-06-08.

Primary source:

- AI Grand Prix Technical Specification VADR-TS-002, Issue 00.02, dated 2026-05-08.
- URL: https://www.theaigrandprix.com/wp-content/uploads/2026/05/260508_Technical_Spec_0002.pdf

## Pinned Interface Facts

- Physics rate: 120 Hz.
- Command rate: less than 100 Hz.
- Minimum heartbeat: 2 Hz.
- Camera: 30 Hz, 640 x 360.
- Camera model: pinhole, no distortion.
- Intrinsics: `fx=320`, `fy=320`, `cx=320`, `cy=180`.
- Camera tilt: +20 degrees upward.
- Vision stream: UDP port 5600, chunked JPEG.
- Vision header: 24 bytes, little-endian.
- Vision fields:
  - `frame_id`: uint32
  - `chunk_id`: uint16
  - `total_chunks`: uint16
  - `jpeg_size`: uint32
  - `payload_size`: uint32
  - `sim_time_ns`: uint64
- MAVLink: MAVLink 2 through MAVSDK-compatible UDP interface.
- Expected simulator-to-client messages:
  - `HEARTBEAT`
  - `ATTITUDE`
  - `HIGHRES_IMU`
  - `TIMESYNC`
- Expected client-to-simulator messages:
  - `SET_ATTITUDE_TARGET`
  - `SET_POSITION_TARGET_LOCAL_NED`
- Coordinate frame: NED for MAVLink-side local/body frames.
- No GPS/global absolute position is exposed.
- Gate inner opening: 1.5 m x 1.5 m.
- Gate outer frame: 2.7 m x 2.7 m.
- Gate depth: 0.26 m.
- Official simulator host OS: Windows 11.
- Python 3.14.2 is known-good per spec.
- Implementation guardrail, not a spec claim: the current UDP JPEG reassembler
  rejects frames above 256 chunks or 2 MiB declared JPEG size to bound per-frame
  memory and CPU exposure.

## Official Development Kit v1.0.3364

User-provided local package:

```text
AI-GP Simulator v1.0.3364.zip
sha256 a09f4e6669b099a28183178ecdeea627c2409723bd78bebf6e3867fadd26ba9b
size 1931484223 bytes
```

Checked-in evidence:

```text
docs/engineering/evidence/official-sim-package-probe-2026-06-08.json
```

The package probe inspected the outer zip manifest, the small official
`PyAIPilotExample.zip` template, and the locally extracted Windows simulator
tree. It did not run the simulator.

Observed package contents:

- `AIGP_3364.zip`: nested Windows simulator archive.
- `PyAIPilotExample.zip`: official Python interface template.
- `README.md`: development-kit setup and host requirements.

Observed extracted simulator tree:

- `FlightSim.exe`: Windows launcher.
- `FlightSim/Binaries/Win64/DCGame-Win64-Shipping.exe`: Windows shipping binary.
- `FlightSim/Content/Paks/FlightSim-WindowsNoEditor.pak`: 4.36 GB content pack.
- 64 files totaling 4,755,012,758 bytes.

Observed from the official Python template:

- MAVLink UDP target: `127.0.0.1:14550`.
- Vision listener: UDP `0.0.0.0:5600`.
- Vision header format: `<IHHIIQ`, matching `vision.reassembler`.
- Dependencies: `pymavlink`, `opencv-python`, `numpy`, `matplotlib`, `keyboard`.
- Additional simulator-to-client messages handled by the sample:
  `LOCAL_POSITION_NED`, `ODOMETRY`, `ENCAPSULATED_DATA`,
  `ACTUATOR_OUTPUT_STATUS`, `COLLISION`, and
  `DATA_TRANSMISSION_HANDSHAKE`.
- Encapsulated race-status payload format: `<BQqqIq`.
- Encapsulated track-packet header format: `<BH`.
- Track gate payload format: `<Hfffffffff`.
- Simulator reset command: `MAVLINK_CMD_SIM_RESET = 31000`.
- Sample controller exposes `SET_ACTUATOR_CONTROL_TARGET`,
  `SET_ATTITUDE_TARGET`, and `SET_POSITION_TARGET_LOCAL_NED` send paths.
- Sample `Controller.update()` defaults to raw actuator control at
  `CONTROL_HZ = 250`.

Raw actuator control is an observed official-template path, not a default repo
decision. It is tracked in issue #33 and needs a focused legality, rate, and
safety gate before use.

## Official Packet Capture Scaffold

Checked-in deterministic fixture:

```text
docs/engineering/evidence/official-packet-capture-fixture-2026-06-08.json
```

The scaffold in `scripts/aigp_official_packet_capture.py` can be run on the
Windows simulator host before any solver loop. It binds the observed official
ports and records bounded packet summaries only:

- vision UDP `0.0.0.0:5600`, parsed as the `<IHHIIQ` chunked JPEG header;
- MAVLink UDP `127.0.0.1:14550`, parsed only as MAVLink v1/v2 frame headers.

Sources for these packet-capture facts are the primary spec URL at the top of
this file plus the checked official-template evidence in
`docs/engineering/evidence/official-sim-package-probe-2026-06-08.json`.

It deliberately does not record raw JPEG bytes, raw MAVLink payload bytes, send
commands, decode images, or claim binary MAVLink message support. Live capture
output should stay under ignored `.local/` storage until reviewed and reduced
to a small evidence fixture.

## Current Ambiguity

The spec text says telemetry includes linear velocities, but the explicit
message table lists `ATTITUDE` and `HIGHRES_IMU`. `HIGHRES_IMU` does not carry
linear velocity.

Current repo behavior:

- `mavlink.telemetry.TelemetryProbe` reports `NOT_AVAILABLE` for ATTITUDE +
  HIGHRES_IMU-only streams.
- If an additional message exposes `vx/vy/vz` or related linear velocity fields,
  the probe reports `AVAILABLE` or `AMBIGUOUS`.

This must be tested against the official simulator.

The official Python template increases the chance that velocity is available:
it handles `LOCAL_POSITION_NED` and `ODOMETRY`, both with `vx/vy/vz` fields in
the sample. This is still not live evidence until captured from the simulator.

## Elodin Practice Harness

Source:

- https://github.com/elodin-sys/ai-grand-prix

Pinned clone:

```text
13f9f9e3d5a3130f0ce0b65500d9f309cc1e11b2
```

Elodin is useful for practice, but it is not the official simulator contract:

- raw RGBA frames instead of official chunked JPEG UDP;
- in-process solver callback instead of MAVLink 2;
- ENU solver state instead of official NED MAVLink boundary;
- Betaflight RC/FDM/PWM bridge instead of official stabilized-controller messages.
