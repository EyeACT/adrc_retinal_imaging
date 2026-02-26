import pydicom
import os
import shutil


def fix_triton():
    base_folder_path = "D:\\year3+manual\\triton"
    fixed_folder_path = "D:\\year3+manual\\triton_fixed"
    if os.path.exists(fixed_folder_path):
        shutil.rmtree(fixed_folder_path)
    os.makedirs(fixed_folder_path, exist_ok=True)

    folder_names = [
        "UW_Triton_20250501-20250530_6330_fda",
        "UW_Triton_20250501-20250530_6331_fda",
        "UW_Triton_20250501-20250530_6332_fda",
        "UW_Triton_20250501-20250530_6333_fda",
        "UW_Triton_20250501-20250530_6334_fda",
        "UW_Triton_20250501-20250530_6335_fda",
    ]

    for folder_name in folder_names:
        folder_path = os.path.join(base_folder_path, folder_name)
        # check if folder_path exists
        if not os.path.exists(folder_path):
            print(f"Folder {folder_path} does not exist")
            continue
        dcm_files = [f for f in os.listdir(folder_path) if f.endswith(".dcm")]
        for dcm_file in dcm_files:
            dcm_file_path = os.path.join(folder_path, dcm_file)
            fixed_dcm_file_path = os.path.join(fixed_folder_path, folder_name, dcm_file)
            os.makedirs(os.path.dirname(fixed_dcm_file_path), exist_ok=True)
            triton = pydicom.dcmread(dcm_file_path)
            triton.PatientID = "AIREADI-1847"
            triton.PatientName = "AIREADI 1847"
            triton.PatientBirthDate = "19810101"
            triton.save_as(fixed_dcm_file_path, write_like_original=False)

    folder_names = [
        "UW_Triton_20250702-20250731_6882_fda",
        "UW_Triton_20250702-20250731_6881_fda",
        "UW_Triton_20250702-20250731_6880_fda",
        "UW_Triton_20250702-20250731_6879_fda",
        "UW_Triton_20250702-20250731_6878_fda",
        "UW_Triton_20250702-20250731_6877_fda",
    ]

    for folder_name in folder_names:
        folder_path = os.path.join(base_folder_path, folder_name)
        # check if folder_path exists
        if not os.path.exists(folder_path):
            print(f"Folder {folder_path} does not exist")
            continue
        dcm_files = [f for f in os.listdir(folder_path) if f.endswith(".dcm")]
        for dcm_file in dcm_files:
            dcm_file_path = os.path.join(folder_path, dcm_file)
            fixed_dcm_file_path = os.path.join(fixed_folder_path, folder_name, dcm_file)
            os.makedirs(os.path.dirname(fixed_dcm_file_path), exist_ok=True)
            triton = pydicom.dcmread(dcm_file_path)
            triton.PatientID = "AIREADI-1937"
            triton.PatientName = "AIREADI 1937"
            triton.save_as(fixed_dcm_file_path, write_like_original=False)

    folder_names = [
        "UW_Triton_20251201-20251230_8148_fda",
        "UW_Triton_20251201-20251230_8149_fda",
        "UW_Triton_20251201-20251230_8150_fda",
        "UW_Triton_20251201-20251230_8151_fda",
        "UW_Triton_20251201-20251230_8152_fda",
        "UW_Triton_20251201-20251230_8153_fda",
    ]

    for folder_name in folder_names:
        folder_path = os.path.join(base_folder_path, folder_name)
        # check if folder_path exists
        if not os.path.exists(folder_path):
            print(f"Folder {folder_path} does not exist")
            continue
        dcm_files = [f for f in os.listdir(folder_path) if f.endswith(".dcm")]
        for dcm_file in dcm_files:
            dcm_file_path = os.path.join(folder_path, dcm_file)
            fixed_dcm_file_path = os.path.join(fixed_folder_path, folder_name, dcm_file)
            os.makedirs(os.path.dirname(fixed_dcm_file_path), exist_ok=True)
            triton = pydicom.dcmread(dcm_file_path)
            triton.PatientName = "AIREADI 2138"
            triton.save_as(fixed_dcm_file_path, write_like_original=False)


