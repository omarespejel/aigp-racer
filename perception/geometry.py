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
class LabeledGateImageCorners:
    """Image points labeled by physical gate-local corner identity."""

    top_left: ImagePoint
    top_right: ImagePoint
    bottom_right: ImagePoint
    bottom_left: ImagePoint

    def as_tuple(self) -> tuple[ImagePoint, ImagePoint, ImagePoint, ImagePoint]:
        return (self.top_left, self.top_right, self.bottom_right, self.bottom_left)


@dataclass(frozen=True)
class CameraPoseEstimate:
    """Gate center pose in optical camera coordinates: X right, Y down, Z forward."""

    x_right_m: float
    y_down_m: float
    z_forward_m: float


@dataclass(frozen=True)
class PlanarGatePoseEstimate:
    """Full planar gate pose in optical camera coordinates."""

    center: CameraPoseEstimate
    rotation_camera_from_gate: tuple[tuple[float, float, float], ...]
    mean_reprojection_error_px: float
    max_reprojection_error_px: float


AIGP_CAMERA = CameraIntrinsics()
AIGP_GATE = GateGeometry()


def inner_gate_corners_gate(
    gate: GateGeometry = AIGP_GATE,
) -> tuple[tuple[float, float, float], ...]:
    """Return inner gate corners in gate-local coordinates around the gate center."""

    half_w = gate.inner_width_m / 2.0
    half_h = gate.inner_height_m / 2.0
    return (
        (-half_w, -half_h, 0.0),
        (half_w, -half_h, 0.0),
        (half_w, half_h, 0.0),
        (-half_w, half_h, 0.0),
    )


