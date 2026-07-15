#!/usr/bin/env python3
"""Generate a printable Bloodseeker Minotaur-inspired proxy.

The sculpt is an original procedural interpretation built from reference
silhouettes. It is not a scan or an exact reconstruction of the CMON model.
"""

from __future__ import annotations

import math
from pathlib import Path

import matplotlib
import numpy as np
import trimesh
from matplotlib import pyplot
from mpl_toolkits.mplot3d.art3d import Poly3DCollection

matplotlib.use("Agg")


# region Constants

KIT_ROOT = Path(__file__).resolve().parents[1]
MODEL_DIRECTORY = KIT_ROOT / "bloodseeker-minotaur"
PREVIEW_DIRECTORY = KIT_ROOT / "previews"
STL_OUTPUT_PATH = MODEL_DIRECTORY / "bloodseeker-minotaur-proxy.stl"
GLB_OUTPUT_PATH = MODEL_DIRECTORY / "bloodseeker-minotaur-proxy.glb"
PREVIEW_OUTPUT_PATH = PREVIEW_DIRECTORY / "bloodseeker-minotaur-preview.png"

TARGET_MODEL_HEIGHT_MILLIMETERS = 64.0
BASE_RADIUS_MILLIMETERS = 24.0
BASE_HEIGHT_MILLIMETERS = 3.2
VOXEL_PITCH_MILLIMETERS = 0.42
MINIMUM_DIRECTION_LENGTH = 0.000001
FULL_CIRCLE_RADIANS = math.tau
DEGREES_IN_HALF_CIRCLE = 180.0

FRONT_DIRECTION = np.array([0.0, 1.0, 0.0])
VERTICAL_DIRECTION = np.array([0.0, 0.0, 1.0])
MODEL_COLOR = (0.46, 0.26, 0.14, 1.0)
PREVIEW_BACKGROUND_COLOR = "#181818"
PREVIEW_MODEL_COLOR = np.array([0.66, 0.38, 0.22])

# endregion


def create_ellipsoid(
    radii: tuple[float, float, float],
    center: tuple[float, float, float],
    subdivisions: int = 2,
) -> trimesh.Trimesh:
    """Create an ellipsoid.

    Args:
        radii: Radius along each axis in millimeters.
        center: Center position in millimeters.
        subdivisions: Surface subdivision level.

    Returns:
        A transformed triangular mesh.
    """
    mesh = trimesh.creation.icosphere(subdivisions=subdivisions, radius=1.0)
    mesh.apply_scale(radii)
    mesh.apply_translation(center)
    return mesh


def create_cylinder_between(
    start: tuple[float, float, float],
    end: tuple[float, float, float],
    radius: float,
    sections: int = 20,
) -> trimesh.Trimesh:
    """Create a cylinder aligned between two positions.

    Args:
        start: First endpoint in millimeters.
        end: Second endpoint in millimeters.
        radius: Cylinder radius in millimeters.
        sections: Number of radial segments.

    Returns:
        An aligned triangular mesh.
    """
    start_position = np.asarray(start, dtype=float)
    end_position = np.asarray(end, dtype=float)
    direction = end_position - start_position
    length = float(np.linalg.norm(direction))
    if length < MINIMUM_DIRECTION_LENGTH:
        raise ValueError("Cylinder endpoints must be different.")

    mesh = trimesh.creation.cylinder(radius=radius, height=length, sections=sections)
    alignment = trimesh.geometry.align_vectors(VERTICAL_DIRECTION, direction / length)
    mesh.apply_transform(alignment)
    mesh.apply_translation((start_position + end_position) / 2.0)
    return mesh


