import os
import re
import glob
import argparse
import numpy as np
import cv2

# ============================================================
# Cube-z reader
# ============================================================


def infer_cube_shape_from_filename(filepath):
    """
    Infer OCT volume shape from the scan size in the filename.

    Returns:
        tuple: (num_bscans, height, width)
    """
    filename = os.path.basename(filepath)

    match = re.search(r"((\d+)mmx(\d+)mm)", filename, re.IGNORECASE)
    if match is None:
        raise ValueError(f"Cannot infer scan size from filename:\n{filename}")

    width_mm = match.group(2)
    height_mm = match.group(3)

    if width_mm == height_mm == "3":
        return (300, 1536, 300)

    if width_mm == height_mm and width_mm in {"6", "9", "12"}:
        return (500, 1536, 500)

    if width_mm == "15" and height_mm == "9":
        return (834, 1536, 500)

    raise ValueError(
        f"Unknown cube-z scan size: {width_mm}mm x {height_mm}mm\n" f"File: {filename}"
    )


# Known raw cube sizes.
# Key   = number of uint8 values in the file
# Value = (B-scans, height, width)
KNOWN_CUBE_SHAPES = {
    67108864: (128, 1024, 512),
    125440000: (350, 1024, 350),
    61465600: (350, 686, 256),
    384000000: (500, 1536, 500),
}


def read_cube_z(filepath, shape=None, flip=True):
    """
    Read a raw OCT cube_z binary file.

    The cube-z format is uint8 and stored as:

        (B-scan, height, width)

    The original pipeline flips the volume vertically and horizontally.
    This behavior is preserved by default.

    Args:
        filepath:
            Path to cube_z .img file.

        shape:
            Optional explicit shape:
            (num_bscans, height, width)

        flip:
            Apply the same orientation correction as the original code.

    Returns:
        np.ndarray:
            OCT volume with shape (N, H, W), dtype uint8.
    """

    raw = np.fromfile(filepath, dtype=np.uint8)

    n_values = raw.size

    if shape is None:
        if n_values in KNOWN_CUBE_SHAPES:
            shape = KNOWN_CUBE_SHAPES[n_values]
        else:
            shape = infer_cube_shape_from_filename(filepath)

    expected_values = int(np.prod(shape))

    if n_values != expected_values:
        raise ValueError(
            f"Unexpected cube size for:\n{filepath}\n"
            f"  Raw values:      {n_values:,}\n"
            f"  Expected values: {expected_values:,}\n"
            f"  Expected shape:  {shape}"
        )

    volume = raw.reshape(shape)

    if flip:
        # Preserve the orientation used by the original pipeline.
        volume = np.flip(volume, axis=2)
        volume = np.flip(volume, axis=1)

    return volume


# ============================================================
# B-scan access
# ============================================================


def get_bscan(volume, index):
    """
    Return one B-scan from an already loaded cube.

    Args:
        volume: [N, H, W]
        index: B-scan index

    Returns:
        [H, W] uint8 image
    """
    if index < 0 or index >= volume.shape[0]:
        raise IndexError(
            f"B-scan index {index} is outside " f"[0, {volume.shape[0] - 1}]"
        )

    return volume[index]


# ============================================================
# Save B-scans for visualization/debugging
# ============================================================


def save_bscans(volume, output_dir, prefix="bscan"):
    """
    Save an OCT volume as individual PNG B-scans.

    This is only for visualization/debugging.
    The change-analysis pipeline does NOT need to create PNGs.
    """

    os.makedirs(output_dir, exist_ok=True)

    for idx in range(volume.shape[0]):
        filepath = os.path.join(output_dir, f"{prefix}_{idx:03d}.png")

        cv2.imwrite(filepath, volume[idx])


# ============================================================
# Find cube-z files
# ============================================================


def find_cube_z_files(root_dir, pattern="*cube_z*.img"):
    """
    Recursively find cube-z files.

    Returns:
        sorted list of file paths
    """

    files = sorted(glob.glob(os.path.join(root_dir, "**", pattern), recursive=True))

    return files


# ============================================================
# Main
# ============================================================


def main():

    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--input", required=True, help="Root directory containing cube_z files"
    )

    parser.add_argument(
        "--save_bscans",
        action="store_true",
        help="Save individual B-scans for inspection",
    )

    parser.add_argument("--output", default=None, help="Output directory for B-scans")

    args = parser.parse_args()

    cube_files = find_cube_z_files(args.input)

    print(f"Found {len(cube_files)} cube-z files")

    for cube_path in cube_files:

        print("\n" + "=" * 80)
        print(cube_path)

        cube = read_cube_z(cube_path)

        print(f"Cube shape: {cube.shape}")
        print(f"dtype:      {cube.dtype}")
        print(f"range:      [{cube.min()}, {cube.max()}]")

        if args.save_bscans:

            if args.output is None:
                raise ValueError("--output is required when --save_bscans is used")

            cube_name = os.path.splitext(os.path.basename(cube_path))[0]

            output_dir = os.path.join(args.output, cube_name)

            save_bscans(cube, output_dir, prefix="bscan")


if __name__ == "__main__":
    main()
