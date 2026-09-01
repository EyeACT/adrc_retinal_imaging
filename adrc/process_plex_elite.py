#!/usr/bin/env python3
"""Organize raw PLEX Elite exports into the AI-READI-style final structure.

Each raw subject folder (e.g. "301-1001") holds a mix of exports produced by
the Zeiss PLEX Elite 9000 review software:

  - "<scan protocol>/" subfolders (e.g. "6x6", "Custom Angio 1") holding
    en face/B-scan preview renders (*.bmp) exported from the viewer.
  - "P<patient_id> <date>/" subfolders holding the raw proprietary binary
    export for each scan: structural OCT cube (*_cube_z.img), OCTA flow
    cube (*_FlowCube_z.img), line-scan SLO (*_lslo.bin), iris tracking
    (*_iris.bin), motion correction (*_mocor.bin), noise (*_noise.bin) and
    a fixation log (*_fixation.txt).
  - Loose color fundus photos and OCT report screenshots (*_Color_*.png,
    *_OCTReport_*.png) directly under the subject folder.
  - A handful of stray DICOM files that belong to a different device
    (seen so far: Topcon Maestro2) that ended up mixed into this raw
    dropbox. These are routed to a separate "foreign_device_dicom" bucket
    instead of being merged into the PLEX Elite structure, since they
    already have their own pipeline (process_maestro2.py).
  - A handful of stray operator notes (e.g. "could not do L.txt") that
    don't match any known suffix. These are routed to "notes" for manual
    review rather than dropped.

Files are routed individually into
<modality>/<submodality>/zeiss_plex_elite/<patient_id>/, matching the
layout used by the AI-READI Maestro2 pipeline's final structure. Every
copy (success or failure) is recorded in logs/organize_manifest.csv so the
routing can be audited; only failures are additionally written to
logs/organize_log.csv.
"""

import csv
import os
import re
import shutil
from datetime import datetime

import pydicom
from tqdm import tqdm

INPUT_FOLDER = "/Volumes/Crucial X10/adrc/raw/plex-elite"
OUTPUT_FOLDER = "/Volumes/Crucial X10/adrc/processed/plex-elite/organized"

DEVICE_FOLDER = "zeiss_plex_elite"

SUBJECT_ID_RE = re.compile(r"^\d{3}-\d{3,4}$")
LATERALITY_RE = re.compile(r"_(OD|OS)(?:_|\.)")
LATERALITY_LR_RE = re.compile(r"_(L|R)_\d+\.png$", re.IGNORECASE)
SCAN_PATTERN_RE = re.compile(r"(Angio \(\d+mmx\d+mm\)|Custom Angio \d+)")
BMP_RENDER_RE = re.compile(r"_(Angiography|Structure)_(.+)\.bmp$", re.IGNORECASE)