def create_capsule_between(
    start: tuple[float, float, float],
    end: tuple[float, float, float],
    radius: float,
    sections: int = 20,
) -> trimesh.Trimesh:
    """Create a rounded limb between two positions.

    Args:
        start: First endpoint in millimeters.
        end: Second endpoint in millimeters.
        radius: Limb radius in millimeters.
        sections: Number of radial segments.

    Returns:
        A connected collection of rounded solids.
    """
    shaft = create_cylinder_between(start, end, radius, sections)
    start_cap = create_ellipsoid((radius, radius, radius), start, subdivisions=2)
    end_cap = create_ellipsoid((radius, radius, radius), end, subdivisions=2)
    return concatenate_meshes([shaft, start_cap, end_cap])


def create_cone_between(
    base: tuple[float, float, float],
    tip: tuple[float, float, float],
    radius: float,
    sections: int = 16,
) -> trimesh.Trimesh:
    """Create a tapered spike between two positions.

    Args:
        base: Wide endpoint in millimeters.
        tip: Pointed endpoint in millimeters.
        radius: Base radius in millimeters.
        sections: Number of radial segments.

    Returns:
        An aligned conical mesh.
    """
    base_position = np.asarray(base, dtype=float)
    tip_position = np.asarray(tip, dtype=float)
    direction = tip_position - base_position
    length = float(np.linalg.norm(direction))
    if length < MINIMUM_DIRECTION_LENGTH:
        raise ValueError("Cone endpoints must be different.")

    mesh = trimesh.creation.cone(radius=radius, height=length, sections=sections)
    mesh.apply_translation((0.0, 0.0, length / 2.0))
    alignment = trimesh.geometry.align_vectors(VERTICAL_DIRECTION, direction / length)
    mesh.apply_transform(alignment)
    mesh.apply_translation(base_position)
    return mesh


def create_box(
    extents: tuple[float, float, float],
    center: tuple[float, float, float],
    rotation_degrees: tuple[float, float, float] = (0.0, 0.0, 0.0),
) -> trimesh.Trimesh:
    """Create a rotated box.

    Args:
        extents: Size along each local axis in millimeters.
        center: Center position in millimeters.
        rotation_degrees: Rotation around each global axis.

    Returns:
        A transformed triangular mesh.
    """
    mesh = trimesh.creation.box(extents=extents)
    rotation_radians = np.radians(rotation_degrees)
    transformation = trimesh.transformations.euler_matrix(
        rotation_radians[0],
        rotation_radians[1],
        rotation_radians[2],
        axes="sxyz",
    )
    mesh.apply_transform(transformation)
    mesh.apply_translation(center)
    return mesh


def create_profile_prism(
    profile: list[tuple[float, float]],
    depth: float,
    center_y: float,
) -> trimesh.Trimesh:
    """Extrude an XZ outline along the depth axis.

    Args:
        profile: Ordered XZ outline positions in millimeters.
        depth: Extrusion depth in millimeters.
        center_y: Center position on the depth axis.

    Returns:
        A closed triangular prism.
    """
    point_count = len(profile)
    front_y = center_y + depth / 2.0
    back_y = center_y - depth / 2.0
    vertices = []
    for x_position, z_position in profile:
        vertices.append((x_position, front_y, z_position))
    for x_position, z_position in profile:
        vertices.append((x_position, back_y, z_position))

    faces: list[tuple[int, int, int]] = []
    for index in range(1, point_count - 1):
        faces.append((0, index, index + 1))
        faces.append((point_count, point_count + index + 1, point_count + index))
    for index in range(point_count):
        next_index = (index + 1) % point_count
        faces.append((index, next_index, point_count + next_index))
        faces.append((index, point_count + next_index, point_count + index))
    return trimesh.Trimesh(vertices=np.asarray(vertices), faces=np.asarray(faces), process=True)


