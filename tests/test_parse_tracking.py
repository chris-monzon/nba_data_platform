"""Unit tests for parse_tracking._explode — the core SportVU reshape.

_explode is a pure function (no file I/O), so these run on a tiny hand-built
`events` dict in milliseconds — no 113 MB download. They lock the non-obvious
edge behavior verified against real data: dedup keep-first, ball-by-id (not
array position), null-timestamp drop, and ball kept off the player rows.
"""
import pytest

from ingestion.parse_tracking import _explode

BALL = [-1, -1, 5.0, 6.0, 7.0]  # team_id/player_id = -1; z = ball height


def _player(player_id, x, y, team_id=1610612744):
    return [team_id, player_id, x, y, 0.0]  # players have z ~= 0


@pytest.fixture
def raw():
    """Four moments covering every edge in one game-shaped payload."""
    return {
        "events": [
            {"moments": [
                # ts=100: normal frame (ball + 2 players)
                [1, 100, 720.0, 24.0, None, [BALL, _player(11, 1.0, 2.0), _player(12, 3.0, 4.0)]],
                # ts=200: ball missing from positions (only players present)
                [1, 200, 700.0, None, None, [_player(11, 1.5, 2.5), _player(12, 3.5, 4.5)]],
                # null timestamp: unusable -> dropped
                [1, None, 690.0, 10.0, None, [BALL, _player(11, 9.0, 9.0)]],
            ]},
            {"moments": [
                # ts=100 re-listed by the next event with DIFFERENT coords:
                # keep-first must win, so these 99.0/8.0/7.0 values must NOT appear.
                [1, 100, 720.0, 24.0, None,
                 [[-1, -1, 99.0, 99.0, 99.0], _player(11, 8.0, 8.0), _player(12, 7.0, 7.0)]],
                # ts=300: normal frame, different period/team
                [2, 300, 360.0, 14.0, None, [BALL, _player(13, 5.5, 6.5, team_id=1610612739)]],
            ]},
        ]
    }


def _by_moment_id(moment_rows):
    # moment row = (moment_id, period, game_clock, shot_clock, ball_x, ball_y, ball_z)
    return {row[0]: row for row in moment_rows}


def test_dedup_keeps_first_occurrence(raw):
    moment_rows, player_rows = _explode(raw)
    moments = _by_moment_id(moment_rows)

    # ts=100 appears twice across events -> exactly one MOMENT row
    assert sorted(moments) == [100, 200, 300]
    # ...and it holds the FIRST occurrence's ball, not the re-listed 99.0s
    assert moments[100][4:7] == (5.0, 6.0, 7.0)
    # likewise the first occurrence's player coords (1,2)/(3,4), not (8,8)/(7,7)
    p100 = {pid: (x, y) for (mid, _team, pid, x, y) in player_rows if mid == 100}
    assert p100 == {11: (1.0, 2.0), 12: (3.0, 4.0)}


def test_missing_ball_yields_null_ball_coords(raw):
    moment_rows, player_rows = _explode(raw)
    moments = _by_moment_id(moment_rows)

    # ball absent (no player_id == -1) -> ball x/y/z are None, frame still kept
    assert moments[200][4:7] == (None, None, None)
    # the two players in that frame still produce rows
    assert sum(1 for r in player_rows if r[0] == 200) == 2


def test_null_timestamp_dropped(raw):
    moment_rows, player_rows = _explode(raw)

    assert all(row[0] is not None for row in moment_rows)
    assert 690.0 not in {row[2] for row in moment_rows}  # the null-ts frame's clock
    assert all(x not in (9.0,) for *_, x, _y in player_rows)  # its player gone too


def test_ball_excluded_from_player_rows(raw):
    moment_rows, player_rows = _explode(raw)

    assert all(player_id != -1 for (_mid, _team, player_id, _x, _y) in player_rows)
    # 2 (ts100) + 2 (ts200) + 1 (ts300) = 5; the dup and null-ts frames contribute none
    assert len(player_rows) == 5
