from pathlib import Path
import pandas as pd


BASE_DIR = Path(__file__).resolve().parents[1]
RAW_DIR = BASE_DIR / "data" / "raw"


def load_groups():
    groups_path = RAW_DIR / "world_cup_groups.csv"
    groups = pd.read_csv(groups_path)

    expected_columns = {"Group", "Team"}
    if not expected_columns.issubset(groups.columns):
        raise ValueError(f"Groups file must contain columns: {expected_columns}")

    return groups


def load_ratings():
    ratings_path = RAW_DIR / "team_ratings.csv"
    ratings = pd.read_csv(ratings_path)

    expected_columns = {"Team", "Rating", "Attack", "Defense"}
    if not expected_columns.issubset(ratings.columns):
        raise ValueError(f"Ratings file must contain columns: {expected_columns}")

    return ratings


def validate_data(groups, ratings):
    group_teams = set(groups["Team"])
    rating_teams = set(ratings["Team"])

    missing_ratings = sorted(group_teams - rating_teams)
    extra_ratings = sorted(rating_teams - group_teams)

    if missing_ratings:
        print("Teams missing ratings:")
        for team in missing_ratings:
            print(f" - {team}")
    else:
        print("Every team has a rating.")

    if extra_ratings:
        print("\nExtra teams in ratings file:")
        for team in extra_ratings:
            print(f" - {team}")

    print("\nGroups loaded:")
    print(groups.groupby("Group")["Team"].count())

    print("\nRatings summary:")
    print(ratings[["Rating", "Attack", "Defense"]].describe())


if __name__ == "__main__":
    groups = load_groups()
    ratings = load_ratings()
    validate_data(groups, ratings)