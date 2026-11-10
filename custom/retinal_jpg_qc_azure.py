"""Convert every DICOM under an Azure Data Lake folder to JPEG for visual QC.

Walks the input folder recursively, downloads each .dcm file, converts it to a
JPEG, and uploads it to the output folder. Both folders live in the same
container.

The input is laid out as <modality>/<submodality>/<device>/<patient_id>/...
To make review easier, every participant for a given modality/submodality/device
lands in one flat folder. The first GROUP_DEPTH path components are kept as
folders; everything below is joined with "-" into the file name, so the
original path stays readable and names cannot collide.

    input:  <input_folder>/modality/submodality/device/1001/file.dcm
    output: <output_folder>/modality/submodality/device/1001-file.dcm.jpg

A status CSV listing every file and any error is uploaded to
<output_folder>/_qc_status_<timestamp>.csv.

Usage: edit the settings in the __main__ block, then run
    python custom/retinal_jpg_qc_azure.py
"""

import contextlib
import csv
import io
import os
import sys
import threading
import time
from multiprocessing.pool import ThreadPool
from traceback import format_exc

import azure.storage.filedatalake as azurelake
import numpy as np
import pydicom
from PIL import Image
from tqdm import tqdm

# Make the repo-root config module importable regardless of the working directory
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import config  # noqa: E402

JPEG_QUALITY = 90

# Number of leading path components (modality/submodality/device) kept as folders
GROUP_DEPTH = 3

thread_local = threading.local()


def log(message: str):
    # tqdm.write prints above the progress bar without breaking it
    tqdm.write(message)


def get_file_system_client(container: str) -> azurelake.FileSystemClient:
    return azurelake.FileSystemClient.from_connection_string(
        config.AZURE_STORAGE_CONNECTION_STRING,
        file_system_name=container,
    )


def list_dicom_paths(file_system_client, input_folder: str) -> list:
    """Return every .dcm file path under input_folder (recursive)."""
    dicom_paths = []

    scanned = tqdm(desc="Listing", unit=" paths")

    for path in file_system_client.get_paths(path=input_folder, recursive=True):
        scanned.update(1)

        if path.is_directory:
            continue

        file_name = path.name.split("/")[-1]

        # exclude hidden/system files and ensure .dcm extension
        if file_name.startswith(".") or not file_name.lower().endswith(".dcm"):
            continue

        dicom_paths.append(path.name)
        scanned.set_postfix(dicom=len(dicom_paths))

    scanned.close()

    return dicom_paths


def to_uint8(arr: np.ndarray) -> np.ndarray:
    """Scale non-8-bit pixel data into 0-255 so it can be saved as JPEG."""
    if arr.dtype == np.uint8:
        return arr

    arr = arr.astype(np.float64)
    lo, hi = arr.min(), arr.max()

    if hi <= lo:
        return np.zeros(arr.shape, dtype=np.uint8)

    return ((arr - lo) / (hi - lo) * 255).round().astype(np.uint8)


def dicom_bytes_to_jpg_bytes(dicom_bytes: bytes) -> bytes:
    """Convert a DICOM file's bytes to JPEG bytes. Raises on failure."""
    ds = pydicom.dcmread(io.BytesIO(dicom_bytes))
    arr = ds.pixel_array

    if arr.ndim == 3 and arr.shape[-1] not in (3, 4):
        # Multi-frame grayscale: use the first frame
        arr = arr[0]
    elif arr.ndim == 4:
        # Multi-frame color: use the first frame
        arr = arr[0]

    if arr.ndim not in (2, 3):
        raise ValueError(f"Unsupported pixel array shape {arr.shape}")

    img = Image.fromarray(to_uint8(arr))

    if img.mode not in ("L", "RGB"):
        img = img.convert("RGB")

    buffer = io.BytesIO()
    img.save(buffer, format="JPEG", quality=JPEG_QUALITY)

    return buffer.getvalue()


