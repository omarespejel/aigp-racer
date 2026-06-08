"""Probe OpenCV/NumPy packaging readiness for the compiled vision path."""

from __future__ import annotations

import argparse
import hashlib
import importlib
import importlib.metadata
import json
import platform
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

SCHEMA_VERSION = "aigp.packaging_probe.v0"
GITHUB_ISSUE = "https://github.com/omarespejel/aigp-racer/issues/31"
DEFAULT_FIXTURE = Path("tests/fixtures/frame_640x360_synthetic.jpg")
DEFAULT_EVIDENCE = Path("docs/engineering/evidence/opencv-numpy-packaging-probe-2026-06-08.json")
EXPECTED_OPENCV_VERSION = "4.13.0.92"
EXPECTED_NUMPY_VERSION = "2.4.6"
EXPECTED_SHAPE_HWC = (360, 640, 3)
CLAIM_BOUNDARY = (
    "packaging and import probe only; not latency evidence, not official simulator evidence, "
    "and not a runtime dependency decision until run on the Windows 11 simulator host"
)
NON_CLAIMS = (
    "not Windows packaging proof unless environment.host_is_windows_11 is true",
    "not official simulator compatibility evidence",
    "not runtime dependency approval",
    "not latency evidence",
    "not valid-run evidence",
)


class PackagingProbeError(ValueError):
    """Raised when packaging-probe evidence cannot run or validate."""


@dataclass(frozen=True)
class PackageExpectation:
    package_name: str
    import_name: str
    expected_version: str


PACKAGES = (
    PackageExpectation("opencv-python", "cv2", EXPECTED_OPENCV_VERSION),
    PackageExpectation("numpy", "numpy", EXPECTED_NUMPY_VERSION),
)


def build_report(
    *,
    fixture_path: Path,
    evidence_path: Path,
    reproduction_command: str | None = None,
) -> dict[str, Any]:
    fixture_bytes = fixture_path.read_bytes()
    package_results = [_probe_package(package) for package in PACKAGES]
    decode_smoke = _decode_smoke(fixture_bytes, package_results)
    environment = _environment()
    host_is_windows_11 = _host_is_windows_11(environment)
    local_smoke_ok = all(item["import_ok"] and item["version_matches"] for item in package_results)
    local_smoke_ok = local_smoke_ok and decode_smoke["ok"]
    if host_is_windows_11 and local_smoke_ok:
        outcome = "GO_WINDOWS"
    elif host_is_windows_11:
        outcome = "NO_GO_WINDOWS"
    elif local_smoke_ok:
        outcome = "NARROW_CLAIM_LOCAL_ONLY"
    else:
        outcome = "NO_GO_LOCAL"

    return {
        "schema_version": SCHEMA_VERSION,
        "github_issue": GITHUB_ISSUE,
        "claim_boundary": CLAIM_BOUNDARY,
        "reproduction_command": reproduction_command
        if reproduction_command is not None
        else _reproduction_command(fixture_path=fixture_path, evidence_path=evidence_path),
        "fixture": _fixture_metadata(fixture_path, fixture_bytes),
        "environment": environment,
        "target_environment": {
            "os": "Windows 11",
            "python": "3.14",
            "purpose": "AI Grand Prix official simulator host packaging check",
        },
        "packages": package_results,
        "decode_smoke": decode_smoke,
        "host_is_windows_11": host_is_windows_11,
        "local_smoke_ok": local_smoke_ok,
        "outcome": outcome,
        "non_claims": list(NON_CLAIMS),
    }


