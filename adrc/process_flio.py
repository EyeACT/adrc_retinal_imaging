#!/usr/bin/env python3
"""Organize raw Heidelberg FLIO scans into the AI-READI-style final structure.

Each raw scan folder holds a Measurement.sdt file (the raw fluorescence
lifetime data) alongside a measurement_info.html file (scan metadata). Unlike
the other AI-READI device pipelines, FLIO doesn't need the full
organize/convert/finalize workflow: `make_flio_dicom_adrc` in
imaging_flio_converter.py reuses the existing SDT/HTML parsers directly and
writes ADRC-compliant DICOMs (short + long wavelength) for a scan folder in
one call, routed into
<modality>/<submodality>/heidelberg_flio/<patient_id>/, matching the layout
used by the other ADRC device pipelines. Every scan folder (success or
failure) is recorded in logs/organize_log.csv so failures can be audited.
"""

import csv
import os
import shutil
import sys
from datetime import datetime

from tqdm import tqdm

project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
year_3_path = os.path.join(project_root, "year_3")

if project_root not in sys.path:
    sys.path.insert(0, project_root)
if year_3_path not in sys.path:
    sys.path.insert(0, year_3_path)

import year_3.imaging_flio_converter as flio_conv  # noqa: E402

INPUT_FOLDER = "/Volumes/Crucial X10/adrc/raw/FLIO"
OUTPUT_FOLDER = "/Volumes/Crucial X10/adrc/processed/flio/organized"

MANIFEST_TSV_FIELDS = [
    "person_id",
    "manufacturer",
    "manufacturers_model_name",
    "laterality",
    "anatomic_region",
    "imaging",
    "height",
    "width",
    "filepath",
]


def write_log(log_file_path, input_path, status, error_message=""):
    """Append a row to a CSV log, writing the header first if needed."""
    file_exists = os.path.exists(log_file_path)

    with open(log_file_path, "a", newline="") as csvfile:
        fieldnames = ["Timestamp", "Input", "Status", "ErrorMessage"]
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)

        if not file_exists:
            writer.writeheader()

        writer.writerow(
            {
                "Timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "Input": input_path,
                "Status": status,
                "ErrorMessage": error_message,
            }
        )


def write_tsv_manifest(output_folder, records):
    """Write manifest.tsv listing every FLIO DICOM produced, under retinal_flio/."""
    modality_dir = os.path.join(output_folder, "retinal_flio")
    os.makedirs(modality_dir, exist_ok=True)
    manifest_path = os.path.join(modality_dir, "manifest.tsv")

    sorted_records = sorted(records, key=lambda r: r["person_id"])
    with open(manifest_path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=MANIFEST_TSV_FIELDS, delimiter="\t")
        writer.writeheader()
        writer.writerows(sorted_records)
    print(f"Manifest written to {manifest_path}")


def main():
    input_folder = INPUT_FOLDER
    output_folder = OUTPUT_FOLDER

    if not os.path.isdir(input_folder):
        raise ValueError(f"Input folder does not exist: {input_folder}")

    if os.path.exists(output_folder):
        shutil.rmtree(output_folder)
    os.makedirs(output_folder)

    logs_folder = os.path.join(output_folder, "logs")
    os.makedirs(logs_folder, exist_ok=True)
    log_path = os.path.join(logs_folder, "organize_log.csv")

    # Scan for directories containing Measurement.sdt
    scan_folders = [
        root for root, _, files in os.walk(input_folder) if "Measurement.sdt" in files
    ]
    print(f"Found {len(scan_folders)} FLIO scan folders in {input_folder}")

    all_manifest_records = []

    for scan_folder in tqdm(scan_folders, desc="Processing FLIO"):
        res = flio_conv.make_flio_dicom_adrc(scan_folder, output_folder)

        if res.get("Error") is not None or not res.get("PatientID"):
            write_log(log_path, scan_folder, "FAILURE", res.get("Error", "Unknown error"))
            continue

        rel_short = "/" + os.path.relpath(res["ShortPath"], output_folder)
        rel_long = "/" + os.path.relpath(res["LongPath"], output_folder)

        all_manifest_records.extend(
            [
                {
                    "person_id": res["PatientID"],
                    "manufacturer": "Heidelberg Engineering",
                    "manufacturers_model_name": "FLIO",
                    "laterality": res["Laterality"],
                    "anatomic_region": "Macula",
                    "imaging": "Fluorescence Lifetime Imaging Ophthalmoscopy Short",
                    "height": res["Rows"],
                    "width": res["Cols"],
                    "filepath": rel_short,
                },
                {
                    "person_id": res["PatientID"],
                    "manufacturer": "Heidelberg Engineering",
                    "manufacturers_model_name": "FLIO",
                    "laterality": res["Laterality"],
                    "anatomic_region": "Macula",
                    "imaging": "Fluorescence Lifetime Imaging Ophthalmoscopy Long",
                    "height": res["Rows"],
                    "width": res["Cols"],
                    "filepath": rel_long,
                },
            ]
        )

    if all_manifest_records:
        write_tsv_manifest(output_folder, all_manifest_records)

    print(f"Done. Log written to {log_path}")


if __name__ == "__main__":
    main()
