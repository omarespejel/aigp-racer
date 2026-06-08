"""Probe the user-provided official AI-GP simulator package without extracting it."""

from __future__ import annotations

import argparse
import hashlib
import io
import json
import zipfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any

SCHEMA_VERSION = "aigp.official_package_probe.v0"
GITHUB_ISSUE = "https://github.com/omarespejel/aigp-racer/issues/4"
DEFAULT_EVIDENCE = Path("docs/engineering/evidence/official-sim-package-probe-2026-06-08.json")
EXPECTED_OUTER_FILES = ("AIGP_3364.zip", "PyAIPilotExample.zip", "README.md")
EXPECTED_EXAMPLE_FILES = (
    "controller.py",
    "main.py",
    "mavlink_rx.py",
    "requirements.txt",
    "setup.py",
    "timesync.py",
    "vision_rx.py",
)
CLAIM_BOUNDARY = (
    "local package-manifest and official-template source inspection only; not a simulator run, "
    "not official login evidence, and not Windows-host execution evidence"
)
NON_CLAIMS = (
    "not a successful official simulator run",
    "not Windows execution evidence",
    "not official account-login evidence",
    "not velocity availability evidence",
    "not raw actuator command approval",
    "not latency, reliability, lap-time, or valid-run evidence",
)


class OfficialPackageProbeError(ValueError):
    """Raised when official-package evidence is missing or malformed."""


@dataclass(frozen=True)
class SourceFile:
    name: str
    text: str


def build_report_from_zip(source_zip: Path, *, sim_tree: Path | None = None) -> dict[str, Any]:
    source_bytes = source_zip.read_bytes()
    with zipfile.ZipFile(io.BytesIO(source_bytes)) as outer_zip:
        outer_entries = [_zip_entry_info(info) for info in outer_zip.infolist()]
        readme_text = outer_zip.read("README.md").decode("utf-8")
        py_example_bytes = outer_zip.read("PyAIPilotExample.zip")

    with zipfile.ZipFile(io.BytesIO(py_example_bytes)) as py_example_zip:
        py_example_entries = [_zip_entry_info(info) for info in py_example_zip.infolist()]
        source_files = {
            name: SourceFile(name=name, text=py_example_zip.read(name).decode("utf-8"))
            for name in EXPECTED_EXAMPLE_FILES
        }
    sim_tree_report = (
        _sim_tree_report(sim_tree) if sim_tree is not None else _sim_tree_not_inspected()
    )
    tree_extracted = bool(sim_tree_report["present"])

    return {
        "schema_version": SCHEMA_VERSION,
        "snapshot_date": "2026-06-08",
        "github_issue": GITHUB_ISSUE,
        "claim_boundary": CLAIM_BOUNDARY,
        "source_zip": {
            "basename": source_zip.name,
            "size_bytes": len(source_bytes),
            "sha256": hashlib.sha256(source_bytes).hexdigest(),
            "path_policy": "local user-provided package path is intentionally not recorded",
        },
        "outer_archive_entries": outer_entries,
        "py_ai_pilot_example_entries": py_example_entries,
        "readme_facts": _readme_facts(readme_text),
        "template_dependencies": _requirements(source_files["requirements.txt"].text),
        "protocol_observations": _protocol_observations(source_files),
        "simulator_tree": sim_tree_report,
        "execution_status": {
            "official_package_present_locally": True,
            "nested_windows_simulator_archive_present": True,
            "nested_windows_simulator_extracted_by_probe": tree_extracted,
            "flight_sim_executable_run_by_probe": False,
            "simulator_account_login_verified": False,
            "current_outcome": _current_outcome(tree_extracted=tree_extracted),
            "blocked_by": _blocked_by(tree_extracted=tree_extracted),
        },
        "next_actions": [
            {
                "priority": 1,
                "action": "copy or expose the extracted AIGP_3364 tree to a Windows 10/11 host",
                "gate": "FlightSim.exe launches and reaches login without modifying repo state",
            },
            {
                "priority": 2,
                "action": "run the day-one telemetry probe against live pymavlink messages",
                "gate": "velocity probe resolves AVAILABLE, NOT_AVAILABLE, or AMBIGUOUS",
            },
            {
                "priority": 3,
                "action": (
                    "capture one official JPEG datagram sequence and one decoded telemetry sample"
                ),
                "gate": "fixtures decode through repo parsers without simulator-only shortcuts",
            },
            {
                "priority": 4,
                "action": "decide whether raw actuator control is legal and useful",
                "gate": (
                    "official docs or live simulator behavior supports a bounded command intent"
                ),
            },
        ],
        "non_claims": list(NON_CLAIMS),
    }


