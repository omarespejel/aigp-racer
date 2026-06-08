from __future__ import annotations

import json
import zipfile
from pathlib import Path

import pytest

from scripts import aigp_official_package_probe as probe


def test_build_report_from_zip_extracts_official_template_observations(tmp_path: Path) -> None:
    source_zip = _write_fixture_package(tmp_path)

    report = probe.build_report_from_zip(source_zip)

    assert report["schema_version"] == probe.SCHEMA_VERSION
    assert report["source_zip"]["basename"] == "AI-GP Simulator v1.0.3364.zip"
    assert report["execution_status"]["current_outcome"] == "PARTIAL_GO_PACKAGE_PRESENT_RUN_BLOCKED"
    assert report["protocol_observations"]["vision_header_matches_reassembler"] is True
    assert report["protocol_observations"]["raw_actuator_command_path_detected"] is True
    assert report["template_dependencies"] == ["pymavlink", "opencv-python", "numpy"]


def test_validate_report_accepts_checked_evidence_shape(tmp_path: Path) -> None:
    report = probe.build_report_from_zip(_write_fixture_package(tmp_path))

    probe.validate_report(report)


def test_validate_report_rejects_missing_raw_actuator_observation(tmp_path: Path) -> None:
    report = probe.build_report_from_zip(_write_fixture_package(tmp_path))
    report["protocol_observations"]["raw_actuator_command_path_detected"] = False

    with pytest.raises(probe.OfficialPackageProbeError, match="raw_actuator"):
        probe.validate_report(report)


def test_validate_report_rejects_path_policy_drift(tmp_path: Path) -> None:
    report = probe.build_report_from_zip(_write_fixture_package(tmp_path))
    report["source_zip"]["path_policy"] = "/Users/example/Downloads/package.zip"

    with pytest.raises(probe.OfficialPackageProbeError, match="path policy"):
        probe.validate_report(report)


def test_checked_evidence_file_validates() -> None:
    evidence_path = (
        Path(__file__).resolve().parents[1]
        / "docs"
        / "engineering"
        / "evidence"
        / "official-sim-package-probe-2026-06-08.json"
    )
    probe.validate_report(json.loads(evidence_path.read_text(encoding="utf-8")))


def _write_fixture_package(tmp_path: Path) -> Path:
    py_example_zip = tmp_path / "PyAIPilotExample.zip"
    with zipfile.ZipFile(py_example_zip, "w") as archive:
        archive.writestr("controller.py", _controller_text())
        archive.writestr("main.py", "SIM_SERVER_UDP_PORT = 14550\n")
        archive.writestr("mavlink_rx.py", _mavlink_rx_text())
        archive.writestr("requirements.txt", "pymavlink\nopencv-python\nnumpy\n")
        archive.writestr("setup.py", "mavutil.mavlink_connection('udpin:%s:%s' % ('x', 1))\n")
        archive.writestr("timesync.py", "class TimeSync: pass\n")
        archive.writestr("vision_rx.py", 'SIM_SERVER_UDP_PORT = 5600\nheader_format = "<IHHIIQ"\n')

    source_zip = tmp_path / "AI-GP Simulator v1.0.3364.zip"
    with zipfile.ZipFile(source_zip, "w") as archive:
        archive.writestr("AIGP_3364.zip", b"windows-sim")
        archive.write(py_example_zip, "PyAIPilotExample.zip")
        archive.writestr(
            "README.md",
            "\n".join(
                [
                    "AI Grand Prix (AI-GP) Development Kit",
                    "AIGP_X.zip (The Simulator)",
                    "FlightSim.exe",
                    "official simulator account credentials",
                    "Python 3.14.2",
                    "64-bit Windows 10 / 11",
                ]
            ),
        )
    return source_zip


def _mavlink_rx_text() -> str:
    return "\n".join(
        [
            '"HEARTBEAT"',
            '"TIMESYNC"',
            '"ATTITUDE"',
            '"LOCAL_POSITION_NED"',
            '"ODOMETRY"',
            '"HIGHRES_IMU"',
            '"ENCAPSULATED_DATA"',
            '"ACTUATOR_OUTPUT_STATUS"',
            '"COLLISION"',
            '"DATA_TRANSMISSION_HANDSHAKE"',
            '"<BQqqIq"',
            '"<BH"',
            '"<Hfffffffff"',
        ]
    )


def _controller_text() -> str:
    return "\n".join(
        [
            "MAVLINK_CMD_SIM_RESET = 31000",
            "CONTROL_HZ = 250",
            "set_actuator_control_target_send()",
            "set_attitude_target_send()",
            "set_position_target_local_ned_send()",
            "update_motor_control(self.sim_conn, self.system_boot_ms)",
        ]
    )
