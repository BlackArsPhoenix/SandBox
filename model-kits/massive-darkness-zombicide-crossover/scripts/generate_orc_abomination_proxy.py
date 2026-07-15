#!/usr/bin/env python3
"""Generate a print-ready Orc Abomination proxy STL.

Original-inspired silhouette based on Zombicide: Green Horde Orc Abomination
reference photos (raised claw, lunging pose, horned mask, skull belt, spiked
pauldron). Not a CMON scan or 1:1 recreation — an original proxy for personal
Massive Darkness 2 / Zombicide crossover printing.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import trimesh
from trimesh.transformations import rotation_matrix


# Region: constants
MILLIMETERS_PER_UNIT = 1.0
BASE_DIAMETER_MM = 40.0
BASE_HEIGHT_MM = 2.5
TARGET_FIGURE_HEIGHT_MM = 58.0
OUTPUT_RELATIVE_PATH = Path(
    "green-horde/orc-abomination/04-orc-abomination-proxy-generated.stl"
)
# End region: constants


def _sphere(radius: float, subdivisions: int = 2) -> trimesh.Trimesh:
    """Create an icosphere.

    Args:
        radius: Sphere radius in millimeters.
        subdivisions: Icosphere subdivision level.
    """
    return trimesh.creation.icosphere(subdivisions=subdivisions, radius=radius)


def _capsule(radius: float, height: float, sections: int = 16) -> trimesh.Trimesh:
    """Create a vertical capsule (cylinder with hemispherical caps).

    Args:
        radius: Capsule radius in millimeters.
        height: Total height including caps.
        sections: Cylinder radial sections.
    """
    shaft_height = max(height - 2.0 * radius, 0.1)
    shaft = trimesh.creation.cylinder(radius=radius, height=shaft_height, sections=sections)
    top = _sphere(radius, subdivisions=2)
    bottom = top.copy()
    top.apply_translation([0.0, 0.0, shaft_height / 2.0])
    bottom.apply_translation([0.0, 0.0, -shaft_height / 2.0])
    return trimesh.util.concatenate([shaft, top, bottom])


def _box(extents: tuple[float, float, float]) -> trimesh.Trimesh:
    """Create an axis-aligned box centered at origin.

    Args:
        extents: Box size along X, Y, Z in millimeters.
    """
    return trimesh.creation.box(extents=list(extents))


def _cone(radius: float, height: float, sections: int = 16) -> trimesh.Trimesh:
    """Create a cone pointing +Z.

    Args:
        radius: Base radius.
        height: Cone height.
        sections: Radial sections.
    """
    return trimesh.creation.cone(radius=radius, height=height, sections=sections)


def _transform(
    mesh: trimesh.Trimesh,
    translation: tuple[float, float, float] | None = None,
    axis: tuple[float, float, float] | None = None,
    angle_degrees: float = 0.0,
) -> trimesh.Trimesh:
    """Copy a mesh, optionally rotate then translate.

    Args:
        mesh: Source mesh.
        translation: Optional XYZ translation in millimeters.
        axis: Optional rotation axis.
        angle_degrees: Rotation angle in degrees.
    """
    result = mesh.copy()
    if axis is not None and abs(angle_degrees) > 1e-6:
        matrix = rotation_matrix(np.deg2rad(angle_degrees), axis)
        result.apply_transform(matrix)
    if translation is not None:
        result.apply_translation(list(translation))
    return result


def _union(parts: list[trimesh.Trimesh]) -> trimesh.Trimesh:
    """Union meshes with a concatenate fallback if boolean fails.

    Args:
        parts: Mesh parts to combine.
    """
    if not parts:
        raise ValueError("No mesh parts to union.")
    combined = parts[0]
    for part in parts[1:]:
        try:
            combined = combined.union(part, engine="manifold")
        except Exception:
            combined = trimesh.util.concatenate([combined, part])
    if isinstance(combined, trimesh.Scene):
        combined = trimesh.util.concatenate(tuple(combined.geometry.values()))
    return combined


def _claw_hand(scale: float = 1.0) -> trimesh.Trimesh:
    """Build a three-fingered claw hand.

    Args:
        scale: Uniform size multiplier.
    """
    palm = _sphere(3.2 * scale, subdivisions=2)
    fingers = []
    finger_offsets = [
        (2.2, 1.4, 2.0),
        (3.0, 0.0, 2.4),
        (2.2, -1.4, 2.0),
    ]
    for index, offset in enumerate(finger_offsets):
        finger = _capsule(0.9 * scale, 7.5 * scale)
        finger = _transform(finger, axis=(1.0, 0.0, 0.0), angle_degrees=70.0)
        tip = _cone(0.95 * scale, 3.2 * scale)
        tip = _transform(
            tip,
            translation=(0.0, 0.0, 4.8 * scale),
            axis=(1.0, 0.0, 0.0),
            angle_degrees=70.0,
        )
        spread = -18.0 + index * 18.0
        finger = _transform(finger, axis=(0.0, 0.0, 1.0), angle_degrees=spread)
        tip = _transform(tip, axis=(0.0, 0.0, 1.0), angle_degrees=spread)
        finger = _transform(finger, translation=tuple(v * scale for v in offset))
        tip = _transform(tip, translation=tuple(v * scale for v in offset))
        fingers.extend([finger, tip])
    return _union([palm, *fingers])


def _skull_trophy(scale: float = 1.0) -> trimesh.Trimesh:
    """Build a small skull trophy for the belt.

    Args:
        scale: Uniform size multiplier.
    """
    cranium = _sphere(1.6 * scale, subdivisions=2)
    jaw = _sphere(1.1 * scale, subdivisions=1)
    jaw = _transform(jaw, translation=(0.0, 0.0, -1.2 * scale))
    return _union([cranium, jaw])


def build_orc_abomination() -> trimesh.Trimesh:
    """Assemble the Orc Abomination proxy mesh in millimeters."""
    parts: list[trimesh.Trimesh] = []

    # Round gaming base
    base = trimesh.creation.cylinder(
        radius=BASE_DIAMETER_MM / 2.0,
        height=BASE_HEIGHT_MM,
        sections=48,
    )
    base.apply_translation([0.0, 0.0, BASE_HEIGHT_MM / 2.0])
    parts.append(base)

    ground = BASE_HEIGHT_MM

    # Legs in lunging stance: front-right planted, rear-left trailing
    left_thigh = _capsule(3.4, 14.0)
    left_thigh = _transform(left_thigh, axis=(1.0, 0.0, 0.0), angle_degrees=35.0)
    left_thigh = _transform(left_thigh, translation=(-4.0, -2.0, ground + 8.0))
    left_shin = _capsule(2.8, 12.0)
    left_shin = _transform(left_shin, axis=(1.0, 0.0, 0.0), angle_degrees=-20.0)
    left_shin = _transform(left_shin, translation=(-5.0, 3.5, ground + 4.5))
    left_foot = _box((7.0, 4.0, 2.2))
    left_foot = _transform(left_foot, translation=(-5.0, 7.0, ground + 1.2))

    right_thigh = _capsule(3.6, 13.0)
    right_thigh = _transform(right_thigh, axis=(1.0, 0.0, 0.0), angle_degrees=-45.0)
    right_thigh = _transform(right_thigh, translation=(4.5, -1.0, ground + 7.5))
    right_shin = _capsule(2.9, 11.0)
    right_shin = _transform(right_shin, axis=(1.0, 0.0, 0.0), angle_degrees=25.0)
    right_shin = _transform(right_shin, translation=(5.0, -6.0, ground + 4.0))
    right_foot = _box((7.5, 4.2, 2.2))
    right_foot = _transform(right_foot, translation=(5.0, -9.0, ground + 1.2))

    # Segmented shin plate on left leg
    shin_plate = _box((4.5, 2.0, 7.0))
    shin_plate = _transform(
        shin_plate,
        translation=(-7.2, 3.0, ground + 5.5),
        axis=(0.0, 1.0, 0.0),
        angle_degrees=12.0,
    )
    rivet_a = _sphere(0.6)
    rivet_a = _transform(rivet_a, translation=(-8.0, 3.0, ground + 7.5))
    rivet_b = _transform(rivet_a, translation=(0.0, 0.0, -2.5))

    parts.extend(
        [
            left_thigh,
            left_shin,
            left_foot,
            right_thigh,
            right_shin,
            right_foot,
            shin_plate,
            rivet_a,
            rivet_b,
        ]
    )

    # Pelvis / loincloth / skull belt
    pelvis = _sphere(6.5, subdivisions=2)
    pelvis.apply_scale([1.15, 0.95, 0.75])
    pelvis = _transform(pelvis, translation=(0.0, -1.0, ground + 14.5))
    loincloth = _box((10.0, 4.0, 8.0))
    loincloth = _transform(loincloth, translation=(0.0, 2.5, ground + 12.0))
    belt = trimesh.creation.torus(major_radius=6.2, minor_radius=1.0, major_sections=32)
    belt = _transform(belt, translation=(0.0, -1.0, ground + 16.0), axis=(1.0, 0.0, 0.0), angle_degrees=90.0)
    skulls = []
    for offset_x in (-3.5, 0.0, 3.5):
        skull = _skull_trophy(1.05)
        skull = _transform(skull, translation=(offset_x, 4.2, ground + 15.5))
        skulls.append(skull)
    parts.extend([pelvis, loincloth, belt, *skulls])

    # Massive torso
    abdomen = _sphere(7.2, subdivisions=2)
    abdomen.apply_scale([1.25, 0.9, 1.1])
    abdomen = _transform(abdomen, translation=(0.0, -1.5, ground + 22.0))
    chest = _sphere(8.0, subdivisions=2)
    chest.apply_scale([1.35, 1.0, 0.95])
    chest = _transform(chest, translation=(0.0, -2.0, ground + 29.0))
    pec_left = _sphere(3.4, subdivisions=2)
    pec_left = _transform(pec_left, translation=(-3.5, 2.5, ground + 30.0))
    pec_right = _sphere(3.4, subdivisions=2)
    pec_right = _transform(pec_right, translation=(3.5, 2.5, ground + 30.0))
    parts.extend([abdomen, chest, pec_left, pec_right])

    # Bone spikes erupting from back / shoulders
    for index, (x, y, z, tilt) in enumerate(
        [
            (-2.0, -6.0, 34.0, -25.0),
            (0.5, -7.0, 36.5, -10.0),
            (3.0, -6.2, 33.5, 20.0),
            (-4.0, -4.5, 31.0, -40.0),
            (4.5, -4.0, 31.5, 35.0),
        ]
    ):
        spike = _cone(1.4, 7.0 + index * 0.4)
        spike = _transform(spike, axis=(1.0, 0.0, 0.0), angle_degrees=tilt)
        spike = _transform(spike, translation=(x, y, ground + z))
        parts.append(spike)

    # Spiked pauldron on viewer's-left / character right shoulder
    pauldron = _sphere(4.8, subdivisions=2)
    pauldron.apply_scale([1.2, 0.85, 0.7])
    pauldron = _transform(pauldron, translation=(8.0, -1.0, ground + 33.5))
    for spike_angle in (-35.0, 0.0, 35.0):
        pauldron_spike = _cone(1.1, 5.5)
        pauldron_spike = _transform(
            pauldron_spike,
            translation=(10.5, -1.0, ground + 36.0),
            axis=(0.0, 1.0, 0.0),
            angle_degrees=spike_angle,
        )
        parts.append(pauldron_spike)
    parts.append(pauldron)

    # Raised left arm (massive claw) — matches reference raised strike
    left_upper = _capsule(4.2, 16.0)
    left_upper = _transform(left_upper, axis=(0.0, 1.0, 0.0), angle_degrees=-35.0)
    left_upper = _transform(left_upper, axis=(1.0, 0.0, 0.0), angle_degrees=-110.0)
    left_upper = _transform(left_upper, translation=(-8.0, 1.0, ground + 38.0))
    left_fore = _capsule(3.6, 14.0)
    left_fore = _transform(left_fore, axis=(0.0, 1.0, 0.0), angle_degrees=-15.0)
    left_fore = _transform(left_fore, axis=(1.0, 0.0, 0.0), angle_degrees=-35.0)
    left_fore = _transform(left_fore, translation=(-12.0, 4.0, ground + 48.0))
    elbow_spike = _cone(1.3, 6.0)
    elbow_spike = _transform(elbow_spike, translation=(-10.5, -1.5, ground + 42.0))
    forearm_band = trimesh.creation.torus(major_radius=3.8, minor_radius=0.7, major_sections=24)
    forearm_band = _transform(
        forearm_band,
        translation=(-12.0, 4.0, ground + 46.0),
        axis=(1.0, 0.0, 0.0),
        angle_degrees=55.0,
    )
    left_claw = _claw_hand(1.35)
    left_claw = _transform(left_claw, axis=(0.0, 0.0, 1.0), angle_degrees=90.0)
    left_claw = _transform(left_claw, axis=(1.0, 0.0, 0.0), angle_degrees=-20.0)
    left_claw = _transform(left_claw, translation=(-13.5, 8.5, ground + 54.0))
    parts.extend([left_upper, left_fore, elbow_spike, forearm_band, left_claw])

    # Lowered / reaching right arm
    right_upper = _capsule(3.5, 14.0)
    right_upper = _transform(right_upper, axis=(0.0, 1.0, 0.0), angle_degrees=25.0)
    right_upper = _transform(right_upper, axis=(1.0, 0.0, 0.0), angle_degrees=55.0)
    right_upper = _transform(right_upper, translation=(8.5, 2.0, ground + 30.0))
    right_fore = _capsule(3.0, 12.0)
    right_fore = _transform(right_fore, axis=(1.0, 0.0, 0.0), angle_degrees=75.0)
    right_fore = _transform(right_fore, translation=(10.0, 7.0, ground + 22.0))
    right_claw = _claw_hand(1.05)
    right_claw = _transform(right_claw, axis=(1.0, 0.0, 0.0), angle_degrees=90.0)
    right_claw = _transform(right_claw, translation=(10.5, 12.0, ground + 14.5))
    parts.extend([right_upper, right_fore, right_claw])

    # Small head with horned / masked face
    neck = _capsule(2.4, 5.0)
    neck = _transform(neck, translation=(-1.0, 1.0, ground + 36.0))
    head = _sphere(3.6, subdivisions=2)
    head.apply_scale([1.05, 1.15, 1.1])
    head = _transform(head, translation=(-1.2, 2.5, ground + 40.0))
    mask = _box((5.5, 2.2, 4.0))
    mask = _transform(mask, translation=(-1.2, 4.4, ground + 40.0))
    horn = _cone(1.5, 7.5)
    horn = _transform(horn, translation=(-1.2, 2.0, ground + 44.5), axis=(1.0, 0.0, 0.0), angle_degrees=-15.0)
    jaw = _sphere(2.2, subdivisions=2)
    jaw.apply_scale([1.3, 1.0, 0.7])
    jaw = _transform(jaw, translation=(-1.2, 3.8, ground + 37.5))
    parts.extend([neck, head, mask, horn, jaw])

    figure = _union(parts)
    figure.remove_unreferenced_vertices()
    figure.merge_vertices()
    if not figure.is_watertight:
        figure.fill_holes()
    figure.fix_normals()

    # Normalize height while keeping base on Z=0
    bounds = figure.bounds
    current_height = bounds[1][2] - bounds[0][2]
    if current_height > 1e-6:
        scale = TARGET_FIGURE_HEIGHT_MM / current_height
        figure.apply_scale(scale)
    figure.apply_translation([0.0, 0.0, -figure.bounds[0][2]])
    return _make_watertight(figure)


def _make_watertight(mesh: trimesh.Trimesh, pitch_mm: float = 0.55) -> trimesh.Trimesh:
    """Voxel-remesh into a single watertight solid suitable for printing.

    Args:
        mesh: Source mesh that may contain overlapping parts.
        pitch_mm: Voxel pitch in millimeters (lower = more detail).
    """
    voxels = mesh.voxelized(pitch=pitch_mm)
    solid = voxels.marching_cubes
    solid.apply_translation(-solid.bounds[0])
    height = solid.extents[2]
    if height > 1e-6:
        solid.apply_scale(TARGET_FIGURE_HEIGHT_MM / height)
        solid.apply_translation(-solid.bounds[0])
    solid.fix_normals()
    return solid


def main() -> None:
    """Generate and write the STL into `_shared-stls/` with a role symlink."""
    import hashlib
    import os

    repo_root = Path(__file__).resolve().parents[1]
    role_path = repo_root / OUTPUT_RELATIVE_PATH
    role_path.parent.mkdir(parents=True, exist_ok=True)
    shared_dir = repo_root / "_shared-stls"
    shared_dir.mkdir(parents=True, exist_ok=True)

    mesh = build_orc_abomination()
    temporary_path = shared_dir / "04-orc-abomination-proxy-generated.tmp.stl"
    mesh.export(temporary_path)
    digest = hashlib.sha256(temporary_path.read_bytes()).hexdigest()[:12]
    shared_path = shared_dir / f"{digest}-04-orc-abomination-proxy-generated.stl"
    temporary_path.replace(shared_path)

    if role_path.exists() or role_path.is_symlink():
        role_path.unlink()
    os.symlink(
        os.path.relpath(shared_path, start=role_path.parent),
        role_path,
    )

    bounds = mesh.bounds
    size = bounds[1] - bounds[0]
    print(f"Wrote {shared_path}")
    print(f"Linked {role_path}")
    print(
        "Bounds mm: "
        f"X={size[0]:.1f} Y={size[1]:.1f} Z={size[2]:.1f} "
        f"faces={len(mesh.faces)} watertight={mesh.is_watertight}"
    )


if __name__ == "__main__":
    main()
