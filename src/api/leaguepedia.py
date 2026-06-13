"""Thin, paginated wrapper around the Leaguepedia (Fandom) Cargo API.

The Cargo endpoint caps a single response at 500 rows. The old code ignored
this, so any query touching more than 500 rows silently lost data. ``query``
here loops over offsets until the table is exhausted, which matters a lot for
scouting (a team's full game history) and for pulling whole tournaments.

Reference: https://lol.fandom.com/wiki/Help:Cargo
"""
from __future__ import annotations

import logging
import time
from typing import Iterable, Sequence

import pandas as pd
from mwclient.errors import APIError
from mwrogue.auth_credentials import AuthCredentials
from mwrogue.esports_client import EsportsClient

from . import fields as F

logger = logging.getLogger(__name__)

# Cargo's hard per-request cap.
CARGO_PAGE_SIZE = 500

# Leaguepedia rate-limits even authenticated clients; back off and retry rather
# than crashing a long ingest mid-way.
RATELIMIT_RETRIES = 5
RATELIMIT_BACKOFF_SECONDS = 30
# Small courtesy pause between paged requests to stay under the limit.
INTER_PAGE_PAUSE_SECONDS = 1.0


class LeaguepediaClient:
    """High-level access to the Cargo tables we care about."""

    def __init__(self, username: str | None = None, password: str | None = None):
        # mwrogue handles anonymous read access out of the box; credentials are
        # only needed for higher rate limits. When supplied, they must be wrapped
        # in an AuthCredentials object (EsportsClient takes `credentials=`, not
        # raw username/password).
        if username and password:
            creds = AuthCredentials(username=username, password=password)
            self._site = EsportsClient("lol", credentials=creds)
        else:
            self._site = EsportsClient("lol")

    # ------------------------------------------------------------------ core
    def query(
        self,
        tables: str,
        fields: Sequence[str] | str,
        *,
        where: str | None = None,
        join_on: str | None = None,
        group_by: str | None = None,
        order_by: str | None = None,
        list_fields: Iterable[str] | None = None,
        limit: int | None = None,
    ) -> pd.DataFrame:
        """Run a Cargo query, paging through all results, return a DataFrame.

        ``fields`` may be a list of column names or a raw Cargo field string.
        ``list_fields`` names columns that should be split from comma strings
        into Python lists (e.g. bans/picks). Defaults to the known list columns.
        """
        field_str = fields if isinstance(fields, str) else ", ".join(fields)
        list_fields = set(list_fields) if list_fields is not None else F.LIST_FIELDS

        rows: list[dict] = []
        offset = 0
        while True:
            page_size = CARGO_PAGE_SIZE
            if limit is not None:
                remaining = limit - len(rows)
                if remaining <= 0:
                    break
                page_size = min(page_size, remaining)

            kwargs = dict(
                tables=tables,
                fields=field_str,
                limit=page_size,
                offset=offset,
            )
            if where:
                kwargs["where"] = where
            if join_on:
                kwargs["join_on"] = join_on
            if group_by:
                kwargs["group_by"] = group_by
            if order_by:
                kwargs["order_by"] = order_by

            page = self._cargo_query_with_retry(kwargs)
            if not page:
                break

            rows.extend(dict(r) for r in page)
            logger.debug("fetched %d rows (offset=%d) from %s", len(page), offset, tables)

            if len(page) < page_size:
                break
            offset += page_size
            time.sleep(INTER_PAGE_PAUSE_SECONDS)

        df = pd.DataFrame(rows)
        return self._split_list_columns(df, list_fields)

    def _cargo_query_with_retry(self, kwargs: dict) -> list:
        """Run one Cargo request, backing off and retrying on rate limits."""
        for attempt in range(1, RATELIMIT_RETRIES + 1):
            try:
                return self._site.cargo_client.query(**kwargs)
            except APIError as exc:
                if getattr(exc, "code", None) != "ratelimited" or attempt == RATELIMIT_RETRIES:
                    raise
                wait = RATELIMIT_BACKOFF_SECONDS * attempt
                logger.warning("rate-limited; waiting %ds (attempt %d/%d)",
                               wait, attempt, RATELIMIT_RETRIES)
                print(f"  [leaguepedia] rate-limited, waiting {wait}s "
                      f"(attempt {attempt}/{RATELIMIT_RETRIES})...")
                time.sleep(wait)
        return []  # unreachable

    @staticmethod
    def _split_list_columns(df: pd.DataFrame, list_fields: set[str]) -> pd.DataFrame:
        """Turn comma-joined Cargo strings into real lists for array columns."""
        for col in df.columns:
            # Cargo aliases may differ from the field name; match on suffix too.
            if col in list_fields or any(col.endswith(lf) for lf in list_fields):
                df[col] = df[col].apply(
                    lambda v: [s.strip() for s in v.split(",")] if isinstance(v, str) and v else []
                )
        return df

    # ------------------------------------------------------- convenience API
    def scoreboard_games(self, *, where: str | None = None, **kwargs) -> pd.DataFrame:
        return self.query("ScoreboardGames=SG", F.SCOREBOARD_GAMES, where=where,
                          order_by="SG.DateTime_UTC", **kwargs)

    def scoreboard_players(self, *, where: str | None = None, **kwargs) -> pd.DataFrame:
        return self.query("ScoreboardPlayers=SP", F.SCOREBOARD_PLAYERS, where=where,
                          order_by="SP.DateTime_UTC", **kwargs)

    def tournaments(self, *, where: str | None = None, **kwargs) -> pd.DataFrame:
        return self.query("Tournaments=T", F.TOURNAMENTS, where=where, **kwargs)

    def leagues(self, *, where: str | None = None, **kwargs) -> pd.DataFrame:
        return self.query("Leagues=L", F.LEAGUES, where=where, **kwargs)

    def current_leagues(self, **kwargs) -> pd.DataFrame:
        return self.query("CurrentLeagues=CL", F.CURRENT_LEAGUES, **kwargs)

    # ------------------------------------------------------ scouting helpers
    def overview_pages_for(self, tournament: str) -> list[str]:
        """Resolve a tournament Name (e.g. 'MSI 2025') to its OverviewPage(s).

        We resolve this separately rather than joining ScoreboardGames to
        Tournaments: Leaguepedia's Cargo backend throws a generic ``db_error``
        on that join, and querying games/players directly by OverviewPage is
        both reliable and faster.
        """
        safe = tournament.replace("'", "''")
        df = self.tournaments(where=f"T.Name = '{safe}'", limit=50)
        if df.empty or "OverviewPage" not in df:
            return []
        return [p for p in df["OverviewPage"].tolist() if p]

    @staticmethod
    def _in_clause(values: list[str]) -> str:
        escaped = ", ".join("'" + v.replace("'", "''") + "'" for v in values)
        return f"({escaped})"

    def games_for_tournament(self, tournament: str, **kwargs) -> pd.DataFrame:
        """All games of a tournament, by its Tournaments.Name (e.g. 'MSI 2025')."""
        pages = self.overview_pages_for(tournament)
        if not pages:
            return pd.DataFrame()
        return self.scoreboard_games(
            where=f"SG.OverviewPage IN {self._in_clause(pages)}", **kwargs
        )

    def players_for_tournament(self, tournament: str, **kwargs) -> pd.DataFrame:
        pages = self.overview_pages_for(tournament)
        if not pages:
            return pd.DataFrame()
        return self.scoreboard_players(
            where=f"SP.OverviewPage IN {self._in_clause(pages)}", **kwargs
        )

    def games_for_team(self, team: str, **kwargs) -> pd.DataFrame:
        """Every game a team played, either side. Core scouting query."""
        safe = team.replace("'", "''")
        return self.scoreboard_games(
            where=f"SG.Team1 = '{safe}' OR SG.Team2 = '{safe}'", **kwargs
        )

    def games_for_player(self, player_link: str, **kwargs) -> pd.DataFrame:
        """Every game a player appeared in, by their Leaguepedia Link/ID."""
        safe = player_link.replace("'", "''")
        return self.scoreboard_players(where=f"SP.Link = '{safe}'", **kwargs)
