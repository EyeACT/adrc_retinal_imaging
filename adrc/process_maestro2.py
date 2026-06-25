#!/usr/bin/env python3
"""Organize raw Maestro2 DICOM exports into the AI-READI final structure.

Each raw "batch_folder_<id>_fda" holds every file for a single Maestro2 scan
(OCT volume, fundus photo, and - when present - the OCTA flow volume, its
en face renders, and the retinal layer segmentation). Files are routed
individually into <modality>/<submodality>/topcon_maestro2/<patient_id>/,
matching the layout used by the AI-READI Topcon pipeline's final structure.
"""

import csv
import os
import shutil
from datetime import datetime

import pydicom
from tqdm import tqdm


INPUT_FOLDER = "/Volumes/Crucial X10/adrc/pre/maestro2/batch_folder_output"
OUTPUT_FOLDER = "/Volumes/Crucial X10/adrc/processed/maestro2/organized"

DEVICE_FOLDER = "topcon_maestro2"

# (Modality, SeriesDescription) -> (modality_folder, submodality_folder, protocol).
PROTOCOL_MAP = {
    ("OP", "FundusPhoto"): ("retinal_photography", "cfp", "maestro2_fundus"),
    ("OP", "IR"): ("retinal_photography", "ir", "maestro2_ir"),
    ("OP", "FAF"): ("retinal_photography", "faf", "maestro2_faf"),
    ("OPT", "OCT 3D H Macula"): ("retinal_oct", "structural_oct", "maestro2_oct_macula"),
    ("OPT", "OCT 3D H Wide"): ("retinal_oct", "structural_oct", "maestro2_oct_wide"),
    ("OPT", "OCT 3D H Disc"): ("retinal_oct", "structural_oct", "maestro2_oct_disc"),
    ("OPT", "OCT 3D H External"): ("retinal_oct", "structural_oct", "maestro2_oct_external"),
    ("OPTBSV", "OCTA Flow Volume Raw Data - for processing"): (
        "retinal_octa",
        "flow_cube",
        "maestro2_octa",
    ),
    ("OPTENF", "OCT Enface Image"): ("retinal_octa", "enface", "maestro2_enface"),
    ("SEG", "Retinal Layer(s) Segmentation"): (
        "retinal_octa",
        "segmentation",
        "maestro2_segmentation",
    ),
}


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


def get_dicom_files(folder):
    """Return paths to candidate DICOM files directly inside a batch folder."""
    files = []
    for entry in sorted(os.listdir(folder)):
        if entry.startswith("."):
            continue
        path = os.path.join(folder, entry)
        if os.path.isfile(path):
            files.append(path)
    return files


def classify_file(ds):
    """Return (modality_folder, submodality_folder, protocol) for a dataset."""
    modality = ds.get("Modality", "")
    series_description = ds.get("SeriesDescription", "")

    classification = PROTOCOL_MAP.get((modality, series_description))
    if classification is not None:
        return classification

    safe_modality = modality or "unknown_modality"
    unknown_protocol = f"unknown_protocol_{safe_modality}"
    return "unknown_protocol", unknown_protocol, unknown_protocol


def get_laterality(ds):
    laterality = ds.get("Laterality") or ds.get("ImageLaterality") or "unknown"
    return laterality.lower()


def organize_file(file_path, output_folder, manifest_writer):
    """Classify a single DICOM file and copy it into the final structure."""
    ds = pydicom.dcmread(file_path, stop_before_pixels=True)

    modality_folder, submodality_folder, protocol = classify_file(ds)
    patient_id = ds.get("PatientID") or "unknown"
    laterality = get_laterality(ds)

    patient_folder = os.path.join(
        output_folder, modality_folder, submodality_folder, DEVICE_FOLDER, patient_id
    )
    os.makedirs(patient_folder, exist_ok=True)

    original_filename = os.path.basename(file_path)
    new_filename = f"{patient_id}_{protocol}_{laterality}_{original_filename}"
    dest_path = os.path.join(patient_folder, new_filename)

    shutil.copy2(file_path, dest_path)

    manifest_writer.writerow(
        {
            "Filename": original_filename,
            "ModalityFolder": modality_folder,
            "SubmodalityFolder": submodality_folder,
            "Protocol": protocol,
            "PatientID": patient_id,
            "Laterality": laterality,
            "SourcePath": file_path,
            "DestPath": dest_path,
        }
    )


def main():
    input_folder = INPUT_FOLDER
    output_folder = OUTPUT_FOLDER

    if not os.path.isdir(input_folder):
        raise ValueError(f"Input folder does not exist: {input_folder}")

    os.makedirs(output_folder, exist_ok=True)

    logs_folder = os.path.join(output_folder, "logs")
    os.makedirs(logs_folder, exist_ok=True)
    log_path = os.path.join(logs_folder, "organize_log.csv")
    manifest_path = os.path.join(logs_folder, "organize_manifest.csv")

    batch_folders = [
        os.path.join(input_folder, entry)
        for entry in sorted(os.listdir(input_folder))
        if os.path.isdir(os.path.join(input_folder, entry))
    ]

    print(f"Found {len(batch_folders)} batch folders in {input_folder}")

    with open(manifest_path, "w", newline="") as manifest_file:
        manifest_fieldnames = [
            "Filename",
            "ModalityFolder",
            "SubmodalityFolder",
            "Protocol",
            "PatientID",
            "Laterality",
            "SourcePath",
            "DestPath",
        ]
        manifest_writer = csv.DictWriter(manifest_file, fieldnames=manifest_fieldnames)
        manifest_writer.writeheader()

        for batch_folder in tqdm(batch_folders, desc="Organizing batch folders"):
            files = get_dicom_files(batch_folder)

            if not files:
                write_log(log_path, batch_folder, "FAILURE", "No files found")
                continue

            for file_path in files:
                try:
                    organize_file(file_path, output_folder, manifest_writer)
                except Exception as e:
                    write_log(log_path, file_path, "FAILURE", str(e))

    print(f"Done. Manifest written to {manifest_path}")


if __name__ == "__main__":
    main()
