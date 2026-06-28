-- silver_pbp.sql
-- Layer: SILVER | Source: raw play-by-play Parquet in GCS bronze (from ingestion/fetch_pbp.py)
-- Purpose: conform NBA nbastats PBP into the semantic EVENT model + EVENT_PARTICIPANT bridge.
--
-- Unlike silver_tracking.sql (pure external DDL, because parse_tracking.py already conformed
-- the Parquet), PBP bronze is RAW -- fetch_pbp.py only filtered-to-game + CSV->Parquet, zero
-- cleaning. So ALL the conform work lives here, in SQL: PCTIMESTRING "MM:SS" -> seconds,
-- decode EVENTMSGTYPE codes, derive season, normalize ids, coalesce descriptions, and
-- normalize the PLAYER1/2/3 repeating group into a participant bridge.
--
-- Three objects:
--   1. pbp_raw           EXTERNAL, zero-transform, over bronze Parquet (declarative landing).
--   2. event             NATIVE, the conformed semantic event spine (PK = game_id, event_id).
--   3. event_participant NATIVE, the EVENT<->PLAYER M:M bridge (PLAYER1/2/3 unpivoted).
--
-- Storage choice (why native, not external like tracking): PBP needs real compute at silver,
-- so we materialize the conform ONCE into native storage (fast, prunable) rather than re-run
-- it on every query (a view) or re-parse files every read (external). Tracking stayed external
-- because its Parquet was pre-conformed -- "materialize where the compute is."
--
-- Retroactive load envelope: our data is a static 10-year-old season, so this is a full
-- CREATE OR REPLACE (backfill). The conform SELECT is written game-filterable so the SAME
-- SELECT becomes a MERGE source if this is ever extended to live nightly accumulation.
--
-- NOTE on partitioning: BigQuery cannot PARTITION BY a STRING, so "partition by season" is
-- realized as integer-range partitioning on a derived season_start_year (INT), with the
-- human-readable season label kept as a separate column. CLUSTER BY game_id either way.


-- ============================================================================
-- 1) pbp_raw -- raw external table over BRONZE Parquet (wildcard recurses season=/game_id=)
-- ============================================================================
CREATE OR REPLACE EXTERNAL TABLE `nba-data-architecture.nba_silver.pbp_raw`
OPTIONS (
  format = 'PARQUET',
  -- *.parquet (not bare *) so stray non-Parquet files (e.g. macOS .DS_Store) are excluded;
  -- BigQuery's wildcard matches across '/', so this still recurses season=/game_id= dirs.
  uris = ['gs://nba-data-architecture-lake/bronze/pbp/*.parquet']
);


-- ============================================================================
-- 2) event -- conformed semantic event spine, one row per (game_id, event_id)
-- ============================================================================
CREATE OR REPLACE TABLE `nba-data-architecture.nba_silver.event`
PARTITION BY RANGE_BUCKET(season_start_year, GENERATE_ARRAY(1996, 2041, 1))
CLUSTER BY game_id AS
WITH raw AS (
  -- Join-key gotcha: payload GAME_ID is int (21500438); zero-pad to the 10-char canonical key.
  -- EXCEPT(GAME_ID) avoids a duplicate-name collision (BQ column names are case-insensitive).
  SELECT LPAD(CAST(GAME_ID AS STRING), 10, '0') AS game_id, * EXCEPT (GAME_ID)
  FROM `nba-data-architecture.nba_silver.pbp_raw`
),
seasoned AS (
  -- PBP payload has no season column; derive it from the game_id encoding.
  -- NBA 10-char id = '00' + season_type(1) + YY(2) + game_num(5); chars 4-5 = season start year.
  -- Century guard (YY<50 => 2000s) only matters for pre-2000 seasons; harmless for ours.
  SELECT
    *,
    IF(CAST(SUBSTR(game_id, 4, 2) AS INT64) < 50,
       2000 + CAST(SUBSTR(game_id, 4, 2) AS INT64),
       1900 + CAST(SUBSTR(game_id, 4, 2) AS INT64)) AS season_start_year
  FROM raw
)
SELECT
  season_start_year,                                              -- INT, partition key
  CONCAT(CAST(season_start_year AS STRING), '-',
         LPAD(CAST(MOD(season_start_year + 1, 100) AS STRING), 2, '0')) AS season,  -- "2015-16" label
  game_id,
  EVENTNUM AS event_id,                                           -- PK = (game_id, event_id)
  PERIOD  AS period,
  -- PCTIMESTRING "MM:SS" -> seconds remaining in the period (SAFE_CAST guards odd formats).
  SAFE_CAST(SPLIT(PCTIMESTRING, ':')[OFFSET(0)] AS INT64) * 60
    + SAFE_CAST(SPLIT(PCTIMESTRING, ':')[OFFSET(1)] AS INT64)    AS event_clock_seconds,
  PCTIMESTRING AS clock_display,
  -- EVENTMSGTYPE decode -- all 14 codes confirmed against in-data descriptions (see
  -- course_materials/pbp_event_code_decode.md). Unknown codes -> 'OTHER', raw code retained.
  CASE EVENTMSGTYPE
    WHEN 1  THEN 'MADE_SHOT'
    WHEN 2  THEN 'MISSED_SHOT'
    WHEN 3  THEN 'FREE_THROW'
    WHEN 4  THEN 'REBOUND'
    WHEN 5  THEN 'TURNOVER'
    WHEN 6  THEN 'FOUL'
    WHEN 7  THEN 'VIOLATION'
    WHEN 8  THEN 'SUBSTITUTION'
    WHEN 9  THEN 'TIMEOUT'
    WHEN 10 THEN 'JUMP_BALL'
    WHEN 11 THEN 'EJECTION'
    WHEN 12 THEN 'PERIOD_BEGIN'
    WHEN 13 THEN 'PERIOD_END'
    WHEN 18 THEN 'INSTANT_REPLAY'                                 -- best-effort ("Support Ruling")
    ELSE 'OTHER'
  END AS event_type,
  EVENTMSGTYPE       AS event_type_code,                          -- raw code, for traceability
  EVENTMSGACTIONTYPE AS event_action_type,                        -- subtype passthrough (decode deferred)
  -- Field-goal made/miss only (types 1/2); FREE_THROW and non-shots are NULL by design.
  CASE WHEN EVENTMSGTYPE = 1 THEN TRUE
       WHEN EVENTMSGTYPE = 2 THEN FALSE END AS shot_made_flag,
  -- Exactly one of the three descriptions is populated (0 all-null rows in our data).
  COALESCE(HOMEDESCRIPTION, VISITORDESCRIPTION, NEUTRALDESCRIPTION) AS description,
  -- Primary actor (PLAYER1). 0 is the "no player" sentinel; team id is float64(NaN) when absent.
  NULLIF(PLAYER1_ID, 0)            AS event_player_id,
  PLAYER1_NAME                     AS event_player_name,
  SAFE_CAST(PLAYER1_TEAM_ID AS INT64) AS event_team_id
