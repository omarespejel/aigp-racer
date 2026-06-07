"""AI Grand Prix camera and gate geometry helpers."""

from __future__ import annotations

import math
from collections.abc import Iterable
from dataclasses import dataclass


@dataclass(frozen=True)
class CameraIntrinsics:
    width_px: int = 640
    height_px: int = 360
    fx_px: float = 320.0
    fy_px: float = 320.0
    cx_px: float = 320.0
    cy_px: float = 180.0
    tilt_up_deg: float = 20.0

    def __post_init__(self) -> None:
        if self.width_px <= 0 or self.height_px <= 0:
            raise ValueError("camera resolution must be positive")
        if self.fx_px <= 0.0 or self.fy_px <= 0.0:
            raise ValueError("camera focal lengths must be positive")
        if not 0.0 <= self.cx_px < float(self.width_px):
            raise ValueError("camera cx must be within image width")
        if not 0.0 <= self.cy_px < float(self.height_px):
            raise ValueError("camera cy must be within image height")


@dataclass(frozen=True)
class GateGeometry:
    inner_width_m: float = 1.5
    inner_height_m: float = 1.5
    outer_width_m: float = 2.7
    outer_height_m: float = 2.7
    depth_m: float = 0.26

    def __post_init__(self) -> None:
        if self.inner_width_m <= 0.0 or self.inner_height_m <= 0.0:
            raise ValueError("inner gate dimensions must be positive")
        if self.outer_width_m <= 0.0 or self.outer_height_m <= 0.0:
            raise ValueError("outer gate dimensions must be positive")
        if self.outer_width_m < self.inner_width_m:
            raise ValueError("outer gate width must be at least inner gate width")
        if self.outer_height_m < self.inner_height_m:
            raise ValueError("outer gate height must be at least inner gate height")
        if self.depth_m <= 0.0:
            raise ValueError("gate depth must be positive")


@dataclass(frozen=True)
class ImagePoint:
    u_px: float
    v_px: float


@dataclass(frozen=True)
class CameraPoseEstimate:
    """Gate center pose in optical camera coordinates: X right, Y down, Z forward."""

    x_right_m: float
    y_down_m: float
    z_forward_m: float


AIGP_CAMERA = CameraIntrinsics()
AIGP_GATE = GateGeometry()


def inner_gate_corners_camera(
    pose: CameraPoseEstimate,
    gate: GateGeometry = AIGP_GATE,
) -> tuple[tuple[float, float, float], ...]:
    """Return fronto-parallel gate inner corners in camera coordinates.

    This is a deterministic sanity fixture, not a full arbitrary-pose PnP solver.
    """

    half_w = gate.inner_width_m / 2.0
    half_h = gate.inner_height_m / 2.0
    return (
        (pose.x_right_m - half_w, pose.y_down_m - half_h, pose.z_forward_m),
        (pose.x_right_m + half_w, pose.y_down_m - half_h, pose.z_forward_m),
        (pose.x_right_m + half_w, pose.y_down_m + half_h, pose.z_forward_m),
        (pose.x_right_m - half_w, pose.y_down_m + half_h, pose.z_forward_m),
    )


def project_point(
    point_camera_m: tuple[float, float, float],
    camera: CameraIntrinsics = AIGP_CAMERA,
) -> ImagePoint:
    x_right_m, y_down_m, z_forward_m = point_camera_m
    if z_forward_m <= 0.0:
        raise ValueError("cannot project a point behind the camera")
    return ImagePoint(
        u_px=camera.fx_px * x_right_m / z_forward_m + camera.cx_px,
        v_px=camera.fy_px * y_down_m / z_forward_m + camera.cy_px,
    )


def project_frontoparallel_gate(
    pose: CameraPoseEstimate,
    camera: CameraIntrinsics = AIGP_CAMERA,
    gate: GateGeometry = AIGP_GATE,
) -> tuple[ImagePoint, ImagePoint, ImagePoint, ImagePoint]:
    return tuple(project_point(corner, camera) for corner in inner_gate_corners_camera(pose, gate))


def estimate_frontoparallel_gate_pose(
    corners: Iterable[ImagePoint],
    camera: CameraIntrinsics = AIGP_CAMERA,
    gate: GateGeometry = AIGP_GATE,
) -> CameraPoseEstimate:
    """Estimate gate center pose for fronto-parallel gate sanity tests."""

    points = tuple(corners)
    if len(points) != 4:
        raise ValueError("fronto-parallel gate pose requires four image corners")

    top_width_px = _distance(points[0], points[1])
    bottom_width_px = _distance(points[3], points[2])
    mean_width_px = (top_width_px + bottom_width_px) / 2.0
    if mean_width_px <= 0.0:
        raise ValueError("gate image width must be positive")

    center_u = sum(point.u_px for point in points) / 4.0
    center_v = sum(point.v_px for point in points) / 4.0
    z_forward_m = camera.fx_px * gate.inner_width_m / mean_width_px
    x_right_m = (center_u - camera.cx_px) * z_forward_m / camera.fx_px
    y_down_m = (center_v - camera.cy_px) * z_forward_m / camera.fy_px
    return CameraPoseEstimate(
        x_right_m=x_right_m,
        y_down_m=y_down_m,
        z_forward_m=z_forward_m,
    )


def normalized_camera_ray(
    point: ImagePoint,
    camera: CameraIntrinsics = AIGP_CAMERA,
) -> tuple[float, float, float]:
    """Return an unnormalized optical-frame ray: X right, Y down, Z forward."""

    return (
        (point.u_px - camera.cx_px) / camera.fx_px,
        (point.v_px - camera.cy_px) / camera.fy_px,
        1.0,
    )


def camera_ray_to_body_ned(
    ray_camera: tuple[float, float, float],
    camera: CameraIntrinsics = AIGP_CAMERA,
) -> tuple[float, float, float]:
    """Map an optical-frame camera ray into body NED coordinates.

    Body NED: X forward, Y right, Z down. Camera optical frame: X right,
    Y down, Z forward. Positive camera tilt points the optical axis upward.
    """

    x_cam, y_cam, z_cam = ray_camera
    tilt = math.radians(camera.tilt_up_deg)
    x_right_basis = (0.0, 1.0, 0.0)
    y_down_basis = (math.sin(tilt), 0.0, math.cos(tilt))
    z_forward_basis = (math.cos(tilt), 0.0, -math.sin(tilt))
    return (
        x_cam * x_right_basis[0] + y_cam * y_down_basis[0] + z_cam * z_forward_basis[0],
        x_cam * x_right_basis[1] + y_cam * y_down_basis[1] + z_cam * z_forward_basis[1],
        x_cam * x_right_basis[2] + y_cam * y_down_basis[2] + z_cam * z_forward_basis[2],
    )


def _distance(left: ImagePoint, right: ImagePoint) -> float:
    return math.hypot(left.u_px - right.u_px, left.v_px - right.v_px)
