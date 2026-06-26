from pathlib import Path
import re
import requests
import pdfplumber
import pandas as pd


BASE_DIR = Path(__file__).resolve().parents[1]
RAW_DIR = BASE_DIR / "data" / "raw"

PDF_URL = "https://digitalhub.fifa.com/m/636f5c9c6f29771f/original/FWC2026_regulations_EN.pdf"
PDF_PATH = RAW_DIR / "FWC2026_regulations_EN.pdf"
OUTPUT_PATH = RAW_DIR / "third_place_mapping.csv"


EXPECTED_COLUMNS = [
    "BestThirdGroups",
    "OpponentFor1A",
    "OpponentFor1B",
    "OpponentFor1D",
    "OpponentFor1E",
    "OpponentFor1G",
    "OpponentFor1I",
    "OpponentFor1K",
    "OpponentFor1L",
]


def download_pdf():
    RAW_DIR.mkdir(parents=True, exist_ok=True)

    if PDF_PATH.exists():
        print(f"PDF already exists: {PDF_PATH}")
        return

    print("Downloading FIFA regulations PDF...")
    response = requests.get(PDF_URL, timeout=60)
    response.raise_for_status()

    PDF_PATH.write_bytes(response.content)
    print(f"Downloaded PDF to: {PDF_PATH}")


def parse_mapping_line(line: str):
    """
    Parses Annexe C rows that look like:

    1 3E 3J 3I 3F 3H 3G 3L 3K

    The eight third-place codes are ordered as FIFA's Annexe C columns:
    1A, 1B, 1D, 1E, 1G, 1I, 1K, 1L
    """

    line = line.strip()
    line = re.sub(r"\s+", " ", line)

    match = re.match(
        r"^(\d{1,3})\s+"
        r"(3[A-L])\s+"
        r"(3[A-L])\s+"
        r"(3[A-L])\s+"
        r"(3[A-L])\s+"
        r"(3[A-L])\s+"
        r"(3[A-L])\s+"
        r"(3[A-L])\s+"
        r"(3[A-L])$",
        line
    )

    if not match:
        return None

    row_number = int(match.group(1))
    codes = list(match.groups()[1:])

    best_third_groups = "".join(
        sorted(code.replace("3", "") for code in codes)
    )

    return {
        "RowNumber": row_number,
        "BestThirdGroups": best_third_groups,
        "OpponentFor1A": codes[0],
        "OpponentFor1B": codes[1],
        "OpponentFor1D": codes[2],
        "OpponentFor1E": codes[3],
        "OpponentFor1G": codes[4],
        "OpponentFor1I": codes[5],
        "OpponentFor1K": codes[6],
        "OpponentFor1L": codes[7],
    }


def extract_mapping_from_pdf_text():
    rows = []

    print("Reading PDF text and searching for Annexe C mapping rows...")

    with pdfplumber.open(PDF_PATH) as pdf:
        for page_number, page in enumerate(pdf.pages, start=1):
            text = page.extract_text() or ""

            # Annexe C appears near the end of the PDF.
            # Scanning all pages is fine because the regex only accepts rows
            # that start with a number and exactly eight 3A-3L codes.
            for line in text.splitlines():
                parsed = parse_mapping_line(line)

                if parsed is not None:
                    rows.append(parsed)

    return rows


def validate_mapping(mapping_df: pd.DataFrame):
    print()
    print("Validating extracted mapping...")

    if mapping_df.empty:
        raise ValueError("No mapping rows were extracted.")

    missing_columns = set(EXPECTED_COLUMNS) - set(mapping_df.columns)
    if missing_columns:
        raise ValueError(f"Missing expected columns: {missing_columns}")

    row_count = len(mapping_df)
    print(f"Extracted rows: {row_count}")

    if row_count != 495:
        print()
        print("Warning: FIFA says this table should have 495 combinations.")
        print("If this is not 495, we need to inspect the missed rows.")
    else:
        print("Row count looks correct: 495")

    duplicate_row_numbers = mapping_df["RowNumber"].duplicated().sum()
    if duplicate_row_numbers > 0:
        duplicates = mapping_df[
            mapping_df["RowNumber"].duplicated(keep=False)
        ].sort_values("RowNumber")

        print(duplicates)
        raise ValueError(f"Found {duplicate_row_numbers} duplicate RowNumber values.")

    duplicate_combinations = mapping_df["BestThirdGroups"].duplicated().sum()
    if duplicate_combinations > 0:
        duplicates = mapping_df[
            mapping_df["BestThirdGroups"].duplicated(keep=False)
        ].sort_values("BestThirdGroups")

        print(duplicates)
        raise ValueError(f"Found {duplicate_combinations} duplicate BestThirdGroups rows.")

    expected_row_numbers = set(range(1, 496))
    actual_row_numbers = set(mapping_df["RowNumber"].tolist())
    missing_row_numbers = sorted(expected_row_numbers - actual_row_numbers)

    if missing_row_numbers:
        raise ValueError(f"Missing row numbers: {missing_row_numbers}")

    invalid_group_rows = mapping_df[
        mapping_df["BestThirdGroups"].str.len() != 8
    ]

    if not invalid_group_rows.empty:
        print(invalid_group_rows)
        raise ValueError("Some BestThirdGroups values do not have exactly 8 letters.")

    assignment_columns = [
        "OpponentFor1A",
        "OpponentFor1B",
        "OpponentFor1D",
        "OpponentFor1E",
        "OpponentFor1G",
        "OpponentFor1I",
        "OpponentFor1K",
        "OpponentFor1L",
    ]

    for column in assignment_columns:
        bad_values = mapping_df[
            ~mapping_df[column].str.match(r"^3[A-L]$")
        ]

        if not bad_values.empty:
            print(bad_values[["RowNumber", "BestThirdGroups", column]])
            raise ValueError(f"Invalid third-place values found in {column}.")

    print("Validation complete.")


def main():
    download_pdf()

    rows = extract_mapping_from_pdf_text()

    mapping_df = pd.DataFrame(rows)

    if not mapping_df.empty:
        mapping_df = mapping_df.drop_duplicates()
        mapping_df = mapping_df.sort_values("RowNumber")

    validate_mapping(mapping_df)

    output_columns = [
        "BestThirdGroups",
        "OpponentFor1A",
        "OpponentFor1B",
        "OpponentFor1D",
        "OpponentFor1E",
        "OpponentFor1G",
        "OpponentFor1I",
        "OpponentFor1K",
        "OpponentFor1L",
    ]

    final_df = mapping_df[output_columns].copy()

    final_df.to_csv(OUTPUT_PATH, index=False)

    print()
    print(f"Saved official third-place mapping to: {OUTPUT_PATH}")
    print()
    print(final_df.head())


if __name__ == "__main__":
    main()