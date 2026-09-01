import shutil
from pathlib import Path

import pydicom
import pandas as pd

DEVICE_FOLDER = "centervue_ocumet"

# OcuMet ImageComments tag ("Infrared Image" / "FPF Image") -> (modality_folder,
# submodality_folder).
MODALITY_FOLDER_MAP = {
    "fpf": ("retinal_photography", "cfp"),
    "infrared": ("retinal_photography", "ir"),
}

LATERALITY_MAP = {"R": "OD", "L": "OS"}


def classify_modality(image_comments):
    """Return (modality_folder, submodality_folder) from the OcuMet ImageComments tag."""
    comments = (image_comments or "").lower()
    return next(
        (
            folders
            for token, folders in MODALITY_FOLDER_MAP.items()
            if token in comments
        ),
        ("unknown_protocol", "unknown_submodality"),
    )


def get_subject_id(ds, fallback):
    """Extract the ADRC subject ID (e.g. "301-1001") from PatientName ("ADRC^301-1001").

    PatientID is not usable here - it's assigned per study/visit and differs
    between images for the same subject.
    """
    patient_name = str(getattr(ds, "PatientName", ""))
    if "^" in patient_name and (subject_id := patient_name.split("^", 1)[1].strip()):
        return subject_id
    return fallback


def organize_ocumet_dataset(input_dir, output_dir):
    """
    Scans input_dir for OcuMet DICOM files, reads subject/laterality/modality from
    DICOM tags, organizes them into
    <modality>/<submodality>/centervue_ocumet/<subject_id>/ folders
    and writes a manifest.tsv file at the output root.
    """
    source_path = Path(input_dir)
    output_path = Path(output_dir)
    manifest_records = []

    if not source_path.exists():
        print(f"Error: Input directory {input_dir} does not exist.")
        return

    output_path.mkdir(parents=True, exist_ok=True)
    print(f"Processing OcuMet DICOM files from '{source_path}' -> '{output_path}'...")

    for file_path in source_path.rglob("*"):
        if file_path.is_dir() or not file_path.name.endswith(".dcm"):
            continue

        try:
            ds = pydicom.dcmread(file_path, stop_before_pixels=True)
        except Exception as e:
            print(f"Warning: Could not read DICOM tags for {file_path.name}: {e}")
            continue

        subject_id = get_subject_id(ds, fallback=file_path.parent.name)
        image_comments = getattr(ds, "ImageComments", "")
        modality_folder, submodality_folder = classify_modality(image_comments)

        laterality_code = str(
            getattr(ds, "ImageLaterality", getattr(ds, "Laterality", ""))
        )
        laterality = LATERALITY_MAP.get(laterality_code.upper(), "")

        # Target destination: output/<modality>/<submodality>/centervue_ocumet/<subject_id>/filename.dcm
        dest_folder = (
            output_path
            / modality_folder
            / submodality_folder
            / DEVICE_FOLDER
            / subject_id
        )
        dest_folder.mkdir(parents=True, exist_ok=True)
        dest_file = dest_folder / file_path.name

        shutil.copy2(file_path, dest_file)

        manifest_records.append(
            {
                "subject_id": subject_id,
                "patient_id": getattr(ds, "PatientID", subject_id),
                "modality": image_comments or getattr(ds, "Modality", "OcuMet"),
                "modality_folder": modality_folder,
                "submodality_folder": submodality_folder,
                "laterality": laterality,
                "study_date": getattr(ds, "StudyDate", ""),
                "sop_instance_uid": getattr(ds, "SOPInstanceUID", ""),
                "series_instance_uid": getattr(ds, "SeriesInstanceUID", ""),
                "file_path": str(dest_file.relative_to(output_path)),
            }
        )

    # Generate manifest.tsv
    if manifest_records:
        df = pd.DataFrame(manifest_records)
        manifest_path = output_path / "manifest.tsv"
        df.to_csv(manifest_path, sep="\t", index=False)
        print(f"\nProcessing complete!")
        print(f"Organized DICOM Files: {len(manifest_records)}")
        print(f"Manifest Generated: {manifest_path}")
    else:
        print("No .dcm files found or processed.")


def main():
    input_folder = "/Volumes/Crucial X10/adrc/raw/Ocumet"
    output_folder = "/Volumes/Crucial X10/adrc/processed/ocumet/organized"

    organize_ocumet_dataset(input_folder, output_folder)


if __name__ == "__main__":
    main()