def output_path_for(input_path: str, input_folder: str, output_folder: str) -> str:
    relative_path = input_path[len(input_folder) :].lstrip("/")
    parts = relative_path.split("/")

    group = parts[: min(GROUP_DEPTH, len(parts) - 1)]
    file_name = "-".join(parts[len(group) :])

    return "/".join([output_folder, *group, f"{file_name}.jpg"])


def process_file(container, input_folder, output_folder, file_item):
    """Download, convert, and upload one file. Runs on a pool thread."""
    # One client per thread, reused across that thread's files
    if not hasattr(thread_local, "client"):
        thread_local.client = get_file_system_client(container)

    file_system_client = thread_local.client

    path = file_item["file_path"]
    output_path = output_path_for(path, input_folder, output_folder)

    try:
        dicom_bytes = (
            file_system_client.get_file_client(file_path=path).download_file().readall()
        )

        jpg_bytes = dicom_bytes_to_jpg_bytes(dicom_bytes)

        file_system_client.get_file_client(file_path=output_path).upload_data(
            jpg_bytes, overwrite=True
        )

        file_item["status"] = "success"
        file_item["output_file"] = output_path
    except Exception as e:
        file_item["error"] = " ".join(format_exc().splitlines())
        log(f"FAIL {path}: {e}")

    return file_item


def upload_status_report(file_system_client, output_folder, file_items):
    timestr = time.strftime("%Y%m%d-%H%M%S")
    report_path = f"{output_folder}/_qc_status_{timestr}.csv"

    buffer = io.StringIO()
    writer = csv.DictWriter(
        buffer, fieldnames=["file_path", "status", "output_file", "error"]
    )
    writer.writeheader()
    writer.writerows(file_items)

    file_system_client.get_file_client(file_path=report_path).upload_data(
        buffer.getvalue().encode("utf-8"), overwrite=True
    )

    return report_path


def pipeline(
    container: str,
    input_folder: str,
    output_folder: str,
    workers: int = 8,
    clean_output: bool = False,
):
    input_folder = input_folder.strip("/")
    output_folder = output_folder.strip("/")

    if input_folder == output_folder or output_folder.startswith(f"{input_folder}/"):
        raise ValueError("output_folder must not be inside input_folder")

    file_system_client = get_file_system_client(container)

    if clean_output:
        log(f"Deleting existing output folder {output_folder}")
        with contextlib.suppress(Exception):
            file_system_client.delete_directory(output_folder)

    log(f"Listing DICOM files under {container}/{input_folder}")
    dicom_paths = list_dicom_paths(file_system_client, input_folder)
    total = len(dicom_paths)
    log(f"Found {total} DICOM files")

    if total == 0:
        return

    file_items = [
        {"file_path": p, "status": "failed", "output_file": "", "error": ""}
        for p in dicom_paths
    ]

    ok, failed = 0, 0

    def run(file_item):
        return process_file(container, input_folder, output_folder, file_item)

    with ThreadPool(workers) as pool, tqdm(
        total=total, desc="Converting", unit=" files"
    ) as progress:
        for file_item in pool.imap_unordered(run, file_items):
            if file_item["status"] == "success":
                ok += 1
            else:
                failed += 1

            progress.update(1)
            progress.set_postfix(ok=ok, failed=failed)

    log(f"Done. Successful: {ok}  Failed: {total - ok}")

    report_path = upload_status_report(file_system_client, output_folder, file_items)
    log(f"Uploaded status report to {container}/{report_path}")


if __name__ == "__main__":
    CONTAINER = "adrc"
    INPUT_FOLDER = "organized/"
    OUTPUT_FOLDER = "JPG_QC/"
    WORKERS = 16
    CLEAN_OUTPUT = False  # True deletes OUTPUT_FOLDER before starting

    pipeline(CONTAINER, INPUT_FOLDER, OUTPUT_FOLDER, WORKERS, CLEAN_OUTPUT)
