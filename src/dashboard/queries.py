"""SQL queries for the dashboard, returning pandas DataFrames.

Kept framework-agnostic (no Streamlit imports) so they're reusable from
notebooks too. The app layer adds caching on top.

Filtering is done on ``overviewpage`` (the Leaguepedia page id), NOT the
``tournament`` display column: Cargo leaves ScoreboardPlayers.tournament empty,
but both tables carry a populated ``overviewpage``. The UI maps the friendly
tournament name to its overviewpage before calling these.
"""
from __future__ import annotations

import pandas as pd
from sqlalchemy import text
from sqlalchemy.engine import Engine


def _df(engine: Engine, sql: str, **params) -> pd.DataFrame:
    with engine.connect() as conn:
        return pd.read_sql(text(sql), conn, params=params)


# ----------------------------------------------------------------- filters
def tournaments(engine: Engine) -> pd.DataFrame:
    """Return distinct tournaments as (name, overviewpage), newest first."""
    return _df(engine, """
        SELECT tournament AS name, overviewpage,
               max(datetime_utc) AS last_game
        FROM scoreboardgames
        WHERE overviewpage <> ''
        GROUP BY tournament, overviewpage
        ORDER BY last_game DESC NULLS LAST
    """)


def teams(engine: Engine, overview: str | None) -> list[str]:
    sql = """
        SELECT team FROM (
            SELECT team1 AS team FROM scoreboardgames WHERE (:op IS NULL OR overviewpage = :op)
            UNION
            SELECT team2 FROM scoreboardgames WHERE (:op IS NULL OR overviewpage = :op)
        ) s WHERE team IS NOT NULL AND team <> '' ORDER BY team
    """
    return _df(engine, sql, op=overview)["team"].tolist()


def players(engine: Engine, overview: str | None, team: str | None) -> list[str]:
    sql = """
        SELECT DISTINCT name FROM scoreboardplayers
        WHERE name IS NOT NULL AND name <> ''
          AND (:op IS NULL OR overviewpage = :op)
          AND (:team IS NULL OR team = :team)
        ORDER BY name
    """
    return _df(engine, sql, op=overview, team=team)["name"].tolist()


# ---------------------------------------------------------------- overview
def overview_kpis(engine: Engine, overview: str | None) -> dict:
    sql = """
        SELECT count(*) AS games,
               count(DISTINCT patch) FILTER (WHERE patch <> '') AS patches,
               string_agg(DISTINCT patch, ', ' ORDER BY patch) FILTER (WHERE patch <> '') AS patch_list,
               min(datetime_utc) AS first_game,
               max(datetime_utc) AS last_game,
               round(avg(gamelength_number)::numeric, 1) AS avg_len_min
        FROM scoreboardgames WHERE (:op IS NULL OR overviewpage = :op)
    """
    row = _df(engine, sql, op=overview).iloc[0].to_dict()
    row["teams"] = len(teams(engine, overview))
    return row


# ----------------------------------------------------------- team scouting
def team_record(engine: Engine, team: str, overview: str | None) -> dict:
    sql = """
        SELECT
          count(*) AS games,
          count(*) FILTER (WHERE (team1=:team AND winner=1) OR (team2=:team AND winner=2)) AS wins,
          count(*) FILTER (WHERE team1=:team) AS blue_games,
          count(*) FILTER (WHERE team1=:team AND winner=1) AS blue_wins,
          count(*) FILTER (WHERE team2=:team) AS red_games,
          count(*) FILTER (WHERE team2=:team AND winner=2) AS red_wins
        FROM scoreboardgames
        WHERE (team1=:team OR team2=:team) AND (:op IS NULL OR overviewpage = :op)
    """
    return _df(engine, sql, team=team, op=overview).iloc[0].to_dict()


def team_objectives(engine: Engine, team: str, overview: str | None) -> dict:
    sql = """
        SELECT
          round(avg(CASE WHEN team1=:team THEN team1dragons ELSE team2dragons END)::numeric, 2) AS dragons,
          round(avg(CASE WHEN team1=:team THEN team1barons ELSE team2barons END)::numeric, 2) AS barons,
          round(avg(CASE WHEN team1=:team THEN team1towers ELSE team2towers END)::numeric, 2) AS towers,
          round(avg(CASE WHEN team1=:team THEN team1riftheralds ELSE team2riftheralds END)::numeric, 2) AS heralds,
          round(avg(CASE WHEN team1=:team THEN team1voidgrubs ELSE team2voidgrubs END)::numeric, 2) AS grubs,
          round(avg(CASE WHEN team1=:team THEN team1kills ELSE team2kills END)::numeric, 1) AS kills
        FROM scoreboardgames
        WHERE (team1=:team OR team2=:team) AND (:op IS NULL OR overviewpage = :op)
    """
    return _df(engine, sql, team=team, op=overview).iloc[0].to_dict()


