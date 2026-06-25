import csv
import os
import sys

import pydicom

INPUT_FOLDER = "/Volumes/Crucial X10/adrc/pre/maestro2"
OUTPUT_CSV = "dicom_metadata.csv"

FIELDS = [
    "Filename",
    "Modality",
    "SeriesDescription",
    "Laterality",
    "NumberOfFrames",
    "Rows",
    "Columns",
    "PatientID",
]


def get_tag_value(ds, tag):
    try:
        val = ds[tag].value
        if isinstance(val, pydicom.sequence.Sequence):
            return str(val)
        return val
    except KeyError:
        return ""


def extract_metadata(filepath):
    try:
        ds = pydicom.dcmread(filepath, stop_before_pixels=True, )
    except Exception as e:
        print(f"  Skipping {filepath}: {e}", file=sys.stderr)
        return None

    return {
        "Filename": os.path.basename(filepath),
        "Modality": get_tag_value(ds, "Modality"),
        "SeriesDescription": get_tag_value(ds, "SeriesDescription"),
        "Laterality": get_tag_value(ds, "Laterality") or get_tag_value(ds, "ImageLaterality"),
        "NumberOfFrames": get_tag_value(ds, "NumberOfFrames"),
        "Rows": get_tag_value(ds, "Rows"),
        "Columns": get_tag_value(ds, "Columns"),
        "PatientID": get_tag_value(ds, "PatientID"),
    }


def main():
    folder = INPUT_FOLDER
    if not os.path.isdir(folder):
        print(f"Error: folder not found: {folder}", file=sys.stderr)
        sys.exit(1)

    rows = []
    for root, _, files in os.walk(folder):
        for fname in files:
            if fname.startswith("."):
                continue
            filepath = os.path.join(root, fname)
            result = extract_metadata(filepath)
            if result is not None:
                rows.append(result)

    rows.sort(key=lambda r: r["Filename"])

    with open(OUTPUT_CSV, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDS)
        writer.writeheader()
        writer.writerows(rows)

    print(f"Wrote {len(rows)} rows to {OUTPUT_CSV}")


if __name__ == "__main__":
    main()
