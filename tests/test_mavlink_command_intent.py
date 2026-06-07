from __future__ import annotations

import json
from pathlib import Path

import pytest

from mavlink.command_intent import (
    CommandIntentError,
    build_position_target_body_velocity_intent,
)
from scripts.aigp_command_intent_gate import build_evidence, write_evidence_json
from solver.commands import CommandKind, ControlCommand


def test_body_velocity_command_maps_to_official_message_intent() -> None:
    intent = build_position_target_body_velocity_intent(
        ControlCommand(
            sim_time_ns=120,
            kind=CommandKind.BODY_VELOCITY,
            source_frame_id=9,
            forward_m_s=1.25,
            right_m_s=-0.25,
            down_m_s=0.1,
            yaw_rate_rad_s=0.05,
            reason="tracking visible gate",
        )
    )

    assert intent.message_name == "SET_POSITION_TARGET_LOCAL_NED"
    assert intent.frame == "MAV_FRAME_BODY_NED"
    assert intent.mode == "TRACK_GATE"
    assert intent.velocity_body_ned_m_s == (1.25, -0.25, 0.1)
    assert intent.yaw_rate_rad_s == 0.05
    assert intent.source_frame_id == 9
    assert intent.ignored_setpoint_groups == ("position", "acceleration", "yaw_angle")


def test_hold_command_zeroes_velocity_and_yaw_rate() -> None:
    intent = build_position_target_body_velocity_intent(
        ControlCommand(
            sim_time_ns=121,
            kind=CommandKind.HOLD,
            forward_m_s=5.0,
            right_m_s=5.0,
            down_m_s=5.0,
            yaw_rate_rad_s=5.0,
            reason="stale telemetry",
        )
    )

    assert intent.mode == "HOLD"
    assert intent.velocity_body_ned_m_s == (0.0, 0.0, 0.0)
    assert intent.yaw_rate_rad_s == 0.0
    assert intent.reason == "stale telemetry"


def test_reacquire_command_preserves_conservative_yaw_intent() -> None:
    intent = build_position_target_body_velocity_intent(
        ControlCommand(
            sim_time_ns=122,
            kind=CommandKind.REACQUIRE,
            source_frame_id=10,
            yaw_rate_rad_s=0.2,
            reason="no gate observation",
        )
    )

    assert intent.mode == "REACQUIRE"
    assert intent.velocity_body_ned_m_s == (0.0, 0.0, 0.0)
    assert intent.yaw_rate_rad_s == 0.2
    assert intent.source_command_kind == "REACQUIRE"


@pytest.mark.parametrize(
    ("field_name", "value"),
    [
        ("forward_m_s", float("nan")),
        ("right_m_s", float("inf")),
        ("down_m_s", float("-inf")),
        ("yaw_rate_rad_s", float("nan")),
    ],
)
def test_command_intent_rejects_non_finite_control_fields(
    field_name: str,
    value: float,
) -> None:
    kwargs = {
        "sim_time_ns": 123,
        "kind": CommandKind.BODY_VELOCITY,
        "forward_m_s": 0.0,
        "right_m_s": 0.0,
        "down_m_s": 0.0,
        "yaw_rate_rad_s": 0.0,
    }
    kwargs[field_name] = value

    with pytest.raises(CommandIntentError, match=field_name):
        build_position_target_body_velocity_intent(ControlCommand(**kwargs))


@pytest.mark.parametrize(
    ("field_name", "value"),
    [
        ("forward_m_s", True),
        ("right_m_s", False),
        ("down_m_s", True),
        ("yaw_rate_rad_s", True),
    ],
)
def test_command_intent_rejects_bool_control_fields(
    field_name: str,
    value: bool,
) -> None:
    kwargs = {
        "sim_time_ns": 123,
        "kind": CommandKind.BODY_VELOCITY,
        "forward_m_s": 0.0,
        "right_m_s": 0.0,
        "down_m_s": 0.0,
        "yaw_rate_rad_s": 0.0,
    }
    kwargs[field_name] = value

    with pytest.raises(CommandIntentError, match=field_name):
        build_position_target_body_velocity_intent(ControlCommand(**kwargs))


@pytest.mark.parametrize("sim_time_ns", [-1, True])
def test_command_intent_rejects_invalid_timestamps(sim_time_ns: int) -> None:
    with pytest.raises(CommandIntentError, match="sim_time_ns"):
        build_position_target_body_velocity_intent(
            ControlCommand(sim_time_ns=sim_time_ns, kind=CommandKind.HOLD)
        )


def test_command_intent_rejects_bool_source_frame_id() -> None:
    with pytest.raises(CommandIntentError, match="source_frame_id"):
        build_position_target_body_velocity_intent(
            ControlCommand(
                sim_time_ns=124,
                kind=CommandKind.HOLD,
                source_frame_id=True,
            )
        )


def test_command_intent_evidence_uses_fixed_float_strings() -> None:
    evidence = build_evidence()
    first_intent = evidence["sample_intents"][0]

    assert evidence["schema_version"] == "aigp.command_intent_evidence.v1"
    assert evidence["mapping"]["float_format"] == "six_decimal_strings_for_evidence_only"
    assert first_intent["velocity_body_ned_m_s"] == ["1.250000", "-0.250000", "0.100000"]
    assert first_intent["yaw_rate_rad_s"] == "0.050000"


def test_command_intent_evidence_writer_formats_raw_floats(tmp_path: Path) -> None:
    evidence_path = tmp_path / "evidence.json"

    write_evidence_json(evidence_path, {"raw_float": 0.1})

    assert json.loads(evidence_path.read_text(encoding="utf-8")) == {"raw_float": "0.100000"}


def test_command_intent_as_dict_is_stable_and_json_shaped() -> None:
    intent = build_position_target_body_velocity_intent(
        ControlCommand(
            sim_time_ns=125,
            kind=CommandKind.BODY_VELOCITY,
            source_frame_id=11,
            forward_m_s=1.0,
            right_m_s=0.0,
            down_m_s=-0.1,
            reason="tracking visible gate",
        )
    )

    assert intent.as_dict() == {
        "schema_version": "aigp.command_intent.v0",
        "source_command_kind": "BODY_VELOCITY",
        "message_name": "SET_POSITION_TARGET_LOCAL_NED",
        "frame": "MAV_FRAME_BODY_NED",
        "intent_profile": "body_ned_velocity_plus_yaw_rate",
        "mode": "TRACK_GATE",
        "sim_time_ns": 125,
        "source_frame_id": 11,
        "velocity_body_ned_m_s": [1.0, 0.0, -0.1],
        "yaw_rate_rad_s": 0.0,
        "ignored_setpoint_groups": ["position", "acceleration", "yaw_angle"],
        "reason": "tracking visible gate",
        "claim_boundary": (
            "transport-independent command intent only; not binary MAVLink or MAVSDK evidence"
        ),
    }
