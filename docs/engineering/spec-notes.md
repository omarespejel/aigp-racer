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
