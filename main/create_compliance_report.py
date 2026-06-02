import argparse
import os
import sys

# Add year_3 directory to path - OS agnostic
year_3_path = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "year_3"
)
sys.path.append(year_3_path)

import compliance_report
import compliance_rules
import imaging_utils
import nested_structure_excel
import pydicom

print(pydicom.__version__)

from pydicom.datadict import DicomDictionary, keyword_dict
from pydicom.dataset import Dataset

# Define items as (VR, VM, description, is_retired flag, keyword)
#   Leave is_retired flag blank.
new_dict_items = {
    0x00221627: (
        "SQ",
        "1",
        "En Face Volume Descriptor Sequence",
        "",
        "EnFaceVolumeDescriptorSequence",
    ),
    0x00221629: (
        "CS",
        "1",
        "En Face Volume Descriptor Scope",
        "",
        "EnFaceVolumeDescriptorScope",
    ),
    0x0008114C: (
        "SQ",
        "1",
        "Referenced Segmentation Sequence",
        "",
        "ReferencedSegmentationSequence",
    ),
    0x00660005: ("FL", "1", "Surface Offset", "", "SurfaceOffset"),
}

# Update the dictionary itself
DicomDictionary.update(new_dict_items)

# Update the reverse mapping from name to tag
new_names_dict = dict([(val[4], tag) for tag, val in new_dict_items.items()])
keyword_dict.update(new_names_dict)


def sort_them_by_sop_class(input_folder, device_protocol, output_folder):
    # Initialize lists to store files based on SOP Class
    sop_class_1 = []
    sop_class_2 = []
    sop_class_3 = []
    sop_class_4 = []
    sop_class_5 = []
    sop_class_6 = []

    device_protocol = device_protocol
    device = device_protocol.split("_")[0]

    output_path = os.path.join(output_folder, device)
    os.makedirs(output_path, exist_ok=True)

    # Get a list of all files in the input folder
    input_list = imaging_utils.get_filtered_file_names(input_folder)
    input_list = sorted(input_list, key=imaging_utils.extract_numeric_part)

    for file in input_list:
        dicom = pydicom.dcmread(file)
        sop_class = dicom.SOPClassUID

        # Sort files based on SOP class
        if sop_class == "1.2.840.10008.5.1.4.1.1.77.1.5.1":
            sop_class_1.append(file)
        elif sop_class == "1.2.840.10008.5.1.4.1.1.77.1.5.4":
            sop_class_2.append(file)
        elif sop_class == "1.2.840.10008.5.1.4.1.1.77.1.5.8":
            sop_class_3.append(file)
        elif (
            sop_class == "1.2.840.10008.5.1.4.xxxxx.1"
            or sop_class == "1.2.840.10008.5.1.4.1.1.66.5"
            or sop_class == "1.3.6.1.4.1.33437.11.10.240.10"
            or sop_class == "1.2.840.10008.5.1.4.1.1.66.8"
        ):
            sop_class_4.append(file)
        elif sop_class == "1.2.840.10008.5.1.4.1.1.77.1.5.7":
            sop_class_5.append(file)

        elif sop_class == "1.2.840.10008.5.1.4.1.1.77.1.5.2":
            sop_class_6.append(file)

    if sop_class_1:
        compliance_report.create_report(
            compliance_rules.cfp_ir_rule,
            sorted(sop_class_1),
            os.path.join(output_folder, device, f"{device_protocol}_eval_op.xlsx"),
        )

        nested_structure_excel.multi_create_excelsheet_nested_structure(
            sorted(sop_class_1),
            [  # anatomic region
                "00082218",
                # patient eye movement
                "00220006",
                # acquisition device type code sequence
                "00220015",
                # IlluminationTypeCodeSequence
                "00220016",
                # LightPathFilterTypeStackCodeSequence
                "00220017",
                # ImagePathFilterTypeStackCodeSequence
                "00220018",
                # LensesCodeSequence
                "00220019",
                # channel description
                "0022001A",
            ],
            os.path.join(
                output_folder, device, f"{device_protocol}_eval_op_nested.xlsx"
            ),
        )

    if sop_class_2:

        compliance_report.create_report(
            compliance_rules.oct_b_rule,
            sorted(sop_class_2),
            os.path.join(output_folder, device, f"{device_protocol}_eval_oct.xlsx"),
        )
        nested_structure_excel.multi_create_excelsheet_nested_structure(
            sorted(sop_class_2),
            [  # SharedFunctionalGroupsSequence
                "52009229",
                # PerFrameFunctionalGroupsSequence
                "52009230",
                # Dimension Organization Sequence
                "00209221",
                # Dimension Index Sequence
                "00209222",
                # Acquisition Context Sequence
                "00400555",
                # AcquisitionDeviceTypeCodeSequence
                "00220015",
                # LightPathFilterTypeStackCodeSequence
                "00220017",
                # AnatomicRegionSequence
                "00082218",
            ],
            os.path.join(
                output_folder, device, f"{device_protocol}_eval_oct_nested.xlsx"
            ),
        )

    if sop_class_3:
        # # oct volume
        compliance_report.create_report(
            compliance_rules.volume_analysis_rule,
            sorted(sop_class_3),
            os.path.join(
                output_folder, device, f"{device_protocol}_eval_volume_analysis.xlsx"
            ),
        )

        # # oct volume
        nested_structure_excel.multi_create_excelsheet_nested_structure(
            sorted(sop_class_3),
            [  # SharedFunctionalGroupsSequence
                "52009229",
                # PerFrameFunctionalGroupsSequence
                "52009230",
                # Dimension Organization Sequence
                "00209221",
                # Dimension Index Sequence
                "00209222",
                # AcquisitionMethodAlgorithmSequence
                "00221423",
                # OCTBScanAnalysisAcquisitionParametersSequence
                "00221640",
            ],
            os.path.join(
                output_folder,
                device,
                f"{device_protocol}_eval_volume_analysis_nested.xlsx",
            ),
        )

    # segmentation
    if sop_class_4:
        compliance_report.create_report(
            compliance_rules.heightmap_rule,
            sorted(sop_class_4),
            os.path.join(
                output_folder,
                device,
                f"{device_protocol}_eval_heightmap_segmentation.xlsx",
            ),
        )

        nested_structure_excel.multi_create_excelsheet_nested_structure(
            sorted(sop_class_4),
            [  # SharedFunctionalGroupsSequence
                "52009229",
                # PerFrameFunctionalGroupsSequence
                "52009230",
                # Dimension Organization Sequence
                "00209221",
                # Dimension Index Sequence
                "00209222",
                # SegmentSequence
                "00620002",
                # ReferencedSeriesSequence
                "00081115",
            ],
            os.path.join(
                output_folder,
                device,
                f"{device_protocol}_eval_heightmap_segmentation_nested.xlsx",
            ),
        )

    # Enface
    if sop_class_5:
        compliance_report.create_report(
            compliance_rules.octa_enface_rule,
            sorted(sop_class_5),
            os.path.join(output_folder, device, f"{device_protocol}_eval_en_face.xlsx"),
        )

        # compliance_report.create_report(
        #     compliance_rules.octa_old_enface_rule,
        #     sorted(sop_class_5),
        #     os.path.join(output_folder, device, f"{device_protocol}_eval_en_face_old.xlsx"),
        # )

        nested_structure_excel.multi_create_excelsheet_nested_structure(
            sorted(sop_class_5),
            [
                # SourceImageSequence
                "00082112",
                # DerivationAlgorithmSequence
                "00221612",
                # OphthalmicImageTypeCodeSequence
                "00221615",
                # ReferencedSurfaceMeshIdentificationSequence
                "00221620",
                # AnatomicRegionSequence
                "00082218",
                # RelativeImagePositionCodeSequence
                "0022001D",
                # PrimaryAnatomicStructureSequence
                "00082228",
                # OphahtlmicFrameLocationSequence
                "00220031",
                "0022EEE0",
                "00081115",
                # new tag
                "00221627",
                # new tag
                "00221632",
            ],
            os.path.join(
                output_folder, device, f"{device_protocol}_eval_enface_nested.xlsx"
            ),
        )

    if sop_class_6:
        compliance_report.create_report(
            compliance_rules.cfp_ir_16_rule,
            sorted(sop_class_6),
            os.path.join(output_folder, device, f"{device_protocol}_op_16.xlsx"),
        )

        # 2d
        nested_structure_excel.multi_create_excelsheet_nested_structure(
            sorted(sop_class_6),
            [  # anatomic region
                "00082218",
                # patient eye movement
                "00220006",
                # acquisition device type code sequence
                "00220015",
                # IlluminationTypeCodeSequence
                "00220016",
                # LightPathFilterTypeStackCodeSequence
                "00220017",
                # ImagePathFilterTypeStackCodeSequence
                "00220018",
                # LensesCodeSequence
                "00220019",
                # channel description
                "0022001A",
            ],
            os.path.join(output_folder, device, f"{device_protocol}_op_16_nested.xlsx"),
        )
    return (
        sop_class_1,
        sop_class_2,
        sop_class_3,
        sop_class_4,
        sop_class_5,
        sop_class_6,
    )