def create_torus(
    major_radius: float,
    minor_radius: float,
    center: tuple[float, float, float],
    rotation_degrees: tuple[float, float, float] = (0.0, 0.0, 0.0),
) -> trimesh.Trimesh:
    """Create a transformed torus.

    Args:
        major_radius: Distance from the center to the tube center.
        minor_radius: Tube radius.
        center: Center position in millimeters.
        rotation_degrees: Rotation around each global axis.

    Returns:
        A transformed toroidal mesh.
    """
    mesh = trimesh.creation.torus(
        major_radius=major_radius,
        minor_radius=minor_radius,
        major_sections=32,
        minor_sections=12,
    )
    rotation_radians = np.radians(rotation_degrees)
    transformation = trimesh.transformations.euler_matrix(
        rotation_radians[0],
        rotation_radians[1],
        rotation_radians[2],
        axes="sxyz",
    )
    mesh.apply_transform(transformation)
    mesh.apply_translation(center)
    return mesh


def concatenate_meshes(meshes: list[trimesh.Trimesh]) -> trimesh.Trimesh:
    """Combine mesh components without changing their transforms.

    Args:
        meshes: Components to combine.

    Returns:
        One mesh containing every component.
    """
    if not meshes:
        raise ValueError("At least one mesh component is required.")
    return trimesh.util.concatenate(meshes)


def add_rivet_rows(
    parts: list[trimesh.Trimesh],
    x_positions: tuple[float, ...],
    z_positions: tuple[float, ...],
    center_y: float,
    radius: float,
) -> None:
    """Add repeated armor studs.

    Args:
        parts: Destination component collection.
        x_positions: Horizontal stud positions.
        z_positions: Vertical stud positions.
        center_y: Depth position in millimeters.
        radius: Stud radius in millimeters.
    """
    for x_position in x_positions:
        for z_position in z_positions:
            parts.append(
                create_ellipsoid(
                    (radius, radius * 0.7, radius),
                    (x_position, center_y, z_position),
                    subdivisions=1,
                )
            )


def build_base(parts: list[trimesh.Trimesh]) -> None:
    """Add the round gaming base and rocky ground.

    Args:
        parts: Destination component collection.
    """
    base = trimesh.creation.cylinder(
        radius=BASE_RADIUS_MILLIMETERS,
        height=BASE_HEIGHT_MILLIMETERS,
        sections=64,
    )
    base.apply_translation((0.0, 0.0, BASE_HEIGHT_MILLIMETERS / 2.0))
    parts.append(base)

    rock_positions = (
        (-14.0, -3.0, 3.5),
        (13.0, 7.0, 3.6),
        (-3.0, -13.0, 3.5),
        (7.0, -11.0, 3.6),
    )
    for index, position in enumerate(rock_positions):
        rock = create_ellipsoid(
            (4.0 + index * 0.35, 3.0, 1.6),
            position,
            subdivisions=1,
        )
        parts.append(rock)


def build_legs(parts: list[trimesh.Trimesh]) -> None:
    """Add a wide, planted minotaur stance.

    Args:
        parts: Destination component collection.
    """
    left_hip = (-6.5, -0.8, 20.5)
    left_knee = (-9.0, 1.3, 12.5)
    left_ankle = (-10.5, 4.2, 6.0)
    right_hip = (6.3, -1.0, 20.2)
    right_knee = (8.7, -2.5, 12.0)
    right_ankle = (10.5, -5.2, 5.7)

    parts.extend(
        [
            create_capsule_between(left_hip, left_knee, 4.5),
            create_capsule_between(left_knee, left_ankle, 3.7),
            create_capsule_between(right_hip, right_knee, 4.7),
            create_capsule_between(right_knee, right_ankle, 3.8),
        ]
    )

    left_hoof = create_box((8.5, 9.5, 4.0), (-10.8, 6.0, 4.7), (0.0, -8.0, 3.0))
    right_hoof = create_box((8.7, 9.2, 4.0), (10.8, -6.0, 4.7), (0.0, 8.0, -4.0))
    parts.extend([left_hoof, right_hoof])

    for hoof_center_x, hoof_center_y in ((-10.8, 9.4), (10.8, -9.3)):
        parts.append(
            create_cone_between(
                (hoof_center_x - 2.2, hoof_center_y, 5.0),
                (hoof_center_x - 2.2, hoof_center_y + 2.3, 4.5),
                1.15,
            )
        )
        parts.append(
            create_cone_between(
                (hoof_center_x + 2.2, hoof_center_y, 5.0),
                (hoof_center_x + 2.2, hoof_center_y + 2.3, 4.5),
                1.15,
            )
        )

    left_greave = create_box((7.0, 3.0, 7.5), (-9.3, 4.0, 9.0), (8.0, -7.0, 1.0))
    right_greave = create_box((7.0, 3.0, 7.5), (9.1, -1.5, 8.8), (-7.0, 8.0, -2.0))
    parts.extend([left_greave, right_greave])
    add_rivet_rows(parts, (-11.6, -7.2), (7.0, 10.0), 5.5, 0.7)
    add_rivet_rows(parts, (7.0, 11.4), (6.9, 9.9), 0.0, 0.7)


