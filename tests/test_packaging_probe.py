from __future__ import annotations

from pathlib import Path

import pytest

from scripts import aigp_packaging_probe as probe


def test_build_report_records_local_only_outcome(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fixture = tmp_path / "frame.jpg"
    fixture.write_bytes(b"jpeg")
    monkeypatch.setattr(probe, "_probe_package", _fake_package)
    monkeypatch.setattr(
        probe,
        "_decode_smoke",
        lambda _fixture_bytes, _packages: {
            "ok": True,
            "reason": None,
            "decoded_shape_hwc": [360, 640, 3],
            "expected_shape_hwc": [360, 640, 3],
        },
    )
    monkeypatch.setattr(
        probe,
        "_environment",
        lambda: {
            "python_version": "3.14.3",
            "platform": "macOS-test",
            "system": "Darwin",
            "release": "26.5.1",
            "machine": "arm64",
            "processor": "arm",
        },
    )
    evidence_path = tmp_path / "evidence.json"

    report = probe.build_report(fixture_path=fixture, evidence_path=evidence_path)

    assert report["schema_version"] == probe.SCHEMA_VERSION
    assert report["github_issue"] == probe.GITHUB_ISSUE
    assert report["host_is_windows_11"] is False
    assert report["local_smoke_ok"] is True
    assert report["outcome"] == "NARROW_CLAIM_LOCAL_ONLY"
    assert "not Windows packaging proof unless" in report["non_claims"][0]


def test_validate_report_accepts_checked_artifact_shape(tmp_path: Path) -> None:
    fixture = tmp_path / "frame.jpg"
    fixture.write_bytes(b"jpeg")
    evidence_path = tmp_path / "evidence.json"
    report = _valid_report(fixture, evidence_path)

    probe.validate_report(report, fixture_path=fixture, evidence_path=evidence_path)


def test_validate_report_rejects_reproduction_command_drift(tmp_path: Path) -> None:
    fixture = tmp_path / "frame.jpg"
    fixture.write_bytes(b"jpeg")
    evidence_path = tmp_path / "evidence.json"
    report = _valid_report(fixture, evidence_path)
    report["reproduction_command"] = "python wrong.py"

    with pytest.raises(probe.PackagingProbeError, match="reproduction_command"):
        probe.validate_report(report, fixture_path=fixture, evidence_path=evidence_path)


def test_validate_report_rejects_version_match_drift(tmp_path: Path) -> None:
    fixture = tmp_path / "frame.jpg"
    fixture.write_bytes(b"jpeg")
    evidence_path = tmp_path / "evidence.json"
    report = _valid_report(fixture, evidence_path)
    report["packages"][0]["version_matches"] = False

    with pytest.raises(probe.PackagingProbeError, match="version_matches"):
        probe.validate_report(report, fixture_path=fixture, evidence_path=evidence_path)


def test_validate_report_rejects_local_smoke_drift(tmp_path: Path) -> None:
    fixture = tmp_path / "frame.jpg"
    fixture.write_bytes(b"jpeg")
    evidence_path = tmp_path / "evidence.json"
    report = _valid_report(fixture, evidence_path)
    report["local_smoke_ok"] = False

    with pytest.raises(probe.PackagingProbeError, match="local_smoke_ok"):
        probe.validate_report(report, fixture_path=fixture, evidence_path=evidence_path)


def test_validate_report_rejects_outcome_drift(tmp_path: Path) -> None:
    fixture = tmp_path / "frame.jpg"
    fixture.write_bytes(b"jpeg")
    evidence_path = tmp_path / "evidence.json"
    report = _valid_report(fixture, evidence_path)
    report["outcome"] = "GO_WINDOWS"

    with pytest.raises(probe.PackagingProbeError, match="outcome"):
        probe.validate_report(report, fixture_path=fixture, evidence_path=evidence_path)


def test_decode_smoke_reports_missing_imports() -> None:
    packages = [
        {
            "package_name": "opencv-python",
            "import_ok": False,
        },
        {
            "package_name": "numpy",
            "import_ok": True,
        },
    ]

    result = probe._decode_smoke(b"jpeg", packages)

    assert result["ok"] is False
    assert result["decoded_shape_hwc"] is None
    assert result["reason"] == "required imports did not all succeed"


def test_expected_outcome() -> None:
    assert probe._expected_outcome(host_is_windows_11=True, local_smoke_ok=True) == "GO_WINDOWS"
    assert probe._expected_outcome(host_is_windows_11=True, local_smoke_ok=False) == "NO_GO_WINDOWS"
    assert (
        probe._expected_outcome(host_is_windows_11=False, local_smoke_ok=True)
        == "NARROW_CLAIM_LOCAL_ONLY"
    )
    assert probe._expected_outcome(host_is_windows_11=False, local_smoke_ok=False) == "NO_GO_LOCAL"


def _fake_package(expectation: probe.PackageExpectation) -> dict[str, object]:
    return {
        "package_name": expectation.package_name,
        "import_name": expectation.import_name,
        "expected_version": expectation.expected_version,
        "installed_version": expectation.expected_version,
        "version_matches": True,
        "import_ok": True,
        "import_error": None,
    }


def _valid_report(fixture: Path, evidence_path: Path) -> dict[str, object]:
    fixture_bytes = fixture.read_bytes()
    return {
        "schema_version": probe.SCHEMA_VERSION,
        "github_issue": probe.GITHUB_ISSUE,
        "claim_boundary": probe.CLAIM_BOUNDARY,
        "reproduction_command": probe._reproduction_command(
            fixture_path=fixture,
            evidence_path=evidence_path,
        ),
        "fixture": probe._fixture_metadata(fixture, fixture_bytes),
        "environment": {
            "python_version": "3.14.3",
            "platform": "macOS-test",
            "system": "Darwin",
            "release": "26.5.1",
            "machine": "arm64",
            "processor": "arm",
        },
        "target_environment": {
            "os": "Windows 11",
            "python": "3.14",
            "purpose": "AI Grand Prix official simulator host packaging check",
        },
        "packages": [_fake_package(package) for package in probe.PACKAGES],
        "decode_smoke": {
            "ok": True,
            "reason": None,
            "decoded_shape_hwc": [360, 640, 3],
            "expected_shape_hwc": [360, 640, 3],
        },
        "host_is_windows_11": False,
        "local_smoke_ok": True,
        "outcome": "NARROW_CLAIM_LOCAL_ONLY",
        "non_claims": list(probe.NON_CLAIMS),
    }
