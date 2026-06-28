-- gold_events_with_location.sql
-- Layer: GOLD | The HEADLINE serving mart for the event/shot map. The one table Streamlit reads.
-- Source: silver `event` (PBP spine) LEFT JOIN silver `shot_location` (ball-trajectory release).
--
-- GRAIN: one row per (game_id, event_id) -- the PBP event spine. For field-goal attempts the row
-- carries the shot's court location + geometry (from shot_location); all other events carry NULL
-- location. (The earlier event x PLAYER full-floor grain is DEFERRED -- the 10-player snapshot needs
-- per-event tracking windows, which the clock-desync finding showed can't be pinned by clock alone.)
--
-- WHY shot_location, not a fuzzy-clock join: PBP and SportVU clocks are NOT synced to the second, so
-- matching an event to the nearest-clock tracking frame lands ~9 ft off (up to 40 ft on transition).
-- ingestion/parse_shot_locations.py instead locates each shot from the ball's flight (ball-at-rim ->
-- back up to release), cutting median error to ~2 ft vs PBP's own stated distances. This mart only
-- applies the geometry to those release coordinates (schema T8: cross-source geometry lives in gold).
--
-- 622 NOTE: game 0021500622's tracking is corrupt (clocks misaligned ~55s, 37% of events missing
-- moments), so it has no shot_location rows -- its PBP events remain here with NULL location.
--
-- Native CREATE OR REPLACE (retroactive backfill); partition by season_start_year, cluster by
-- (game_id, period) so single-game/period dashboard reads prune to a few blocks.

CREATE OR REPLACE TABLE `nba-data-architecture.nba_gold.events_with_location`
PARTITION BY RANGE_BUCKET(season_start_year, GENERATE_ARRAY(1996, 2041, 1))
CLUSTER BY game_id, period AS

WITH located AS (
  SELECT
    -- event spine
    e.season_start_year, e.season, e.game_id, e.event_id, e.period,
    e.event_clock_seconds, e.clock_display, e.event_type, e.event_action_type,
    e.shot_made_flag, e.description,
    e.event_player_id, e.event_player_name, e.event_team_id,
    -- shot release location (NULL for non-shots and for unlocatable / 622 shots)
    sl.shot_player_id,
    sl.shooter_x, sl.shooter_y,           -- shooter's feet at release (the shot-chart location)
    sl.ball_x, sl.ball_y,                 -- ball at release (official-NBA basis; exposed for later)
    sl.release_game_clock,
    sl.shooter_x IS NOT NULL AS has_shot_location,
    -- shot distance: nearest-hoop from the shooter's release position. Hoops at (5.25,25) &
    -- (88.75,25) on the 94x50 ft court; nearest-hoop is correct except >47ft heaves (self-flagging).
    CASE WHEN sl.shooter_x IS NOT NULL THEN LEAST(
      SQRT(POW(sl.shooter_x -  5.25, 2) + POW(sl.shooter_y - 25, 2)),
      SQRT(POW(sl.shooter_x - 88.75, 2) + POW(sl.shooter_y - 25, 2))
    ) END AS shot_distance
  FROM `nba-data-architecture.nba_silver.event` e
  LEFT JOIN `nba-data-architecture.nba_silver.shot_location` sl
    ON sl.game_id = e.game_id AND sl.event_id = e.event_id
)

SELECT
  *,
  -- 3pt classification: corner is a straight 22ft line (within 3ft of a sideline, |y-25|>=22),
  -- elsewhere the 23.75ft arc. NULL for rows without a shot location.
  CASE
    WHEN shot_distance IS NULL          THEN NULL
    WHEN ABS(shooter_y - 25) >= 22      THEN shot_distance >= 22
    ELSE                                     shot_distance >= 23.75
  END AS is_three
FROM located;


-- ============================================================================
-- Validation (run after load):
--   -- 1) spine intact: one row per event (936 = 491 game-438 + 445 game-622)
--   SELECT COUNT(*), COUNT(DISTINCT FORMAT('%s-%d', game_id, event_id)) FROM ...events_with_location;
--   -- 2) shot coverage: located shots per game (622 expected 0)
--   SELECT game_id, COUNTIF(has_shot_location) located, COUNTIF(shot_made_flag IS NOT NULL) fgs
--   FROM ...events_with_location GROUP BY 1;
--   -- 3) geometry sanity: realistic distances (~14ft avg) + 3pt share ~33%
--   SELECT ROUND(AVG(shot_distance),1) avg_ft, COUNTIF(is_three)/COUNT(*) three_rate
--   FROM ...events_with_location WHERE has_shot_location;
--   -- 4) ground truth: is_three vs PBP '3PT' text (diagonal = agreement, expect ~85%)
--   SELECT CONTAINS_SUBSTR(description,'3PT') pbp3, is_three, COUNT(*)
--   FROM ...events_with_location WHERE has_shot_location GROUP BY 1,2 ORDER BY 1,2;
-- ============================================================================
