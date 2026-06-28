-- silver_dims.sql
-- Layer: SILVER | Source: per-game dim/roster Parquet in GCS (from ingestion/parse_dims.py)
-- Purpose: conformed dimensions (PLAYER/TEAM/GAME/SEASON) + the PLAYER_TEAM_SEASON SCD2 bridge.
--
-- parse_dims.py writes each game's SLICE of every dimension as its own per-game Parquet, so a
-- player/team recurs across games. The cross-game DEDUP is compute, so by "materialize where the
-- compute is" the deduped dims are NATIVE: an external `*_raw` staging table over the Parquet,
-- then a native dim that dedups ON THE KEY (not DISTINCT *, so any cross-game attribute
-- disagreement collapses to one row instead of breaking the PK).
--
-- PLAYER is BIO-ONLY: a player's team is time-varying, so it is not a player attribute. Team-for-
-- a-play comes from the facts; roster history is the PLAYER_TEAM_SEASON Type-2 SCD bridge below.
-- See schema/CHANGES.md (#5).
--
-- Conference (TEAM) and arena (GAME) are not in our sources -> NULL (see course notes). Dims are
-- conformed reference data, so they are clustered by natural key but NOT season-partitioned.


-- ============================================================================
-- External staging (raw, per-game, duplicated) over the silver Parquet
-- ============================================================================
CREATE OR REPLACE EXTERNAL TABLE `nba-data-architecture.nba_silver.dim_player_raw`
OPTIONS (format='PARQUET', uris=['gs://nba-data-architecture-lake/silver/dim_player/*.parquet']);

CREATE OR REPLACE EXTERNAL TABLE `nba-data-architecture.nba_silver.dim_team_raw`
OPTIONS (format='PARQUET', uris=['gs://nba-data-architecture-lake/silver/dim_team/*.parquet']);

CREATE OR REPLACE EXTERNAL TABLE `nba-data-architecture.nba_silver.dim_game_raw`
OPTIONS (format='PARQUET', uris=['gs://nba-data-architecture-lake/silver/dim_game/*.parquet']);

CREATE OR REPLACE EXTERNAL TABLE `nba-data-architecture.nba_silver.roster_raw`
OPTIONS (format='PARQUET', uris=['gs://nba-data-architecture-lake/silver/roster/*.parquet']);


-- ============================================================================
-- dim_player -- bio only, deduped on player_id
-- ============================================================================
CREATE OR REPLACE TABLE `nba-data-architecture.nba_silver.dim_player`
CLUSTER BY player_id AS
SELECT player_id, first_name, last_name, position
FROM (
  SELECT *, ROW_NUMBER() OVER (PARTITION BY player_id ORDER BY last_name, first_name) AS rn
  FROM `nba-data-architecture.nba_silver.dim_player_raw`
)
WHERE rn = 1;


-- ============================================================================
-- dim_team -- deduped on team_id; conference not in source (NULL)
-- ============================================================================
CREATE OR REPLACE TABLE `nba-data-architecture.nba_silver.dim_team`
CLUSTER BY team_id AS
SELECT team_id, abbreviation, full_name, CAST(NULL AS STRING) AS conference
FROM (
  SELECT *, ROW_NUMBER() OVER (PARTITION BY team_id ORDER BY abbreviation) AS rn
  FROM `nba-data-architecture.nba_silver.dim_team_raw`
)
WHERE rn = 1;


-- ============================================================================
-- dim_game -- one row per game; arena not in source (NULL)
-- ============================================================================
CREATE OR REPLACE TABLE `nba-data-architecture.nba_silver.dim_game`
CLUSTER BY game_id AS
SELECT game_id, season_id, home_team_id, away_team_id, game_date, CAST(NULL AS STRING) AS arena
FROM (
  SELECT *, ROW_NUMBER() OVER (PARTITION BY game_id ORDER BY game_date) AS rn
  FROM `nba-data-architecture.nba_silver.dim_game_raw`
)
WHERE rn = 1;


-- ============================================================================
-- dim_season -- static (no source feed); dates are the official 2015-16 calendar (approx)
-- ============================================================================
CREATE OR REPLACE TABLE `nba-data-architecture.nba_silver.dim_season` AS
SELECT * FROM UNNEST([STRUCT(
  2015 AS season_id, '2015-16' AS season_label,
  DATE '2015-10-27' AS start_date, DATE '2016-06-19' AS end_date
)]);


-- ============================================================================
-- player_team_season -- Type-2 SCD bridge for roster membership over time
-- ============================================================================
-- One row per (player, team, season) stint. PoC = single season, so every stint is OPEN
-- (valid_to NULL, is_current TRUE) -- there is no prior team to close. The surrogate key is a
-- deterministic hash of the natural stint key (stable across rebuilds). valid_from = the season
-- start; at multi-season scale, a team change closes the old stint and opens a new one -- see the
-- MERGE sketch below (the part that actually exercises SCD2).
CREATE OR REPLACE TABLE `nba-data-architecture.nba_silver.player_team_season`
CLUSTER BY player_id AS
WITH stints AS (
  SELECT DISTINCT season_id, team_id, player_id
  FROM `nba-data-architecture.nba_silver.roster_raw`
)
SELECT
  FARM_FINGERPRINT(FORMAT('%d|%d|%d', s.season_id, s.team_id, s.player_id)) AS player_team_season_id,
  s.player_id,
  s.team_id,
  s.season_id,
  d.start_date        AS valid_from,
  CAST(NULL AS DATE)  AS valid_to,      -- NULL = current stint
  TRUE                AS is_current
FROM stints s
JOIN `nba-data-architecture.nba_silver.dim_season` d USING (season_id);

-- Multi-season SCD2 load (documented; activates once there are team changes to detect).
-- Two steps because a single MERGE can't both expire the old row and insert the new one:
--
--   -- 1) expire stints whose (player) now maps to a different current team in the new batch
--   MERGE player_team_season t
--   USING (SELECT player_id, team_id, season_id, start_date AS valid_from FROM new_stints) s
--   ON  t.player_id = s.player_id AND t.is_current
--   WHEN MATCHED AND t.team_id <> s.team_id THEN
--     UPDATE SET valid_to = DATE_SUB(s.valid_from, INTERVAL 1 DAY), is_current = FALSE;
--
--   -- 2) insert the new current stints that don't already exist
--   INSERT player_team_season (player_team_season_id, player_id, team_id, season_id,
--                              valid_from, valid_to, is_current)
--   SELECT FARM_FINGERPRINT(FORMAT('%d|%d|%d', season_id, team_id, player_id)),
--          player_id, team_id, season_id, start_date, NULL, TRUE
--   FROM new_stints n
--   WHERE NOT EXISTS (SELECT 1 FROM player_team_season t
--                     WHERE t.player_id = n.player_id AND t.team_id = n.team_id
--                       AND t.season_id = n.season_id);


-- ============================================================================
-- Validation (after load; expected from the 2 manifest games -- both GSW vs CLE):
--   SELECT COUNT(*) FROM nba_silver.dim_player;                 -- 27 (deduped from 52)
--   SELECT COUNT(*), COUNT(DISTINCT player_id) FROM nba_silver.dim_player;  -- 27, 27 (key unique)
--   SELECT COUNT(*) FROM nba_silver.dim_team;                   -- 2 (GSW, CLE)
--   SELECT COUNT(*) FROM nba_silver.dim_game;                   -- 2
--   SELECT COUNT(*) FROM nba_silver.player_team_season;         -- 27, all is_current = TRUE
--   -- every player_location player should resolve in dim_player:
--   SELECT COUNT(*) FROM (SELECT DISTINCT player_id FROM nba_silver.player_location) pl
--   LEFT JOIN nba_silver.dim_player d USING (player_id) WHERE d.player_id IS NULL;  -- 0
-- ============================================================================