def build_body(parts: list[trimesh.Trimesh]) -> None:
    """Add the torso, layered armor, skirt, and cloak.

    Args:
        parts: Destination component collection.
    """
    pelvis = create_ellipsoid((9.5, 7.5, 7.0), (0.0, -0.5, 21.5), subdivisions=2)
    abdomen = create_ellipsoid((10.2, 7.8, 9.5), (0.0, -0.8, 28.0), subdivisions=2)
    chest = create_ellipsoid((13.0, 8.7, 9.0), (0.0, -1.8, 36.0), subdivisions=2)
    parts.extend([pelvis, abdomen, chest])

    belly_plate = create_ellipsoid((8.2, 2.5, 8.0), (0.0, 6.2, 29.0), subdivisions=2)
    breast_plate_left = create_ellipsoid((6.0, 2.5, 4.7), (-5.0, 6.2, 37.1), subdivisions=2)
    breast_plate_right = create_ellipsoid((6.0, 2.5, 4.7), (5.0, 6.2, 37.1), subdivisions=2)
    parts.extend([belly_plate, breast_plate_left, breast_plate_right])

    for x_position in (-5.3, -2.65, 0.0, 2.65, 5.3):
        divider = create_capsule_between(
            (x_position, 8.0, 24.2),
            (x_position, 8.0, 33.8),
            0.48,
            sections=12,
        )
        parts.append(divider)
    add_rivet_rows(parts, (-5.2, 0.0, 5.2), (25.7, 29.0, 32.3), 8.4, 0.72)

    belt = create_torus(8.8, 1.0, (0.0, 0.5, 22.8), (90.0, 0.0, 0.0))
    buckle = create_box((4.8, 2.2, 3.8), (0.0, 8.3, 22.7), (0.0, 0.0, 0.0))
    parts.extend([belt, buckle])

    skirt_centers = (
        (-8.5, 4.0, 17.6, -18.0),
        (-4.4, 6.5, 16.8, -9.0),
        (0.0, 7.1, 16.4, 0.0),
        (4.4, 6.5, 16.8, 9.0),
        (8.5, 4.0, 17.6, 18.0),
    )
    for center_x, center_y, center_z, rotation_z in skirt_centers:
        plate = create_box(
            (5.3, 2.2, 9.0),
            (center_x, center_y, center_z),
            (0.0, rotation_z * 0.2, rotation_z),
        )
        parts.append(plate)
        parts.append(
            create_ellipsoid(
                (0.75, 0.65, 0.75),
                (center_x, center_y + 1.2, center_z + 2.4),
                subdivisions=1,
            )
        )

    cloak = create_ellipsoid((15.0, 3.0, 18.0), (3.5, -8.5, 28.5), subdivisions=2)
    cloak_tip = create_cone_between((10.5, -8.0, 18.0), (19.0, -7.5, 9.5), 5.0, sections=20)
    parts.extend([cloak, cloak_tip])

    fur_tuft_positions = (
        (-9.5, -5.0, 39.5, -14.0),
        (-6.0, -7.8, 42.0, -8.0),
        (-1.5, -9.0, 43.0, 0.0),
        (3.0, -9.0, 42.5, 8.0),
        (7.0, -7.2, 40.5, 14.0),
        (11.0, -6.0, 37.0, 22.0),
    )
    for center_x, center_y, center_z, tilt in fur_tuft_positions:
        parts.append(
            create_cone_between(
                (center_x, center_y, center_z),
                (
                    center_x + math.sin(math.radians(tilt)) * 5.5,
                    center_y - 1.7,
                    center_z + math.cos(math.radians(tilt)) * 5.5,
                ),
                2.0,
            )
        )


