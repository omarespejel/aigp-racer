from __future__ import annotations

import pytest

from mavlink.telemetry import (
    HeartbeatMonitor,
    TelemetryError,
    TelemetryProbe,
    VelocityProbeStatus,
    extract_linear_velocity,
    parse_attitude,
    parse_heartbeat,
    parse_highres_imu,
    parse_timesync,
)


def test_parse_attitude_message() -> None:
    attitude = parse_attitude(
        {
            "mavpackettype": "ATTITUDE",
            "time_boot_ms": 12,
            "roll": 0.1,
            "pitch": -0.2,
            "yaw": 1.5,
            "rollspeed": 0.01,
            "pitchspeed": 0.02,
            "yawspeed": 0.03,
        }
    )

    assert attitude.time_boot_ms == 12
    assert attitude.pitch_rad == -0.2
    assert attitude.yawspeed_rad_s == 0.03


def test_parse_highres_imu_message() -> None:
    imu = parse_highres_imu(
        {
            "mavpackettype": "HIGHRES_IMU",
            "time_usec": 99,
            "xacc": 1.0,
            "yacc": 2.0,
            "zacc": -9.8,
            "xgyro": 0.1,
            "ygyro": 0.2,
            "zgyro": 0.3,
            "fields_updated": 7,
        }
    )

    assert imu.acceleration_m_s2 == (1.0, 2.0, -9.8)
    assert imu.gyro_rad_s == (0.1, 0.2, 0.3)
    assert imu.fields_updated == 7


def test_parse_heartbeat_and_timesync() -> None:
    heartbeat = parse_heartbeat({"mavpackettype": "HEARTBEAT", "system_status": 4})
    timesync = parse_timesync({"mavpackettype": "TIMESYNC", "tc1": 10, "ts1": 20})

    assert heartbeat.system_status == 4
    assert timesync.tc1 == 10
    assert timesync.ts1 == 20


def test_missing_required_field_raises() -> None:
    with pytest.raises(TelemetryError, match="roll"):
        parse_attitude({"mavpackettype": "ATTITUDE", "time_boot_ms": 1})


def test_heartbeat_monitor_requires_recent_heartbeat() -> None:
    monitor = HeartbeatMonitor(timeout_s=2.5)

    assert not monitor.is_fresh(10.0)
    monitor.observe(10.0)
    assert monitor.is_fresh(12.49)
    assert not monitor.is_fresh(12.51)


def test_velocity_probe_reports_not_available_for_spec_messages() -> None:
    probe = TelemetryProbe()
    probe.observe(
        {
            "mavpackettype": "HIGHRES_IMU",
            "time_usec": 1,
            "xacc": 0.0,
            "yacc": 0.0,
            "zacc": -9.8,
            "xgyro": 0.0,
            "ygyro": 0.0,
            "zgyro": 0.0,
        }
    )
    probe.observe({"mavpackettype": "ATTITUDE", "time_boot_ms": 1})

    report = probe.report()

    assert report.status == VelocityProbeStatus.NOT_AVAILABLE
    assert report.inspected_message_types == ("ATTITUDE", "HIGHRES_IMU")


def test_velocity_probe_reports_available_when_velocity_fields_exist() -> None:
    probe = TelemetryProbe()
    probe.observe({"mavpackettype": "LOCAL_POSITION_NED", "vx": 1.0, "vy": 2.0, "vz": 3.0})

    report = probe.report()

    assert report.status == VelocityProbeStatus.AVAILABLE
    assert report.candidates[0].velocity_m_s == (1.0, 2.0, 3.0)
    assert report.candidates[0].source_fields == ("vx", "vy", "vz")


def test_velocity_probe_reports_ambiguous_for_multiple_field_sets() -> None:
    probe = TelemetryProbe()
    probe.observe({"mavpackettype": "A", "vx": 1.0, "vy": 2.0, "vz": 3.0})
    probe.observe(
        {
            "mavpackettype": "B",
            "linear_velocity_x": 1.0,
            "linear_velocity_y": 2.0,
            "linear_velocity_z": 3.0,
        }
    )

    assert probe.report().status == VelocityProbeStatus.AMBIGUOUS


def test_velocity_probe_reports_ambiguous_for_same_fields_from_multiple_messages() -> None:
    probe = TelemetryProbe()
    probe.observe({"mavpackettype": "LOCAL_POSITION_NED", "vx": 1.0, "vy": 2.0, "vz": 3.0})
    probe.observe({"mavpackettype": "ODOMETRY", "vx": 1.0, "vy": 2.0, "vz": 3.0})

    report = probe.report()

    assert report.status == VelocityProbeStatus.AMBIGUOUS
    assert len(report.candidates) == 2


def test_extract_linear_velocity_supports_object_messages() -> None:
    class LocalPosition:
        vx = 1.0
        vy = 2.0
        vz = -0.5

        def get_type(self) -> str:
            return "LOCAL_POSITION_NED"

    velocity = extract_linear_velocity(LocalPosition())

    assert velocity is not None
    assert velocity.source_message == "LOCAL_POSITION_NED"
    assert velocity.velocity_m_s == (1.0, 2.0, -0.5)
