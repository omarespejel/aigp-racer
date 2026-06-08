# OpenCV NumPy Packaging Probe

Date: 2026-06-08
Issue: #31

## Thesis

The compiled vision path from PR #30 depends on `opencv-python` and `numpy`.
Before that path can become a runtime dependency decision, the same package pair
must install, import, and decode the 640x360 JPEG fixture on the official
Windows 11 simulator host.

## Result

NARROW_CLAIM_LOCAL_ONLY.

The local macOS probe succeeded:

```text
opencv-python 4.13.0.92 import_ok: true version_matches: true
numpy 2.4.6 import_ok: true version_matches: true
cv2.imdecode fixture shape: [360, 640, 3]
local_smoke_ok: true
host_is_windows_11: false
outcome: NARROW_CLAIM_LOCAL_ONLY
```

This does not close issue #31. The GO gate requires the same probe on the
official Windows 11 simulator host.

## Evidence

Artifact:

```text
docs/engineering/evidence/opencv-numpy-packaging-probe-2026-06-08.json
```

Reproduction command:

```bash
uv run --python 3.14 --with opencv-python --with numpy \
  python scripts/aigp_packaging_probe.py \
  --fixture tests/fixtures/frame_640x360_synthetic.jpg \
  --write-json docs/engineering/evidence/opencv-numpy-packaging-probe-2026-06-08.json
```

Check command:

```bash
uv run --python 3.14 \
  python scripts/aigp_packaging_probe.py \
  --fixture tests/fixtures/frame_640x360_synthetic.jpg \
  --check-json docs/engineering/evidence/opencv-numpy-packaging-probe-2026-06-08.json
```

## GO Gate

Run the reproduction command on the official Windows 11 simulator host. The
result is a GO only if:

- `host_is_windows_11` is true.
- `local_smoke_ok` is true.
- `outcome` is `GO_WINDOWS`.
- `opencv-python` resolves to `4.13.0.92`.
- `numpy` resolves to `2.4.6`.
- `cv2.imdecode` returns `[360, 640, 3]` for the checked fixture.

## NO-GO Gate

Treat the package pair as not ready for the runtime path if:

- either package cannot install or import on Windows 11 Python 3.14;
- package versions drift without review;
- `cv2.imdecode` fails or returns the wrong shape;
- the official simulator host forbids this dependency path.

If that happens, evaluate `opencv-python-headless`, TurboJPEG, or a native
detector/decode path in a separate issue.

## Non-Claims

- Not Windows packaging proof.
- Not official simulator compatibility evidence.
- Not runtime dependency approval.
- Not latency evidence.
- Not valid-run evidence.