def inner_gate_corners_camera(
    pose: CameraPoseEstimate,
    gate: GateGeometry = AIGP_GATE,
) -> tuple[tuple[float, float, float], ...]:
    """Return fronto-parallel gate inner corners in camera coordinates.

    This is a deterministic sanity fixture, not a full arbitrary-pose PnP solver.
    """

    return tuple(
        (
            pose.x_right_m + corner[0],
            pose.y_down_m + corner[1],
            pose.z_forward_m + corner[2],
        )
        for corner in inner_gate_corners_gate(gate)
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


def project_planar_gate(
    pose: CameraPoseEstimate,
    rotation_camera_from_gate: tuple[tuple[float, float, float], ...],
    camera: CameraIntrinsics = AIGP_CAMERA,
    gate: GateGeometry = AIGP_GATE,
) -> LabeledGateImageCorners:
    _validate_rotation(rotation_camera_from_gate)
    points_camera = tuple(
        _add3(
            _mat_vec_mul(rotation_camera_from_gate, point_gate),
            (pose.x_right_m, pose.y_down_m, pose.z_forward_m),
        )
        for point_gate in inner_gate_corners_gate(gate)
    )
    image_points = tuple(project_point(point, camera) for point in points_camera)
    return LabeledGateImageCorners(*image_points)


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


def estimate_planar_gate_pose(
    corners: LabeledGateImageCorners,
    camera: CameraIntrinsics = AIGP_CAMERA,
    gate: GateGeometry = AIGP_GATE,
) -> PlanarGatePoseEstimate:
    """EXPERIMENTAL: recover planar gate pose from physical corner labels.

    The input must carry physical gate-local corner IDs: top-left, top-right,
    bottom-right, bottom-left. Screen-space bbox corners are not enough to
    determine the physical in-plane orientation of a square gate. The
    implementation uses a planar homography decomposition in normalized camera
    coordinates; it is a deterministic pure-Python PnP path, not a substitute
    for an optimized OpenCV solver in the final runtime.
    """

    if not isinstance(corners, LabeledGateImageCorners):
        raise TypeError("planar gate pose requires LabeledGateImageCorners")
    image_points = corners.as_tuple()
    _validate_labeled_gate_corners(image_points)

    object_points = tuple((corner[0], corner[1]) for corner in inner_gate_corners_gate(gate))
    normalized_points = tuple(
        (
            (point.u_px - camera.cx_px) / camera.fx_px,
            (point.v_px - camera.cy_px) / camera.fy_px,
        )
        for point in image_points
    )
    homography = _solve_planar_homography(object_points, normalized_points)
    rotation, translation = _decompose_normalized_homography(homography)
    pose = CameraPoseEstimate(
        x_right_m=translation[0],
        y_down_m=translation[1],
        z_forward_m=translation[2],
    )
    projected = project_planar_gate(pose, rotation, camera, gate).as_tuple()
    errors = tuple(
        _distance(observed, reprojection)
        for observed, reprojection in zip(image_points, projected, strict=True)
    )
    return PlanarGatePoseEstimate(
        center=pose,
        rotation_camera_from_gate=rotation,
        mean_reprojection_error_px=sum(errors) / len(errors),
        max_reprojection_error_px=max(errors),
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


def _solve_planar_homography(
    object_points: tuple[tuple[float, float], ...],
    normalized_points: tuple[tuple[float, float], ...],
) -> tuple[tuple[float, float, float], ...]:
    rows: list[list[float]] = []
    values: list[float] = []
    for (x_m, y_m), (u_norm, v_norm) in zip(
        object_points,
        normalized_points,
        strict=True,
    ):
        rows.append([x_m, y_m, 1.0, 0.0, 0.0, 0.0, -u_norm * x_m, -u_norm * y_m])
        values.append(u_norm)
        rows.append([0.0, 0.0, 0.0, x_m, y_m, 1.0, -v_norm * x_m, -v_norm * y_m])
        values.append(v_norm)
    solution = _solve_linear_system(rows, values)
    return (
        (solution[0], solution[1], solution[2]),
        (solution[3], solution[4], solution[5]),
        (solution[6], solution[7], 1.0),
    )


def _decompose_normalized_homography(
    homography: tuple[tuple[float, float, float], ...],
) -> tuple[tuple[tuple[float, float, float], ...], tuple[float, float, float]]:
    col_1 = (homography[0][0], homography[1][0], homography[2][0])
    col_2 = (homography[0][1], homography[1][1], homography[2][1])
    col_3 = (homography[0][2], homography[1][2], homography[2][2])
    norm_1 = _norm3(col_1)
    norm_2 = _norm3(col_2)
    if norm_1 <= 0.0 or norm_2 <= 0.0:
        raise ValueError("degenerate homography columns")

    scale = 2.0 / (norm_1 + norm_2)
    if scale * col_3[2] <= 0.0:
        scale = -scale
    raw_r1 = _scale3(col_1, scale)
    raw_r2 = _scale3(col_2, scale)
    translation = _scale3(col_3, scale)

    r1 = _normalize3(raw_r1)
    r2 = _normalize3(_sub3(raw_r2, _scale3(r1, _dot3(r1, raw_r2))))
    r3 = _cross3(r1, r2)
    return (
        (
            (r1[0], r2[0], r3[0]),
            (r1[1], r2[1], r3[1]),
            (r1[2], r2[2], r3[2]),
        ),
        translation,
    )


def _solve_linear_system(matrix: list[list[float]], values: list[float]) -> list[float]:
    size = len(values)
    if len(matrix) != size or any(len(row) != size for row in matrix):
        raise ValueError("linear system must be square")
    augmented = [[*row[:], value] for row, value in zip(matrix, values, strict=True)]
    for pivot_index in range(size):
        pivot_row = max(
            range(pivot_index, size),
            key=lambda row_index: abs(augmented[row_index][pivot_index]),
        )
        if abs(augmented[pivot_row][pivot_index]) < 1e-12:
            raise ValueError("degenerate planar gate homography")
        if pivot_row != pivot_index:
            augmented[pivot_index], augmented[pivot_row] = (
                augmented[pivot_row],
                augmented[pivot_index],
            )
        pivot = augmented[pivot_index][pivot_index]
        augmented[pivot_index] = [value / pivot for value in augmented[pivot_index]]
        for row_index in range(size):
            if row_index == pivot_index:
                continue
            factor = augmented[row_index][pivot_index]
            if factor == 0.0:
                continue
            augmented[row_index] = [
                value - factor * pivot_value
                for value, pivot_value in zip(
                    augmented[row_index],
                    augmented[pivot_index],
                    strict=True,
                )
            ]
    return [row[-1] for row in augmented]


def _validate_rotation(rotation: tuple[tuple[float, float, float], ...]) -> None:
    if len(rotation) != 3 or any(len(row) != 3 for row in rotation):
        raise ValueError("rotation must be a 3x3 matrix")
    eps = 1e-6
    row0, row1, row2 = rotation
    if any(abs(_norm3(row) - 1.0) > eps for row in rotation):
        raise ValueError("rotation rows must be unit length")
    if abs(_dot3(row0, row1)) > eps or abs(_dot3(row0, row2)) > eps or abs(_dot3(row1, row2)) > eps:
        raise ValueError("rotation rows must be orthogonal")
    determinant = _dot3(row0, _cross3(row1, row2))
    if determinant <= 0.0:
        raise ValueError("rotation must be right-handed")


def _validate_labeled_gate_corners(
    points: tuple[ImagePoint, ImagePoint, ImagePoint, ImagePoint],
) -> None:
    """Validate front-facing, non-degenerate, convex physical corner labels."""

    next_points = points[1:] + points[:1]
    area2 = sum(
        left.u_px * right.v_px - right.u_px * left.v_px
        for left, right in zip(points, next_points, strict=True)
    )
    if abs(area2) <= 1e-12:
        raise ValueError("degenerate planar gate corners")
    if area2 < 0.0:
        raise ValueError(
            "planar gate corners must be front-facing and ordered "
            "top-left, top-right, bottom-right, bottom-left"
        )
    for left, middle, right in zip(points, next_points, points[2:] + points[:2], strict=True):
        edge_a = (middle.u_px - left.u_px, middle.v_px - left.v_px)
        edge_b = (right.u_px - middle.u_px, right.v_px - middle.v_px)
        if edge_a[0] * edge_b[1] - edge_a[1] * edge_b[0] <= 0.0:
            raise ValueError("planar gate corners must form a convex quadrilateral")


def _mat_vec_mul(
    matrix: tuple[tuple[float, float, float], ...],
    vector: tuple[float, float, float],
) -> tuple[float, float, float]:
    return tuple(sum(matrix[row][col] * vector[col] for col in range(3)) for row in range(3))


def _add3(
    left: tuple[float, float, float],
    right: tuple[float, float, float],
) -> tuple[float, float, float]:
    return (left[0] + right[0], left[1] + right[1], left[2] + right[2])


def _sub3(
    left: tuple[float, float, float],
    right: tuple[float, float, float],
) -> tuple[float, float, float]:
    return (left[0] - right[0], left[1] - right[1], left[2] - right[2])


def _scale3(vector: tuple[float, float, float], scale: float) -> tuple[float, float, float]:
    return (vector[0] * scale, vector[1] * scale, vector[2] * scale)


def _dot3(
    left: tuple[float, float, float],
    right: tuple[float, float, float],
) -> float:
    return left[0] * right[0] + left[1] * right[1] + left[2] * right[2]


def _cross3(
    left: tuple[float, float, float],
    right: tuple[float, float, float],
) -> tuple[float, float, float]:
    return (
        left[1] * right[2] - left[2] * right[1],
        left[2] * right[0] - left[0] * right[2],
        left[0] * right[1] - left[1] * right[0],
    )


def _norm3(vector: tuple[float, float, float]) -> float:
    return math.sqrt(_dot3(vector, vector))


def _normalize3(vector: tuple[float, float, float]) -> tuple[float, float, float]:
    norm = _norm3(vector)
    if norm <= 0.0:
        raise ValueError("cannot normalize zero vector")
    return _scale3(vector, 1.0 / norm)