def team_champion_pool(engine: Engine, team: str, overview: str | None) -> pd.DataFrame:
    sql = """
        SELECT champion,
               count(*) AS games,
               sum(CASE WHEN playerwin='Yes' THEN 1 ELSE 0 END) AS wins,
               round(100.0 * sum(CASE WHEN playerwin='Yes' THEN 1 ELSE 0 END) / count(*), 1) AS winrate_pct
        FROM scoreboardplayers
        WHERE team=:team AND (:op IS NULL OR overviewpage = :op) AND champion <> ''
        GROUP BY champion ORDER BY games DESC, winrate_pct DESC
    """
    return _df(engine, sql, team=team, op=overview)


def team_bans(engine: Engine, team: str, overview: str | None) -> pd.DataFrame:
    sql = """
        SELECT champ AS champion, count(*) AS bans FROM (
            SELECT unnest(team1bans) AS champ FROM scoreboardgames
              WHERE team1=:team AND (:op IS NULL OR overviewpage = :op)
            UNION ALL
            SELECT unnest(team2bans) FROM scoreboardgames
              WHERE team2=:team AND (:op IS NULL OR overviewpage = :op)
        ) b WHERE champ IS NOT NULL AND champ <> ''
        GROUP BY champ ORDER BY bans DESC
    """
    return _df(engine, sql, team=team, op=overview)


def team_games(engine: Engine, team: str, overview: str | None) -> pd.DataFrame:
    sql = """
        SELECT datetime_utc AS date, team1, team2,
               CASE WHEN winner=1 THEN team1 WHEN winner=2 THEN team2 END AS winner,
               patch, gamelength AS length
        FROM scoreboardgames
        WHERE (team1=:team OR team2=:team) AND (:op IS NULL OR overviewpage = :op)
        ORDER BY datetime_utc DESC
    """
    return _df(engine, sql, team=team, op=overview)


# ----------------------------------------------------------------- players
def player_summary(engine: Engine, name: str, overview: str | None) -> dict:
    sql = """
        SELECT count(*) AS games,
               round(avg(kills)::numeric,1) AS k,
               round(avg(deaths)::numeric,1) AS d,
               round(avg(assists)::numeric,1) AS a,
               round((sum(kills)+sum(assists))::numeric / NULLIF(sum(deaths),0), 2) AS kda,
               round(avg(cs)::numeric,0) AS cs,
               round(avg(gold)::numeric,0) AS gold,
               round(avg(damagetochampions)::numeric,0) AS dmg,
               round(avg(visionscore)::numeric,1) AS vision,
               round(100.0*sum(CASE WHEN playerwin='Yes' THEN 1 ELSE 0 END)/count(*),1) AS winrate_pct
        FROM scoreboardplayers
        WHERE name=:name AND (:op IS NULL OR overviewpage = :op)
    """
    return _df(engine, sql, name=name, op=overview).iloc[0].to_dict()


def player_champions(engine: Engine, name: str, overview: str | None) -> pd.DataFrame:
    sql = """
        SELECT champion, count(*) AS games,
               round(100.0*sum(CASE WHEN playerwin='Yes' THEN 1 ELSE 0 END)/count(*),1) AS winrate_pct,
               round((sum(kills)+sum(assists))::numeric / NULLIF(sum(deaths),0),2) AS kda
        FROM scoreboardplayers
        WHERE name=:name AND (:op IS NULL OR overviewpage = :op) AND champion <> ''
        GROUP BY champion ORDER BY games DESC
    """
    return _df(engine, sql, name=name, op=overview)


def player_games(engine: Engine, name: str, overview: str | None) -> pd.DataFrame:
    sql = """
        SELECT datetime_utc AS date, team, champion, role,
               kills, deaths, assists, cs, gold, damagetochampions AS dmg,
               visionscore AS vision, playerwin AS win
        FROM scoreboardplayers
        WHERE name=:name AND (:op IS NULL OR overviewpage = :op)
        ORDER BY datetime_utc DESC
    """
    return _df(engine, sql, name=name, op=overview)


# ------------------------------------------------------------------- draft
def top_picks(engine: Engine, overview: str | None) -> pd.DataFrame:
    sql = """
        SELECT champion, count(*) AS picks,
               round(100.0*sum(CASE WHEN playerwin='Yes' THEN 1 ELSE 0 END)/count(*),1) AS winrate_pct
        FROM scoreboardplayers
        WHERE (:op IS NULL OR overviewpage = :op) AND champion <> ''
        GROUP BY champion ORDER BY picks DESC
    """
    return _df(engine, sql, op=overview)


def top_bans(engine: Engine, overview: str | None) -> pd.DataFrame:
    sql = """
        SELECT champ AS champion, count(*) AS bans FROM (
            SELECT unnest(team1bans) AS champ FROM scoreboardgames WHERE (:op IS NULL OR overviewpage = :op)
            UNION ALL
            SELECT unnest(team2bans) FROM scoreboardgames WHERE (:op IS NULL OR overviewpage = :op)
        ) b WHERE champ IS NOT NULL AND champ <> ''
        GROUP BY champ ORDER BY bans DESC
    """
    return _df(engine, sql, op=overview)
