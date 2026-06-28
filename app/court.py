"""Court geometry and drawing for the shot map.

Pure matplotlib — no Streamlit, no data access. Coordinates are in FEET on a
94x50 ft court with the origin at a corner (the gold layer's convention); the
two rims sit at (5.25, 25) and (88.75, 25).

Shots happen at BOTH ends because teams switch baskets at the half, so
``shooter_x`` spans roughly [4, 94]. ``fold_shots`` collapses the far end onto
the near end (a 180-deg rotation about the court center) to produce a standard
single-hoop shot chart with the rim at the LEFT, court opening to the right.
"""

from __future__ import annotations

import matplotlib.pyplot as plt
import numpy as np
from matplotlib.patches import Arc, Circle, Rectangle

# --- court constants (feet) -------------------------------------------------
HOOP_X, HOOP_Y = 5.25, 25.0      # near rim (the half we fold everything onto)
COURT_LEN, COURT_WID = 94.0, 50.0
HALF_LEN = COURT_LEN / 2.0       # 47.0 -> right edge of the drawn half court
THREE_R = 23.75                  # arc radius from rim center
CORNER_Y = 22.0                  # corner-3 is the straight line |y - 25| = 22

_LINE = "black"
_LW = 1.4


def fold_shots(df):
    """Return a copy of ``df`` with ``plot_x``/``plot_y`` folded onto one half.

    Far-end shots (x > 47) are rotated 180 deg about the court center
    (x -> 94 - x, y -> 50 - y) so every shot lands on the left half relative to
    a single rim at (5.25, 25). ``shot_distance`` / ``is_three`` are unaffected
    by the fold (the gold layer measures them to the nearest hoop).
    """
    far = df["shooter_x"] > HALF_LEN
    out = df.copy()
    out["plot_x"] = np.where(far, COURT_LEN - df["shooter_x"], df["shooter_x"])
    out["plot_y"] = np.where(far, COURT_WID - df["shooter_y"], df["shooter_y"])
    return out


def draw_court(ax=None):
    """Draw an NBA half court (rim at left) onto ``ax``; returns the Axes."""
    if ax is None:
        _, ax = plt.subplots(figsize=(7, 7))

    def _line(x, y):
        ax.plot(x, y, color=_LINE, lw=_LW, zorder=1)

    # outer boundary: baseline (x=0), half-court line (x=47), sidelines
    _line([0, 0], [0, COURT_WID])
    _line([HALF_LEN, HALF_LEN], [0, COURT_WID])
    _line([0, HALF_LEN], [0, 0])
    _line([0, HALF_LEN], [COURT_WID, COURT_WID])

    # rim + backboard
    ax.add_patch(Circle((HOOP_X, HOOP_Y), 0.75, fill=False, color=_LINE, lw=_LW, zorder=2))
    _line([4.0, 4.0], [HOOP_Y - 3, HOOP_Y + 3])

    # paint: 16 ft wide, 19 ft deep (baseline -> free-throw line)
    ax.add_patch(Rectangle((0, HOOP_Y - 8), 19, 16, fill=False, color=_LINE, lw=_LW, zorder=1))
    # free-throw circle: solid top half, dashed bottom half
    ax.add_patch(Arc((19, HOOP_Y), 12, 12, theta1=-90, theta2=90, color=_LINE, lw=_LW))
    ax.add_patch(Arc((19, HOOP_Y), 12, 12, theta1=90, theta2=270, color=_LINE, lw=_LW, linestyle="--"))
    # restricted-area arc (4 ft from rim)
    ax.add_patch(Arc((HOOP_X, HOOP_Y), 8, 8, theta1=-90, theta2=90, color=_LINE, lw=_LW))

    # three-point line: corner straight segments + the arc
    corner_x = HOOP_X + np.sqrt(THREE_R ** 2 - CORNER_Y ** 2)  # where arc meets corner line
    _line([0, corner_x], [HOOP_Y - CORNER_Y, HOOP_Y - CORNER_Y])
    _line([0, corner_x], [HOOP_Y + CORNER_Y, HOOP_Y + CORNER_Y])
    theta = np.degrees(np.arctan2(CORNER_Y, corner_x - HOOP_X))
    ax.add_patch(Arc((HOOP_X, HOOP_Y), 2 * THREE_R, 2 * THREE_R,
                     theta1=-theta, theta2=theta, color=_LINE, lw=_LW))

    ax.set_xlim(-1, HALF_LEN + 1)
    ax.set_ylim(-1, COURT_WID + 1)
    ax.set_aspect("equal")
    ax.axis("off")
    return ax


def plot_shots(df, ax=None):
    """Fold and scatter shots: made = green filled circle, miss = red x."""
    ax = draw_court(ax)
    if df is not None and len(df):
        folded = fold_shots(df)
        made = folded[folded["shot_made_flag"]]
        miss = folded[~folded["shot_made_flag"]]
        ax.scatter(miss["plot_x"], miss["plot_y"], marker="x", c="#d62728",
                   s=70, linewidths=2, label="Miss", zorder=3)
        ax.scatter(made["plot_x"], made["plot_y"], marker="o", c="#2ca02c",
                   s=70, edgecolors="black", linewidths=0.6, label="Made", zorder=3)
        ax.legend(loc="upper right", frameon=True, fontsize=9)
    return ax
