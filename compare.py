#!/usr/bin/env python3
"""
Script to compare file paths and contents between two folders.
Compares contents for .dcm (DICOM), .tsv, and .csv files, ignores .DS_Store files.
"""

import os
from typing import Dict, Set, List, Tuple
import pydicom
import csv
import sys

# Add year_3 directory to path
repo_path = os.path.dirname(os.path.abspath(__file__))
year_3_path = os.path.join(repo_path, "year_3")
sys.path.append(year_3_path)
import organize_utils


def normalize_path(path: str) -> str:
    """
    Normalize a file path for comparison.
    - Normalizes path separators to forward slashes
    - Converts to lowercase (for case-insensitive comparison)
    - Normalizes relative path components

    Args:
        path: File path to normalize

    Returns:
        Normalized path string
    """
    # Normalize path separators and resolve relative components
    normalized = os.path.normpath(path).replace(os.sep, "/")
    # Convert to lowercase for case-insensitive comparison
    normalized = normalized.lower()
    return normalized


def looks_like_filepath(value: str) -> bool:
    """
    Check if a string value looks like a file path.

    Args:
        value: String value to check

    Returns:
        True if the value appears to be a file path
    """
    if not value or not isinstance(value, str):
        return False
    # Check for path separators or common path patterns
    return (
        "/" in value
        or "\\" in value
        or value.startswith("./")
        or value.startswith("../")
    )


def normalize_tsv_value(value: str) -> str:
    """
    Normalize a TSV cell value, handling file paths if present.

    Args:
        value: Cell value from TSV

    Returns:
        Normalized value (file paths are normalized, other values unchanged)
    """
    if not value:
        return value
    if looks_like_filepath(value):
        return normalize_path(value)
    return value


def get_all_files(root_dir: str, ignore_patterns: Set[str] = None) -> Dict[str, str]:
    """
    Recursively get all files in a directory, returning relative paths.

    Args:
        root_dir: Root directory to scan
        ignore_patterns: Set of file names/patterns to ignore (e.g., {'.DS_Store'})

    Returns:
        Dictionary mapping relative paths to absolute paths
    """
    if ignore_patterns is None:
        ignore_patterns = {".DS_Store"}

    files = {}

    for root, dirs, filenames in os.walk(root_dir):
        # Skip hidden directories
        dirs[:] = [d for d in dirs if not d.startswith(".")]

        for filename in filenames:
            # Skip ignored files
            if filename in ignore_patterns:
                continue

            abs_path = os.path.join(root, filename)
            rel_path = os.path.relpath(abs_path, root_dir)
            # Normalize the relative path for comparison
            normalized_path = normalize_path(rel_path)
            files[normalized_path] = abs_path

    return files


def compare_dicom_files(file1: str, file2: str) -> Tuple[bool, List[str]]:
    """
    Compare two DICOM files by comparing their metadata.

    Args:
        file1: Path to first DICOM file
        file2: Path to second DICOM file

    Returns:
        Tuple of (are_equal, list_of_differences)
    """
    differences = []

    try:
        ds1 = pydicom.dcmread(file1)
        ds2 = pydicom.dcmread(file2)

        # Get all tags from both files
        tags1 = set(ds1.keys())
        tags2 = set(ds2.keys())

        # Check for tags only in file1
        only_in_file1 = tags1 - tags2
        if only_in_file1:
            differences.append(f"Tags only in {file1}: {sorted(only_in_file1)}")

        # Check for tags only in file2
        only_in_file2 = tags2 - tags1
        if only_in_file2:
            differences.append(f"Tags only in {file2}: {sorted(only_in_file2)}")

        # Compare common tags
        common_tags = tags1 & tags2
        for tag in sorted(common_tags):
            try:
                val1 = ds1[tag].value
                val2 = ds2[tag].value

                # Handle sequences and complex types
                if isinstance(val1, (list, tuple)) and isinstance(val2, (list, tuple)):
                    if len(val1) != len(val2):
                        differences.append(
                            f"Tag {tag}: different lengths ({len(val1)} vs {len(val2)})"
                        )
                    else:
                        for i, (v1, v2) in enumerate(zip(val1, val2)):
                            if v1 != v2:
                                differences.append(f"Tag {tag}[{i}]: {v1} != {v2}")
                elif val1 != val2:
                    # Skip pixel data comparison (too large and may differ due to compression)
                    if tag.keyword == "PixelData":
                        continue
                    differences.append(f"Tag {tag}: {val1} != {val2}")
            except Exception as e:
                differences.append(f"Error comparing tag {tag}: {e}")

        return len(differences) == 0, differences

    except Exception as e:
        return False, [f"Error reading DICOM files: {e}"]


