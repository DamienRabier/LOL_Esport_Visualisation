"""Early-game queries over Oracle's Elixir data (``oe_match_data``).

OE carries the lane-diff timeline metrics Leaguepedia doesn't: gold/xp/cs diffs
at 10/15/20/25. These power the "Early game" view. OE isn't keyed to our
Leaguepedia tournament ids, so this view scopes by OE's own fields: league code
(LCK, LEC, LCS, …), year, and split.

Only ``datacompleteness = 'complete'`` rows have timeline data, so every query
filters on that. Team-level diffs are summed from the five role rows per game
(robust regardless of whether OE's team rows carry the diffs).
"""
from __future__ import annotations

import pandas as pd
from sqlalchemy import text
from sqlalchemy.engine import Engine

ROLES = ["top", "jng", "mid", "bot", "sup"]
ROLE_LABELS = {"top": "Top", "jng": "Jungle", "mid": "Mid", "bot": "Bot", "sup": "Support"}


def _df(engine: Engine, sql: str, **params) -> pd.DataFrame:
    with engine.connect() as conn:
        return pd.read_sql(text(sql), conn, params=params)


def attach_players_gd15(engine: Engine, df: pd.DataFrame, overview: str | None,
                        player_col: str = "player") -> pd.DataFrame:
    """Add a tournament GD@15 column to a players table (OE joined by name+champ+date)."""
    if df.empty:
        return df
    sql = """
        SELECT sp.name AS player, round(avg(oe.golddiffat15)::numeric) AS gd15
        FROM scoreboardplayers sp
        JOIN oe_match_data oe
          ON lower(oe.playername) = lower(sp.name)
         AND lower(oe.champion) = lower(sp.champion)
         AND substring(oe.date FROM 1 FOR 10) = to_char(sp.datetime_utc, 'YYYY-MM-DD')
         AND oe.position IN ('top','jng','mid','bot','sup')
         AND oe.datacompleteness = 'complete' AND oe.golddiffat15 IS NOT NULL
        WHERE (:op IS NULL OR sp.overviewpage = :op) AND sp.name <> ''
        GROUP BY sp.name
    """
    m = {str(r.player).strip().lower(): r.gd15 for r in _df(engine, sql, op=overview).itertuples()}
    out = df.copy()
    out["GD@15"] = [m.get(str(p).strip().lower()) for p in out[player_col]]
    return out


def top_players_gd15(engine: Engine, overview: str | None, limit: int = 3,
                     min_games: int = 3) -> pd.DataFrame:
    """Top players by avg GD@15 in a tournament, joining OE to Leaguepedia rows.

    Both tables live in the same Postgres DB, so this joins in-database on
    player + champion + date (OE has no shared game id).
    """
    sql = """
        SELECT sp.name AS player, sp.team AS team, count(*) AS games,
               round(avg(oe.golddiffat15)::numeric) AS gd15
        FROM scoreboardplayers sp
        JOIN oe_match_data oe
          ON lower(oe.playername) = lower(sp.name)
         AND lower(oe.champion) = lower(sp.champion)
         AND substring(oe.date FROM 1 FOR 10) = to_char(sp.datetime_utc, 'YYYY-MM-DD')
         AND oe.position IN ('top','jng','mid','bot','sup')
         AND oe.datacompleteness = 'complete' AND oe.golddiffat15 IS NOT NULL
        WHERE (:op IS NULL OR sp.overviewpage = :op) AND sp.name <> ''
        GROUP BY sp.name, sp.team
        HAVING count(*) >= :mg
        ORDER BY gd15 DESC
        LIMIT :lim
    """
    return _df(engine, sql, op=overview, mg=min_games, lim=limit)


def oe_team_profile(engine: Engine, team: str, year: str) -> pd.DataFrame:
    """A team's early-game role profile for a year (all leagues), by name.

    Used to overlay OE lane diffs on the Team scouting page. Joined on teamname
    since OE isn't keyed to Leaguepedia game ids.
    """
    sql = """
        SELECT position AS role, count(*) AS games,
               round(avg(golddiffat10)::numeric) AS gd10,
               round(avg(golddiffat15)::numeric) AS gd15,
               round(avg(xpdiffat10)::numeric)   AS xd10,
               round(avg(csdiffat10)::numeric,1) AS cd10
        FROM oe_match_data
        WHERE position IN ('top','jng','mid','bot','sup')
          AND teamname = :team AND year = :y AND datacompleteness = 'complete'
          AND golddiffat10 IS NOT NULL
        GROUP BY position
    """
    df = _df(engine, sql, team=team, y=year)
    if not df.empty:
        df["order"] = df["role"].map({r: i for i, r in enumerate(ROLES)})
        df = df.sort_values("order").drop(columns="order")
        df["role"] = df["role"].map(ROLE_LABELS)
    return df


