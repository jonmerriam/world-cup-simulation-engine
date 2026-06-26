from pathlib import Path
import sys
from itertools import combinations

import pandas as pd

# Allows imports when running this file directly
BASE_DIR = Path(__file__).resolve().parents[1]
SRC_DIR = BASE_DIR / "src"
sys.path.append(str(SRC_DIR))

from load_data import load_groups, load_ratings
from simulate_match import simulate_group_match


def initialize_group_table(teams: list[str]) -> dict:
    table = {}

    for team in teams:
        table[team] = {
            "Team": team,
            "Played": 0,
            "Wins": 0,
            "Draws": 0,
            "Losses": 0,
            "GoalsFor": 0,
            "GoalsAgainst": 0,
            "GoalDifference": 0,
            "Points": 0,
        }

    return table


def update_group_table(table: dict, match: dict) -> None:
    team_a = match["TeamA"]
    team_b = match["TeamB"]
    goals_a = match["GoalsA"]
    goals_b = match["GoalsB"]

    table[team_a]["Played"] += 1
    table[team_b]["Played"] += 1

    table[team_a]["GoalsFor"] += goals_a
    table[team_a]["GoalsAgainst"] += goals_b

    table[team_b]["GoalsFor"] += goals_b
    table[team_b]["GoalsAgainst"] += goals_a

    if goals_a > goals_b:
        table[team_a]["Wins"] += 1
        table[team_b]["Losses"] += 1
        table[team_a]["Points"] += 3
    elif goals_b > goals_a:
        table[team_b]["Wins"] += 1
        table[team_a]["Losses"] += 1
        table[team_b]["Points"] += 3
    else:
        table[team_a]["Draws"] += 1
        table[team_b]["Draws"] += 1
        table[team_a]["Points"] += 1
        table[team_b]["Points"] += 1

    table[team_a]["GoalDifference"] = (
        table[team_a]["GoalsFor"] - table[team_a]["GoalsAgainst"]
    )
    table[team_b]["GoalDifference"] = (
        table[team_b]["GoalsFor"] - table[team_b]["GoalsAgainst"]
    )


def calculate_head_to_head_points(
    tied_teams: list[str],
    match_results: list[dict]
) -> dict:
    """
    Calculates points earned only in matches played between the tied teams.

    This is used as the first tiebreaker after total group points.
    """

    head_to_head_points = {
        team: 0
        for team in tied_teams
    }

    tied_team_set = set(tied_teams)

    for match in match_results:
        team_a = match["TeamA"]
        team_b = match["TeamB"]

        if team_a not in tied_team_set or team_b not in tied_team_set:
            continue

        goals_a = match["GoalsA"]
        goals_b = match["GoalsB"]

        if goals_a > goals_b:
            head_to_head_points[team_a] += 3
        elif goals_b > goals_a:
            head_to_head_points[team_b] += 3
        else:
            head_to_head_points[team_a] += 1
            head_to_head_points[team_b] += 1

    return head_to_head_points


def rank_points_tied_group(
    tied_group: pd.DataFrame,
    match_results: list[dict]
) -> pd.DataFrame:
    """
    Ranks teams that are tied on total group points.

    Tiebreakers used here:
    1. Head-to-head points among the tied teams
    2. Overall goal difference
    3. Overall goals scored
    4. Rating fallback
    """

    tied_group = tied_group.copy()

    if len(tied_group) == 1:
        tied_group["HeadToHeadPoints"] = 0
        return tied_group

    tied_teams = tied_group["Team"].tolist()

    head_to_head_points = calculate_head_to_head_points(
        tied_teams=tied_teams,
        match_results=match_results
    )

    tied_group["HeadToHeadPoints"] = tied_group["Team"].map(head_to_head_points)

    tied_group = tied_group.sort_values(
        by=[
            "HeadToHeadPoints",
            "GoalDifference",
            "GoalsFor",
            "Rating",
        ],
        ascending=[
            False,
            False,
            False,
            False,
        ],
    )

    return tied_group


