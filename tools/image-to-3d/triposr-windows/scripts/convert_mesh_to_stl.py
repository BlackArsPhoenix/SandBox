#!/usr/bin/env python3
"""Convert an image-generated mesh into a printable STL."""

from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np
import trimesh


# region Constants

MINIMUM_MEASURABLE_SIZE = 0.000001
MILLIMETERS_UNIT_NAME = "millimeters"

# endregion


def parse_arguments() -> argparse.Namespace:
    """Read command-line conversion settings.

    Returns:
        Parsed file paths, scale, and optional remeshing resolution.
    """
    parser = argparse.ArgumentParser(
        description="Convert OBJ or GLB geometry to a checked STL mesh."
    )
    parser.add_argument(
        "--input",
        required=True,
        type=Path,
        help="Source OBJ or GLB path.",
    )
    parser.add_argument(
        "--output",
        required=True,
        type=Path,
        help="Destination STL path.",
    )
    parser.add_argument(
        "--target-height-millimeters",
        default=0.0,
        type=float,
        help="Target model height; zero preserves source coordinates.",
    )
    parser.add_argument(
        "--voxel-pitch-millimeters",
        default=0.0,
        type=float,
        help="Voxel size for watertight remeshing; zero disables remeshing.",
    )
    return parser.parse_args()


def load_combined_mesh(input_path: Path) -> trimesh.Trimesh:
    """Load every transformed geometry from a model file.

    Args:
        input_path: Source OBJ or GLB path.

    Returns:
        A single triangular mesh with scene transforms applied.
    """
    loaded_model = trimesh.load(input_path, force="scene")
    if isinstance(loaded_model, trimesh.Trimesh):
        combined_mesh = loaded_model
    elif hasattr(loaded_model, "to_geometry"):
        combined_mesh = loaded_model.to_geometry()
    else:
        combined_mesh = loaded_model.dump(concatenate=True)

    if not isinstance(combined_mesh, trimesh.Trimesh):
        raise TypeError("Source file did not contain convertible mesh geometry.")
    if len(combined_mesh.faces) == 0:
        raise ValueError("Source mesh contains no triangular faces.")

    combined_mesh.process(validate=True)
    combined_mesh.remove_unreferenced_vertices()
    combined_mesh.merge_vertices()
    trimesh.repair.fix_normals(combined_mesh, multibody=True)
    trimesh.repair.fill_holes(combined_mesh)
    return combined_mesh


def scale_to_height(mesh: trimesh.Trimesh, target_height_millimeters: float) -> None:
    """Apply an optional physical height.

    Args:
        mesh: Geometry modified in place.
        target_height_millimeters: Required height or zero to retain coordinates.
    """
    if target_height_millimeters <= 0.0:
        return

    current_height = float(mesh.extents[2])
    if current_height < MINIMUM_MEASURABLE_SIZE:
        raise ValueError("Source mesh has no measurable height.")
    mesh.apply_scale(target_height_millimeters / current_height)
    mesh.units = MILLIMETERS_UNIT_NAME


def move_to_print_origin(mesh: trimesh.Trimesh) -> None:
    """Center geometry over the build plate.

    Args:
        mesh: Geometry modified in place.
    """
    bounds = mesh.bounds
    horizontal_center = (bounds[0][:2] + bounds[1][:2]) / 2.0
    mesh.apply_translation(
        np.asarray(
            [
                -horizontal_center[0],
                -horizontal_center[1],
                -bounds[0][2],
            ]
        )
    )


def create_watertight_voxel_mesh(
    mesh: trimesh.Trimesh,
    voxel_pitch_millimeters: float,
) -> trimesh.Trimesh:
    """Reconstruct geometry as a filled watertight surface.

    Args:
        mesh: Scaled source geometry.
        voxel_pitch_millimeters: Edge length of one cubic sample.

    Returns:
        A reconstructed triangular mesh.
    """
    voxel_grid = mesh.voxelized(pitch=voxel_pitch_millimeters).fill()
    reconstructed_mesh = voxel_grid.marching_cubes
    reconstructed_mesh.apply_scale(voxel_pitch_millimeters)
    reconstructed_mesh.process(validate=True)
    reconstructed_mesh.remove_unreferenced_vertices()
    reconstructed_mesh.merge_vertices()
    trimesh.repair.fix_normals(reconstructed_mesh, multibody=True)
    move_to_print_origin(reconstructed_mesh)
    return reconstructed_mesh


def validate_settings(arguments: argparse.Namespace) -> None:
    """Reject invalid conversion settings.

    Args:
        arguments: Parsed command-line values.
    """
    if arguments.target_height_millimeters < 0.0:
        raise ValueError("Target height cannot be negative.")
    if arguments.voxel_pitch_millimeters < 0.0:
        raise ValueError("Voxel pitch cannot be negative.")
    if not arguments.input.is_file():
        raise FileNotFoundError(f"Source model does not exist: {arguments.input}")
    if arguments.input.resolve() == arguments.output.resolve():
        raise ValueError("Input and output paths must be different.")


def main() -> None:
    """Convert, validate, and report the resulting STL."""
    arguments = parse_arguments()
    validate_settings(arguments)

    mesh = load_combined_mesh(arguments.input)
    scale_to_height(mesh, arguments.target_height_millimeters)
    move_to_print_origin(mesh)

    if arguments.voxel_pitch_millimeters > 0.0:
        mesh = create_watertight_voxel_mesh(
            mesh,
            arguments.voxel_pitch_millimeters,
        )

    arguments.output.parent.mkdir(parents=True, exist_ok=True)
    mesh.export(arguments.output, file_type="stl")

    connected_components = mesh.split(only_watertight=False)
    print(f"Wrote: {arguments.output}")
    print(
        "Bounds: "
        f"X={mesh.extents[0]:.3f} "
        f"Y={mesh.extents[1]:.3f} "
        f"Z={mesh.extents[2]:.3f}"
    )
    print(f"Faces: {len(mesh.faces)}")
    print(f"Watertight: {mesh.is_watertight}")
    print(f"Connected components: {len(connected_components)}")

    if not mesh.is_watertight:
        print(
            "Warning: the STL still has open boundaries. "
            "Repeat conversion with a positive voxel pitch."
        )


if __name__ == "__main__":
    main()