def validate_report(report: object) -> None:
    if not isinstance(report, dict):
        raise OfficialPackageProbeError("report root must be an object")
    _expect(report.get("schema_version") == SCHEMA_VERSION, "schema_version drifted")
    _expect(report.get("github_issue") == GITHUB_ISSUE, "github_issue drifted")
    _expect(report.get("claim_boundary") == CLAIM_BOUNDARY, "claim_boundary drifted")
    _expect(report.get("non_claims") == list(NON_CLAIMS), "non_claims drifted")
    source_zip = report.get("source_zip")
    _expect(isinstance(source_zip, dict), "source_zip must be an object")
    _expect(
        source_zip.get("basename") == "AI-GP Simulator v1.0.3364.zip",
        "source basename drifted",
    )
    _expect(
        isinstance(source_zip.get("sha256"), str) and len(source_zip["sha256"]) == 64,
        "source sha256 must be recorded",
    )
    _expect(
        source_zip.get("path_policy")
        == "local user-provided package path is intentionally not recorded",
        "source path policy drifted",
    )
    _validate_zip_entries(
        report.get("outer_archive_entries"),
        EXPECTED_OUTER_FILES,
        "outer archive",
    )
    _validate_zip_entries(
        report.get("py_ai_pilot_example_entries"),
        EXPECTED_EXAMPLE_FILES,
        "PyAIPilotExample",
    )
    protocol = report.get("protocol_observations")
    _expect(isinstance(protocol, dict), "protocol_observations must be an object")
    required_true_flags = (
        "main_uses_mavlink_udp_14550",
        "setup_uses_pymavlink_udpin",
        "vision_uses_udp_5600",
        "vision_header_matches_reassembler",
        "race_status_format_detected",
        "track_packet_header_format_detected",
        "track_gate_format_detected",
        "raw_actuator_command_path_detected",
        "attitude_command_path_detected",
        "position_command_path_detected",
        "sim_reset_command_detected",
    )
    for flag in required_true_flags:
        _expect(protocol.get(flag) is True, f"{flag} must be true")
    execution_status = report.get("execution_status")
    _expect(isinstance(execution_status, dict), "execution_status must be an object")
    _validate_simulator_tree(report.get("simulator_tree"))
    tree_extracted = bool(report["simulator_tree"]["present"])
    _expect(
        execution_status.get("current_outcome") == _current_outcome(tree_extracted=tree_extracted),
        "execution outcome drifted",
    )
    _expect(
        execution_status.get("nested_windows_simulator_extracted_by_probe") is tree_extracted,
        "tree extraction flag drifted",
    )
    _expect(
        execution_status.get("flight_sim_executable_run_by_probe") is False,
        "probe must not claim FlightSim execution",
    )


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _zip_entry_info(info: zipfile.ZipInfo) -> dict[str, Any]:
    return {
        "filename": info.filename,
        "file_size": info.file_size,
        "compress_size": info.compress_size,
        "crc32_hex": f"{info.CRC:08x}",
        "date_time": _date_time(info.date_time),
    }


def _date_time(value: tuple[int, int, int, int, int, int]) -> str:
    year, month, day, hour, minute, second = value
    return f"{year:04d}-{month:02d}-{day:02d}T{hour:02d}:{minute:02d}:{second:02d}"


def _readme_facts(readme_text: str) -> dict[str, Any]:
    return {
        "development_kit_name_detected": "AI Grand Prix (AI-GP) Development Kit" in readme_text,
        "windows_simulator_archive_described": "AIGP_X.zip (The Simulator)" in readme_text,
        "flight_sim_executable_described": "FlightSim.exe" in readme_text,
        "account_login_required": "official simulator account credentials" in readme_text,
        "python_3142_template_described": "Python 3.14.2" in readme_text,
        "windows_10_11_requirement_described": "64-bit Windows 10 / 11" in readme_text,
        "storage_requirement_gb": 12,
    }