def fix_maestro2():
    base_folder_path = "D:\\year3+manual\\maestro2"
    fixed_folder_path = "D:\\year3+manual\\maestro2_fixed"
    if os.path.exists(fixed_folder_path):
        shutil.rmtree(fixed_folder_path)
    os.makedirs(fixed_folder_path, exist_ok=True)

    folder_names = [
        "UW_Maestro2_20250701-20250731_8893_fda",
        "UW_Maestro2_20250701-20250731_8894_fda",
        "UW_Maestro2_20250701-20250731_8895_fda",
        "UW_Maestro2_20250701-20250731_8896_fda",
        "UW_Maestro2_20250701-20250731_8897_fda",
        "UW_Maestro2_20250701-20250731_8898_fda",
    ]

    for folder_name in folder_names:
        folder_path = os.path.join(base_folder_path, folder_name)
        # check if folder_path exists
        if not os.path.exists(folder_path):
            print(f"Folder {folder_path} does not exist")
            continue
        dcm_files = [f for f in os.listdir(folder_path) if f.endswith(".dcm")]
        for dcm_file in dcm_files:
            dcm_file_path = os.path.join(folder_path, dcm_file)
            fixed_dcm_file_path = os.path.join(fixed_folder_path, folder_name, dcm_file)
            os.makedirs(os.path.dirname(fixed_dcm_file_path), exist_ok=True)
            maestro2 = pydicom.dcmread(dcm_file_path)
            maestro2.PatientName = "AIREADI 1909"
            maestro2.save_as(fixed_dcm_file_path, write_like_original=False)

    folder_names = [
        "UCSD_Maestro2_20250501-20250531_4617_fda",
        "UCSD_Maestro2_20250501-20250531_4616_fda",
        "UCSD_Maestro2_20250501-20250531_4615_fda",
        "UCSD_Maestro2_20250501-20250531_4614_fda",
        "UCSD_Maestro2_20250501-20250531_4613_fda",
        "UCSD_Maestro2_20250501-20250531_4611_fda",
    ]

    for folder_name in folder_names:
        folder_path = os.path.join(base_folder_path, folder_name)
        # check if folder_path exists
        if not os.path.exists(folder_path):
            print(f"Folder {folder_path} does not exist")
            continue
        dcm_files = [f for f in os.listdir(folder_path) if f.endswith(".dcm")]
        for dcm_file in dcm_files:
            dcm_file_path = os.path.join(folder_path, dcm_file)
            fixed_dcm_file_path = os.path.join(fixed_folder_path, folder_name, dcm_file)
            os.makedirs(os.path.dirname(fixed_dcm_file_path), exist_ok=True)
            maestro2 = pydicom.dcmread(dcm_file_path)
            maestro2.PatientID = "AIREADI-4698"
            maestro2.PatientName = "AIREADI 4698"
            maestro2.save_as(fixed_dcm_file_path, write_like_original=False)

    folder_names = [
        "UCSD_Maestro2_20251001-20251031_605_fda",
        "UCSD_Maestro2_20251001-20251031_604_fda",
        "UCSD_Maestro2_20251001-20251031_603_fda",
        "UCSD_Maestro2_20251001-20251031_602_fda",
        "UCSD_Maestro2_20251001-20251031_601_fda",
        "UCSD_Maestro2_20251001-20251031_600_fda",
    ]

    for folder_name in folder_names:
        folder_path = os.path.join(base_folder_path, folder_name)
        # check if folder_path exists
        if not os.path.exists(folder_path):
            print(f"Folder {folder_path} does not exist")
            continue
        dcm_files = [f for f in os.listdir(folder_path) if f.endswith(".dcm")]
        for dcm_file in dcm_files:
            dcm_file_path = os.path.join(folder_path, dcm_file)
            fixed_dcm_file_path = os.path.join(fixed_folder_path, folder_name, dcm_file)
            os.makedirs(os.path.dirname(fixed_dcm_file_path), exist_ok=True)
            maestro2 = pydicom.dcmread(dcm_file_path)
            maestro2.PatientID = "AIREADI-4940"
            maestro2.PatientName = "AIREADI 4940"
            maestro2.save_as(fixed_dcm_file_path, write_like_original=False)


if __name__ == "__main__":
    # fix_triton()
    fix_maestro2()
