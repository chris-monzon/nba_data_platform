-- silver_shot_location.sql
-- Layer: SILVER | Source: per-game shot-location Parquet in GCS (from ingestion/parse_shot_locations.py)
-- Purpose: expose the ball-trajectory-derived shot release locations to BigQuery, zero-copy.
--
-- parse_shot_locations.py already conformed types/ids (one row per PBP field-goal attempt, with
-- the shooter's and ball's court (x,y) at the detected release instant), so there is NO transform
-- here -- just external-table DDL over the Parquet, exactly like silver_tracking.sql.
--
-- The release detection (find the ball-at-rim frame, back up to release) is trajectory analysis
-- done in Python; this table carries only the resulting coordinates. The distance/zone GEOMETRY is
-- computed downstream in gold (schema decision T8: cross-source geometry lives in gold).
--
-- Grain: one row per (game_id, event_id) field-goal attempt. shooter_x/y NULL when the shot could
-- not be located (no ball-at-rim frame, or shooter untracked near release).

CREATE OR REPLACE EXTERNAL TABLE `nba-data-architecture.nba_silver.shot_location`
OPTIONS (
  format = 'PARQUET',
  uris = ['gs://nba-data-architecture-lake/silver/shot_location/*']
);
