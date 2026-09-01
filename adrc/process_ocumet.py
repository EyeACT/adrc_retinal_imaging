import os
import re
import shutil
import argparse
import pydicom
import pandas as pd
from pathlib import Path

def parse_ocumet_filename(filename):
    """Extracts laterality, modality, and position from OcuMet DICOM filenames."""
    pattern = r'(?P<subject>\d+-\d+).*?-(?P<eye>right|left)-(?P<position>\d+)-(?P<modality>fpf|infrared)'
    match = re.search(pattern, filename, re.IGNORECASE)
    if match:
        data = match.groupdict()
        data['eye'] = 'OD' if data['eye'].lower() == 'right' else 'OS'
        return data
    return None

def organize_ocumet_dataset(input_dir, output_dir):
    """
    Scans input_dir for OcuMet DICOM files, organizes them into sub-<subject_id>/ folders,
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

    for file_path in source_path.rglob('*'):
        if file_path.is_dir() or not file_path.name.endswith('.dcm'):
            continue

        filename = file_path.name
        parsed_info = parse_ocumet_filename(filename)
        
        # Determine subject ID
        subject_id = parsed_info['subject'] if (parsed_info and 'subject' in parsed_info) else file_path.parent.name
        
        # Target destination: output/sub-<subject_id>/filename.dcm
        dest_folder = output_path / f"sub-{subject_id}"
        dest_folder.mkdir(parents=True, exist_ok=True)
        dest_file = dest_folder / filename
        
        shutil.copy2(file_path, dest_file)

        # DICOM tag parsing for manifest
        try:
            ds = pydicom.dcmread(dest_file, stop_before_pixels=True)
            manifest_records.append({
                "subject_id": subject_id,
                "patient_id": getattr(ds, "PatientID", subject_id),
                "modality": parsed_info.get("modality", getattr(ds, "Modality", "OcuMet")) if parsed_info else "OcuMet",
                "laterality": parsed_info.get("eye", getattr(ds, "ImageLaterality", "")) if parsed_info else "",
                "study_date": getattr(ds, "StudyDate", ""),
                "sop_instance_uid": getattr(ds, "SOPInstanceUID", ""),
                "series_instance_uid": getattr(ds, "SeriesInstanceUID", ""),
                "file_path": str(dest_file.relative_to(output_path))
            })
        except Exception as e:
            print(f"Warning: Could not read DICOM tags for {filename}: {e}")

    # Generate manifest.tsv
    if manifest_records:
        df = pd.DataFrame(manifest_records)
        manifest_path = output_path / "manifest.tsv"
        df.to_csv(manifest_path, sep='\t', index=False)
        print(f"\nProcessing complete!")
        print(f"Organized DICOM Files: {len(manifest_records)}")
        print(f"Manifest Generated: {manifest_path}")
    else:
        print("No .dcm files found or processed.")

def main():
    parser = argparse.ArgumentParser(
        description="Organize OcuMet DICOM datasets into subject folders and generate a manifest."
    )
    parser.add_argument(
        "-i", "--input",
        required=True,
        help="Path to raw OcuMet input directory"
    )
    parser.add_argument(
        "-o", "--output",
        required=True,
        help="Path to organized output directory"
    )

    args = parser.parse_args()
    organize_ocumet_dataset(args.input, args.output)

if __name__ == "__main__":
    main()