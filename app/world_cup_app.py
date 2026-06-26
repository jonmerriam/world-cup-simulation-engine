from pathlib import Path
import sys
import json
import time

import pandas as pd
import streamlit as st
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch


BASE_DIR = Path(__file__).resolve().parents[1]
SRC_DIR = BASE_DIR / "src"
PROCESSED_DIR = BASE_DIR / "data" / "processed"

sys.path.append(str(SRC_DIR))

from load_data import load_groups, load_ratings
from run_simulations import run_simulations
from format_results import format_probability_columns, add_contender_tiers
from simulate_tournament import simulate_one_tournament


st.set_page_config(
    page_title="World Cup Simulation Engine",
    page_icon="⚽",
    layout="wide"
)


TEAM_FLAG_URLS = {
    "Mexico": "https://flagcdn.com/w40/mx.png",
    "South Africa": "https://flagcdn.com/w40/za.png",
    "South Korea": "https://flagcdn.com/w40/kr.png",
    "Czechia": "https://flagcdn.com/w40/cz.png",
    "Canada": "https://flagcdn.com/w40/ca.png",
    "Bosnia and Herzegovina": "https://flagcdn.com/w40/ba.png",
    "Qatar": "https://flagcdn.com/w40/qa.png",
    "Switzerland": "https://flagcdn.com/w40/ch.png",
    "Brazil": "https://flagcdn.com/w40/br.png",
    "Morocco": "https://flagcdn.com/w40/ma.png",
    "Haiti": "https://flagcdn.com/w40/ht.png",
    "Scotland": "https://flagcdn.com/w40/gb-sct.png",
    "United States": "https://flagcdn.com/w40/us.png",
    "Paraguay": "https://flagcdn.com/w40/py.png",
    "Australia": "https://flagcdn.com/w40/au.png",
    "Turkey": "https://flagcdn.com/w40/tr.png",
    "Germany": "https://flagcdn.com/w40/de.png",
    "Curacao": "https://flagcdn.com/w40/cw.png",
    "Ivory Coast": "https://flagcdn.com/w40/ci.png",
    "Ecuador": "https://flagcdn.com/w40/ec.png",
    "Netherlands": "https://flagcdn.com/w40/nl.png",
    "Japan": "https://flagcdn.com/w40/jp.png",
    "Sweden": "https://flagcdn.com/w40/se.png",
    "Tunisia": "https://flagcdn.com/w40/tn.png",
    "Belgium": "https://flagcdn.com/w40/be.png",
    "Egypt": "https://flagcdn.com/w40/eg.png",
    "Iran": "https://flagcdn.com/w40/ir.png",
    "New Zealand": "https://flagcdn.com/w40/nz.png",
    "Spain": "https://flagcdn.com/w40/es.png",
    "Cape Verde": "https://flagcdn.com/w40/cv.png",
    "Saudi Arabia": "https://flagcdn.com/w40/sa.png",
    "Uruguay": "https://flagcdn.com/w40/uy.png",
    "France": "https://flagcdn.com/w40/fr.png",
    "Senegal": "https://flagcdn.com/w40/sn.png",
    "Iraq": "https://flagcdn.com/w40/iq.png",
    "Norway": "https://flagcdn.com/w40/no.png",
    "Argentina": "https://flagcdn.com/w40/ar.png",
    "Algeria": "https://flagcdn.com/w40/dz.png",
    "Austria": "https://flagcdn.com/w40/at.png",
    "Jordan": "https://flagcdn.com/w40/jo.png",
    "Portugal": "https://flagcdn.com/w40/pt.png",
    "DR Congo": "https://flagcdn.com/w40/cd.png",
    "Uzbekistan": "https://flagcdn.com/w40/uz.png",
    "Colombia": "https://flagcdn.com/w40/co.png",
    "England": "https://flagcdn.com/w40/gb-eng.png",
    "Croatia": "https://flagcdn.com/w40/hr.png",
    "Ghana": "https://flagcdn.com/w40/gh.png",
    "Panama": "https://flagcdn.com/w40/pa.png",
}