def oe_player_profile(engine: Engine, player: str, year: str) -> dict:
    """A player's headline early-game diffs for a year, joined on playername."""
    sql = """
        SELECT count(*) AS games,
               round(avg(golddiffat10)::numeric) AS gd10,
               round(avg(golddiffat15)::numeric) AS gd15,
               round(avg(csdiffat10)::numeric,1) AS cd10,
               round(avg(xpdiffat10)::numeric)   AS xd10
        FROM oe_match_data
        WHERE position IN ('top','jng','mid','bot','sup')
          AND playername = :player AND year = :y AND datacompleteness = 'complete'
          AND golddiffat10 IS NOT NULL
    """
    df = _df(engine, sql, player=player, y=year)
    return df.iloc[0].to_dict() if not df.empty else {}


def attach_game_earlygame(engine: Engine, players: pd.DataFrame, date_str: str,
                          team1: str | None, team2: str | None) -> pd.DataFrame:
    """Attach per-player early-game diffs to a game's scoreboard (best effort).

    OE has no shared game id with Leaguepedia, so we match each player by
    (playername, champion) among OE rows on the same date for the two teams.
    Same player + champion twice on one day (e.g. a Bo5) is averaged.
    """
    if players.empty or not date_str or not (team1 or team2):
        return players
    teams = [t for t in (team1, team2) if t]
    sql = """
        SELECT playername, champion,
               round(avg(golddiffat10)::numeric) AS gd10,
               round(avg(golddiffat15)::numeric) AS gd15,
               round(avg(csdiffat10)::numeric,1) AS cd10
        FROM oe_match_data
        WHERE position IN ('top','jng','mid','bot','sup')
          AND substring(date FROM 1 FOR 10) = :d
          AND teamname IN :teams
          AND datacompleteness = 'complete'
        GROUP BY playername, champion
    """
    from sqlalchemy import bindparam
    stmt = text(sql).bindparams(bindparam("teams", expanding=True))
    with engine.connect() as conn:
        oe = pd.read_sql(stmt, conn, params={"d": date_str, "teams": teams})

    out = players.copy()
    if oe.empty:
        out["gd10"] = out["gd15"] = out["cd10"] = None
        return out

    def key(n, c):
        return f"{str(n).strip().lower()}|{str(c).strip().lower()}"

    oe["_k"] = [key(n, c) for n, c in zip(oe["playername"], oe["champion"])]
    lut = oe.set_index("_k")[["gd10", "gd15", "cd10"]].to_dict("index")
    out["_k"] = [key(n, c) for n, c in zip(out.get("name", ""), out.get("champion", ""))]
    out["gd10"] = [lut.get(k, {}).get("gd10") for k in out["_k"]]
    out["gd15"] = [lut.get(k, {}).get("gd15") for k in out["_k"]]
    out["cd10"] = [lut.get(k, {}).get("cd10") for k in out["_k"]]
    return out.drop(columns="_k")


def attach_player_games(engine: Engine, games: pd.DataFrame, player: str,
                        year: str) -> pd.DataFrame:
    """Add per-game GD@10/GD@15/CSD@10 to a player's game log (by champion+date)."""
    out = games.copy()
    if out.empty or not year:
        return out
    sql = """
        SELECT substring(date FROM 1 FOR 10) AS d, champion,
               round(avg(golddiffat10)::numeric) AS gd10,
               round(avg(golddiffat15)::numeric) AS gd15,
               round(avg(csdiffat10)::numeric,1) AS cd10
        FROM oe_match_data
        WHERE playername = :p AND year = :y
          AND position IN ('top','jng','mid','bot','sup')
          AND datacompleteness = 'complete' AND golddiffat10 IS NOT NULL
        GROUP BY d, champion
    """
    oe = _df(engine, sql, p=player, y=year)
    if oe.empty:
        out["GD@10"] = out["GD@15"] = out["CSD@10"] = None
        return out

    lut = {(r.d, str(r.champion).strip().lower()): (r.gd10, r.gd15, r.cd10)
           for r in oe.itertuples()}
    keys = [(str(d)[:10], str(c).strip().lower()) for d, c in zip(out["date"], out["champion"])]
    out["GD@10"] = [lut.get(k, (None, None, None))[0] for k in keys]
    out["GD@15"] = [lut.get(k, (None, None, None))[1] for k in keys]
    out["CSD@10"] = [lut.get(k, (None, None, None))[2] for k in keys]
    return out


