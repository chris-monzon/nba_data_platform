"""Streamlit shot-map dashboard (consumer — thin view).

Pick a player, filter by made/miss and 2PT/3PT, and render a folded half-court
shot chart from the gold layer. This file stays a thin view: data access lives
in queries.py, court geometry/drawing in court.py.

Run: uv run streamlit run app/streamlit_app.py
"""

from __future__ import annotations

import matplotlib.pyplot as plt
import streamlit as st

import court
import queries


def _fg_line(df) -> str:
    """Format a player's shooting line from their full located-shot set."""
    att = len(df)
    if att == 0:
        return "0 located shots in this game"
    made = int(df["shot_made_flag"].sum())
    t_att = int(df["is_three"].sum())
    t_made = int((df["is_three"] & df["shot_made_flag"]).sum())
    fg_pct = round(100 * made / att)
    three = f"{t_made}/{t_att} 3PT ({round(100 * t_made / t_att)}%)" if t_att else "0/0 3PT"
    return f"{made}/{att} FG ({fg_pct}%) · {three}"


def main() -> None:
    st.set_page_config(page_title="NBA Shot Map", layout="wide")
    st.title("NBA Shot Map")
    st.caption("Denver Chicken Nuggets · CLE @ GSW, 2015-12-25 (game 0021500438)")

    players = queries.list_players()
    if not players:
        st.error("No player data returned from the gold layer.")
        return

    controls, chart = st.columns([1, 2], gap="large")
    with controls:
        player = st.selectbox("Player", players)
        result = st.segmented_control("Result", ["All", "Made", "Missed"], default="All")
        shot_type = st.segmented_control("Shot type", ["All", "2PT", "3PT"], default="All")

    shots = queries.get_shots(player)

    # in-memory subset for the chart (toggles never re-hit BigQuery)
    view = shots
    if result == "Made":
        view = view[view["shot_made_flag"]]
    elif result == "Missed":
        view = view[~view["shot_made_flag"]]
    if shot_type == "2PT":
        view = view[~view["is_three"]]
    elif shot_type == "3PT":
        view = view[view["is_three"]]

    with controls:
        st.metric("Located shots shown", f"{len(view)} of {len(shots)}")
        st.markdown(f"**{player}** — {_fg_line(shots)}")
        if len(shots) == 0:
            st.info("This player has no tracking-located shots in this game.")

    with chart:
        fig, ax = plt.subplots(figsize=(8, 8))
        court.plot_shots(view, ax)
        ax.set_title(f"{player} — shot locations", fontsize=12)
        st.pyplot(fig, use_container_width=True)


if __name__ == "__main__":
    main()
