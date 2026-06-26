# app/

**Consumer layer — the Streamlit event-map dashboard.** Sits on top of the gold layer; it is
*not* part of the pipeline.

Select a player + event type → render a court map of where those events occurred.

## Structure

| File | Role |
|---|---|
| `streamlit_app.py` | thin view — dropdowns + render |
| `queries.py` | gold-layer data access (keeps table/column names in one place) |
| `court.py` | `(x, y)` → court coordinates + court drawing |

Logic lives in `queries.py` / `court.py`, keeping `streamlit_app.py` a thin view.