MANIFEST_FIELDS = [
    "Filename",
    "ModalityFolder",
    "SubmodalityFolder",
    "Protocol",
    "PatientID",
    "Laterality",
    "SourcePath",
    "DestPath",
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


def slugify(text):
    """Turn an arbitrary label (e.g. "CC Max(Global)") into a filesystem-safe slug."""
    text = re.sub(r"[^0-9a-zA-Z]+", "_", text).strip("_").lower()
    return text or "unknown"


def normalize_laterality(value):
    if not value:
        return "unknown"
    value = str(value).strip().upper()
    if value in {"OD", "R", "RIGHT"}:
        return "od"
    return "os" if value in {"OS", "L", "LEFT"} else "unknown"


def get_laterality(filename):
    match = LATERALITY_RE.search(filename)
    if match:
        return normalize_laterality(match.group(1))

    match = LATERALITY_LR_RE.search(filename)
    return normalize_laterality(match.group(1)) if match else "unknown"


def get_scan_slug(filename):
    """Pull the scan protocol token (e.g. "Angio (6mmx6mm)") out of a filename, if present."""
    match = SCAN_PATTERN_RE.search(filename)
    return slugify(match.group(1)) if match else None


def classify_file(filename):
    """Return (modality_folder, submodality_folder, protocol) for one raw export file.

    Classification is filename-pattern based rather than tag based: PLEX
    Elite's raw export is a mix of proprietary binary files and BMP
    renders, none of which carry DICOM metadata.
    """
    lower = filename.lower()
    scan_slug = get_scan_slug(filename)
    scan_suffix = f"_{scan_slug}" if scan_slug else ""

    if lower.endswith("flowcube_z.img"):
        return "retinal_octa", "flow_cube", f"plex_elite_octa_flow_cube{scan_suffix}"

    if lower.endswith("cube_z.img"):
        return "retinal_oct", "structural_oct", f"plex_elite_oct_cube{scan_suffix}"

    if lower.endswith("_lslo.bin"):
        return "retinal_photography", "ir", "plex_elite_lslo"

    if lower.endswith("_iris.bin"):
        return "auxiliary", "iris_tracking", "plex_elite_iris"

    if lower.endswith("_mocor.bin"):
        return "auxiliary", "motion_correction", "plex_elite_mocor"

    if lower.endswith("_noise.bin"):
        return "auxiliary", "noise", "plex_elite_noise"

    if lower.endswith("_fixation.txt"):
        return "auxiliary", "fixation", "plex_elite_fixation"

    if lower.endswith(".bmp"):
        if lower.endswith("b-scan.bmp"):
            return "retinal_oct", "bscan", f"plex_elite_oct_bscan{scan_suffix}"

        match = BMP_RENDER_RE.search(filename)
        if match:
            category, subtype = match.group(1).lower(), slugify(match.group(2))
            if category == "angiography":
                return "retinal_octa", "enface", f"plex_elite_octa_enface_{subtype}"
            return "retinal_oct", "enface", f"plex_elite_oct_enface_{subtype}"

        return "unknown_protocol", "unknown_protocol_bmp", "plex_elite_unknown_bmp"

    if lower.endswith(".png"):
        if "_color_" in lower:
            return "retinal_photography", "cfp", "plex_elite_color_fundus"
        if "_octreport_" in lower:
            return "reports", "oct_report", "plex_elite_oct_report"
        return "unknown_protocol", "unknown_protocol_png", "plex_elite_unknown_png"

    if lower.endswith(".txt"):
        # Fixation logs are handled above; anything else here is an
        # operator note (e.g. "could not do L.txt") worth keeping but not
        # part of the imaging structure.
        return "notes", "operator_notes", "plex_elite_note"

    extension = lower.rsplit(".", 1)[-1] if "." in lower else "noext"
    return "unknown_protocol", f"unknown_protocol_{extension}", "plex_elite_unknown"


def classify_dicom(ds):  # sourcery skip: extract-method
    """Route a stray DICOM file: genuine Zeiss data vs. a foreign device that got mixed in."""
    manufacturer = str(ds.get("Manufacturer", "")).strip()

    if "zeiss" in manufacturer.lower():
        modality = slugify(str(ds.get("Modality", "unknown")))
        series = slugify(str(ds.get("SeriesDescription", "unknown")))
        protocol = f"plex_elite_dicom_{modality}_{series}"
        if ds.get("Modality") == "OP":
            return "retinal_photography", "cfp", protocol
        if ds.get("Modality") == "OPT":
            return "retinal_oct", "structural_oct", protocol
        return "unknown_protocol", "unknown_protocol_dicom", protocol

    model = str(ds.get("ManufacturerModelName", "")).strip()
    bucket = (
        slugify(f"{manufacturer}_{model}")
        if (manufacturer or model)
        else "unknown_manufacturer"
    )
    return "foreign_device_dicom", bucket, f"foreign_{bucket}"


def organize_file(file_path, subject_id, output_folder, manifest_writer):
    """Classify a single raw file, copy it into the final structure, and log the routing."""
    filename = os.path.basename(file_path)
    extension = os.path.splitext(filename)[1].lower()

    if extension == ".dcm":
        ds = pydicom.dcmread(file_path, stop_before_pixels=True, force=True)
        modality_folder, submodality_folder, protocol = classify_dicom(ds)
        laterality = normalize_laterality(
            ds.get("ImageLaterality") or ds.get("Laterality")
        )
    else:
        modality_folder, submodality_folder, protocol = classify_file(filename)
        laterality = get_laterality(filename)

    dest_dir = os.path.join(
        output_folder, modality_folder, submodality_folder, DEVICE_FOLDER, subject_id
    )
    os.makedirs(dest_dir, exist_ok=True)

    new_filename = f"{subject_id}_{protocol}_{laterality}_{filename}"
    dest_path = os.path.join(dest_dir, new_filename)

    shutil.copy2(file_path, dest_path)

    manifest_writer.writerow(
        {
            "Filename": filename,
            "ModalityFolder": modality_folder,
            "SubmodalityFolder": submodality_folder,
            "Protocol": protocol,
            "PatientID": subject_id,
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

    subject_ids = sorted(
        entry
        for entry in os.listdir(input_folder)
        if SUBJECT_ID_RE.match(entry)
        and os.path.isdir(os.path.join(input_folder, entry))
    )

    print(f"Found {len(subject_ids)} subject folders in {input_folder}")

    with open(manifest_path, "w", newline="") as manifest_file:
        manifest_writer = csv.DictWriter(manifest_file, fieldnames=MANIFEST_FIELDS)
        manifest_writer.writeheader()

        for subject_id in tqdm(subject_ids, desc="Organizing subjects"):
            subject_dir = os.path.join(input_folder, subject_id)

            for root, _dirs, files in os.walk(subject_dir):
                for name in files:
                    if name.startswith("."):
                        continue

                    file_path = os.path.join(root, name)
                    try:
                        organize_file(
                            file_path, subject_id, output_folder, manifest_writer
                        )
                    except Exception as e:
                        write_log(log_path, file_path, "FAILURE", str(e))

    print(f"Done. Manifest written to {manifest_path}")


if __name__ == "__main__":
    main()
