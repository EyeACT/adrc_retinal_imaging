import csv
import os
from collections import defaultdict

RAW_DIR = "/Volumes/Crucial X10/adrc/raw/acuity"
PROCESSED_DIR = "/Volumes/Crucial X10/adrc/processed/acuity"

ACUITY_PREFIX = "Acuity_All_"
ACFCSFS_PREFIX = "ACSFSAndLinearContrast_All_"


def find_csv_files(base_dir):
    files = []
    for root, _, fnames in os.walk(base_dir):
        for fname in fnames:
            if fname.lower().endswith(".csv") and not fname.startswith("._"):
                files.append(os.path.join(root, fname))
    return sorted(files)


def bucket_files(files):
    acuity, acfcsfs, other = [], [], []
    for f in files:
        name = os.path.basename(f)
        if name.startswith(ACUITY_PREFIX):
            acuity.append(f)
        elif name.startswith(ACFCSFS_PREFIX):
            acfcsfs.append(f)
        else:
            other.append(f)
    return acuity, acfcsfs, other


def read_unique_records(files):
    header = None
    seen = set()
    records = []
    for f in files:
        with open(f, newline="", encoding="utf-8-sig", errors="replace") as fh:
            reader = csv.reader(fh)
            file_header = next(reader)
            if header is None:
                header = file_header
            elif file_header != header:
                raise ValueError(f"Header mismatch in {f}: {file_header} != {header}")
            for row in reader:
                key = tuple(row)
                if key in seen:
                    continue
                seen.add(key)
                records.append(row)
    return header, records


def split_by_subject(header, records):
    subject_idx = header.index("SUBJECTID")
    by_subject = defaultdict(list)
    for row in records:
        subject = row[subject_idx].strip()
        by_subject[subject].append(row)
    return by_subject


def write_subject_files(by_subject, header, out_filename):
    for subject, rows in by_subject.items():
        out_dir = os.path.join(PROCESSED_DIR, subject)
        os.makedirs(out_dir, exist_ok=True)
        out_path = os.path.join(out_dir, out_filename)
        with open(out_path, "w", newline="", encoding="utf-8") as fh:
            writer = csv.writer(fh)
            writer.writerow(header)
            writer.writerows(rows)


def main():
    files = find_csv_files(RAW_DIR)
    acuity_files, acfcsfs_files, other_files = bucket_files(files)

    print(f"Found {len(files)} CSV files under {RAW_DIR}")
    print(f"  {ACUITY_PREFIX}*: {len(acuity_files)}")
    print(f"  {ACFCSFS_PREFIX}*: {len(acfcsfs_files)}")
    print(f"  Unmatched (not used): {len(other_files)}")
    for f in other_files:
        print(f"    - {f}")

    acuity_header, acuity_records = read_unique_records(acuity_files)
    print(f"Acuity unique records: {len(acuity_records)}")

    acfcsfs_header, acfcsfs_records = read_unique_records(acfcsfs_files)
    print(f"ACSFSAndLinearContrast unique records: {len(acfcsfs_records)}")

    acuity_by_subject = split_by_subject(acuity_header, acuity_records)
    acfcsfs_by_subject = split_by_subject(acfcsfs_header, acfcsfs_records)

    write_subject_files(acuity_by_subject, acuity_header, "Acuity.csv")
    write_subject_files(acfcsfs_by_subject, acfcsfs_header, "ACFCSFSAndLinearContrast.csv")

    all_subjects = sorted(set(acuity_by_subject) | set(acfcsfs_by_subject))
    print(f"Wrote data for {len(all_subjects)} unique subjects to {PROCESSED_DIR}")


if __name__ == "__main__":
    main()