def build_beast_pauldron(
    parts: list[trimesh.Trimesh],
    center_x: float,
    mirrored: bool,
) -> None:
    """Add a snarling animal-head shoulder guard.

    Args:
        parts: Destination component collection.
        center_x: Horizontal shoulder position.
        mirrored: Whether the guard faces the opposite side.
    """
    side = -1.0 if mirrored else 1.0
    head_center = (center_x, 0.6, 41.5)
    muzzle_center = (center_x + side * 3.8, 4.0, 40.5)
    parts.append(create_ellipsoid((5.5, 5.0, 4.8), head_center, subdivisions=2))
    parts.append(create_ellipsoid((4.6, 4.0, 2.8), muzzle_center, subdivisions=2))
    parts.append(
        create_cone_between(
            (center_x - 1.8, 0.5, 44.8),
            (center_x - 3.7, -1.0, 48.2),
            1.6,
        )
    )
    parts.append(
        create_cone_between(
            (center_x + 1.8, 0.5, 44.8),
            (center_x + 3.7, -1.0, 48.2),
            1.6,
        )
    )
    for vertical_offset in (-1.0, 1.0):
        tooth_base = (
            muzzle_center[0] + side * 2.3,
            muzzle_center[1] + 2.0,
            muzzle_center[2] + vertical_offset,
        )
        tooth_tip = (
            tooth_base[0] + side * 1.0,
            tooth_base[1] + 1.8,
            tooth_base[2] - 0.5,
        )
        parts.append(create_cone_between(tooth_base, tooth_tip, 0.65, sections=12))


def build_head(parts: list[trimesh.Trimesh]) -> None:
    """Add the horned minotaur head, tusks, and mane.

    Args:
        parts: Destination component collection.
    """
    neck = create_capsule_between((0.0, -1.0, 39.5), (0.0, 0.5, 45.0), 4.8)
    skull = create_ellipsoid((5.3, 5.2, 5.7), (0.0, 1.7, 46.6), subdivisions=2)
    muzzle = create_ellipsoid((4.4, 4.5, 3.2), (0.0, 5.5, 44.5), subdivisions=2)
    nose = create_ellipsoid((3.0, 1.5, 1.8), (0.0, 9.0, 45.0), subdivisions=2)
    brow = create_box((8.0, 3.0, 2.0), (0.0, 5.3, 48.8), (-5.0, 0.0, 0.0))
    parts.extend([neck, skull, muzzle, nose, brow])

    horn_pairs = (
        ((-3.8, 0.7, 49.5), (-9.5, -0.2, 55.8)),
        ((3.8, 0.7, 49.5), (9.5, -0.2, 55.8)),
    )
    for horn_base, horn_tip in horn_pairs:
        midpoint = tuple((np.asarray(horn_base) + np.asarray(horn_tip)) / 2.0)
        midpoint = (midpoint[0] * 1.15, midpoint[1], midpoint[2] + 1.0)
        parts.append(create_cone_between(horn_base, midpoint, 2.2, sections=20))
        parts.append(create_cone_between(midpoint, horn_tip, 1.35, sections=18))

    tusk_pairs = (
        ((-2.8, 7.4, 44.3), (-4.8, 11.4, 48.2)),
        ((2.8, 7.4, 44.3), (4.8, 11.4, 48.2)),
    )
    for tusk_base, tusk_tip in tusk_pairs:
        parts.append(create_cone_between(tusk_base, tusk_tip, 1.15, sections=14))

    beard_tuft_positions = (
        (-3.2, 6.0, 43.1, -5.0, 10.0, 38.5),
        (0.0, 6.7, 42.5, 0.0, 11.0, 36.8),
        (3.2, 6.0, 43.1, 5.0, 10.0, 38.5),
    )
    for base_x, base_y, base_z, tip_x, tip_y, tip_z in beard_tuft_positions:
        parts.append(
            create_cone_between(
                (base_x, base_y, base_z),
                (tip_x, tip_y, tip_z),
                1.7,
            )
        )

    mane_angles = tuple(range(-135, 136, 30))
    for angle_degrees in mane_angles:
        angle_radians = math.radians(angle_degrees)
        base_x = math.sin(angle_radians) * 4.5
        base_y = -1.0 - math.cos(angle_radians) * 2.8
        base_z = 46.5 + math.cos(angle_radians) * 4.8
        tip_x = math.sin(angle_radians) * 7.2
        tip_y = base_y - 2.5
        tip_z = 46.5 + math.cos(angle_radians) * 7.5
        parts.append(
            create_cone_between(
                (base_x, base_y, base_z),
                (tip_x, tip_y, tip_z),
                1.45,
                sections=14,
            )
        )

    nose_ring = create_torus(2.0, 0.42, (0.0, 9.9, 43.8), (90.0, 0.0, 0.0))
    parts.append(nose_ring)


