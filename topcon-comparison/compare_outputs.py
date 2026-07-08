"""
Compare DICOM outputs from two versions of DicomOctExport.

Checks for each matching folder pair:
  - Same number of .dcm files
  - Same DICOM tags (excluding per-run UIDs and timestamps)

Usage:
    python compare_outputs.py <private_root> <public_root>

Example:
    python compare_outputs.py D:\\eyeact\\pre\\maestro2_private D:\\eyeact\\pre\\maestro2_public
"""

import sys
import io
import argparse
import contextlib
from datetime import datetime
from pathlib import Path
import pydicom

# Tags that are expected to differ between independent export runs
SKIP_TAGS = {
    (0x0008, 0x0018),  # SOPInstanceUID
    (0x0020, 0x000D),  # StudyInstanceUID
    (0x0020, 0x000E),  # SeriesInstanceUID
    (0x0008, 0x0012),  # InstanceCreationDate
    (0x0008, 0x0013),  # InstanceCreationTime
    (0x0008, 0x002A),  # AcquisitionDateTime
}


def compare_dicom_files(
    file_a: Path, file_b: Path, label_a: str, label_b: str
) -> list[str]:
    try:
        ds_a = pydicom.dcmread(str(file_a), stop_before_pixels=True)
    except Exception as e:
        return [f"  Could not read {label_a} file: {e}"]
    try:
        ds_b = pydicom.dcmread(str(file_b), stop_before_pixels=True)
    except Exception as e:
        return [f"  Could not read {label_b} file: {e}"]

    diffs = []
    all_tags = set(ds_a.keys()) | set(ds_b.keys())

    for tag in sorted(all_tags):
        if (tag.group, tag.element) in SKIP_TAGS:
            continue

        in_a = tag in ds_a
        in_b = tag in ds_b

        if in_a != in_b:
            elem = ds_a[tag] if in_a else ds_b[tag]
            name = elem.keyword or str(tag)
            only_in = label_a if in_a else label_b
            diffs.append(f"    Tag {tag} ({name}): only in {only_in}")
        else:
            val_a = ds_a[tag].value
            val_b = ds_b[tag].value
            if val_a != val_b:
                name = ds_a[tag].keyword or str(tag)
                diffs.extend(
                    (
                        f"    Tag {tag} ({name}):",
                        f"      {label_a}: {val_a!r}",
                        f"      {label_b}: {val_b!r}",
                    )
                )
    return diffs


def compare_folders(root_a: Path, root_b: Path, label_a: str, label_b: str):
    folders_a = {p.relative_to(root_a) for p in root_a.rglob("*") if p.is_dir()}
    folders_b = {p.relative_to(root_b) for p in root_b.rglob("*") if p.is_dir()}

    only_in_a = folders_a - folders_b
    only_in_b = folders_b - folders_a
    common = folders_a & folders_b

    if only_in_a:
        print(f"\nFolders only in {label_a}:")
        for f in sorted(only_in_a):
            print(f"  {f}")

    if only_in_b:
        print(f"\nFolders only in {label_b}:")
        for f in sorted(only_in_b):
            print(f"  {f}")

    print(f"\nComparing {len(common)} common folder(s)...\n")

    total_folders = 0
    folders_count_mismatch = 0
    folders_tag_diff = 0

    for rel in sorted(common):
        dir_a = root_a / rel
        dir_b = root_b / rel

        dcms_a = sorted(dir_a.glob("*.dcm"))
        dcms_b = sorted(dir_b.glob("*.dcm"))

        names_a = {f.name for f in dcms_a}
        names_b = {f.name for f in dcms_b}

        if not dcms_a and not dcms_b:
            continue  # empty leaf folder, skip

        total_folders += 1
        count_ok = len(dcms_a) == len(dcms_b)

        if not count_ok:
            folders_count_mismatch += 1
            print(f"[COUNT MISMATCH] {rel}")
            print(
                f"  {label_a}: {len(dcms_a)} files  |  {label_b}: {len(dcms_b)} files"
            )
            if names_a - names_b:
                print(f"  Only in {label_a}: {sorted(names_a - names_b)}")
            if names_b - names_a:
                print(f"  Only in {label_b}: {sorted(names_b - names_a)}")
            print()

        common_files = names_a & names_b
        folder_has_diff = False

        for fname in sorted(common_files):
            if diffs := compare_dicom_files(
                dir_a / fname, dir_b / fname, label_a, label_b
            ):
                if not folder_has_diff:
                    folder_has_diff = True
                    folders_tag_diff += 1
                    print(f"[TAG DIFF] {rel}")
                print(f"  {fname}")
                for d in diffs:
                    print(d)
        if folder_has_diff:
            print()

    print("=" * 60)
    print("SUMMARY")
    print("=" * 60)
    print(f"  Folders with DICOM files compared : {total_folders}")
    print(f"  File count mismatches             : {folders_count_mismatch}")
    print(f"  Folders with tag differences      : {folders_tag_diff}")
    if folders_count_mismatch == 0 and folders_tag_diff == 0:
        print("\n  Result: OUTPUTS MATCH")
    else:
        print("\n  Result: DIFFERENCES FOUND")


def main():
    parser = argparse.ArgumentParser(
        description="Compare DICOM outputs from two DicomOctExport versions."
    )
    parser.add_argument("root_a", help="First output root (e.g. maestro2_private)")
    parser.add_argument("root_b", help="Second output root (e.g. maestro2_public)")
    parser.add_argument(
        "--label-a", default="private", help="Label for first root (default: private)"
    )
    parser.add_argument(
        "--label-b", default="public", help="Label for second root (default: public)"
    )
    parser.add_argument(
        "--output", default=None, help="Path for the report file (default: comparison_<timestamp>.txt)"
    )
    args = parser.parse_args()

    root_a = Path(args.root_a)
    root_b = Path(args.root_b)

    if not root_a.exists():
        print(f"ERROR: path does not exist: {root_a}")
        sys.exit(1)
    if not root_b.exists():
        print(f"ERROR: path does not exist: {root_b}")
        sys.exit(1)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    default_output = Path(f"comparison_{timestamp}.txt")
    output_path = Path(args.output) if args.output else default_output

    header = f"{args.label_a}: {root_a}\n{args.label_b}: {root_b}"
    print(header)

    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        print(header)
        compare_folders(root_a, root_b, args.label_a, args.label_b)

    body = buf.getvalue()
    # Print everything after the header (already printed above)
    print(body[len(header) + 1:], end="")

    output_path.write_text(body, encoding="utf-8")
    print(f"\nReport saved to: {output_path}")


if __name__ == "__main__":
    main()
