#!/usr/bin/env python3
"""Consolidate raw ADRC acuity/contrast exports into per-subject CSVs.

Each raw export batch contains an "Acuity_All_*.csv" and an
"ACSFSAndLinearContrast_All_*.csv" snapshot that cumulatively re-includes
prior records, so the same test result shows up across many files. Records
are pooled, deduplicated on their full row content, and split by SUBJECTID
into <VISUAL_ACUITY_DIR>/<subject_id>/Acuity.csv and
<CSFS_DIR>/<subject_id>/ACFCSFSAndLinearContrast.csv (siblings under
PROCESSED_DIR), with a combined manifest.tsv written to PROCESSED_DIR.
"""

import csv
import os
from collections import defaultdict
from datetime import datetime

RAW_DIR = "/Volumes/Crucial X10/adrc/raw/acuity"
PROCESSED_DIR = "/Volumes/Crucial X10/adrc/processed/acuity"
VISUAL_ACUITY_DIR = os.path.join(PROCESSED_DIR, "visual_acuity")
CSFS_DIR = os.path.join(PROCESSED_DIR, "csfs")

ACUITY_PREFIX = "Acuity_All_"
ACFCSFS_PREFIX = "ACSFSAndLinearContrast_All_"

MANIFEST_TSV_FIELDS = ["person_id", "protocol", "record_count", "filepath"]

DATE_COLUMN = "DATE"
TIME_COLUMN_CANDIDATES = ("STARTTIME", "TIME")


def find_csv_files(base_dir):
    """Return paths to all real CSVs under base_dir, skipping AppleDouble files."""
    files = []
    for root, _, fnames in os.walk(base_dir):
        for fname in fnames:
            if fname.lower().endswith(".csv") and not fname.startswith("._"):
                files.append(os.path.join(root, fname))
    return sorted(files)


def bucket_files(files):
    """Sort files into (acuity, acfcsfs, other) by their filename prefix."""
    acuity, acfcsfs, other = [], [], []
    for f in files:
        name = os.path.basename(f)
        if name.startswith(ACUITY_PREFIX):
            acuity.append(f)
        elif name.startswith(ACFCSFS_PREFIX):
            acfcsfs.append(f)
        else:
            other.append(f)
    return acuity, acfcsfs, other


def read_unique_records(files):
    """Read files sharing one header and return (header, rows deduped on full content)."""
    header = None
    seen = set()
    records = []
    for f in files:
        with open(f, newline="", encoding="utf-8-sig", errors="replace") as fh:
            reader = csv.reader(fh)
            file_header = next(reader)
            if header is None:
                header = file_header
            elif file_header != header:
                raise ValueError(f"Header mismatch in {f}: {file_header} != {header}")
            for row in reader:
                key = tuple(row)
                if key in seen:
                    continue
                seen.add(key)
                records.append(row)
    return header, records


def split_by_subject(header, records):
    """Group records by the (stripped) SUBJECTID column value."""
    subject_idx = header.index("SUBJECTID")
    by_subject = defaultdict(list)
    for row in records:
        if subject := row[subject_idx].strip():
            by_subject[subject].append(row)
    return by_subject


def _parse_date(value):
    value = value.strip()
    if not value:
        return datetime.min
    try:
        return datetime.strptime(value, "%m/%d/%Y")
    except ValueError:
        return datetime.min


def _parse_time(value):
    value = value.strip()
    if not value:
        return datetime.min.time()
    try:
        return datetime.strptime(value, "%I:%M %p").time()
    except ValueError:
        return datetime.min.time()


def sort_rows_by_date_time(header, rows):
    """Sort rows by DATE, then a time column (STARTTIME/TIME) to break ties, if present."""
    if DATE_COLUMN not in header:
        return rows

    date_idx = header.index(DATE_COLUMN)
    time_idx = next((header.index(c) for c in TIME_COLUMN_CANDIDATES if c in header), None)

    def key(row):
        date_key = _parse_date(row[date_idx])
        time_key = _parse_time(row[time_idx]) if time_idx is not None else datetime.min.time()
        return (date_key, time_key)

    return sorted(rows, key=key)


def write_subject_files(by_subject, header, out_dir_base, out_filename, protocol):
    """Write one CSV per subject under out_dir_base/<subject_id>/<out_filename>.

    Returns the manifest records (person_id, protocol, record_count, filepath)
    describing each file written, with filepath relative to out_dir_base.
    """
    manifest_records = []
    for subject, rows in by_subject.items():
        rows = sort_rows_by_date_time(header, rows)

        out_dir = os.path.join(out_dir_base, subject)
        os.makedirs(out_dir, exist_ok=True)
        out_path = os.path.join(out_dir, out_filename)
        with open(out_path, "w", newline="", encoding="utf-8") as fh:
            writer = csv.writer(fh)
            writer.writerow(header)
            writer.writerows(rows)

        manifest_records.append(
            {
                "person_id": subject,
                "protocol": protocol,
                "record_count": len(rows),
                "filepath": f"/{os.path.relpath(out_path, PROCESSED_DIR)}",
            }
        )
    return manifest_records


def write_manifest(manifests, out_filename="manifest.tsv"):
    """Write a manifest.tsv under PROCESSED_DIR listing every per-subject file produced."""
    sorted_records = sorted(manifests, key=lambda r: (r["person_id"], r["protocol"]))
    manifest_path = os.path.join(PROCESSED_DIR, out_filename)
    with open(manifest_path, "w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=MANIFEST_TSV_FIELDS, delimiter="\t")
        writer.writeheader()
        writer.writerows(sorted_records)
    print(f"Manifest written: {manifest_path}")


def main():
    files = find_csv_files(RAW_DIR)
    acuity_files, acfcsfs_files, other_files = bucket_files(files)

    print(f"Found {len(files)} CSV files under {RAW_DIR}")
    print(f"  {ACUITY_PREFIX}*: {len(acuity_files)}")
    print(f"  {ACFCSFS_PREFIX}*: {len(acfcsfs_files)}")
    print(f"  Unmatched (not used): {len(other_files)}")
    for f in other_files:
        print(f"    - {f}")

    acuity_header, acuity_records = read_unique_records(acuity_files)
    print(f"Acuity unique records: {len(acuity_records)}")

    acfcsfs_header, acfcsfs_records = read_unique_records(acfcsfs_files)
    print(f"ACSFSAndLinearContrast unique records: {len(acfcsfs_records)}")

    acuity_by_subject = split_by_subject(acuity_header, acuity_records)
    acfcsfs_by_subject = split_by_subject(acfcsfs_header, acfcsfs_records)

    acuity_manifest = write_subject_files(
        acuity_by_subject, acuity_header, VISUAL_ACUITY_DIR, "acuity.csv", "acuity"
    )
    acfcsfs_manifest = write_subject_files(
        acfcsfs_by_subject,
        acfcsfs_header,
        CSFS_DIR,
        "acfcsfs_and_linear_contrast.csv",
        "acfcsfs_and_linear_contrast",
    )

    all_subjects = sorted(set(acuity_by_subject) | set(acfcsfs_by_subject))
    print(f"Wrote data for {len(all_subjects)} unique subjects to {PROCESSED_DIR}")

    write_manifest(acuity_manifest + acfcsfs_manifest)


if __name__ == "__main__":
    main()