def attach_team_games(engine: Engine, games: pd.DataFrame, team: str, year: str) -> pd.DataFrame:
    """Add per-game team GD@10/GD@15 to a team's recent-games table.

    Best effort: matches by (date, opponent). OE has no opponent column, so we
    self-join its team rows on gameid to recover the opponent. Multiple games vs
    the same opponent on one day are averaged.
    """
    out = games.copy()
    if out.empty or not year:
        return out
    sql = """
        WITH tg AS (
            SELECT gameid, substring(date FROM 1 FOR 10) AS d, teamname,
                   sum(golddiffat10) AS gd10, sum(golddiffat15) AS gd15
            FROM oe_match_data
            WHERE position IN ('top','jng','mid','bot','sup')
              AND year = :y AND datacompleteness = 'complete'
            GROUP BY gameid, substring(date FROM 1 FOR 10), teamname
        )
        SELECT a.d AS d, b.teamname AS opponent,
               round(avg(a.gd10)::numeric) AS gd10,
               round(avg(a.gd15)::numeric) AS gd15
        FROM tg a JOIN tg b ON a.gameid = b.gameid AND a.teamname <> b.teamname
        WHERE a.teamname = :team
        GROUP BY a.d, b.teamname
    """
    oe = _df(engine, sql, y=year, team=team)
    if oe.empty:
        out["GD@10"] = out["GD@15"] = None
        return out
    lut = {(r.d, str(r.opponent).strip().lower()): (r.gd10, r.gd15) for r in oe.itertuples()}
    opps = [(t2 if t1 == team else t1) for t1, t2 in zip(out["team1"], out["team2"])]
    keys = [(str(d)[:10], str(o).strip().lower()) for d, o in zip(out["date"], opps)]
    out["GD@10"] = [lut.get(k, (None, None))[0] for k in keys]
    out["GD@15"] = [lut.get(k, (None, None))[1] for k in keys]
    return out


def oe_champion_gd15(engine: Engine, year: str) -> dict:
    """{champion(lowercased): avg GD@15} across a year — a champ's early-game strength."""
    sql = """
        SELECT champion, round(avg(golddiffat15)::numeric) AS g
        FROM oe_match_data
        WHERE year = :y AND position IN ('top','jng','mid','bot','sup')
          AND datacompleteness = 'complete' AND golddiffat15 IS NOT NULL AND champion <> ''
        GROUP BY champion
    """
    df = _df(engine, sql, y=year)
    return {str(r.champion).strip().lower(): r.g for r in df.itertuples()}


def oe_team_gd15(engine: Engine, year: str) -> dict:
    """{team(lowercased): avg team GD@15} across a year (summed from roles/game)."""
    sql = """
        WITH per_game AS (
            SELECT gameid, teamname, sum(golddiffat15) AS gd15
            FROM oe_match_data
            WHERE year = :y AND position IN ('top','jng','mid','bot','sup')
              AND datacompleteness = 'complete'
            GROUP BY gameid, teamname
        )
        SELECT teamname, round(avg(gd15)::numeric) AS g
        FROM per_game WHERE teamname IS NOT NULL AND teamname <> ''
        GROUP BY teamname
    """
    df = _df(engine, sql, y=year)
    return {str(r.teamname).strip().lower(): r.g for r in df.itertuples()}


def attach_team_gd15(engine: Engine, df: pd.DataFrame, year: str,
                     team_col: str = "team") -> pd.DataFrame:
    """Add an avg team GD@15 column, joined on team name."""
    if df.empty or not year:
        return df
    m = oe_team_gd15(engine, year)
    out = df.copy()
    out["GD@15"] = [m.get(str(t).strip().lower()) for t in out[team_col]]
    return out


def attach_champion_gd15(engine: Engine, df: pd.DataFrame, year: str,
                         champ_col: str = "champion") -> pd.DataFrame:
    """Add an avg-GD@15-per-champion column to a champion table."""
    if df.empty or not year:
        return df
    m = oe_champion_gd15(engine, year)
    out = df.copy()
    out["GD@15"] = [m.get(str(c).strip().lower()) for c in out[champ_col]]
    return out