PERCENT_FORMAT = "%.2f%%"


@st.cache_data
def load_saved_simulation_results():
    results_path = PROCESSED_DIR / "simulation_results_formatted.csv"
    return pd.read_csv(results_path)


@st.cache_data
def load_simulation_metadata():
    metadata_path = PROCESSED_DIR / "simulation_metadata.json"

    if not metadata_path.exists():
        return None

    with open(metadata_path, "r", encoding="utf-8") as file:
        return json.load(file)


@st.cache_data
def load_base_data():
    groups = load_groups()
    ratings = load_ratings()
    return groups, ratings


def run_new_simulation(n_sims: int) -> pd.DataFrame:
    progress_bar = st.progress(0)
    status_text = st.empty()

    def update_progress(current_sim: int, total_sims: int):
        progress = current_sim / total_sims
        progress_bar.progress(progress)
        status_text.write(
            f"Completed {current_sim:,} of {total_sims:,} simulations..."
        )

        # Gives Streamlit a tiny chance to refresh the progress bar
        time.sleep(0.001)

    raw_results = run_simulations(
        n_sims=n_sims,
        progress_callback=update_progress
    )

    progress_bar.progress(1.0)
    status_text.write(f"Completed {n_sims:,} simulations. Formatting results...")

    formatted = format_probability_columns(raw_results)
    formatted = add_contender_tiers(formatted)

    status_text.write("Simulation complete.")

    return formatted


def add_flag_columns(results: pd.DataFrame) -> pd.DataFrame:
    results = results.copy()
    results["Flag"] = results["Team"].map(TEAM_FLAG_URLS)
    return results


def add_match_display_columns(matches: pd.DataFrame) -> pd.DataFrame:
    matches = matches.copy()

    matches["TeamAFlag"] = matches["TeamA"].map(TEAM_FLAG_URLS)
    matches["TeamBFlag"] = matches["TeamB"].map(TEAM_FLAG_URLS)
    matches["Score"] = (
        matches["GoalsA"].astype(str)
        + " - "
        + matches["GoalsB"].astype(str)
    )

    if "Winner" in matches.columns:
        matches["WinnerFlag"] = matches["Winner"].map(TEAM_FLAG_URLS)

    return matches


def add_group_table_display_columns(group_table: pd.DataFrame) -> pd.DataFrame:
    group_table = group_table.copy()
    group_table["Flag"] = group_table["Team"].map(TEAM_FLAG_URLS)
    group_table["Record"] = (
        group_table["Wins"].astype(str)
        + "-"
        + group_table["Draws"].astype(str)
        + "-"
        + group_table["Losses"].astype(str)
    )
    return group_table


def display_top_metrics(results: pd.DataFrame, n_sims_label: str):
    top_team = results.iloc[0]

    col1, col2, col3 = st.columns(3)

    col1.metric("Tournament Simulations", n_sims_label)
    col2.metric("Favorite", top_team["Team"])
    col3.metric("Champion Probability", f"{top_team['Champion']:.2f}%")


def display_group_page(results: pd.DataFrame):
    st.subheader("Group Advancement Probabilities")

    groups = sorted(results["Group"].unique())

    for i in range(0, len(groups), 2):
        col1, col2 = st.columns(2)

        for col, group_name in zip([col1, col2], groups[i:i + 2]):
            with col:
                group_results = results[results["Group"] == group_name].copy()

                group_results = group_results.sort_values(
                    by="Finish1st",
                    ascending=False
                )

                st.markdown(f"### Group {group_name}")

                display_columns = [
                    "Flag",
                    "Team",
                    "Finish1st",
                    "Finish2nd",
                    "Finish3rd",
                    "Finish4th",
                    "AdvanceFromGroup",
                    "EliminatedInGroup",
                ]

                renamed = group_results[display_columns].rename(
                    columns={
                        "Finish1st": "1st",
                        "Finish2nd": "2nd",
                        "Finish3rd": "3rd",
                        "Finish4th": "4th",
                        "AdvanceFromGroup": "Advance",
                        "EliminatedInGroup": "Eliminated",
                    }
                )

                st.dataframe(
                    renamed,
                    use_container_width=True,
                    hide_index=True,
                    column_config={
                        "Flag": st.column_config.ImageColumn("Flag", width="small"),
                        "1st": st.column_config.NumberColumn("1st", format=PERCENT_FORMAT),
                        "2nd": st.column_config.NumberColumn("2nd", format=PERCENT_FORMAT),
                        "3rd": st.column_config.NumberColumn("3rd", format=PERCENT_FORMAT),
                        "4th": st.column_config.NumberColumn("4th", format=PERCENT_FORMAT),
                        "Advance": st.column_config.NumberColumn("Advance", format=PERCENT_FORMAT),
                        "Eliminated": st.column_config.NumberColumn("Eliminated", format=PERCENT_FORMAT),
                    },
                )


