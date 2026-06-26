from pathlib import Path
import sys
import pandas as pd

BASE_DIR = Path(__file__).resolve().parents[1]
SRC_DIR = BASE_DIR / "src"
sys.path.append(str(SRC_DIR))

from load_data import load_groups, load_ratings
from simulate_group_stage import simulate_all_groups, get_qualified_teams
from simulate_match import simulate_knockout_match
from bracket_mapping import get_third_place_mapping_row, get_opponent_code_for_group_winner


def get_team_from_group_rank(group_tables: pd.DataFrame, group: str, rank: int) -> str:
    match = group_tables[
        (group_tables["Group"] == group)
        & (group_tables["GroupRank"] == rank)
    ]

    if match.empty:
        raise ValueError(f"No team found for Group {group}, rank {rank}")

    return match.iloc[0]["Team"]


def get_third_place_team_by_group(qualified_teams: pd.DataFrame, group: str) -> str:
    match = qualified_teams[
        (qualified_teams["Group"] == group)
        & (qualified_teams["GroupRank"] == 3)
    ]

    if match.empty:
        raise ValueError(f"No qualified third-place team found from Group {group}")

    return match.iloc[0]["Team"]


def resolve_team_code(
    team_code: str,
    group_tables: pd.DataFrame,
    qualified_teams: pd.DataFrame
) -> str:
    """
    Converts official bracket codes into team names.

    Examples:
    1A = Group A winner
    2B = Group B runner-up
    3E = qualified third-place team from Group E
    """

    rank = int(team_code[0])
    group = team_code[1]

    if rank in [1, 2]:
        return get_team_from_group_rank(group_tables, group, rank)

    if rank == 3:
        return get_third_place_team_by_group(qualified_teams, group)

    raise ValueError(f"Unsupported team code: {team_code}")


def build_official_round_of_32(
    group_tables: pd.DataFrame,
    qualified_teams: pd.DataFrame
) -> list[dict]:
    """
    Builds the official FIFA 2026 Round of 32 using:
    - fixed group winner/runner-up slots
    - Annexe C mapping for best third-place teams
    """

    best_third_teams = qualified_teams[qualified_teams["GroupRank"] == 3].copy()

    best_third_groups = sorted(best_third_teams["Group"].tolist())

    if len(best_third_groups) != 8:
        raise ValueError(
            f"Expected 8 best third-place groups, found {len(best_third_groups)}: {best_third_groups}"
        )

    mapping_row = get_third_place_mapping_row(best_third_groups)

    opponent_for_1a = get_opponent_code_for_group_winner(mapping_row, "1A")
    opponent_for_1b = get_opponent_code_for_group_winner(mapping_row, "1B")
    opponent_for_1d = get_opponent_code_for_group_winner(mapping_row, "1D")
    opponent_for_1e = get_opponent_code_for_group_winner(mapping_row, "1E")
    opponent_for_1g = get_opponent_code_for_group_winner(mapping_row, "1G")
    opponent_for_1i = get_opponent_code_for_group_winner(mapping_row, "1I")
    opponent_for_1k = get_opponent_code_for_group_winner(mapping_row, "1K")
    opponent_for_1l = get_opponent_code_for_group_winner(mapping_row, "1L")

    official_slots = [
        ("M73", "2A", "2B"),
        ("M74", "1E", opponent_for_1e),
        ("M75", "1F", "2C"),
        ("M76", "1C", "2F"),
        ("M77", "1I", opponent_for_1i),
        ("M78", "2E", "2I"),
        ("M79", "1A", opponent_for_1a),
        ("M80", "1L", opponent_for_1l),
        ("M81", "1D", opponent_for_1d),
        ("M82", "1G", opponent_for_1g),
        ("M83", "2K", "2L"),
        ("M84", "1H", "2J"),
        ("M85", "1B", opponent_for_1b),
        ("M86", "1J", "2H"),
        ("M87", "1K", opponent_for_1k),
        ("M88", "2D", "2G"),
    ]

    matches = []

    for match_id, team_a_code, team_b_code in official_slots:
        matches.append(
            {
                "Round": "Round of 32",
                "MatchID": match_id,
                "TeamA": resolve_team_code(team_a_code, group_tables, qualified_teams),
                "TeamB": resolve_team_code(team_b_code, group_tables, qualified_teams),
                "TeamACode": team_a_code,
                "TeamBCode": team_b_code,
            }
        )

    return matches