def build_arms(parts: list[trimesh.Trimesh]) -> None:
    """Add both armored arms gripping the polearm.

    Args:
        parts: Destination component collection.
    """
    left_shoulder = (-12.0, -0.2, 39.7)
    left_elbow = (-17.3, 2.3, 33.8)
    left_wrist = (-20.0, 7.0, 30.8)
    right_shoulder = (12.0, -0.3, 39.5)
    right_elbow = (17.0, 2.0, 34.0)
    right_wrist = (19.8, 6.6, 30.8)

    parts.extend(
        [
            create_capsule_between(left_shoulder, left_elbow, 4.5),
            create_capsule_between(left_elbow, left_wrist, 3.8),
            create_capsule_between(right_shoulder, right_elbow, 4.5),
            create_capsule_between(right_elbow, right_wrist, 3.8),
        ]
    )

    left_bracer = create_capsule_between((-17.7, 3.0, 33.2), (-19.6, 6.0, 31.1), 4.15)
    right_bracer = create_capsule_between((17.5, 2.8, 33.2), (19.5, 5.8, 31.1), 4.15)
    parts.extend([left_bracer, right_bracer])

    for center_x in (-18.5, 18.5):
        parts.append(create_torus(4.0, 0.65, (center_x, 4.4, 32.3), (55.0, 0.0, 0.0)))

    left_hand = create_ellipsoid((3.2, 3.0, 3.4), left_wrist, subdivisions=2)
    right_hand = create_ellipsoid((3.2, 3.0, 3.4), right_wrist, subdivisions=2)
    parts.extend([left_hand, right_hand])

    build_beast_pauldron(parts, -12.5, mirrored=True)
    build_beast_pauldron(parts, 12.5, mirrored=False)