def display_results_table(results: pd.DataFrame):
    st.subheader("Full Simulation Results")

    display_columns = [
        "Group",
        "Flag",
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

    existing_columns = [
        column for column in display_columns
        if column in results.columns
    ]

    renamed = results[existing_columns].rename(
        columns={
            "Finish1st": "Finish 1st",
            "Finish2nd": "Finish 2nd",
            "Finish3rd": "Finish 3rd",
            "Finish4th": "Finish 4th",
            "AdvanceFromGroup": "Advance To Knockout",
            "AdvanceR16": "Round of 16",
        }
    )

    st.dataframe(
        renamed,
        use_container_width=True,
        hide_index=True,
        column_config={
            "Flag": st.column_config.ImageColumn("Flag", width="small"),
            "Finish 1st": st.column_config.NumberColumn("Finish 1st", format=PERCENT_FORMAT),
            "Finish 2nd": st.column_config.NumberColumn("Finish 2nd", format=PERCENT_FORMAT),
            "Finish 3rd": st.column_config.NumberColumn("Finish 3rd", format=PERCENT_FORMAT),
            "Finish 4th": st.column_config.NumberColumn("Finish 4th", format=PERCENT_FORMAT),
            "Advance To Knockout": st.column_config.NumberColumn("Advance To Knockout", format=PERCENT_FORMAT),
            "Round of 16": st.column_config.NumberColumn("Round of 16", format=PERCENT_FORMAT),
            "Quarterfinals": st.column_config.NumberColumn("Quarterfinals", format=PERCENT_FORMAT),
            "Semifinals": st.column_config.NumberColumn("Semifinals", format=PERCENT_FORMAT),
            "Final": st.column_config.NumberColumn("Final", format=PERCENT_FORMAT),
            "Champion": st.column_config.NumberColumn("Champion", format=PERCENT_FORMAT),
        },
    )


def display_elo_table():
    st.subheader("Elo Rating Inputs")
    st.caption(
        "Current team strength inputs used by the simulator. "
        "Ratings pulled on 6/10/2026."
    )

    groups, ratings = load_base_data()

    ratings_table = ratings.copy()
    groups_table = groups.copy()

    if "Group" not in ratings_table.columns:
        ratings_table = ratings_table.merge(
            groups_table,
            on="Team",
            how="left"
        )

    ratings_table["Flag"] = ratings_table["Team"].map(TEAM_FLAG_URLS)

    sort_column = "AdjustedElo" if "AdjustedElo" in ratings_table.columns else "Elo"

    ratings_table = ratings_table.sort_values(
        by=sort_column,
        ascending=False
    )

    display_columns = [
        "Group",
        "Flag",
        "Team",
        "Elo",
        "HostEloBoost",
        "AdjustedElo",
        "Rating",
    ]

    existing_columns = [
        column for column in display_columns
        if column in ratings_table.columns
    ]

    renamed = ratings_table[existing_columns].rename(
        columns={
            "HostEloBoost": "Host Boost",
            "AdjustedElo": "Adjusted Elo",
        }
    )

    with st.expander("View Elo Ratings Table", expanded=False):
        st.dataframe(
            renamed,
            use_container_width=True,
            hide_index=True,
            column_config={
                "Flag": st.column_config.ImageColumn("Flag", width="small"),
                "Elo": st.column_config.NumberColumn("Elo", format="%.0f"),
                "Host Boost": st.column_config.NumberColumn("Host Boost", format="%.0f"),
                "Adjusted Elo": st.column_config.NumberColumn("Adjusted Elo", format="%.0f"),
                "Rating": st.column_config.NumberColumn("Rating", format="%.2f"),
            },
        )


def display_simulation_metadata():
    st.subheader("Simulation Metadata")

    metadata = load_simulation_metadata()

    if metadata is None:
        st.info("No simulation metadata file found yet. Run simulations to generate metadata.")
        return

    col1, col2, col3 = st.columns(3)

    col1.metric("Saved Simulations", f"{metadata.get('n_sims', 'N/A'):,}")
    col2.metric("Host Elo Boost", f"+{metadata.get('host_elo_boost', 'N/A')}")
    col3.metric("Strength Adjustment", metadata.get("strength_adjustment", "N/A"))

    metadata_table = pd.DataFrame(
        [
            {"Setting": "Rating Source", "Value": metadata.get("rating_source", "N/A")},
            {"Setting": "Third-Place Mapping", "Value": metadata.get("third_place_mapping", "N/A")},
            {"Setting": "Knockout Path", "Value": metadata.get("knockout_path", "N/A")},
            {"Setting": "Generated At", "Value": metadata.get("generated_at", "N/A")},
        ]
    )

    st.dataframe(
        metadata_table,
        use_container_width=True,
        hide_index=True
    )


def run_single_tournament():
    groups, ratings = load_base_data()
    return simulate_one_tournament(groups, ratings)


def display_single_tournament_section():
    st.subheader("Single Tournament Simulator")
    st.caption(
        "Click the button to simulate one complete World Cup from the group stage through the final."
    )

    if "single_tournament" not in st.session_state:
        st.session_state["single_tournament"] = None

    if st.button("Simulate One Full Tournament"):
        st.session_state["single_tournament"] = run_single_tournament()

    tournament = st.session_state["single_tournament"]

    if tournament is None:
        st.info("Click 'Simulate One Full Tournament' to generate a full tournament result.")
        return

    champion = tournament["Champion"]
    champion_flag = TEAM_FLAG_URLS.get(champion)

    col1, col2 = st.columns([1, 4])

    with col1:
        if champion_flag:
            st.image(champion_flag, width=70)

    with col2:
        st.metric("Champion", champion)

    st.divider()

    display_single_group_tables(tournament["GroupTables"])
    st.divider()

    display_single_group_matches(tournament["GroupMatches"])
    st.divider()

    display_single_knockout_bracket(tournament["KnockoutResults"])


def display_single_group_tables(group_tables: pd.DataFrame):
    st.markdown("## Group Tables")

    groups = sorted(group_tables["Group"].unique())

    for i in range(0, len(groups), 2):
        col1, col2 = st.columns(2)

        for col, group_name in zip([col1, col2], groups[i:i + 2]):
            with col:
                group_table = group_tables[group_tables["Group"] == group_name].copy()
                group_table = group_table.sort_values("GroupRank")

                group_table = add_group_table_display_columns(group_table)

                display_columns = [
                    "GroupRank",
                    "Flag",
                    "Team",
                    "Record",
                    "Points",
                    "GoalsFor",
                    "GoalsAgainst",
                    "GoalDifference",
                ]

                renamed = group_table[display_columns].rename(
                    columns={
                        "GroupRank": "Rank",
                        "GoalsFor": "GF",
                        "GoalsAgainst": "GA",
                        "GoalDifference": "GD",
                    }
                )

                st.markdown(f"### Group {group_name}")

                st.dataframe(
                    renamed,
                    use_container_width=True,
                    hide_index=True,
                    column_config={
                        "Flag": st.column_config.ImageColumn("Flag", width="small")
                    },
                )


def display_single_group_matches(group_matches: pd.DataFrame):
    st.markdown("## Group Match Results")

    group_matches = add_match_display_columns(group_matches)

    groups = sorted(group_matches["Group"].unique())

    for group_name in groups:
        with st.expander(f"Group {group_name} Matches"):
            matches = group_matches[group_matches["Group"] == group_name].copy()

            display_columns = [
                "TeamAFlag",
                "TeamA",
                "Score",
                "TeamBFlag",
                "TeamB",
                "Winner",
            ]

            renamed = matches[display_columns].rename(
                columns={
                    "TeamAFlag": "",
                    "TeamBFlag": " ",
                }
            )

            st.dataframe(
                renamed,
                use_container_width=True,
                hide_index=True,
                column_config={
                    "": st.column_config.ImageColumn("", width="small"),
                    " ": st.column_config.ImageColumn(" ", width="small"),
                },
            )


def get_match_label(match: pd.Series) -> str:
    team_a = str(match["TeamA"])
    team_b = str(match["TeamB"])
    winner = str(match["Winner"])

    goals_a = match["GoalsA"]
    goals_b = match["GoalsB"]

    decided_by = match.get("WonBy", "Regulation")

    if decided_by == "Extra Time":
        extra_note = "\nET"
    elif decided_by == "Penalties":
        extra_note = "\nPens"
    elif decided_by == "Extra Time/Penalties":
        extra_note = "\nET/Pens"
    else:
        extra_note = ""

    if team_a == winner:
        return f"✓ {team_a} {goals_a}\n{team_b} {goals_b}{extra_note}"
    else:
        return f"✓ {team_b} {goals_b}\n{team_a} {goals_a}{extra_note}"


def draw_match_box(ax, x, y, match: pd.Series, is_final: bool = False):
    if is_final:
        face_color = "#1d4ed8"
        edge_color = "#93c5fd"
        line_width = 2.2
    else:
        face_color = "#111827"
        edge_color = "#334155"
        line_width = 1.4

    box_width = 1.25
    box_height = 0.68

    box = FancyBboxPatch(
        (x - box_width / 2, y - box_height / 2),
        box_width,
        box_height,
        boxstyle="round,pad=0.04,rounding_size=0.08",
        linewidth=line_width,
        edgecolor=edge_color,
        facecolor=face_color,
        zorder=3,
    )

    ax.add_patch(box)

    label = get_match_label(match)

    ax.text(
        x,
        y,
        label,
        ha="center",
        va="center",
        color="white",
        fontsize=7.2,
        fontweight="bold",
        linespacing=1.15,
        zorder=4,
    )


def draw_connector(ax, x_source, y_source_1, y_source_2, x_target, y_target):
    box_width = 1.25

    source_right = x_source + box_width / 2
    target_left = x_target - box_width / 2

    gap = 0.03

    start_x = source_right + gap
    end_x = target_left - gap
    mid_x = (start_x + end_x) / 2

    line_color = "#94a3b8"

    ax.plot([start_x, mid_x], [y_source_1, y_source_1], color=line_color, linewidth=1.2, zorder=1)
    ax.plot([start_x, mid_x], [y_source_2, y_source_2], color=line_color, linewidth=1.2, zorder=1)
    ax.plot([mid_x, mid_x], [y_source_1, y_source_2], color=line_color, linewidth=1.2, zorder=1)
    ax.plot([mid_x, end_x], [y_target, y_target], color=line_color, linewidth=1.2, zorder=1)


def display_single_knockout_bracket(knockout_results: pd.DataFrame):
    st.markdown("## Knockout Bracket")
    st.caption("Full 32 team knockout bracket based on above simulated group stage results. Winner is marked with a check.")

    knockout_results = knockout_results.copy()

    match_lookup = {
        row["MatchID"]: row
        for _, row in knockout_results.iterrows()
    }

    round_ids = {
        "Round of 32": [
            "M74", "M77",
            "M73", "M75",
            "M83", "M84",
            "M81", "M82",
            "M76", "M78",
            "M79", "M80",
            "M86", "M88",
            "M85", "M87",
        ],
        "Round of 16": [
            "M89", "M90",
            "M93", "M94",
            "M91", "M92",
            "M95", "M96",
        ],
        "Quarterfinals": [
            "M97", "M98",
            "M99", "M100",
        ],
        "Semifinals": [
            "M101", "M102",
        ],
        "Final": [
            "M104",
        ],
    }

    x_positions = {
        "Round of 32": 0,
        "Round of 16": 1.8,
        "Quarterfinals": 3.6,
        "Semifinals": 5.4,
        "Final": 7.2,
    }

    round_of_16_sources = {
        "M89": ("M74", "M77"),
        "M90": ("M73", "M75"),
        "M93": ("M83", "M84"),
        "M94": ("M81", "M82"),
        "M91": ("M76", "M78"),
        "M92": ("M79", "M80"),
        "M95": ("M86", "M88"),
        "M96": ("M85", "M87"),
    }

    quarterfinal_sources = {
        "M97": ("M89", "M90"),
        "M98": ("M93", "M94"),
        "M99": ("M91", "M92"),
        "M100": ("M95", "M96"),
    }

    semifinal_sources = {
        "M101": ("M97", "M98"),
        "M102": ("M99", "M100"),
    }

    final_sources = {
        "M104": ("M101", "M102"),
    }

    y_positions = {}

    for i, match_id in enumerate(round_ids["Round of 32"]):
        y_positions[match_id] = 15 - i

    for match_id, (source_1, source_2) in round_of_16_sources.items():
        y_positions[match_id] = (y_positions[source_1] + y_positions[source_2]) / 2

    for match_id, (source_1, source_2) in quarterfinal_sources.items():
        y_positions[match_id] = (y_positions[source_1] + y_positions[source_2]) / 2

    for match_id, (source_1, source_2) in semifinal_sources.items():
        y_positions[match_id] = (y_positions[source_1] + y_positions[source_2]) / 2

    for match_id, (source_1, source_2) in final_sources.items():
        y_positions[match_id] = (y_positions[source_1] + y_positions[source_2]) / 2

    fig, ax = plt.subplots(figsize=(18, 11.5))
    fig.patch.set_facecolor("#0b0f19")
    ax.set_facecolor("#0b0f19")

    for round_name, x in x_positions.items():
        ax.text(
            x,
            16.2,
            round_name,
            ha="center",
            va="center",
            color="white",
            fontsize=12,
            fontweight="bold",
        )

    for target, (source_1, source_2) in round_of_16_sources.items():
        draw_connector(
            ax,
            x_positions["Round of 32"],
            y_positions[source_1],
            y_positions[source_2],
            x_positions["Round of 16"],
            y_positions[target],
        )

    for target, (source_1, source_2) in quarterfinal_sources.items():
        draw_connector(
            ax,
            x_positions["Round of 16"],
            y_positions[source_1],
            y_positions[source_2],
            x_positions["Quarterfinals"],
            y_positions[target],
        )

    for target, (source_1, source_2) in semifinal_sources.items():
        draw_connector(
            ax,
            x_positions["Quarterfinals"],
            y_positions[source_1],
            y_positions[source_2],
            x_positions["Semifinals"],
            y_positions[target],
        )

    for target, (source_1, source_2) in final_sources.items():
        draw_connector(
            ax,
            x_positions["Semifinals"],
            y_positions[source_1],
            y_positions[source_2],
            x_positions["Final"],
            y_positions[target],
        )

    for round_name, ids in round_ids.items():
        for match_id in ids:
            if match_id not in match_lookup:
                continue

            draw_match_box(
                ax,
                x_positions[round_name],
                y_positions[match_id],
                match_lookup[match_id],
                is_final=(match_id == "M104"),
            )

    ax.set_xlim(-0.9, 8.2)
    ax.set_ylim(-0.8, 16.7)
    ax.axis("off")

    st.pyplot(fig, use_container_width=True)
    plt.close(fig)


def display_model_explanation():
    st.subheader("How the Simulation Works")

    st.markdown(
        """
        This project simulates the full 48-team World Cup to estimate each team's probability of
        advancing through the group stage, reaching each knockout round, and winning the tournament.

        ### 1. Team strength inputs

        The model uses World Football Elo ratings as the main measure of team strength. Elo is useful because it is
        based on match results, opponent quality, and relative team strength.

        The three host nations receive a small host adjustment:

        ```text
        United States: +35 Elo
        Mexico: +35 Elo
        Canada: +35 Elo
        ```

        The adjusted Elo value is then used as the main strength input for match simulation.

        ### 2. Match simulation

        Each match is simulated using expected goals. The difference between two teams' adjusted Elo ratings changes
        the expected goals for each team. Goals are then generated using a Poisson scoring process, which is commonly
        used for low-scoring sports like soccer.

        ### 3. Group stage

        Every group is simulated as a four-team round robin. Group-stage matches can end in a draw. Record is listed as Wins-Draws-Losses. Ties in points are broken by:

        ```text
        1. Head-to-head results
        2. Goal difference
        3. Goals scored
        4. Team rating 
        ```

        The top two teams from each group advance automatically. The eight best third-place teams based on the above tiebreakers also advance.

        ### 4. Knockout stage

        Knockout matches cannot end in a draw. If a knockout match is tied after regulation:

        ```text
        Extra time: sometimes produces a winning goal and changes the final score
        Penalties: if still tied, score remains tied and a winner is selected by penalties
        ```

        Penalty shootouts are intentionally more random than normal match results.

        ### 5. Official FIFA bracket mapping

        The simulator uses the official FIFA 2026 knockout path including the official third-place assignment table.
        This matters because the eight best third-place teams do not simply get placed randomly or by rank. Their bracket
        slots depend on which groups produced the best third-place teams.

        ### 6. Current limitations

        This version does not yet include:

        ```text
        Player injuries
        Lineup changes
        Separate attack and defense ratings
        Fair play tiebreakers (4th tiebreaker in group stage)
        Third place match
        ```

        The goal of this version is to create a clean, explainable, Elo-based tournament simulator with the correct
        2026 tournament structure.
        """
    )


def main():
    st.title("FIFA World Cup Simulation Engine")
    st.caption(
        "Simulate the expanded 48-team World Cup for 2026. Use the tabs below to explore Monte Carlo probabilities, simulate a single tournament, and view model details. "
    )

    tab1, tab2, tab3 = st.tabs(
        [
            "Monte Carlo Probabilities",
            "Single Tournament Simulator",
            "Model Explanation",
        ]
    )

    with tab1:
        st.subheader("Monte Carlo Simulation Controls")

        col1, col2 = st.columns([1, 3])

        with col1:
            n_sims = st.selectbox(
                "Number of tournament simulations",
                options=[50, 100, 250, 500, 1000],
                index=2
            )

        with col2:
            st.write("")
            st.write("")
            run_button = st.button("Run New Simulation")

        if run_button:
            with st.spinner(f"Running {n_sims:,} full tournament simulations..."):
                results = run_new_simulation(n_sims)

            st.success(f"Completed {n_sims:,} simulations.")
            n_sims_label = f"{n_sims:,}"

            # Clear cached saved data so metadata can refresh if user reruns in the same session
            load_simulation_metadata.clear()
        else:
            results = load_saved_simulation_results()
            n_sims_label = "Saved results"

        results = add_flag_columns(results)

        st.divider()

        display_top_metrics(results, n_sims_label)

        st.divider()

        display_group_page(results)

        st.divider()

        display_results_table(results)

        st.divider()

        display_elo_table()

    with tab2:
        display_single_tournament_section()

    with tab3:
        display_model_explanation()

        st.divider()

        display_simulation_metadata()

    st.caption(
        "Created by Jonathan Merriam. Data and model are for educational purposes only. Not affiliated with FIFA or any official organization."
    )


if __name__ == "__main__":
    main()