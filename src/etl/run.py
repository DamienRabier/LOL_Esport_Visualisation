"""ETL command line: fetch from Leaguepedia and load into PostgreSQL.

Examples
--------
    # Create tables (run once)
    python -m src.etl.run init-db

    # Ingest a whole tournament (games + players)
    python -m src.etl.run tournament "MSI 2025"

    # Ingest a team's full game history (scouting)
    python -m src.etl.run team "G2 Esports"

    # Refresh reference tables
    python -m src.etl.run leagues
    python -m src.etl.run current-leagues

    # Load Oracle's Elixir advanced stats for a year (lane diffs, etc.)
    python -m src.etl.run oe 2026
"""
from __future__ import annotations

import argparse

from config import LEAGUEPEDIA
from src import oracleselixir as oe
from src.api import LeaguepediaClient
from src.db import init_schema, upsert_dataframe


def _client() -> LeaguepediaClient:
    return LeaguepediaClient(LEAGUEPEDIA.username, LEAGUEPEDIA.password)


def ingest_tournament(name: str) -> None:
    api = _client()
    print(f"Fetching tournament metadata for '{name}'...")
    safe = name.replace("'", "''")
    upsert_dataframe(api.tournaments(where=f"T.Name = '{safe}'"), "Tournaments")

    print("Fetching games...")
    upsert_dataframe(api.games_for_tournament(name), "ScoreboardGames")

    print("Fetching players...")
    upsert_dataframe(api.players_for_tournament(name), "ScoreboardPlayers")


def ingest_team(name: str) -> None:
    api = _client()
    print(f"Fetching all games for team '{name}'...")
    upsert_dataframe(api.games_for_team(name), "ScoreboardGames")

    # Player rows for that team — queried directly by SP.Team so we don't build
    # a giant GameId IN (...) clause that could exceed Cargo's query limit.
    print(f"Fetching player rows for team '{name}'...")
    safe = name.replace("'", "''")
    players = api.scoreboard_players(where=f"SP.Team = '{safe}'")
    upsert_dataframe(players, "ScoreboardPlayers")


def refresh_leagues() -> None:
    upsert_dataframe(_client().leagues(), "Leagues")


def refresh_current_leagues() -> None:
    upsert_dataframe(_client().current_leagues(), "CurrentLeagues")


def ingest_oracleselixir(year: int, force: bool = False) -> None:
    oe.ingest_year(year, force=force)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Leaguepedia -> PostgreSQL ETL")
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("init-db", help="create tables/indexes")

    p_t = sub.add_parser("tournament", help="ingest a tournament by Name")
    p_t.add_argument("name")

    p_team = sub.add_parser("team", help="ingest a team's full game history")
    p_team.add_argument("name")

    sub.add_parser("leagues", help="refresh the Leagues table")
    sub.add_parser("current-leagues", help="refresh the CurrentLeagues table")

    p_oe = sub.add_parser("oe", help="load Oracle's Elixir match data for a year")
    p_oe.add_argument("year", type=int)
    p_oe.add_argument("--force", action="store_true", help="re-download even if cached")
    return parser


def main(argv: list[str] | None = None) -> None:
    args = build_parser().parse_args(argv)
    if args.command == "init-db":
        init_schema()
    elif args.command == "tournament":
        ingest_tournament(args.name)
    elif args.command == "team":
        ingest_team(args.name)
    elif args.command == "leagues":
        refresh_leagues()
    elif args.command == "current-leagues":
        refresh_current_leagues()
    elif args.command == "oe":
        ingest_oracleselixir(args.year, force=args.force)


if __name__ == "__main__":
    main()