def validate_report(
    report: object,
    *,
    fixture_path: Path,
    evidence_path: Path,
) -> None:
    if not isinstance(report, dict):
        raise PackagingProbeError("report root must be an object")
    if report.get("schema_version") != SCHEMA_VERSION:
        raise PackagingProbeError("schema_version drifted")
    if report.get("github_issue") != GITHUB_ISSUE:
        raise PackagingProbeError("github_issue drifted")
    if report.get("claim_boundary") != CLAIM_BOUNDARY:
        raise PackagingProbeError("claim_boundary drifted")
    expected_command = _reproduction_command(fixture_path=fixture_path, evidence_path=evidence_path)
    if report.get("reproduction_command") != expected_command:
        raise PackagingProbeError("reproduction_command drifted")
    if report.get("non_claims") != list(NON_CLAIMS):
        raise PackagingProbeError("non_claims drifted")
    _validate_fixture(report.get("fixture"), fixture_path)
    _validate_environment(report.get("environment"))
    _validate_target_environment(report.get("target_environment"))
    packages = report.get("packages")
    if not isinstance(packages, list) or len(packages) != len(PACKAGES):
        raise PackagingProbeError("packages must list expected package probes")
    for value, expectation in zip(packages, PACKAGES, strict=True):
        _validate_package_result(value, expectation)
    decode_smoke = report.get("decode_smoke")
    _validate_decode_smoke(decode_smoke)
    host_is_windows_11 = report.get("host_is_windows_11")
    local_smoke_ok = report.get("local_smoke_ok")
    if type(host_is_windows_11) is not bool:
        raise PackagingProbeError("host_is_windows_11 must be a bool")
    if type(local_smoke_ok) is not bool:
        raise PackagingProbeError("local_smoke_ok must be a bool")
    expected_local_smoke = (
        all(item["import_ok"] and item["version_matches"] for item in packages)
        and decode_smoke["ok"]
    )
    if local_smoke_ok != expected_local_smoke:
        raise PackagingProbeError("local_smoke_ok does not match package and decode results")
    expected_outcome = _expected_outcome(
        host_is_windows_11=host_is_windows_11,
        local_smoke_ok=local_smoke_ok,
    )
    if report.get("outcome") != expected_outcome:
        raise PackagingProbeError("outcome drifted")


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _probe_package(expectation: PackageExpectation) -> dict[str, Any]:
    installed_version = _package_version(expectation.package_name)
    import_ok = False
    import_error = None
    try:
        importlib.import_module(expectation.import_name)
        import_ok = True
    except Exception as exc:  # pragma: no cover - exercised by integration environment.
        import_error = f"{type(exc).__name__}: {exc}"
    return {
        "package_name": expectation.package_name,
        "import_name": expectation.import_name,
        "expected_version": expectation.expected_version,
        "installed_version": installed_version,
        "version_matches": installed_version == expectation.expected_version,
        "import_ok": import_ok,
        "import_error": import_error,
    }


def _decode_smoke(fixture_bytes: bytes, packages: list[dict[str, Any]]) -> dict[str, Any]:
    package_map = {item["package_name"]: item for item in packages}
    if not package_map["opencv-python"]["import_ok"] or not package_map["numpy"]["import_ok"]:
        return {
            "ok": False,
            "reason": "required imports did not all succeed",
            "decoded_shape_hwc": None,
            "expected_shape_hwc": list(EXPECTED_SHAPE_HWC),
        }
    try:
        cv2 = importlib.import_module("cv2")
        np = importlib.import_module("numpy")
        array = np.frombuffer(fixture_bytes, dtype=np.uint8)
        image = cv2.imdecode(array, cv2.IMREAD_COLOR)
        if image is None:
            return {
                "ok": False,
                "reason": "cv2.imdecode returned None",
                "decoded_shape_hwc": None,
                "expected_shape_hwc": list(EXPECTED_SHAPE_HWC),
            }
        decoded_shape = tuple(int(value) for value in image.shape)
        return {
            "ok": decoded_shape == EXPECTED_SHAPE_HWC,
            "reason": None if decoded_shape == EXPECTED_SHAPE_HWC else "decoded shape drifted",
            "decoded_shape_hwc": list(decoded_shape),
            "expected_shape_hwc": list(EXPECTED_SHAPE_HWC),
        }
    except Exception as exc:  # pragma: no cover - exercised by integration environment.
        return {
            "ok": False,
            "reason": f"{type(exc).__name__}: {exc}",
            "decoded_shape_hwc": None,
            "expected_shape_hwc": list(EXPECTED_SHAPE_HWC),
        }


def _fixture_metadata(path: Path, data: bytes) -> dict[str, Any]:
    return {
        "path": path.as_posix(),
        "size_bytes": len(data),
        "sha256": hashlib.sha256(data).hexdigest(),
    }


def _environment() -> dict[str, str]:
    return {
        "python_version": sys.version.split()[0],
        "platform": platform.platform(),
        "system": platform.system(),
        "release": platform.release(),
        "machine": platform.machine(),
        "processor": platform.processor(),
    }


def _host_is_windows_11(environment: dict[str, str]) -> bool:
    return environment["system"] == "Windows" and environment["release"].startswith("11")


def _expected_outcome(*, host_is_windows_11: bool, local_smoke_ok: bool) -> str:
    if host_is_windows_11 and local_smoke_ok:
        return "GO_WINDOWS"
    if host_is_windows_11:
        return "NO_GO_WINDOWS"
    if local_smoke_ok:
        return "NARROW_CLAIM_LOCAL_ONLY"
    return "NO_GO_LOCAL"