def build_polearm(parts: list[trimesh.Trimesh]) -> None:
    """Add the broad axe and spiked counterweight.

    Args:
        parts: Destination component collection.
    """
    shaft_start = (-33.5, 7.0, 29.8)
    shaft_end = (35.0, 7.0, 31.8)
    shaft = create_cylinder_between(shaft_start, shaft_end, 1.55, sections=24)
    parts.append(shaft)

    shaft_direction = np.asarray(shaft_end) - np.asarray(shaft_start)
    shaft_direction = shaft_direction / np.linalg.norm(shaft_direction)

    axe_center_x = -34.5
    axe_center_z = 29.8
    axe_profile = [
        (axe_center_x - 11.0, axe_center_z + 8.5),
        (axe_center_x - 3.5, axe_center_z + 7.2),
        (axe_center_x + 1.8, axe_center_z + 3.0),
        (axe_center_x + 1.8, axe_center_z - 3.0),
        (axe_center_x - 4.0, axe_center_z - 7.5),
        (axe_center_x - 12.0, axe_center_z - 8.8),
        (axe_center_x - 9.0, axe_center_z - 3.0),
        (axe_center_x - 9.5, axe_center_z + 2.5),
    ]
    axe_head = create_profile_prism(axe_profile, 4.6, 7.0)
    axe_collar = create_cylinder_between(
        tuple(np.asarray(shaft_start) - shaft_direction * 2.5),
        tuple(np.asarray(shaft_start) + shaft_direction * 3.0),
        2.4,
        sections=24,
    )
    parts.extend([axe_head, axe_collar])

    decorative_cutout = create_torus(3.2, 0.6, (-40.0, 9.1, 30.0), (90.0, 0.0, 0.0))
    parts.append(decorative_cutout)

    mace_center = np.asarray(shaft_end) + shaft_direction * 4.7
    mace_head = create_box(
        (9.0, 8.0, 10.0),
        tuple(mace_center),
        (0.0, 14.0, 2.0),
    )
    mace_collar = create_cylinder_between(
        tuple(np.asarray(shaft_end) - shaft_direction * 1.0),
        tuple(np.asarray(shaft_end) + shaft_direction * 3.0),
        2.4,
        sections=24,
    )
    parts.extend([mace_head, mace_collar])

    spike_directions = (
        (0.0, 0.0, 1.0),
        (0.0, 0.0, -1.0),
        (0.0, 1.0, 0.0),
        (0.0, -1.0, 0.0),
        (1.0, 0.0, 0.0),
    )
    for direction in spike_directions:
        direction_vector = np.asarray(direction, dtype=float)
        spike_base = mace_center + direction_vector * 4.0
        spike_tip = mace_center + direction_vector * 8.0
        parts.append(
            create_cone_between(
                tuple(spike_base),
                tuple(spike_tip),
                1.55,
                sections=14,
            )
        )


def make_printable(mesh: trimesh.Trimesh) -> trimesh.Trimesh:
    """Fuse all overlapping components into one printable solid.

    Args:
        mesh: Source mesh containing intersecting components.

    Returns:
        A watertight mesh scaled to the target height.
    """
    voxel_grid = mesh.voxelized(pitch=VOXEL_PITCH_MILLIMETERS)
    voxel_grid = voxel_grid.fill()
    solid = voxel_grid.marching_cubes
    solid.remove_unreferenced_vertices()
    solid.merge_vertices()
    solid.fix_normals()

    current_height = float(solid.extents[2])
    if current_height < MINIMUM_DIRECTION_LENGTH:
        raise ValueError("Generated model has no measurable height.")
    solid.apply_scale(TARGET_MODEL_HEIGHT_MILLIMETERS / current_height)
    solid.apply_translation((0.0, 0.0, -solid.bounds[0][2]))

    connected_components = solid.split(only_watertight=False)
    if len(connected_components) > 1:
        largest_component = max(connected_components, key=lambda component: component.volume)
        discarded_volume = sum(
            abs(component.volume)
            for component in connected_components
            if component is not largest_component
        )
        if discarded_volume > 1.0:
            raise ValueError("Generated details are not connected to the main solid.")
        solid = largest_component

    solid.visual.face_colors = np.tile(
        np.asarray([117, 67, 36, 255], dtype=np.uint8),
        (len(solid.faces), 1),
    )
    return solid


def build_model() -> trimesh.Trimesh:
    """Assemble and fuse the complete miniature.

    Returns:
        A print-ready triangular mesh.
    """
    parts: list[trimesh.Trimesh] = []
    build_base(parts)
    build_legs(parts)
    build_body(parts)
    build_head(parts)
    build_arms(parts)
    build_polearm(parts)
    return make_printable(concatenate_meshes(parts))