def rank_group_table(
    table: dict,
    ratings: pd.DataFrame,
    match_results: list[dict]
) -> pd.DataFrame:
    """
    Ranks a group table using the 2026-style tiebreaker order.

    Main ranking order:
    1. Points
    2. Head-to-head points among teams tied on points
    3. Overall goal difference
    4. Overall goals scored
    5. Rating fallback

    The rating fallback replaces deeper tiebreakers that are not modeled here,
    such as fair play points and drawing of lots.
    """

    group_table = pd.DataFrame(table.values())

    group_table = group_table.merge(
        ratings[["Team", "Rating"]],
        on="Team",
        how="left"
    )

    ranked_chunks = []

    unique_point_totals = sorted(
        group_table["Points"].unique(),
        reverse=True
    )

    for points_total in unique_point_totals:
        tied_group = group_table[group_table["Points"] == points_total].copy()

        ranked_tied_group = rank_points_tied_group(
            tied_group=tied_group,
            match_results=match_results
        )

        ranked_chunks.append(ranked_tied_group)

    ranked_table = pd.concat(
        ranked_chunks,
        ignore_index=True
    )

    ranked_table["GroupRank"] = ranked_table.index + 1

    return ranked_table


def simulate_one_group(
    group_name: str,
    teams: list[str],
    ratings: pd.DataFrame
) -> tuple[pd.DataFrame, pd.DataFrame]:
    table = initialize_group_table(teams)
    match_results = []

    for team_a, team_b in combinations(teams, 2):
        match = simulate_group_match(team_a, team_b, ratings)
        match["Group"] = group_name

        update_group_table(table, match)
        match_results.append(match)

    ranked_table = rank_group_table(
        table=table,
        ratings=ratings,
        match_results=match_results
    )

    match_results_df = pd.DataFrame(match_results)

    return ranked_table, match_results_df


def simulate_all_groups(
    groups: pd.DataFrame,
    ratings: pd.DataFrame
) -> tuple[pd.DataFrame, pd.DataFrame]:
    all_tables = []
    all_matches = []

    for group_name in sorted(groups["Group"].unique()):
        teams = groups.loc[groups["Group"] == group_name, "Team"].tolist()

        group_table, group_matches = simulate_one_group(
            group_name=group_name,
            teams=teams,
            ratings=ratings
        )

        group_table["Group"] = group_name

        all_tables.append(group_table)
        all_matches.append(group_matches)

    full_table = pd.concat(all_tables, ignore_index=True)
    full_matches = pd.concat(all_matches, ignore_index=True)

    columns = ["Group"] + [
        column for column in full_table.columns
        if column != "Group"
    ]

    full_table = full_table[columns]

    return full_table, full_matches


def get_qualified_teams(group_tables: pd.DataFrame) -> pd.DataFrame:
    """
    2026 format:
    - Top 2 teams from each group qualify automatically: 24 teams
    - Best 8 third-place teams qualify: 8 teams
    - Total: 32 teams

    Note:
    The best third-place ranking is across teams from different groups, so
    head-to-head does not apply there. We use points, goal difference, goals
    scored, and rating fallback.
    """

    top_two = group_tables[group_tables["GroupRank"] <= 2].copy()
    third_place = group_tables[group_tables["GroupRank"] == 3].copy()

    best_third = third_place.sort_values(
        by=[
            "Points",
            "GoalDifference",
            "GoalsFor",
            "Rating",
        ],
        ascending=[
            False,
            False,
            False,
            False,
        ],
    ).head(8).copy()

    top_two["QualificationType"] = "Top 2"
    best_third["QualificationType"] = "Best 3rd"

    qualifiers = pd.concat(
        [top_two, best_third],
        ignore_index=True
    )

    return qualifiers


if __name__ == "__main__":
    groups = load_groups()
    ratings = load_ratings()

    group_tables, group_matches = simulate_all_groups(groups, ratings)
    qualifiers = get_qualified_teams(group_tables)

    print("Group match results:")
    print(group_matches.head(12))

    print("\nGroup tables:")
    print(group_tables)

    print("\nQualified teams:")
    print(
        qualifiers[
            [
                "Group",
                "GroupRank",
                "Team",
                "Points",
                "HeadToHeadPoints",
                "GoalDifference",
                "GoalsFor",
                "QualificationType",
            ]
        ]
    )

    print(f"\nTotal qualified teams: {len(qualifiers)}")