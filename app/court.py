"""Court geometry and drawing for the event map.

Converts tracking (x, y) to court coordinates and draws a basketball half/full
court for plotting events. Pure functions — no Streamlit, no data access.

TODO:
  - draw_court(ax) -> matplotlib Axes with court markings
  - plot_events(events_df) -> Figure of event locations on the court
"""

from __future__ import annotations


def draw_court(ax=None):
    """Draw a basketball court onto a matplotlib Axes."""
    raise NotImplementedError("app.court.draw_court — see module docstring")


def plot_events(events_df):
    """Plot event (x, y) locations on a court."""
    raise NotImplementedError("app.court.plot_events — see module docstring")
