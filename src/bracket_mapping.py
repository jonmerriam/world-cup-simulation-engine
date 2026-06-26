from pathlib import Path
import pandas as pd


BASE_DIR = Path(__file__).resolve().parents[1]
RAW_DIR = BASE_DIR / "data" / "raw"

THIRD_PLACE_MAPPING_PATH = RAW_DIR / "third_place_mapping.csv"


THIRD_PLACE_COLUMNS = {
    "1A": "OpponentFor1A",
    "1B": "OpponentFor1B",
    "1D": "OpponentFor1D",
    "1E": "OpponentFor1E",
    "1G": "OpponentFor1G",
    "1I": "OpponentFor1I",
    "1K": "OpponentFor1K",
    "1L": "OpponentFor1L",
}


def load_third_place_mapping() -> pd.DataFrame:
    mapping = pd.read_csv(THIRD_PLACE_MAPPING_PATH)

    required_columns = [
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

    missing_columns = set(required_columns) - set(mapping.columns)

    if missing_columns:
        raise ValueError(f"Third-place mapping file is missing columns: {missing_columns}")

    return mapping


def get_third_place_mapping_row(best_third_groups: list[str]) -> pd.Series:
    mapping = load_third_place_mapping()

    key = "".join(sorted(best_third_groups))

    match = mapping[mapping["BestThirdGroups"] == key]

    if match.empty:
        raise ValueError(
            f"No FIFA third-place mapping found for best third-place groups: {key}"
        )

    return match.iloc[0]


def get_opponent_code_for_group_winner(mapping_row: pd.Series, group_winner_code: str) -> str:
    """
    Example:
    group_winner_code = '1A'
    returns something like '3E'
    """

    if group_winner_code not in THIRD_PLACE_COLUMNS:
        raise ValueError(f"Unsupported group winner code: {group_winner_code}")

    column_name = THIRD_PLACE_COLUMNS[group_winner_code]
    return mapping_row[column_name]