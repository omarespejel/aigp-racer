# JPEG Decode Benchmark

Issue: #17.

## Decision

Add a dependency-optional JPEG decode benchmark before choosing a runtime JPEG
decoder. The official vision stream is chunked JPEG, but this PR does not add a
mandatory runtime decoder dependency and does not decide the final decode path.

The benchmark supports optional decoder candidates:

- Pillow fallback decoder;
- OpenCV fallback decoder;
- PyTurboJPEG/libjpeg-turbo speed candidate.

The source sweep for issue #17 used:

- VADR-TS-002, Issue 00.02, dated 2026-05-08:
  https://www.theaigrandprix.com/wp-content/uploads/2026/05/260508_Technical_Spec_0002.pdf
- libjpeg-turbo documentation, page last modified 2026-03-26:
  https://libjpeg-turbo.org/Documentation/Documentation
- libjpeg-turbo official binaries:
  https://libjpeg-turbo.org/Documentation/OfficialBinaries
- PyTurboJPEG:
  https://pypi.org/project/PyTurboJPEG/
- Pillow stable docs:
  https://pillow.readthedocs.io/_/downloads/en/stable/pdf/
- opencv-python release listing:
  https://deps.dev/pypi/opencv-python/3.4.14.51/versions
- JPEG decoder benchmark:
  https://arxiv.org/abs/2501.13131
- 2026 JPEG decoder/data-loader benchmark:
  https://arxiv.org/abs/2605.08731

## Boundary

The benchmark accepts:

```text
JPEG fixture bytes + optional installed decoder candidates
```

It emits:

```text
decoder availability, dependency version, decoded shape, p50/p95/p99 latency,
fixture hash, local platform metadata, and non-claims
```

The checked-in fixture is synthetic:

```text
tests/fixtures/frame_640x360_synthetic.jpg
sha256 300317f992c7d4c90396af410c46832d58cc6efed480d229ffaff4b4239b9401
```

It is not an official simulator frame.

## Evidence

Measured artifact:

```text
docs/engineering/evidence/jpeg-decode-benchmark-2026-06-08.json
sha256 5df775b271b33d75ebf7ecf166a61f14c888647e88ed2a118bbfa6109e9aa0f3
```

Measured command:

```bash
uv run --python 3.14 --with 'pillow==12.2.0' python scripts/aigp_jpeg_decode_benchmark.py \
  --generate-synthetic-fixture \
  --fixture tests/fixtures/frame_640x360_synthetic.jpg \
  --decoders pillow,opencv,pyturbojpeg \
  --iterations 1000 \
  --warmup 25 \
  --write-json docs/engineering/evidence/jpeg-decode-benchmark-2026-06-08.json
```

Local measured result:

```text
platform: macOS-26.5.1-arm64-arm-64bit-Mach-O
python: 3.14.3
decoder: Pillow 12.2.0
fixture: 640 x 360 synthetic JPEG, 65050 bytes
p50: 0.637645 ms
p95: 0.725919 ms
p99: 0.806251 ms
opencv: missing dependency in this local run, source metadata recorded
pyturbojpeg: missing dependency in this local run, source metadata recorded
```

Interpretation:

- Pillow is viable as a simple fallback on this local Mac fixture.
- This does not prove the final Windows packaging path.
- This does not prove performance on official simulator frames.
- OpenCV and PyTurboJPEG remain candidates, but neither was installed in this
  local measurement environment.
- PyTurboJPEG/libjpeg-turbo remains the likely speed candidate to test once the
  Windows host/native library path is available.

## Validation

Code validation:

```bash
uv run --python 3.14 --with pytest \
  python -m pytest tests/test_jpeg_decode_benchmark.py tests/test_vision_reassembler.py
uv run --python 3.14 python scripts/aigp_jpeg_decode_benchmark.py \
  --check-json docs/engineering/evidence/jpeg-decode-benchmark-2026-06-08.json \
  --fixture tests/fixtures/frame_640x360_synthetic.jpg
./scripts/aigp_local_gate.sh
```

The timing values are measured evidence and are not regenerated in CI. The
checked-in artifact is validated by `--check-json` in `aigp_local_gate.sh` and
GitHub Actions for fixture hash, schema version, all-candidate coverage,
1,000-iteration requirement, fixed six-decimal strings, dependency metadata,
status separation, and required non-claims.

## GO Evidence

- `test_percentile_interpolates_sorted_values`
- `test_benchmark_config_rejects_invalid_values`
- `test_run_benchmark_records_latency_stats_with_injected_clock`
- `test_run_benchmark_uses_current_default_clock`
- `test_build_report_records_available_and_unavailable_candidates`
- `test_build_report_separates_benchmark_errors`
- `test_validate_report_accepts_checked_artifact_shape`
- `test_validate_report_rejects_unfixed_latency_strings`
- `test_write_json_sorts_keys`
- `test_parse_decoders_rejects_unknown_decoder`

## Non-Claims

- not a runtime dependency decision;
- not official simulator frame evidence;
- not detector latency evidence;
- not full vision-pipeline p99 evidence;
- not Windows packaging proof until run on the official Windows host.
