from __future__ import annotations

import math

import pytest

from perception.geometry import (
    AIGP_CAMERA,
    AIGP_GATE,
    CameraIntrinsics,
    CameraPoseEstimate,
    GateGeometry,
    ImagePoint,
    LabeledGateImageCorners,
    camera_ray_to_body_ned,
    estimate_frontoparallel_gate_pose,
    estimate_planar_gate_pose,
    normalized_camera_ray,
    project_frontoparallel_gate,
    project_planar_gate,
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


def test_planar_pnp_recovers_perspective_skewed_gate_pose() -> None:
    pose = CameraPoseEstimate(x_right_m=0.35, y_down_m=-0.2, z_forward_m=4.5)
    rotation = _rotation_y_down(math.radians(18.0))
    corners = project_planar_gate(pose, rotation)

    estimate = estimate_planar_gate_pose(corners)

    assert estimate.center.x_right_m == pytest.approx(pose.x_right_m, abs=1e-9, rel=0.0)
    assert estimate.center.y_down_m == pytest.approx(pose.y_down_m, abs=1e-9, rel=0.0)
    assert estimate.center.z_forward_m == pytest.approx(pose.z_forward_m, abs=1e-9, rel=0.0)
    assert estimate.mean_reprojection_error_px < 1e-9
    assert estimate.max_reprojection_error_px < 1e-9
    assert estimate.rotation_camera_from_gate[0][0] == pytest.approx(
        rotation[0][0],
        abs=1e-9,
        rel=0.0,
    )
    assert estimate.rotation_camera_from_gate[2][0] == pytest.approx(
        rotation[2][0],
        abs=1e-9,
        rel=0.0,
    )


def test_planar_pnp_recovers_rolled_gate_pose() -> None:
    pose = CameraPoseEstimate(x_right_m=0.15, y_down_m=0.05, z_forward_m=5.0)
    rotation = _rotation_z_forward(math.radians(60.0))
    corners = project_planar_gate(pose, rotation)

    estimate = estimate_planar_gate_pose(corners)

    assert estimate.center.x_right_m == pytest.approx(pose.x_right_m, abs=1e-9, rel=0.0)
    assert estimate.center.y_down_m == pytest.approx(pose.y_down_m, abs=1e-9, rel=0.0)
    assert estimate.center.z_forward_m == pytest.approx(pose.z_forward_m, abs=1e-9, rel=0.0)
    for actual_row, expected_row in zip(
        estimate.rotation_camera_from_gate,
        rotation,
        strict=True,
    ):
        for actual, expected in zip(actual_row, expected_row, strict=True):
            assert actual == pytest.approx(expected, abs=1e-9, rel=0.0)


def test_planar_pnp_center_pose_maps_to_body_ned_with_camera_tilt() -> None:
    pose = CameraPoseEstimate(x_right_m=0.0, y_down_m=0.0, z_forward_m=4.0)
    corners = project_planar_gate(pose, _identity_rotation())

    estimate = estimate_planar_gate_pose(corners)
    body_ray = camera_ray_to_body_ned(
        (
            estimate.center.x_right_m,
            estimate.center.y_down_m,
            estimate.center.z_forward_m,
        )
    )

    assert body_ray[0] == pytest.approx(4.0 * math.cos(math.radians(20.0)))
    assert body_ray[1] == pytest.approx(0.0)
    assert body_ray[2] == pytest.approx(-4.0 * math.sin(math.radians(20.0)))


def test_pose_estimate_requires_four_corners() -> None:
    with pytest.raises(ValueError, match="four"):
        estimate_frontoparallel_gate_pose([ImagePoint(0.0, 0.0)])


def test_planar_pnp_requires_four_corners() -> None:
    with pytest.raises(TypeError, match="LabeledGateImageCorners"):
        estimate_planar_gate_pose([ImagePoint(0.0, 0.0)])


def test_planar_pnp_rejects_degenerate_corners() -> None:
    with pytest.raises(ValueError, match="degenerate"):
        estimate_planar_gate_pose(
            LabeledGateImageCorners(
                ImagePoint(100.0, 100.0),
                ImagePoint(100.0, 100.0),
                ImagePoint(100.0, 100.0),
                ImagePoint(100.0, 100.0),
            )
        )


def test_planar_pnp_rejects_wrong_corner_winding() -> None:
    pose = CameraPoseEstimate(x_right_m=0.0, y_down_m=0.0, z_forward_m=4.0)
    corners = project_planar_gate(pose, _identity_rotation())
    reversed_corners = LabeledGateImageCorners(*reversed(corners.as_tuple()))

    with pytest.raises(ValueError, match="front-facing"):
        estimate_planar_gate_pose(reversed_corners)


def test_planar_pnp_rejects_nonconvex_corners() -> None:
    top_left = ImagePoint(0.0, 0.0)
    top_right = ImagePoint(2.0, 0.0)
    inward_corner = ImagePoint(0.5, 0.5)
    bottom_left = ImagePoint(0.0, 2.0)

    with pytest.raises(ValueError, match="convex"):
        estimate_planar_gate_pose(
            LabeledGateImageCorners(top_left, top_right, inward_corner, bottom_left)
        )


def test_planar_projection_rejects_scaled_rotation_matrix() -> None:
    pose = CameraPoseEstimate(x_right_m=0.0, y_down_m=0.0, z_forward_m=4.0)
    scaled_rotation = (
        (2.0, 0.0, 0.0),
        (0.0, 1.0, 0.0),
        (0.0, 0.0, 1.0),
    )

    with pytest.raises(ValueError, match="unit length"):
        project_planar_gate(pose, scaled_rotation)


def test_planar_projection_rejects_reflected_rotation_matrix() -> None:
    pose = CameraPoseEstimate(x_right_m=0.0, y_down_m=0.0, z_forward_m=4.0)
    reflected_rotation = (
        (-1.0, 0.0, 0.0),
        (0.0, 1.0, 0.0),
        (0.0, 0.0, 1.0),
    )

    with pytest.raises(ValueError, match="right-handed"):
        project_planar_gate(pose, reflected_rotation)


def test_center_pixel_ray_tilts_up_in_body_ned() -> None:
    ray = normalized_camera_ray(ImagePoint(AIGP_CAMERA.cx_px, AIGP_CAMERA.cy_px))
    body_ray = camera_ray_to_body_ned(ray)

    assert body_ray[0] == pytest.approx(math.cos(math.radians(20.0)))
    assert body_ray[1] == pytest.approx(0.0)
    assert body_ray[2] == pytest.approx(-math.sin(math.radians(20.0)))


def test_camera_intrinsics_validate_constructor_invariants() -> None:
    with pytest.raises(ValueError, match="resolution"):
        CameraIntrinsics(width_px=0)
    with pytest.raises(ValueError, match="focal"):
        CameraIntrinsics(fx_px=0.0)
    with pytest.raises(ValueError, match="cx"):
        CameraIntrinsics(cx_px=640.0)
    with pytest.raises(ValueError, match="cy"):
        CameraIntrinsics(cy_px=360.0)


def test_gate_geometry_validates_constructor_invariants() -> None:
    with pytest.raises(ValueError, match="inner"):
        GateGeometry(inner_width_m=0.0)
    with pytest.raises(ValueError, match="outer gate width"):
        GateGeometry(outer_width_m=1.0)
    with pytest.raises(ValueError, match="outer gate height"):
        GateGeometry(outer_height_m=1.0)
    with pytest.raises(ValueError, match="depth"):
        GateGeometry(depth_m=0.0)


def _rotation_y_down(angle_rad: float) -> tuple[tuple[float, float, float], ...]:
    cos_angle = math.cos(angle_rad)
    sin_angle = math.sin(angle_rad)
    return (
        (cos_angle, 0.0, sin_angle),
        (0.0, 1.0, 0.0),
        (-sin_angle, 0.0, cos_angle),
    )


def _rotation_z_forward(angle_rad: float) -> tuple[tuple[float, float, float], ...]:
    cos_angle = math.cos(angle_rad)
    sin_angle = math.sin(angle_rad)
    return (
        (cos_angle, -sin_angle, 0.0),
        (sin_angle, cos_angle, 0.0),
        (0.0, 0.0, 1.0),
    )


def _identity_rotation() -> tuple[tuple[float, float, float], ...]:
    return (
        (1.0, 0.0, 0.0),
        (0.0, 1.0, 0.0),
        (0.0, 0.0, 1.0),
    )