def _requirements(requirements_text: str) -> list[str]:
    return [
        line.strip()
        for line in requirements_text.splitlines()
        if line.strip() and not line.strip().startswith("#")
    ]


def _protocol_observations(source_files: dict[str, SourceFile]) -> dict[str, Any]:
    main = source_files["main.py"].text
    setup = source_files["setup.py"].text
    vision_rx = source_files["vision_rx.py"].text
    mavlink_rx = source_files["mavlink_rx.py"].text
    controller = source_files["controller.py"].text
    return {
        "main_uses_mavlink_udp_14550": "SIM_SERVER_UDP_PORT = 14550" in main,
        "setup_uses_pymavlink_udpin": "mavutil.mavlink_connection('udpin:%s:%s'" in setup,
        "vision_uses_udp_5600": "SIM_SERVER_UDP_PORT = 5600" in vision_rx,
        "vision_header_format": "<IHHIIQ" if 'header_format = "<IHHIIQ"' in vision_rx else None,
        "vision_header_matches_reassembler": 'header_format = "<IHHIIQ"' in vision_rx,
        "race_status_format_detected": '"<BQqqIq"' in mavlink_rx,
        "track_packet_header_format_detected": '"<BH"' in mavlink_rx,
        "track_gate_format_detected": '"<Hfffffffff"' in mavlink_rx,
        "handled_mavlink_messages": [
            message
            for message in (
                "HEARTBEAT",
                "TIMESYNC",
                "ATTITUDE",
                "LOCAL_POSITION_NED",
                "ODOMETRY",
                "HIGHRES_IMU",
                "ENCAPSULATED_DATA",
                "ACTUATOR_OUTPUT_STATUS",
                "COLLISION",
                "DATA_TRANSMISSION_HANDSHAKE",
            )
            if message in mavlink_rx
        ],
        "raw_actuator_command_path_detected": "set_actuator_control_target_send" in controller,
        "attitude_command_path_detected": "set_attitude_target_send" in controller,
        "position_command_path_detected": "set_position_target_local_ned_send" in controller,
        "sim_reset_command_detected": "MAVLINK_CMD_SIM_RESET = 31000" in controller,
        "sample_control_hz": 250 if "CONTROL_HZ = 250" in controller else None,
        "sample_default_update_uses_motor_control": (
            "update_motor_control(self.sim_conn" in controller
        ),
    }


def _sim_tree_not_inspected() -> dict[str, Any]:
    return {
        "present": False,
        "path_policy": "local extracted simulator path is intentionally not recorded",
        "file_count": 0,
        "total_file_size_bytes": 0,
        "entrypoints": [],
        "content_pak": None,
        "pgos_config": None,
        "manifest_files": [],
    }


def _sim_tree_report(sim_tree: Path) -> dict[str, Any]:
    if not sim_tree.is_dir():
        raise OfficialPackageProbeError("sim_tree must be an extracted simulator directory")
    files = sorted(path for path in sim_tree.rglob("*") if path.is_file())
    rel_files = {path.relative_to(sim_tree).as_posix(): path for path in files}
    entrypoint_names = (
        "FlightSim.exe",
        "FlightSim/Binaries/Win64/DCGame-Win64-Shipping.exe",
    )
    entrypoints = []
    for name in entrypoint_names:
        path = rel_files.get(name)
        entrypoints.append(
            {
                "path": name,
                "present": path is not None,
                "size_bytes": path.stat().st_size if path is not None else None,
                "platform": "windows-pe-x86-64",
            }
        )
    pak_path = rel_files.get("FlightSim/Content/Paks/FlightSim-WindowsNoEditor.pak")
    pgos_path = rel_files.get("FlightSim/Binaries/pgos_res/pgos_config.ini")
    return {
        "present": True,
        "path_policy": "local extracted simulator path is intentionally not recorded",
        "file_count": len(files),
        "total_file_size_bytes": sum(path.stat().st_size for path in files),
        "entrypoints": entrypoints,
        "content_pak": {
            "path": "FlightSim/Content/Paks/FlightSim-WindowsNoEditor.pak",
            "present": pak_path is not None,
            "size_bytes": pak_path.stat().st_size if pak_path is not None else None,
        },
        "pgos_config": _pgos_config(pgos_path),
        "manifest_files": [
            name
            for name in ("Manifest_DebugFiles_Win64.txt", "Manifest_NonUFSFiles_Win64.txt")
            if name in rel_files
        ],
    }


