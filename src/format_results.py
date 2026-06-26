from pathlib import Path
import pandas as pd


BASE_DIR = Path(__file__).resolve().parents[1]
PROCESSED_DIR = BASE_DIR / "data" / "processed"


def format_probability_columns(df: pd.DataFrame) -> pd.DataFrame:
    probability_columns = [
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

    formatted = df.copy()

    for col in probability_columns:
        if col in formatted.columns:
            formatted[col] = (formatted[col] * 100).round(2)

    return formatted


def add_contender_tiers(df: pd.DataFrame) -> pd.DataFrame:
    formatted = df.copy()

    def assign_tier(champion_pct):
        if champion_pct >= 10:
            return "Favorite"
        elif champion_pct >= 3:
            return "Contender"
        elif champion_pct >= 1:
            return "Dark Horse"
        elif champion_pct >= 0.1:
            return "Long Shot"
        else:
            return "Very Long Shot"

    formatted["ContenderTier"] = formatted["Champion"].apply(assign_tier)

    return formatted


def main():
    input_path = PROCESSED_DIR / "simulation_results.csv"
    output_path = PROCESSED_DIR / "simulation_results_formatted.csv"

    results = pd.read_csv(input_path)

    formatted = format_probability_columns(results)
    formatted = add_contender_tiers(formatted)

    formatted.to_csv(output_path, index=False)

    print(f"Saved formatted results to: {output_path}")

    print("\nTop 20 formatted results:")
    print(
        formatted[
            [
                "Group",
                "Team",
                "ContenderTier",
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
        ].head(20).to_string(index=False)
    )


if __name__ == "__main__":
    main()