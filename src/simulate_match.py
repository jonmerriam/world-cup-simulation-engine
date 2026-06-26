from pathlib import Path
import sys
import numpy as np
import pandas as pd

# Allows this file to import load_data.py when run directly
BASE_DIR = Path(__file__).resolve().parents[1]
SRC_DIR = BASE_DIR / "src"
sys.path.append(str(SRC_DIR))

from load_data import load_ratings


def get_team_row(ratings: pd.DataFrame, team: str) -> pd.Series:
    match = ratings[ratings["Team"] == team]

    if match.empty:
        raise ValueError(f"Team not found in ratings file: {team}")

    return match.iloc[0]


def get_team_strength(team_row: pd.Series) -> float:
    """
    Uses the best available team strength value.

    Preferred:
    1. AdjustedElo - includes host boost
    2. Elo - raw Elo
    3. Rating - fallback for older ratings files
    """

    if "AdjustedElo" in team_row.index:
        return float(team_row["AdjustedElo"])

    if "Elo" in team_row.index:
        return float(team_row["Elo"])

    return float(team_row["Rating"])


def calculate_expected_goals(team_a_row: pd.Series, team_b_row: pd.Series) -> tuple[float, float]:
    """
    Converts Elo difference into expected goals.

    This version avoids double-counting team strength through Rating,
    Attack, and Defense. Elo is the main driver.

    A 400-point Elo gap is large, but in soccer it should not make
    the favorite unbeatable, so the goal adjustment is intentionally moderate.
    """

    base_goals = 1.25

    strength_a = get_team_strength(team_a_row)
    strength_b = get_team_strength(team_b_row)

    elo_diff = strength_a - strength_b

    
    strength_adjustment = (elo_diff / 400) * 0.60

    lambda_a = base_goals + strength_adjustment
    lambda_b = base_goals - strength_adjustment

    # Keep goal expectations realistic
    lambda_a = max(0.35, min(lambda_a, 2.75))
    lambda_b = max(0.35, min(lambda_b, 2.75))

    return lambda_a, lambda_b


def simulate_score(lambda_a: float, lambda_b: float) -> tuple[int, int]:
    goals_a = np.random.poisson(lambda_a)
    goals_b = np.random.poisson(lambda_b)

    return goals_a, goals_b


def get_tiebreaker_probability(team_a_row: pd.Series, team_b_row: pd.Series, divisor: float = 250) -> float:
    """
    Gives the stronger team an edge in extra time or penalties.

    This uses Elo-style strength directly.

    Smaller divisor = stronger favorite edge.
    Larger divisor = closer to 50/50.
    """

    strength_a = get_team_strength(team_a_row)
    strength_b = get_team_strength(team_b_row)

    return 1 / (1 + np.exp(-(strength_a - strength_b) / divisor))


def simulate_group_match(team_a: str, team_b: str, ratings: pd.DataFrame) -> dict:
    """
    Simulates a group-stage match.
    Draws are allowed.
    """

    team_a_row = get_team_row(ratings, team_a)
    team_b_row = get_team_row(ratings, team_b)

    lambda_a, lambda_b = calculate_expected_goals(team_a_row, team_b_row)
    goals_a, goals_b = simulate_score(lambda_a, lambda_b)

    if goals_a > goals_b:
        winner = team_a
        result = "Team A Win"
    elif goals_b > goals_a:
        winner = team_b
        result = "Team B Win"
    else:
        winner = None
        result = "Draw"

    return {
        "TeamA": team_a,
        "TeamB": team_b,
        "ExpectedGoalsA": lambda_a,
        "ExpectedGoalsB": lambda_b,
        "GoalsA": goals_a,
        "GoalsB": goals_b,
        "Winner": winner,
        "Result": result,
    }


