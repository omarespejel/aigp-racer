"""Minimal RaceEpisode and DecisionTrace schemas for offline evidence."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class EpisodeEvent:
    event_type: str
    sim_time_ns: int
    payload: dict[str, Any]
    source_frame_id: int | None = None


@dataclass(frozen=True)
class RaceEpisode:
    schema_version: str
    episode_id: str
    source: str
    claim_boundary: str
    non_claims: tuple[str, ...]
    events: tuple[EpisodeEvent, ...]


@dataclass(frozen=True)
class DecisionTrace:
    schema_version: str
    trace_id: str
    episode_id: str
    observation: dict[str, Any]
    goal: dict[str, Any]
    candidate_actions: tuple[dict[str, Any], ...]
    scores: tuple[dict[str, Any], ...]
    selected_action: dict[str, Any]
    predicted_outcome: dict[str, Any]
    measured_or_analytic_outcome: dict[str, Any]
    reproducibility: dict[str, Any]
    non_claims: tuple[str, ...]


def build_bootstrap_episode() -> RaceEpisode:
    non_claims = (
        "not official simulator compatibility evidence",
        "not a valid-run result",
        "not a speedup claim",
        "not a reliability claim",
        "not physical-drone transfer evidence",
    )
    return RaceEpisode(
        schema_version="aigp.race_episode.v0",
        episode_id="fixture-ten-hour-bootstrap-2026-06-08",
        source="deterministic local fixture",
        claim_boundary="offline fixture only; no simulator run",
        non_claims=non_claims,
        events=(
            EpisodeEvent(
                event_type="gate_observation",
                sim_time_ns=44,
                source_frame_id=7,
                payload={
                    "confidence": 0.5,
                    "source": "round1_color_bbox",
                    "corners_px": [[240.0, 100.0], [400.0, 100.0], [400.0, 260.0], [240.0, 260.0]],
                },
            ),
            EpisodeEvent(
                event_type="state_estimate",
                sim_time_ns=44,
                source_frame_id=7,
                payload={
                    "status": "GATE_WITHOUT_VELOCITY",
                    "stale": False,
                    "gate_pose_camera_m": {
                        "x_right": 0.0,
                        "y_down": 0.0,
                        "z_forward": 3.0,
                    },
                },
            ),
            EpisodeEvent(
                event_type="control_command",
                sim_time_ns=44,
                source_frame_id=7,
                payload={
                    "kind": "BODY_VELOCITY",
                    "forward_m_s": 0.75,
                    "right_m_s": 0.0,
                    "down_m_s": 0.0,
                    "reason": "tracking visible gate",
                },
            ),
        ),
    )


def build_bootstrap_decision_trace() -> DecisionTrace:
    non_claims = (
        "not generated in the live flight hot path",
        "not a learned-policy evaluation",
        "not a simulator result",
    )
    return DecisionTrace(
        schema_version="decision_trace.v1-draft",
        trace_id="fixture-control-decision-2026-06-08",
        episode_id="fixture-ten-hour-bootstrap-2026-06-08",
        observation={
            "state_status": "GATE_WITHOUT_VELOCITY",
            "source_frame_id": 7,
            "gate_confidence": 0.5,
            "gate_pose_camera_m": {
                "x_right": 0.0,
                "y_down": 0.0,
                "z_forward": 3.0,
            },
        },
        goal={
            "objective": "conservative first valid run",
            "next_step": "move toward visible gate center without speed claim",
        },
        candidate_actions=(
            {"id": "hold", "kind": "HOLD", "forward_m_s": 0.0},
            {"id": "track_gate", "kind": "BODY_VELOCITY", "forward_m_s": 0.75},
        ),
        scores=(
            {"action_id": "hold", "score": 0.1, "reason": "safe but no progress"},
            {"action_id": "track_gate", "score": 0.6, "reason": "visible centered gate"},
        ),
        selected_action={"id": "track_gate", "kind": "BODY_VELOCITY", "forward_m_s": 0.75},
        predicted_outcome={"progress": "approach gate", "risk": "low in fixture"},
        measured_or_analytic_outcome={"source": "analytic fixture", "regret": None},
        reproducibility={
            "generator": "worldforge_bridge.schema.build_bootstrap_decision_trace",
            "issue": "https://github.com/omarespejel/aigp-racer/issues/2",
        },
        non_claims=non_claims,
    )


def to_json_dict(value: RaceEpisode | DecisionTrace) -> dict[str, Any]:
    return asdict(value)


def write_json(path: Path, value: RaceEpisode | DecisionTrace) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(to_json_dict(value), indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