FROM seasoned;


-- ============================================================================
-- 3) event_participant -- EVENT<->PLAYER bridge: PLAYER1/2/3 repeating group, normalized
-- ============================================================================
-- Resolves the M:M between events and their direct participants (shooter/assister, fouler/
-- fouled, etc.). role is event-type-dependent semantics -> left NULL now, decoded later
-- (additive, non-breaking). PK = (game_id, event_id, player_id); a player can't fill two
-- slots of one event, so player-keyed is collision-free and is the natural participant grain.
CREATE OR REPLACE TABLE `nba-data-architecture.nba_silver.event_participant`
PARTITION BY RANGE_BUCKET(season_start_year, GENERATE_ARRAY(1996, 2041, 1))
CLUSTER BY game_id AS
WITH raw AS (
  SELECT LPAD(CAST(GAME_ID AS STRING), 10, '0') AS game_id, * EXCEPT (GAME_ID)
  FROM `nba-data-architecture.nba_silver.pbp_raw`
),
seasoned AS (
  SELECT
    *,
    IF(CAST(SUBSTR(game_id, 4, 2) AS INT64) < 50,
       2000 + CAST(SUBSTR(game_id, 4, 2) AS INT64),
       1900 + CAST(SUBSTR(game_id, 4, 2) AS INT64)) AS season_start_year
  FROM raw
),
unpivoted AS (
  -- Multi-column UNPIVOT: each PLAYERn_* triple becomes one row, tagged with participant_slot.
  SELECT season_start_year, game_id, EVENTNUM AS event_id,
         participant_slot, player_id, player_name, player_team_id
  FROM seasoned
  UNPIVOT (
    (player_id, player_name, player_team_id)
    FOR participant_slot IN (
      (PLAYER1_ID, PLAYER1_NAME, PLAYER1_TEAM_ID) AS 1,
      (PLAYER2_ID, PLAYER2_NAME, PLAYER2_TEAM_ID) AS 2,
      (PLAYER3_ID, PLAYER3_NAME, PLAYER3_TEAM_ID) AS 3
    )
  )
)
SELECT
  season_start_year,
  game_id,
  event_id,
  participant_slot,
  player_id,
  player_name,
  SAFE_CAST(player_team_id AS INT64) AS team_id,
  CAST(NULL AS STRING)               AS role        -- semantic role decode deferred (additive later)
FROM unpivoted
WHERE player_id <> 0;                               -- drop empty slots (0 = "no player")


-- ============================================================================
-- Validation (run after load; expected from the 2 manifest games):
--   SELECT COUNT(*) FROM nba_silver.event;                       -- 936 (491 + 445)
--   SELECT event_type, COUNT(*) FROM nba_silver.event GROUP BY 1 ORDER BY 2 DESC;
--   SELECT COUNT(*) FROM nba_silver.event WHERE event_type = 'OTHER';   -- expect 0 (all codes mapped)
--   SELECT COUNT(*) FROM nba_silver.event_participant;           -- <= 936*3, > 936
--   SELECT COUNT(*) FROM nba_silver.event_participant WHERE player_id IS NULL; -- 0
--   SELECT COUNT(DISTINCT season) FROM nba_silver.event;         -- 1 ("2015-16")
-- ============================================================================
