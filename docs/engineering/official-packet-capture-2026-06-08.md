# Official Packet Capture Scaffold

Issue: #35.

## Decision

Add a bounded UDP packet-capture scaffold before implementing binary MAVLink
runtime support. The goal is to produce the first official-simulator packet
fixtures without sending commands, decoding camera images, or depending on
`pymavlink`.

This is the next step after the official package probe: package evidence is
merged, the Windows simulator tree is extracted locally, and the remaining gap
is a live run on a Windows 10/11 host.

## Evidence

Deterministic fixture artifact:

```text
docs/engineering/evidence/official-packet-capture-fixture-2026-06-08.json
```

Fixture regeneration command:

```bash
uv run --python 3.14 --with jsonschema --with pyyaml --with ruff --with pytest \
  python scripts/aigp_official_packet_capture.py \
  --fixture \
  --write-json docs/engineering/evidence/official-packet-capture-fixture-2026-06-08.json \
  --check-json docs/engineering/evidence/official-packet-capture-fixture-2026-06-08.json
```

Windows-host live capture command, to run beside the official simulator before
any solver loop:

```bash
uv run --python 3.14 --with jsonschema --with pyyaml --with ruff --with pytest \
  python scripts/aigp_official_packet_capture.py \
  --live \
  --duration-s 15 \
  --max-datagrams-per-stream 64 \
  --max-total-bytes 10485760 \
  --write-json .local/official-packet-capture-live.json
```

The live output path is intentionally under `.local/` and ignored by git. After
review, promote only a small redacted or summarized fixture into
`docs/engineering/evidence/`.

## What The Scaffold Records

- Vision UDP stream on `0.0.0.0:5600`.
- MAVLink UDP stream on `127.0.0.1:14550`.
- Datagram size and SHA-256 prefix.
- Remote address and local bind.
- For vision packets: parsed `<IHHIIQ` header fields, including `frame_id`,
  `chunk_id`, `total_chunks`, `jpeg_size`, `payload_size`, and `sim_time_ns`.
- For MAVLink packets: MAVLink v1/v2 frame header fields only, including
  version, message id, sequence, system id, component id, payload length, and
  best-effort message-name mapping for known messages.

## What The Scaffold Does Not Record

- Raw JPEG bytes.
- Raw MAVLink payload bytes.
- Decoded images.
- Decoded binary MAVLink message fields.
- Commands sent to the simulator.
- Full race logs.

## GO / NO-GO

`GO`: the deterministic fixture passes no-drift checks, and a Windows-host live
run can capture bounded vision plus MAVLink summaries under `.local/`.

`NARROW_CLAIM`: this PR proves the capture scaffold and deterministic evidence
shape only. It does not prove official simulator runtime behavior until the
Windows-host live artifact is attached.

`NO-GO`: if the live capture needs raw video/log artifacts in git, unbounded
capture, host-specific evidence paths, or command emission.

## Non-Claims

- not a successful official simulator run;
- not decoded binary MAVLink support;
- not velocity availability evidence until a live run is attached;
- not valid-run, latency, reliability, lap-time, or controller evidence;
- not permission to use raw actuator control.
