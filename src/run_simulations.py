from pathlib import Path
from datetime import datetime
import json

import pandas as pd

from load_data import load_groups, load_ratings
from simulate_tournament import simulate_one_tournament


BASE_DIR = Path(__file__).resolve().parents[1]
PROCESSED_DIR = BASE_DIR / "data" / "processed"

SIMULATION_RESULTS_PATH = PROCESSED_DIR / "simulation_results.csv"
METADATA_OUTPUT_PATH = PROCESSED_DIR / "simulation_metadata.json"


ROUND_COLUMNS = [
    "GroupWinner",
    "AdvanceR32",
    "AdvanceR16",
    "Quarterfinals",
    "Semifinals",
    "Final",
    "Champion",
]

GROUP_COLUMNS = [
    "Finish1st",
    "Finish2nd",
    "Finish3rd",
    "Finish4th",
    "AdvanceFromGroup",
    "EliminatedInGroup",
]


RATING_SOURCE = "World Football Elo"
HOST_ELO_BOOST = 35
STRENGTH_ADJUSTMENT = 0.60
THIRD_PLACE_MAPPING = "Official FIFA Annexe C"
KNOCKOUT_PATH = "Official FIFA 2026 M73-M104 path"


def initialize_tracking(groups: pd.DataFrame) -> pd.DataFrame:
    """
    Creates the tracking table that will store how many times each team
    reaches each stage across all simulations.
    """

    tracking = groups.copy()

    for column in GROUP_COLUMNS + ROUND_COLUMNS:
        tracking[column] = 0

    return tracking


def increment_team_count(tracking: pd.DataFrame, team: str, column: str):
    """
    Adds 1 to a team's count for a given tracking column.
    """

    tracking.loc[tracking["Team"] == team, column] += 1


def update_group_tracking(tracking: pd.DataFrame, tournament: dict):
    """
    Updates group finish counts and group advancement counts.
    """

    group_tables = tournament["GroupTables"]

    if "Qualifiers" in tournament:
        qualifiers = tournament["Qualifiers"]
    elif "QualifiedTeams" in tournament:
        qualifiers = tournament["QualifiedTeams"]
    else:
        raise KeyError("Tournament output is missing both 'Qualifiers' and 'QualifiedTeams'.")

    qualified_team_names = set(qualifiers["Team"].tolist())

    for _, row in group_tables.iterrows():
        team = row["Team"]
        group_rank = int(row["GroupRank"])

        if group_rank == 1:
            increment_team_count(tracking, team, "Finish1st")
            increment_team_count(tracking, team, "GroupWinner")
        elif group_rank == 2:
            increment_team_count(tracking, team, "Finish2nd")
        elif group_rank == 3:
            increment_team_count(tracking, team, "Finish3rd")
        elif group_rank == 4:
            increment_team_count(tracking, team, "Finish4th")

        if team in qualified_team_names:
            increment_team_count(tracking, team, "AdvanceFromGroup")
            increment_team_count(tracking, team, "AdvanceR32")
        else:
            increment_team_count(tracking, team, "EliminatedInGroup")


def update_knockout_tracking(tracking: pd.DataFrame, tournament: dict):
    """
    Updates knockout advancement counts based on match winners.

    Meaning of columns:
    - AdvanceR32: reached the Round of 32
    - AdvanceR16: reached the Round of 16
    - Quarterfinals: reached the Quarterfinals
    - Semifinals: reached the Semifinals
    - Final: reached the Final
    - Champion: won the tournament
    """

    knockout_results = tournament["KnockoutResults"]

    round_to_column = {
        "Round of 32": "AdvanceR16",
        "Round of 16": "Quarterfinals",
        "Quarterfinals": "Semifinals",
        "Semifinals": "Final",
        "Final": "Champion",
    }

    for _, row in knockout_results.iterrows():
        round_name = row["Round"]
        winner = row["Winner"]

        if round_name not in round_to_column:
            continue

        column = round_to_column[round_name]
        increment_team_count(tracking, winner, column)