def compare_tsv_files(file1: str, file2: str) -> Tuple[bool, List[str]]:
    """
    Compare two TSV files by reading them into dictionaries and comparing.

    Args:
        file1: Path to first TSV file
        file2: Path to second TSV file

    Returns:
        Tuple of (are_equal, list_of_differences)
    """
    differences = []

    try:
        # Read TSV files into dictionaries
        dict1 = []
        dict2 = []

        with open(file1, "r", encoding="utf-8") as f1:
            reader1 = csv.DictReader(f1, delimiter="\t")
            dict1 = [row for row in reader1]

        with open(file2, "r", encoding="utf-8") as f2:
            reader2 = csv.DictReader(f2, delimiter="\t")
            dict2 = [row for row in reader2]

        # Normalize file paths in the data
        for row in dict1:
            for key in row:
                row[key] = normalize_tsv_value(row[key])

        for row in dict2:
            for key in row:
                row[key] = normalize_tsv_value(row[key])

        # Compare number of rows
        if len(dict1) != len(dict2):
            differences.append(
                f"Different number of rows: {len(dict1)} vs {len(dict2)}"
            )

        # Compare columns (keys from first row)
        if dict1 and dict2:
            keys1 = set(dict1[0].keys())
            keys2 = set(dict2[0].keys())

            if keys1 != keys2:
                only_in_1 = keys1 - keys2
                only_in_2 = keys2 - keys1
                if only_in_1:
                    differences.append(f"Columns only in file1: {sorted(only_in_1)}")
                if only_in_2:
                    differences.append(f"Columns only in file2: {sorted(only_in_2)}")

            # Sort rows by all columns to ensure consistent ordering for comparison
            # This handles cases where rows are in different orders
            common_keys = sorted(keys1 & keys2)

            def sort_key(row):
                """Create a sort key from all column values in the row."""
                return tuple(row.get(key, "") for key in common_keys)

            # Sort both lists using the same key function
            dict1_sorted = sorted(dict1, key=sort_key)
            dict2_sorted = sorted(dict2, key=sort_key)

            # Compare data row by row (now both are sorted)
            min_rows = min(len(dict1_sorted), len(dict2_sorted))

            for i in range(min_rows):
                row1 = dict1_sorted[i]
                row2 = dict2_sorted[i]

                for key in common_keys:
                    val1 = row1.get(key, "")
                    val2 = row2.get(key, "")
                    if val1 != val2:
                        differences.append(
                            f"Row {i + 1} (after sorting), column '{key}': '{val1}' != '{val2}'"
                        )
                        # Limit output to first 10 differences
                        if len(differences) >= 10:
                            return False, differences

            # Check for extra rows
            if len(dict1_sorted) > len(dict2_sorted):
                differences.append(
                    f"File1 has {len(dict1_sorted) - len(dict2_sorted)} extra rows"
                )
            elif len(dict2_sorted) > len(dict1_sorted):
                differences.append(
                    f"File2 has {len(dict2_sorted) - len(dict1_sorted)} extra rows"
                )
        elif dict1 and not dict2:
            differences.append("File1 has data but file2 is empty")
        elif dict2 and not dict1:
            differences.append("File2 has data but file1 is empty")
        elif not dict1 and not dict2:
            # Both empty - they're equal
            pass

        return len(differences) == 0, differences

    except Exception as e:
        return False, [f"Error reading TSV files: {e}"]


