# Containerizes the tracking parse step for Cloud Run.
# STUB — to be completed when the parse logic is implemented.

FROM python:3.11-slim

WORKDIR /app

# Install uv and resolve dependencies from the project lockfile.
COPY pyproject.toml uv.lock ./
RUN pip install --no-cache-dir uv && uv sync --frozen --no-dev

COPY ingestion/ ./ingestion/

# TODO: set entrypoint to the parse job (e.g. a single game_id passed via env/arg).
# ENTRYPOINT ["uv", "run", "python", "ingestion/parse_tracking.py"]