def _package_version(package_name: str) -> str | None:
    try:
        return importlib.metadata.version(package_name)
    except importlib.metadata.PackageNotFoundError:
        return None


def _validate_fixture(value: object, fixture_path: Path) -> None:
    if not isinstance(value, dict):
        raise PackagingProbeError("fixture must be an object")
    fixture_bytes = fixture_path.read_bytes()
    if value.get("path") != fixture_path.as_posix():
        raise PackagingProbeError("fixture path drifted")
    if type(value.get("size_bytes")) is not int or value["size_bytes"] != len(fixture_bytes):
        raise PackagingProbeError("fixture size drifted")
    if value.get("sha256") != hashlib.sha256(fixture_bytes).hexdigest():
        raise PackagingProbeError("fixture sha256 drifted")


def _validate_environment(value: object) -> None:
    if not isinstance(value, dict):
        raise PackagingProbeError("environment must be an object")
    for key in ("python_version", "platform", "system", "release", "machine", "processor"):
        if not isinstance(value.get(key), str):
            raise PackagingProbeError(f"environment.{key} must be a string")


def _validate_target_environment(value: object) -> None:
    if not isinstance(value, dict):
        raise PackagingProbeError("target_environment must be an object")
    if value.get("os") != "Windows 11":
        raise PackagingProbeError("target_environment.os drifted")
    if value.get("python") != "3.14":
        raise PackagingProbeError("target_environment.python drifted")


def _validate_package_result(value: object, expectation: PackageExpectation) -> None:
    if not isinstance(value, dict):
        raise PackagingProbeError("package result must be an object")
    for key in ("package_name", "import_name", "expected_version"):
        if value.get(key) != getattr(expectation, key):
            raise PackagingProbeError(f"package {expectation.package_name} {key} drifted")
    installed_version = value.get("installed_version")
    if installed_version is not None and not isinstance(installed_version, str):
        raise PackagingProbeError("installed_version must be null or string")
    for key in ("version_matches", "import_ok"):
        if type(value.get(key)) is not bool:
            raise PackagingProbeError(f"{expectation.package_name}.{key} must be a bool")
    if value["version_matches"] != (installed_version == expectation.expected_version):
        raise PackagingProbeError(f"{expectation.package_name}.version_matches drifted")
    import_error = value.get("import_error")
    if import_error is not None and not isinstance(import_error, str):
        raise PackagingProbeError("import_error must be null or string")


def _validate_decode_smoke(value: object) -> None:
    if not isinstance(value, dict):
        raise PackagingProbeError("decode_smoke must be an object")
    if type(value.get("ok")) is not bool:
        raise PackagingProbeError("decode_smoke.ok must be a bool")
    if value.get("expected_shape_hwc") != list(EXPECTED_SHAPE_HWC):
        raise PackagingProbeError("decode_smoke expected shape drifted")
    decoded_shape = value.get("decoded_shape_hwc")
    if decoded_shape is not None and decoded_shape != list(EXPECTED_SHAPE_HWC):
        if value["ok"]:
            raise PackagingProbeError("decode_smoke ok cannot be true for wrong shape")
    if value["ok"] and decoded_shape != list(EXPECTED_SHAPE_HWC):
        raise PackagingProbeError("decode_smoke ok drifted")
    reason = value.get("reason")
    if reason is not None and not isinstance(reason, str):
        raise PackagingProbeError("decode_smoke.reason must be null or string")


def _reproduction_command(*, fixture_path: Path, evidence_path: Path) -> str:
    return (
        "uv run --python 3.14 --with opencv-python --with numpy "
        "python scripts/aigp_packaging_probe.py "
        f"--fixture {fixture_path.as_posix()} --write-json {evidence_path.as_posix()}"
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--fixture", type=Path, default=DEFAULT_FIXTURE)
    parser.add_argument("--write-json", type=Path)
    parser.add_argument("--check-json", type=Path)
    args = parser.parse_args()
    if args.write_json is None and args.check_json is None:
        parser.error("one of --write-json or --check-json is required")
    if args.write_json is not None:
        report = build_report(fixture_path=args.fixture, evidence_path=args.write_json)
        write_json(args.write_json, report)
    if args.check_json is not None:
        report = json.loads(args.check_json.read_text(encoding="utf-8"))
        validate_report(report, fixture_path=args.fixture, evidence_path=args.check_json)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