def compare_csv_files(file1: str, file2: str) -> Tuple[bool, List[str]]:
    """
    Compare two CSV files by reading them into dictionaries and comparing.

    Args:
        file1: Path to first CSV file
        file2: Path to second CSV file

    Returns:
        Tuple of (are_equal, list_of_differences)
    """
    differences = []

    try:
        with open(file1, "r", encoding="utf-8") as f1:
            reader1 = csv.DictReader(f1, delimiter=",")
            dict1 = [row for row in reader1]

        with open(file2, "r", encoding="utf-8") as f2:
            reader2 = csv.DictReader(f2, delimiter=",")
            dict2 = [row for row in reader2]

        # Normalize file paths in the data
        for row in dict1:
            for key in row:
                row[key] = normalize_tsv_value(row[key])

        for row in dict2:
            for key in row:
                row[key] = normalize_tsv_value(row[key])

        # Compare number of rows
        if len(dict1) != len(dict2):
            differences.append(
                f"Different number of rows: {len(dict1)} vs {len(dict2)}"
            )

        # Compare columns (keys from first row)
        if dict1 and dict2:
            keys1 = set(dict1[0].keys())
            keys2 = set(dict2[0].keys())

            if keys1 != keys2:
                only_in_1 = keys1 - keys2
                only_in_2 = keys2 - keys1
                if only_in_1:
                    differences.append(f"Columns only in file1: {sorted(only_in_1)}")
                if only_in_2:
                    differences.append(f"Columns only in file2: {sorted(only_in_2)}")

            common_keys = sorted(keys1 & keys2)

            def sort_key(row):
                """Create a sort key from all column values in the row."""
                return tuple(row.get(key, "") for key in common_keys)

            dict1_sorted = sorted(dict1, key=sort_key)
            dict2_sorted = sorted(dict2, key=sort_key)

            min_rows = min(len(dict1_sorted), len(dict2_sorted))

            for i in range(min_rows):
                row1 = dict1_sorted[i]
                row2 = dict2_sorted[i]

                for key in common_keys:
                    val1 = row1.get(key, "")
                    val2 = row2.get(key, "")
                    if val1 != val2:
                        differences.append(
                            f"Row {i + 1} (after sorting), column '{key}': '{val1}' != '{val2}'"
                        )
                        if len(differences) >= 10:
                            return False, differences

            if len(dict1_sorted) > len(dict2_sorted):
                differences.append(
                    f"File1 has {len(dict1_sorted) - len(dict2_sorted)} extra rows"
                )
            elif len(dict2_sorted) > len(dict1_sorted):
                differences.append(
                    f"File2 has {len(dict2_sorted) - len(dict1_sorted)} extra rows"
                )
        elif dict1 and not dict2:
            differences.append("File1 has data but file2 is empty")
        elif dict2 and not dict1:
            differences.append("File2 has data but file1 is empty")

        return len(differences) == 0, differences

    except Exception as e:
        return False, [f"Error reading CSV files: {e}"]