def simulate_knockout_round(
    matches: list[dict],
    ratings: pd.DataFrame,
    round_name: str
) -> pd.DataFrame:
    results = []

    for match in matches:
        simulated = simulate_knockout_match(
            match["TeamA"],
            match["TeamB"],
            ratings
        )

        simulated["Round"] = round_name
        simulated["MatchID"] = match["MatchID"]

        if "TeamACode" in match:
            simulated["TeamACode"] = match["TeamACode"]

        if "TeamBCode" in match:
            simulated["TeamBCode"] = match["TeamBCode"]

        results.append(simulated)

    return pd.DataFrame(results)


def get_winner_from_match(results: pd.DataFrame, match_id: str) -> str:
    match = results[results["MatchID"] == match_id]

    if match.empty:
        raise ValueError(f"No result found for match {match_id}")

    return match.iloc[0]["Winner"]


def build_next_round_matches(
    previous_results: pd.DataFrame,
    round_name: str,
    matchups: list[tuple[str, str, str]]
) -> list[dict]:
    """
    matchups format:
    [
        ("M89", "M74", "M77"),
        ...
    ]

    This means:
    M89 = winner of M74 vs winner of M77
    """

    matches = []

    for new_match_id, source_match_a, source_match_b in matchups:
        team_a = get_winner_from_match(previous_results, source_match_a)
        team_b = get_winner_from_match(previous_results, source_match_b)

        matches.append(
            {
                "Round": round_name,
                "MatchID": new_match_id,
                "TeamA": team_a,
                "TeamB": team_b,
                "TeamACode": f"W{source_match_a}",
                "TeamBCode": f"W{source_match_b}",
            }
        )

    return matches


def simulate_one_tournament(groups: pd.DataFrame, ratings: pd.DataFrame) -> dict:
    group_tables, group_matches = simulate_all_groups(groups, ratings)

    qualified_teams = get_qualified_teams(group_tables)

    round_of_32_matches = build_official_round_of_32(
        group_tables,
        qualified_teams
    )

    round_of_32_results = simulate_knockout_round(
        round_of_32_matches,
        ratings,
        "Round of 32"
    )

    round_of_16_matchups = [
        ("M89", "M74", "M77"),
        ("M90", "M73", "M75"),
        ("M91", "M76", "M78"),
        ("M92", "M79", "M80"),
        ("M93", "M83", "M84"),
        ("M94", "M81", "M82"),
        ("M95", "M86", "M88"),
        ("M96", "M85", "M87"),
    ]

    round_of_16_matches = build_next_round_matches(
        round_of_32_results,
        "Round of 16",
        round_of_16_matchups
    )

    round_of_16_results = simulate_knockout_round(
        round_of_16_matches,
        ratings,
        "Round of 16"
    )

    quarterfinal_matchups = [
        ("M97", "M89", "M90"),
        ("M98", "M93", "M94"),
        ("M99", "M91", "M92"),
        ("M100", "M95", "M96"),
    ]

    quarterfinal_matches = build_next_round_matches(
        round_of_16_results,
        "Quarterfinals",
        quarterfinal_matchups
    )

    quarterfinal_results = simulate_knockout_round(
        quarterfinal_matches,
        ratings,
        "Quarterfinals"
    )

    semifinal_matchups = [
        ("M101", "M97", "M98"),
        ("M102", "M99", "M100"),
    ]

    semifinal_matches = build_next_round_matches(
        quarterfinal_results,
        "Semifinals",
        semifinal_matchups
    )

    semifinal_results = simulate_knockout_round(
        semifinal_matches,
        ratings,
        "Semifinals"
    )

    final_matchups = [
        ("M104", "M101", "M102"),
    ]

    final_matches = build_next_round_matches(
        semifinal_results,
        "Final",
        final_matchups
    )

    final_results = simulate_knockout_round(
        final_matches,
        ratings,
        "Final"
    )

    knockout_results = pd.concat(
        [
            round_of_32_results,
            round_of_16_results,
            quarterfinal_results,
            semifinal_results,
            final_results,
        ],
        ignore_index=True
    )

    champion = final_results.iloc[0]["Winner"]

    return {
    "Champion": champion,
    "Qualifiers": qualified_teams,
    "QualifiedTeams": qualified_teams,
    "GroupTables": group_tables,
    "GroupMatches": group_matches,
    "KnockoutResults": knockout_results,
}


if __name__ == "__main__":
    groups = load_groups()
    ratings = load_ratings()

    tournament = simulate_one_tournament(groups, ratings)

    print()
    print("Champion:")
    print(tournament["Champion"])

    print()
    print("Qualified Teams:")
    print(tournament["QualifiedTeams"][["Group", "Team", "GroupRank"]])

    print()
    print("Knockout Results:")
    print(
        tournament["KnockoutResults"][
            ["Round", "MatchID", "TeamA", "TeamB", "GoalsA", "GoalsB", "Winner", "WonBy"]
        ]
    )