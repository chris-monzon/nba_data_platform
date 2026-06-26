-- silver_tracking.sql
-- Layer: SILVER | Source: silver tracking Parquet in GCS (from ingestion/parse_tracking.py)
-- Purpose: expose the parsed 25 Hz tracking moments to BigQuery, zero-copy.
--
-- parse_tracking.py already conformed types/ids/clocks (game_clock is float
-- seconds), so there is NO transform here -- just external-table DDL over the
-- Parquet. Header/detail pair: `moment` (one row per instant, ball x/y/z + clocks)
-- and `player_location` (one row per player per instant), joined downstream by
-- (game_id, moment_id).
--
-- No hive partition columns declared on purpose: the Parquet payload already
-- carries game_id (+ season on moment), which would collide with the season=/
-- game_id= path keys (BigQuery rejects that). BQ reads them from the payload
-- instead; player_location needs no season (it inherits it from moment on join).

CREATE OR REPLACE EXTERNAL TABLE `nba-data-architecture.nba_silver.moment`
OPTIONS (
  format = 'PARQUET',
  uris = ['gs://nba-data-architecture-lake/silver/tracking_moment/*']
);

CREATE OR REPLACE EXTERNAL TABLE `nba-data-architecture.nba_silver.player_location`
OPTIONS (
  format = 'PARQUET',
  uris = ['gs://nba-data-architecture-lake/silver/player_location/*']
);
