import os
import sys
import shutil
import numpy as np
from joblib import Parallel, delayed

# This line is specific to your local machine's setup.
# It tells Python where to find your custom modules.
# Add year_3 directory to path - OS agnostic
year_3_path = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "year_3"
)
sys.path.append(year_3_path)

import organize_utils


def split_into_n_parts(lst, n):
    """Split list into n nearly equal parts"""
    return np.array_split(lst, n)


def process_sublist(sublist, sublist_index, dst_root):
    ok, fail = 0, 0
    for f in sublist:
        try:
            organize_utils.file_to_jpg(f, dst_root)
            ok += 1
        except Exception:
            fail += 1
    return ok, fail


def dicom_to_jpg(files, output_folder):
    print("Total files:", len(files))

    sublists = split_into_n_parts(files, 100)

    results = Parallel(n_jobs=10, backend="loky")(
        delayed(process_sublist)(sublist, i, output_folder)
        for i, sublist in enumerate(sublists)
    )

    total_ok = sum(ok for ok, _ in results)
    total_fail = sum(fail for _, fail in results)
    print(f"Done. Successful: {total_ok}  Failed: {total_fail}")


def process_dicom_to_jpb_per_site(device, modality, input, output_root):

    dicom_folder = f"{input}/{modality}/{device}"

    files = organize_utils.get_dcm_files(dicom_folder)

    list_1 = []
    list_4 = []
    list_7 = []
    others = []

    for f in files:
        base = os.path.basename(f)
        if base.startswith(("1", "2", "3")):
            list_1.append(f)
        elif base.startswith(("4", "5")):
            list_4.append(f)
        elif base.startswith(("7", "8")):
            list_7.append(f)
        else:
            others.append(f)

    print("Starts with 1:", len(list_1))
    print("Starts with 4:", len(list_4))
    print("Starts with 7:", len(list_7))

    if others:
        print("\nFiles with unexpected IDs:")
        for o in others:
            print(o)
    else:
        print("\n✅ All files start with 1, 4, or 7.")

    uw_folder = os.path.join(output_root, "UW", device, modality)
    ucsd_folder = os.path.join(output_root, "UCSD", device, modality)
    uab_folder = os.path.join(output_root, "UAB", device, modality)

    dicom_to_jpg(list_1, uw_folder)
    dicom_to_jpg(list_4, ucsd_folder)
    dicom_to_jpg(list_7, uab_folder)


if __name__ == "__main__":
    download_data_folder = r"D:\\year3+processed"

    output_root = os.path.join(download_data_folder, "JPG_QC")
    input = os.path.join(download_data_folder, "retinal_photography")

    if os.path.exists(output_root):
        shutil.rmtree(output_root)

    device = "icare_eidon"
    modality = "ir"
    process_dicom_to_jpb_per_site(device, modality, input, output_root)

    device = "icare_eidon"
    modality = "cfp"
    process_dicom_to_jpb_per_site(device, modality, input, output_root)

    device = "icare_eidon"
    modality = "faf"
    process_dicom_to_jpb_per_site(device, modality, input, output_root)

    device = "optomed_aurora"
    modality = "cfp"
    process_dicom_to_jpb_per_site(device, modality, input, output_root)

    device = "topcon_maestro2"
    modality = "cfp"
    process_dicom_to_jpb_per_site(device, modality, input, output_root)

    device = "topcon_maestro2"
    modality = "ir"
    process_dicom_to_jpb_per_site(device, modality, input, output_root)

    device = "topcon_triton"
    modality = "cfp"
    process_dicom_to_jpb_per_site(device, modality, input, output_root)

    device = "heidelberg_spectralis"
    modality = "ir"
    process_dicom_to_jpb_per_site(device, modality, input, output_root)

    device = "zeiss_cirrus"
    modality = "ir"
    process_dicom_to_jpb_per_site(device, modality, input, output_root)