def render_preview(mesh: trimesh.Trimesh, output_path: Path) -> None:
    """Render three inspection views without an interactive window.

    Args:
        mesh: Printable mesh to render.
        output_path: Destination image path.
    """
    figure = pyplot.figure(figsize=(15.0, 5.4), facecolor=PREVIEW_BACKGROUND_COLOR)
    view_settings = (
        ("front-left", 18.0, -70.0),
        ("front-right", 18.0, -110.0),
        ("rear", 15.0, 75.0),
    )

    maximum_preview_faces = 26000
    face_step = max(1, len(mesh.faces) // maximum_preview_faces)
    preview_faces = mesh.faces[::face_step]
    triangles = mesh.vertices[preview_faces]
    face_normals = mesh.face_normals[::face_step]
    light_direction = np.asarray([-0.4, -0.7, 0.8])
    light_direction = light_direction / np.linalg.norm(light_direction)
    brightness = np.clip(face_normals @ light_direction, -0.4, 1.0)
    brightness = 0.48 + (brightness + 0.4) * 0.38
    colors = np.clip(PREVIEW_MODEL_COLOR[None, :] * brightness[:, None], 0.0, 1.0)

    center = mesh.bounds.mean(axis=0)
    maximum_extent = float(max(mesh.extents)) * 0.57
    for plot_index, (title, elevation, azimuth) in enumerate(view_settings, start=1):
        axis = figure.add_subplot(1, 3, plot_index, projection="3d")
        collection = Poly3DCollection(
            triangles,
            facecolors=colors,
            edgecolors="none",
            linewidths=0.0,
        )
        axis.add_collection3d(collection)
        axis.set_xlim(center[0] - maximum_extent, center[0] + maximum_extent)
        axis.set_ylim(center[1] - maximum_extent, center[1] + maximum_extent)
        axis.set_zlim(0.0, maximum_extent * 2.0)
        axis.set_box_aspect((1.0, 1.0, 1.25))
        axis.view_init(elev=elevation, azim=azimuth)
        axis.set_axis_off()
        axis.set_facecolor(PREVIEW_BACKGROUND_COLOR)
        axis.set_title(title, color="white", fontsize=11, pad=2)

    figure.tight_layout(pad=0.35)
    figure.savefig(
        output_path,
        dpi=180,
        facecolor=figure.get_facecolor(),
        bbox_inches="tight",
    )
    pyplot.close(figure)


def export_model(mesh: trimesh.Trimesh) -> None:
    """Write printable and preview-oriented model formats.

    Args:
        mesh: Final mesh to export.
    """
    MODEL_DIRECTORY.mkdir(parents=True, exist_ok=True)
    PREVIEW_DIRECTORY.mkdir(parents=True, exist_ok=True)
    mesh.export(STL_OUTPUT_PATH)

    scene = trimesh.Scene()
    scene.add_geometry(mesh, node_name="bloodseeker_minotaur_proxy")
    GLB_OUTPUT_PATH.write_bytes(scene.export(file_type="glb"))
    render_preview(mesh, PREVIEW_OUTPUT_PATH)


def main() -> None:
    """Generate all model artifacts and report print checks."""
    mesh = build_model()
    export_model(mesh)
    print(f"Wrote {STL_OUTPUT_PATH}")
    print(f"Wrote {GLB_OUTPUT_PATH}")
    print(f"Wrote {PREVIEW_OUTPUT_PATH}")
    print(
        "Bounds millimeters: "
        f"X={mesh.extents[0]:.1f} "
        f"Y={mesh.extents[1]:.1f} "
        f"Z={mesh.extents[2]:.1f}"
    )
    print(
        f"Faces={len(mesh.faces)} "
        f"watertight={mesh.is_watertight} "
        f"components={len(mesh.split(only_watertight=False))}"
    )


if __name__ == "__main__":
    main()
