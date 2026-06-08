# Official Simulator Package Probe

Issue: #4.

## Decision

Narrow issue #4 from "official package unavailable" to "official package is
present locally, but execution still requires Windows extraction, simulator
account login, and live packet capture."

The package is:

```text
AI-GP Simulator v1.0.3364.zip
sha256 a09f4e6669b099a28183178ecdeea627c2409723bd78bebf6e3867fadd26ba9b
size 1931484223 bytes
```

The probe now records the extracted nested simulator tree. It did not run
`FlightSim.exe`.

## Evidence

Generated artifact:

```text
docs/engineering/evidence/official-sim-package-probe-2026-06-08.json
```

Reproduction command on a machine that holds the local package and extracted
tree. `AIGP_OFFICIAL_ZIP` is host-specific and should point to the local
download path outside git:

```bash
export AIGP_OFFICIAL_ZIP="/path/to/AI-GP Simulator v1.0.3364.zip"

uv run --python 3.14 --with jsonschema --with pyyaml --with ruff --with pytest \
  python scripts/aigp_official_package_probe.py \
  --source-zip "$AIGP_OFFICIAL_ZIP" \
  --sim-tree .local/simulator-v1.0.3364/AIGP_3364 \
  --write-json docs/engineering/evidence/official-sim-package-probe-2026-06-08.json \
  --check-json docs/engineering/evidence/official-sim-package-probe-2026-06-08.json
```

Deterministic local-gate check:

```bash
uv run --python 3.14 --with jsonschema --with pyyaml --with ruff --with pytest \
  python scripts/aigp_official_package_probe.py \
  --check-json docs/engineering/evidence/official-sim-package-probe-2026-06-08.json
```

## What Changed

The official development kit includes:

- `AIGP_3364.zip`: Windows simulator archive.
- `PyAIPilotExample.zip`: official Python interface template.
- `README.md`: setup, login, and host requirements.

The extracted simulator tree records:

- `FlightSim.exe`: Windows launcher.
- `FlightSim/Binaries/Win64/DCGame-Win64-Shipping.exe`: Windows shipping binary.
- `FlightSim/Content/Paks/FlightSim-WindowsNoEditor.pak`: 4.36 GB content pack.
- `FlightSim/Binaries/pgos_res/pgos_config.ini`: PGOS network configuration.
- 64 files totaling 4,755,012,758 bytes.

The Python template confirms several practical details:

- MAVLink UDP target `127.0.0.1:14550`.
- Vision UDP listener `0.0.0.0:5600`.
- Vision packet format `<IHHIIQ`, matching the repo reassembler.
- Required template dependencies: `pymavlink`, `opencv-python`, `numpy`,
  `matplotlib`, `keyboard`.
- Additional messages handled by the sample: `LOCAL_POSITION_NED`, `ODOMETRY`,
  `ENCAPSULATED_DATA`, `ACTUATOR_OUTPUT_STATUS`, `COLLISION`, and
  `DATA_TRANSMISSION_HANDSHAKE`.
- Race status format `<BQqqIq`.
- Track packet header format `<BH`.
- Track gate format `<Hfffffffff`.
- Simulator reset command `31000`.
- Sample control paths for raw actuator, attitude, and position commands.

The raw actuator path is tracked separately in issue #33 because it needs a
legality, command-rate, and safety investigation before any command intent is
added.

## GO / NO-GO

`GO`: move to live simulator probing when the extracted tree is available on a
Windows host, `FlightSim.exe` launches, account login succeeds, and the repo
captures one JPEG sequence plus one decoded telemetry/race/track sample.

`NARROW_CLAIM`: package evidence is real, but no runtime behavior has been
observed yet.

`NO-GO`: if the Windows simulator cannot launch or if the sample protocol cannot
connect after login, open a focused simulator-integration hardening issue.

## Non-Claims

- not a successful official simulator run;
- not Windows execution evidence;
- not official account-login evidence;
- not velocity availability evidence;
- not raw actuator command approval;
- not latency, reliability, lap-time, or valid-run evidence.
