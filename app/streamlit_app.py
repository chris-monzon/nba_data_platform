"""Streamlit event-map dashboard (consumer — thin view).

Select a player + event type → render a court map from the gold layer.
Keep this file a thin view: dropdowns + render only. Data access lives in
queries.py; court geometry/drawing lives in court.py.

Run: uv run streamlit run app/streamlit_app.py
"""

import streamlit as st


def main() -> None:
    st.set_page_config(page_title="NBA Event Map", layout="wide")
    st.title("NBA Event Map")
    st.caption("Denver Chicken Nuggets · scaffolding placeholder")

    # TODO: populate dropdowns from queries.list_players() / list_event_types()
    st.selectbox("Player", ["(coming soon)"], disabled=True)
    st.selectbox("Event type", ["(coming soon)"], disabled=True)

    # TODO: events = queries.get_player_events(player_id, event_type)
    #       fig = court.plot_events(events); st.pyplot(fig)
    st.info("Dashboard under construction — gold layer + queries not yet wired up.")


if __name__ == "__main__":
    main()
