#!/usr/bin/env python3
"""ADRC FLIO Processing Script.

Directly calls `make_flio_dicom_adrc` from `imaging_flio_converter.py`
without altering any existing AIREADI functions.
"""

# import argparse
import csv
import os
import sys
from tqdm import tqdm
import shutil

project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
year_3_path = os.path.join(project_root, "year_3")

if project_root not in sys.path:
    sys.path.insert(0, project_root)
if year_3_path not in sys.path:
    sys.path.insert(0, year_3_path)

import year_3.imaging_flio_converter as flio_conv  # noqa: E402

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


def write_tsv_manifest(output_folder, records):
    """Generates the ADRC compliant manifest.tsv inside retinal_flio/."""
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
    # parser = argparse.ArgumentParser(
    #     description="Process raw FLIO for ADRC using dedicated helper function."
    # )
    # parser.add_argument(
    #     "-i",
    #     "--input-folder",
    #     required=True,
    #     help="Input folder containing raw FLIO scans",
    # )
    # parser.add_argument(
    #     "-o",
    #     "--output-folder",
    #     required=True,
    #     help="Output organized directory",
    # )
    # args = parser.parse_args()

    # input_folder = os.path.abspath(args.input_folder)
    # output_folder = os.path.abspath(args.output_folder)

    input_folder = "/Volumes/Crucial X10/adrc/raw/FLIO"
    output_folder = "/Volumes/Crucial X10/adrc/processed/flio/organized"

    # delete the output folder if it exists to ensure a clean start
    if os.path.exists(output_folder):
        shutil.rmtree(output_folder)

    # Scan for directories containing Measurement.sdt
    scan_folders = []
    scan_folders.extend(
        root for root, _, files in os.walk(input_folder) if "Measurement.sdt" in files
    )
    print(f"Found {len(scan_folders)} FLIO scan folders.")

    all_manifest_records = []

    # Process each scan folder using the dedicated new converter function
    for scan_folder in tqdm(scan_folders, desc="Processing FLIO"):
        res = flio_conv.make_flio_dicom_adrc(scan_folder, output_folder)

        if res.get("Error") is None and res.get("PatientID"):
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

    print("--- Finished ---")


if __name__ == "__main__":
    main()
