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

    games = queries.list_games()
    if not games:
        st.error("No games with located shots in the gold layer.")
        return
    game_ids = {g["label"]: g["game_id"] for g in games}

    controls, chart = st.columns([1, 2], gap="large")
    with controls:
        game_label = st.selectbox("Game", list(game_ids))
        game_id = game_ids[game_label]
        player = st.selectbox("Player", queries.list_players(game_id))
        result = st.segmented_control("Result", ["All", "Made", "Missed"], default="All")
        shot_type = st.segmented_control("Shot type", ["All", "2PT", "3PT"], default="All")

    # one cached query per game; player / result / type all filter in-memory
    game_shots = queries.get_shots(game_id)
    player_shots = game_shots[game_shots["event_player_name"] == player]

    view = player_shots
    if result == "Made":
        view = view[view["shot_made_flag"]]
    elif result == "Missed":
        view = view[~view["shot_made_flag"]]
    if shot_type == "2PT":
        view = view[~view["is_three"]]
    elif shot_type == "3PT":
        view = view[view["is_three"]]

    with controls:
        st.metric("Located shots shown", f"{len(view)} of {len(player_shots)}")
        st.markdown(f"**{player}** — {_fg_line(player_shots)}")
        if len(player_shots) == 0:
            st.info("This player has no tracking-located shots in this game.")

    with chart:
        fig, ax = plt.subplots(figsize=(8, 8))
        court.plot_shots(view, ax)
        ax.set_title(f"{player} — shot locations", fontsize=12)
        st.pyplot(fig, use_container_width=True)


if __name__ == "__main__":
    main()
