from pathlib import Path
import pandas as pd


BASE_DIR = Path(__file__).resolve().parents[1]
RAW_DIR = BASE_DIR / "data" / "raw"

ELO_INPUT_PATH = RAW_DIR / "team_elo_ratings.csv"
TEAM_RATINGS_OUTPUT_PATH = RAW_DIR / "team_ratings.csv"


HOST_TEAMS = {
    "United States",
    "Mexico",
    "Canada",
}

HOST_ELO_BOOST = 35


def scale_elo_to_rating(elo: float, min_elo: float, max_elo: float) -> float:
    """
    Converts Elo ratings into the existing 60-100 rating scale.

    The lowest Elo team in the tournament gets around 60.
    The highest Elo team in the tournament gets around 100.
    Everyone else is scaled between those values.
    """

    if max_elo == min_elo:
        return 80

    rating = 60 + ((elo - min_elo) / (max_elo - min_elo)) * 40
    return round(rating, 2)


def build_team_ratings():
    elo_df = pd.read_csv(ELO_INPUT_PATH)

    required_columns = {"Team", "Elo"}
    missing_columns = required_columns - set(elo_df.columns)

    if missing_columns:
        raise ValueError(f"Missing required columns: {missing_columns}")

    if elo_df["Elo"].isna().any():
        missing_teams = elo_df[elo_df["Elo"].isna()]["Team"].tolist()
        raise ValueError(f"These teams are missing Elo ratings: {missing_teams}")

    elo_df["HostEloBoost"] = elo_df["Team"].apply(
        lambda team: HOST_ELO_BOOST if team in HOST_TEAMS else 0
    )

    elo_df["AdjustedElo"] = elo_df["Elo"] + elo_df["HostEloBoost"]

    min_adjusted_elo = elo_df["AdjustedElo"].min()
    max_adjusted_elo = elo_df["AdjustedElo"].max()

    elo_df["Rating"] = elo_df["AdjustedElo"].apply(
        lambda elo: scale_elo_to_rating(
            elo,
            min_adjusted_elo,
            max_adjusted_elo
        )
    )

    # First Elo-only version:
    # Attack and Defense are both based on overall Elo strength.
    # We are intentionally NOT using recent form yet.
    elo_df["Attack"] = elo_df["Rating"]
    elo_df["Defense"] = elo_df["Rating"]

    output_columns = [
        "Team",
        "Elo",
        "HostEloBoost",
        "AdjustedElo",
        "Rating",
        "Attack",
        "Defense",
    ]

    final_df = elo_df[output_columns].sort_values(
        by="AdjustedElo",
        ascending=False
    )

    final_df.to_csv(TEAM_RATINGS_OUTPUT_PATH, index=False)

    print(f"Created updated ratings file: {TEAM_RATINGS_OUTPUT_PATH}")
    print()
    print(final_df.head(15))


if __name__ == "__main__":
    build_team_ratings()