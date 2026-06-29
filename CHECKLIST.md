# GitHub Readiness Checklist — Final

**Repo:** https://github.com/chris-monzon/nba_data_platform  _(update if the owner/name changes)_
**Public:** Yes

> Status as of the final build. Pipeline is implemented end-to-end (bronze → silver → gold) and
> runs on GCP (GCS + BigQuery); the dashboard reads the gold layer.

## Tier 1 — Must-have

| Item | Status | Note |
|---|---|---|
| README (what it is, data source, how to run, current state) | ✅ Yes | `README.md` |
| Data ingestion — script or notes on how raw data was obtained | ✅ Yes | `ingestion/` scripts (`download_tracking`, `fetch_pbp`) + `data/README.md` |
| Transformation scripts | ✅ Yes | Python parse (`parse_tracking`, `parse_dims`, `parse_shot_locations`) + BigQuery SQL in `transform/` (silver + gold), all run |
| No secrets/credentials committed | ✅ Yes | `.gitignore` covers keys/`.env`; `.env.example` only |
| Schema design visible in the repo | ✅ Yes | `schema/er_diagram.md` (Mermaid) + `schema/CHANGES.md` (midterm → final changes) |

## Tier 2 — Good practice

| Item | Status | Note |
|---|---|---|
| Dependencies/Config/Environment files | ✅ Yes | `pyproject.toml` + `uv.lock`, `.python-version` (3.11), `ingestion/Dockerfile` |
| Commit history shows incremental work | ✅ Yes | feature branches + PRs (#1–#6); all members commit under their own accounts |
| Note on data source / sample-data approach | ✅ Yes | `data/README.md` (representative subset of games) |
| Folder structure separates code by purpose | ✅ Yes | `ingestion/` · `transform/` · `schema/` · `app/` (platform vs consumer) |

## Tier 3 — Aspirational

| Item | Status | Note |
|---|---|---|
| Infra-as-code (`.tf` files, shell scripts) | 🟡 Built, not committed | Terraform provisions the GCS bucket + BigQuery datasets, applied & verified; **intentionally gitignored (security)** and shown live in the final demo for the +20 bonus |
| Automated data quality tests (Great Expectations, etc.) | ⬜ Not yet | chose Terraform as the bonus tool instead |
| CI/CD config file | ⬜ Not yet | — |
| Orchestration DAG definition | ⬜ N/A | Airflow not required for the final; ingestion is containerized (Cloud Run-ready) |
| ADR(s) committed to the repo | ⬜ Not yet | key decisions captured in the deck + `schema/CHANGES.md` |