def _pgos_config(path: Path | None) -> dict[str, Any] | None:
    if path is None:
        return None
    values = {}
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        if "=" not in line:
            continue
        key, value = line.split("=", 1)
        values[key.strip()] = value.strip()
    return {
        "path": "FlightSim/Binaries/pgos_res/pgos_config.ini",
        "title_id_empty": values.get("title_id", "") == "",
        "socket_base_url": values.get("socket_base_url"),
        "http_base_url": values.get("http_base_url"),
    }


def _current_outcome(*, tree_extracted: bool) -> str:
    if tree_extracted:
        return "PARTIAL_GO_PACKAGE_AND_TREE_PRESENT_RUN_BLOCKED"
    return "PARTIAL_GO_PACKAGE_PRESENT_RUN_BLOCKED"


def _blocked_by(*, tree_extracted: bool) -> list[str]:
    blockers = []
    if not tree_extracted:
        blockers.append(
            "full Windows simulator extraction deferred until enough disk headroom exists"
        )
    blockers.extend(
        [
            "FlightSim.exe requires a Windows 10/11 host",
            "virtual qualifier requires official simulator account credentials",
        ]
    )
    return blockers


def _validate_simulator_tree(value: object) -> None:
    _expect(isinstance(value, dict), "simulator_tree must be an object")
    present = value.get("present")
    _expect(type(present) is bool, "simulator_tree.present must be bool")
    _expect(
        value.get("path_policy") == "local extracted simulator path is intentionally not recorded",
        "simulator_tree path policy drifted",
    )
    _expect(isinstance(value.get("file_count"), int), "simulator_tree.file_count must be int")
    _expect(
        isinstance(value.get("total_file_size_bytes"), int),
        "simulator_tree.total_file_size_bytes must be int",
    )
    if not present:
        _expect(value.get("entrypoints") == [], "absent simulator_tree must not list entrypoints")
        return
    entrypoints = value.get("entrypoints")
    _expect(isinstance(entrypoints, list) and len(entrypoints) == 2, "entrypoints drifted")
    _expect(all(item.get("present") is True for item in entrypoints), "entrypoints must exist")
    content_pak = value.get("content_pak")
    _expect(isinstance(content_pak, dict), "content_pak must be an object")
    _expect(content_pak.get("present") is True, "content_pak must exist")
    pgos_config = value.get("pgos_config")
    _expect(isinstance(pgos_config, dict), "pgos_config must be an object")
    _expect(
        pgos_config.get("path") == "FlightSim/Binaries/pgos_res/pgos_config.ini",
        "pgos_config path drifted",
    )


def _validate_zip_entries(value: object, expected_names: tuple[str, ...], label: str) -> None:
    _expect(isinstance(value, list), f"{label} entries must be a list")
    names = tuple(item.get("filename") for item in value if isinstance(item, dict))
    _expect(names == expected_names, f"{label} entries drifted")
    for item in value:
        _expect(isinstance(item, dict), f"{label} entry must be an object")
        _expect(isinstance(item.get("file_size"), int), f"{label} file_size must be int")
        _expect(isinstance(item.get("compress_size"), int), f"{label} compress_size must be int")
        _expect(isinstance(item.get("crc32_hex"), str), f"{label} crc32_hex must be string")
        _expect(isinstance(item.get("date_time"), str), f"{label} date_time must be string")


def _expect(condition: bool, message: str) -> None:
    if not condition:
        raise OfficialPackageProbeError(message)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-zip", type=Path)
    parser.add_argument("--sim-tree", type=Path)
    parser.add_argument("--write-json", type=Path)
    parser.add_argument("--check-json", type=Path)
    args = parser.parse_args()

    if args.write_json is not None:
        if args.source_zip is None:
            parser.error("--write-json requires --source-zip")
        write_json(args.write_json, build_report_from_zip(args.source_zip, sim_tree=args.sim_tree))

    if args.check_json is not None:
        validate_report(json.loads(args.check_json.read_text(encoding="utf-8")))

    if args.write_json is None and args.check_json is None:
        parser.error("provide --write-json or --check-json")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