def simulate_extra_time(
    team_a: str,
    team_b: str,
    team_a_row: pd.Series,
    team_b_row: pd.Series,
    goals_a: int,
    goals_b: int
) -> tuple[int, int, str | None]:
    """
    Simulates extra time after a tied knockout match.

    If extra time produces a winner, the final score changes.
    If not, the match goes to penalties.
    """

    extra_time_goal_probability = 0.32

    if np.random.random() > extra_time_goal_probability:
        return goals_a, goals_b, None

    prob_a_scores = get_tiebreaker_probability(team_a_row, team_b_row, divisor=300)

    if np.random.random() < prob_a_scores:
        goals_a += 1
        winner = team_a
    else:
        goals_b += 1
        winner = team_b

    return goals_a, goals_b, winner


def simulate_penalties(
    team_a: str,
    team_b: str,
    team_a_row: pd.Series,
    team_b_row: pd.Series
) -> str:
    """
    Simulates penalties after a match is still tied after extra time.

    Score remains tied, but a winner is selected.
    Penalties are intentionally closer to random than regulation strength.
    """

    prob_a_wins_pens = get_tiebreaker_probability(team_a_row, team_b_row, divisor=450)

    if np.random.random() < prob_a_wins_pens:
        return team_a

    return team_b


def simulate_knockout_match(team_a: str, team_b: str, ratings: pd.DataFrame) -> dict:
    """
    Simulates a knockout match.

    If the regulation score is tied:
    - Extra time may produce a final-score winner.
    - If extra time does not produce a winner, penalties decide the winner.
    """

    match = simulate_group_match(team_a, team_b, ratings)

    team_a_row = get_team_row(ratings, team_a)
    team_b_row = get_team_row(ratings, team_b)

    goals_a = match["GoalsA"]
    goals_b = match["GoalsB"]

    if goals_a > goals_b:
        match["Winner"] = team_a
        match["WonBy"] = "Regulation"
        match["PenaltyWinner"] = None
        return match

    if goals_b > goals_a:
        match["Winner"] = team_b
        match["WonBy"] = "Regulation"
        match["PenaltyWinner"] = None
        return match

    goals_a_after_et, goals_b_after_et, extra_time_winner = simulate_extra_time(
        team_a,
        team_b,
        team_a_row,
        team_b_row,
        goals_a,
        goals_b
    )

    match["GoalsA"] = goals_a_after_et
    match["GoalsB"] = goals_b_after_et

    if extra_time_winner is not None:
        match["Winner"] = extra_time_winner
        match["WonBy"] = "Extra Time"
        match["PenaltyWinner"] = None
        return match

    penalty_winner = simulate_penalties(team_a, team_b, team_a_row, team_b_row)

    match["Winner"] = penalty_winner
    match["WonBy"] = "Penalties"
    match["PenaltyWinner"] = penalty_winner

    return match


def estimate_match_probabilities(team_a: str, team_b: str, ratings: pd.DataFrame, n_sims: int = 10000) -> dict:
    """
    Runs one matchup many times to estimate group-stage win/draw probabilities.
    """

    team_a_wins = 0
    team_b_wins = 0
    draws = 0

    for _ in range(n_sims):
        match = simulate_group_match(team_a, team_b, ratings)

        if match["Result"] == "Team A Win":
            team_a_wins += 1
        elif match["Result"] == "Team B Win":
            team_b_wins += 1
        else:
            draws += 1

    return {
        "TeamA": team_a,
        "TeamB": team_b,
        "TeamA_WinPct": team_a_wins / n_sims,
        "DrawPct": draws / n_sims,
        "TeamB_WinPct": team_b_wins / n_sims,
    }


if __name__ == "__main__":
    ratings = load_ratings()

    team_a = "Spain"
    team_b = "Argentina"

    print("Single group-stage simulation:")
    print(simulate_group_match(team_a, team_b, ratings))

    print("\nEstimated match probabilities:")
    print(estimate_match_probabilities(team_a, team_b, ratings, n_sims=10000))

    print("\nSingle knockout simulation:")
    print(simulate_knockout_match(team_a, team_b, ratings))