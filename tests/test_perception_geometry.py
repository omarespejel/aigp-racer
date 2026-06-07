from __future__ import annotations

import math

import pytest

from perception.geometry import (
    AIGP_CAMERA,
    AIGP_GATE,
    CameraPoseEstimate,
    ImagePoint,
    camera_ray_to_body_ned,
    estimate_frontoparallel_gate_pose,
    normalized_camera_ray,
    project_frontoparallel_gate,
)


def test_camera_intrinsics_match_spec() -> None:
    assert AIGP_CAMERA.width_px == 640
    assert AIGP_CAMERA.height_px == 360
    assert AIGP_CAMERA.fx_px == 320.0
    assert AIGP_CAMERA.fy_px == 320.0
    assert AIGP_CAMERA.cx_px == 320.0
    assert AIGP_CAMERA.cy_px == 180.0
    assert AIGP_CAMERA.tilt_up_deg == 20.0


def test_gate_dimensions_match_spec() -> None:
    assert AIGP_GATE.inner_width_m == 1.5
    assert AIGP_GATE.inner_height_m == 1.5
    assert AIGP_GATE.outer_width_m == 2.7
    assert AIGP_GATE.outer_height_m == 2.7
    assert AIGP_GATE.depth_m == 0.26


def test_frontoparallel_projection_and_pose_estimate_round_trip() -> None:
    pose = CameraPoseEstimate(x_right_m=0.25, y_down_m=-0.1, z_forward_m=4.0)
    corners = project_frontoparallel_gate(pose)

    estimate = estimate_frontoparallel_gate_pose(corners)

    assert estimate.x_right_m == pytest.approx(0.25)
    assert estimate.y_down_m == pytest.approx(-0.1)
    assert estimate.z_forward_m == pytest.approx(4.0)


def test_pose_estimate_requires_four_corners() -> None:
    with pytest.raises(ValueError, match="four"):
        estimate_frontoparallel_gate_pose([ImagePoint(0.0, 0.0)])


def test_center_pixel_ray_tilts_up_in_body_ned() -> None:
    ray = normalized_camera_ray(ImagePoint(AIGP_CAMERA.cx_px, AIGP_CAMERA.cy_px))
    body_ray = camera_ray_to_body_ned(ray)

    assert body_ray[0] == pytest.approx(math.cos(math.radians(20.0)))
    assert body_ray[1] == pytest.approx(0.0)
    assert body_ray[2] == pytest.approx(-math.sin(math.radians(20.0)))
