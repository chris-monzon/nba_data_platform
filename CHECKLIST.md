# GitHub Readiness Checklist — Milestone 4

**Repo:** https://github.com/chris-monzon/nba_data_platform  _(update if the owner/name changes)_
**Public:** Yes

> Status as of the M4 scaffolding commit. "Not yet" is a valid answer per the assignment;
> we mark honestly and will flip items to ✅ as the build progresses.

## Tier 1 — Must-have

| Item | Status | Note |
|---|---|---|
| README (what it is, data source, how to run, current state) | ✅ Yes | `README.md` |
| Data ingestion — script or notes on how raw data was obtained | ✅ Yes | `ingestion/README.md` + `data/README.md`; scripts stubbed |
| Transformation scripts | 🟡 Partial | `transform/` SQL stubs present; logic in progress |
| No secrets/credentials committed | ✅ Yes | `.gitignore` covers keys/`.env`; `.env.example` only |
| Schema design visible in the repo | ✅ Yes | `schema/` ER diagram (draft — under revision) |

## Tier 2 — Good practice

| Item | Status | Note |
|---|---|---|
| Dependencies/Config/Environment files | ✅ Yes | `pyproject.toml` + `uv.lock`, `.python-version` (3.11) |
| Commit history shows incremental work | 🟡 In progress | all 3 members commit under own accounts; feature branches + PRs |
| Note on data source / sample-data approach | ✅ Yes | `data/README.md` (representative subset of games) |
| Folder structure separates code by purpose | ✅ Yes | `ingestion/` · `transform/` · `schema/` · `app/` (platform vs consumer) |

## Tier 3 — Aspirational

| Item | Status | Note |
|---|---|---|
| Infra-as-code (`.tf` files, shell scripts) | ⬜ Not yet | candidate for the +20 bonus (Terraform for GCS/BigQuery/Cloud Run) |
| Automated data quality tests (Great Expectations, etc.) | ⬜ Not yet | alternative +20 bonus path |
| CI/CD config file | ⬜ Not yet | — |
| Orchestration DAG definition | ⬜ N/A | Airflow not required for final; ingestion is a Cloud Run job |
| ADR(s) committed to the repo | ⬜ Not yet | key decisions currently captured in the deck |