def compare_folders(folder1: str, folder2: str, verbose: bool = False) -> None:
    """
    Compare two folders: file paths and contents (for .dcm, .tsv, and .csv files).

    Args:
        folder1: Path to first folder
        folder2: Path to second folder
        verbose: If True, print detailed information
    """
    if not os.path.exists(folder1):
        print(f"Error: Folder 1 does not exist: {folder1}")
        return

    if not os.path.exists(folder2):
        print(f"Error: Folder 2 does not exist: {folder2}")
        return

    print(f"Scanning folder 1: {folder1}")
    files1 = get_all_files(folder1)
    print(f"Found {len(files1)} files in folder 1")

    print(f"Scanning folder 2: {folder2}")
    files2 = get_all_files(folder2)
    print(f"Found {len(files2)} files in folder 2")
    print()

    # Get sets of relative paths
    paths1 = set(files1.keys())
    paths2 = set(files2.keys())

    # Find differences in file paths
    only_in_folder1 = paths1 - paths2
    only_in_folder2 = paths2 - paths1
    common_paths = paths1 & paths2

    print("=" * 80)
    print("FILE PATH COMPARISON")
    print("=" * 80)
    print(f"Files only in folder 1: {len(only_in_folder1)}")
    print(f"Files only in folder 2: {len(only_in_folder2)}")
    print(f"Files in both folders: {len(common_paths)}")
    print()

    if only_in_folder1:
        print(f"\nFiles only in folder 1 ({len(only_in_folder1)}):")
        for path in sorted(only_in_folder1)[:20]:  # Show first 20
            print(f"  {path}")
        if len(only_in_folder1) > 20:
            print(f"  ... and {len(only_in_folder1) - 20} more")

    if only_in_folder2:
        print(f"\nFiles only in folder 2 ({len(only_in_folder2)}):")
        for path in sorted(only_in_folder2)[:20]:  # Show first 20
            print(f"  {path}")
        if len(only_in_folder2) > 20:
            print(f"  ... and {len(only_in_folder2) - 20} more")

    # Compare contents for common files
    print("\n" + "=" * 80)
    print("CONTENT COMPARISON (for .dcm, .tsv, and .csv files)")
    print("=" * 80)

    dcm_files = [p for p in common_paths if p.lower().endswith(".dcm")]
    tsv_files = [p for p in common_paths if p.lower().endswith(".tsv")]
    csv_files = [p for p in common_paths if p.lower().endswith(".csv")]

    print(f"\nComparing {len(dcm_files)} DICOM files...")
    dcm_differences = []

    for rel_path in sorted(dcm_files):
        file1 = files1[rel_path]
        file2 = files2[rel_path]

        # Use organize_utils.diff_dicom_structures (which uses _diff_ds) to compare structures
        diffs = organize_utils.diff_dicom_structures(file1, file2)

        if diffs:
            dcm_differences.append((rel_path, diffs))
            if verbose:
                print(f"\n  Differences in {rel_path}:")
                for diff in diffs:
                    print(f"    {diff}")

    print(f"  DICOM files with differences: {len(dcm_differences)}")
    if dcm_differences and not verbose:
        print("  (Use --verbose to see details)")
        for rel_path, _ in dcm_differences[:10]:  # Show first 10
            print(f"    {rel_path}")
        if len(dcm_differences) > 10:
            print(f"    ... and {len(dcm_differences) - 10} more")

    print(f"\nComparing {len(tsv_files)} TSV files...")
    tsv_differences = []
    for rel_path in sorted(tsv_files):
        file1 = files1[rel_path]
        file2 = files2[rel_path]
        are_equal, diffs = compare_tsv_files(file1, file2)
        if not are_equal:
            tsv_differences.append((rel_path, diffs))
            if verbose:
                print(f"\n  Differences in {rel_path}:")
                for diff in diffs:
                    print(f"    {diff}")

    print(f"  TSV files with differences: {len(tsv_differences)}")
    if tsv_differences and not verbose:
        print("  (Use --verbose to see details)")
        for rel_path, _ in tsv_differences[:10]:  # Show first 10
            print(f"    {rel_path}")
        if len(tsv_differences) > 10:
            print(f"    ... and {len(tsv_differences) - 10} more")

    print(f"\nComparing {len(csv_files)} CSV files...")
    csv_differences = []
    for rel_path in sorted(csv_files):
        file1 = files1[rel_path]
        file2 = files2[rel_path]
        are_equal, diffs = compare_csv_files(file1, file2)
        if not are_equal:
            csv_differences.append((rel_path, diffs))
            if verbose:
                print(f"\n  Differences in {rel_path}:")
                for diff in diffs:
                    print(f"    {diff}")

    print(f"  CSV files with differences: {len(csv_differences)}")
    if csv_differences and not verbose:
        print("  (Use --verbose to see details)")
        for rel_path, _ in csv_differences[:10]:  # Show first 10
            print(f"    {rel_path}")
        if len(csv_differences) > 10:
            print(f"    ... and {len(csv_differences) - 10} more")

    # Summary
    print("\n" + "=" * 80)
    print("SUMMARY")
    print("=" * 80)
    total_differences = (
        len(only_in_folder1)
        + len(only_in_folder2)
        + len(dcm_differences)
        + len(tsv_differences)
        + len(csv_differences)
    )
    if total_differences == 0:
        print("✓ Folders are identical!")
    else:
        print(f"x Found {total_differences} differences:")
        print(f"  - {len(only_in_folder1)} files only in folder 1")
        print(f"  - {len(only_in_folder2)} files only in folder 2")
        print(f"  - {len(dcm_differences)} DICOM files with content differences")
        print(f"  - {len(tsv_differences)} TSV files with content differences")
        print(f"  - {len(csv_differences)} CSV files with content differences")


def main():
    # home_folder = os.path.expanduser("~")
    base_folder1 = r"C:\\Users\\sanjay\\Downloads\\sample_data\\cirrus\\input"
    # base_folder1 = os.path.join(home_folder, "Downloads", "sample_data")
    base_folder2 = r"D:\\sample_data\\cirrus\\input"
    # base_folder2 = os.path.join(home_folder, "Downloads", "2024release", "sample_data")

    folders = [
        # ["spectralis", "final"],
        # ["cirrus", "final"],
        # ["flio", "final"],
        # ["optomed", "final"],
        # ["eidon", "final"],
        # ["maestro2", "final"],
        # ["triton", "final"],
    ]

    print("base_folder1", base_folder1)
    print("base_folder2", base_folder2)
    compare_folders(base_folder1, base_folder2, verbose=True)

    for folder in folders:
        folder1 = os.path.join(base_folder1, *folder)
        folder2 = os.path.join(base_folder2, *folder)
        print("folder1", folder1)
        print("folder2", folder2)
        compare_folders(folder1, folder2, verbose=True)
        print("=" * 80)


if __name__ == "__main__":
    main()