if __name__ == "__main__":
    # 1. Create an ArgumentParser object
    parser = argparse.ArgumentParser(
        description="Sort DICOM files by SOP Class UID and generate compliance reports."
    )

    # 2. Add arguments for input folder, device name, and output folder
    parser.add_argument(
        "input_folder",
        type=str,
        help="Path to the folder containing the input DICOM files.",
    )
    parser.add_argument(
        "device_name",
        type=str,
        help="A unique name for the device and protocol (e.g., 'Heidelberg_Spectralis_OCT').",
    )
    parser.add_argument(
        "output_folder",
        type=str,
        help="Path to the folder where the output reports will be saved.",
    )

    # 3. Parse the command-line arguments
    args = parser.parse_args()

    # 4. Call the main function with the parsed arguments
    print("--- Starting DICOM Sorting and Reporting ---")

    sop1, sop2, sop3, sop4, sop5, sop6 = sort_them_by_sop_class(
        input_folder=args.input_folder,
        device_protocol=args.device_name,
        output_folder=args.output_folder,
    )

    print("\n--- Analysis Complete ---")
    print(
        f"Found {len(sop1)} files for Ophthalmic Photography 8 Bit Image (SOP Class 1)"
    )
    print(f"Found {len(sop2)} files for Ophthalmic Tomography Image (SOP Class 2)")
    print(f"Found {len(sop3)} files for Ophthalmic Tomography Volume (SOP Class 3)")
    print(f"Found {len(sop4)} files for Segmentation (SOP Class 4)")
    print(f"Found {len(sop5)} files for En Face (SOP Class 5)")
    print(
        f"Found {len(sop6)} files for Ophthalmic Photography 16 Bit Image (SOP Class 6)"
    )
    print(f"\nAll reports have been saved in the '{args.output_folder}' directory.")
    print("-----------------------------------------")
