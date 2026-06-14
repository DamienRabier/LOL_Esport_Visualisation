"""Tournament catalog: a persisted list of all Leaguepedia tournaments used to
power the dashboard's autocomplete.

Stored in its own ``tournament_catalog`` table (replaced wholesale on refresh)
so the app gets instant autocomplete without re-hitting the API every load.
"""
from __future__ import annotations

import pandas as pd
from sqlalchemy import text
from sqlalchemy.engine import Engine

from src.api import LeaguepediaClient

CATALOG_TABLE = "tournament_catalog"
_COLUMNS = ["name", "year", "region", "league", "datestart", "overviewpage"]


def load_catalog(engine: Engine) -> pd.DataFrame:
    """Return the cached tournament catalog, or an empty frame if not built yet."""
    with engine.connect() as conn:
        if not conn.dialect.has_table(conn, CATALOG_TABLE):
            return pd.DataFrame(columns=_COLUMNS)
        return pd.read_sql(
            text(f"SELECT {', '.join(_COLUMNS)} FROM {CATALOG_TABLE} "
                 "ORDER BY datestart DESC NULLS LAST"),
            conn,
        )


def refresh_catalog(client: LeaguepediaClient, engine: Engine) -> int:
    """Fetch every tournament from Leaguepedia and (re)build the catalog table."""
    df = client.list_tournaments()
    keep = [c for c in ["Name", "Year", "Region", "League", "DateStart", "OverviewPage"]
            if c in df.columns]
    df = df[keep].copy()
    df.columns = [c.lower() for c in df.columns]
    df = df[df["name"].notna() & (df["name"] != "")]
    df = df.drop_duplicates(subset=["name"])  # most-recent kept (query is date-desc)
    df.to_sql(CATALOG_TABLE, engine, if_exists="replace", index=False, chunksize=5000)
    return len(df)