def calculate_probabilities(
    tracking: pd.DataFrame,
    ratings: pd.DataFrame,
    n_sims: int
) -> pd.DataFrame:
    """
    Converts raw simulation counts into probabilities.
    """

    results = tracking.copy()

    probability_columns = GROUP_COLUMNS + ROUND_COLUMNS

    for column in probability_columns:
        results[column] = results[column] / n_sims

    ratings_columns = [
        column for column in ratings.columns
        if column != "Group"
    ]

    ratings_for_merge = ratings[ratings_columns].copy()

    results = results.merge(
        ratings_for_merge,
        on="Team",
        how="left"
    )

    preferred_column_order = [
        "Group",
        "Team",
        "Elo",
        "HostEloBoost",
        "AdjustedElo",
        "Rating",
        "Attack",
        "Defense",
        "Finish1st",
        "Finish2nd",
        "Finish3rd",
        "Finish4th",
        "AdvanceFromGroup",
        "EliminatedInGroup",
        "GroupWinner",
        "AdvanceR32",
        "AdvanceR16",
        "Quarterfinals",
        "Semifinals",
        "Final",
        "Champion",
    ]

    existing_preferred_columns = [
        column for column in preferred_column_order
        if column in results.columns
    ]

    other_columns = [
        column for column in results.columns
        if column not in existing_preferred_columns
    ]

    results = results[existing_preferred_columns + other_columns]

    results = results.sort_values(
        by="Champion",
        ascending=False
    )

    return results


def save_simulation_metadata(n_sims: int):
    """
    Saves metadata explaining how the simulation results were generated.
    The Streamlit app displays this information.
    """

    metadata = {
        "n_sims": n_sims,
        "rating_source": RATING_SOURCE,
        "host_elo_boost": HOST_ELO_BOOST,
        "strength_adjustment": STRENGTH_ADJUSTMENT,
        "third_place_mapping": THIRD_PLACE_MAPPING,
        "knockout_path": KNOCKOUT_PATH,
        "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    }

    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)

    with open(METADATA_OUTPUT_PATH, "w", encoding="utf-8") as file:
        json.dump(metadata, file, indent=4)

    print(f"Saved simulation metadata to: {METADATA_OUTPUT_PATH}")


def run_simulations(n_sims: int = 1000, progress_callback=None) -> pd.DataFrame:
    """
    Runs the full World Cup simulation many times and calculates each team's
    probability of reaching each tournament stage.

    progress_callback is optional and is used by the Streamlit app to update
    a progress bar.
    """

    groups = load_groups()
    ratings = load_ratings()

    tracking = initialize_tracking(groups)

    for simulation_number in range(1, n_sims + 1):
        tournament = simulate_one_tournament(groups, ratings)

        update_group_tracking(tracking, tournament)
        update_knockout_tracking(tracking, tournament)

        if progress_callback is not None:
            if simulation_number % 5 == 0 or simulation_number == n_sims:
                progress_callback(simulation_number, n_sims)

        if simulation_number % 100 == 0 or simulation_number == n_sims:
            print(f"Completed {simulation_number:,} of {n_sims:,} simulations")

    results = calculate_probabilities(
        tracking=tracking,
        ratings=ratings,
        n_sims=n_sims
    )

    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)

    results.to_csv(SIMULATION_RESULTS_PATH, index=False)
    print(f"Saved simulation results to: {SIMULATION_RESULTS_PATH}")

    save_simulation_metadata(n_sims)

    return results


if __name__ == "__main__":
    results = run_simulations(n_sims=1000)

    print()
    print("Top 20 simulation results:")
    print(
        results[
            [
                "Group",
                "Team",
                "Finish1st",
                "Finish2nd",
                "Finish3rd",
                "Finish4th",
                "AdvanceFromGroup",
                "AdvanceR16",
                "Quarterfinals",
                "Semifinals",
                "Final",
                "Champion",
            ]
        ].head(20)
    )