"""Auto-refresh of the leagues/events the user always wants kept up to date.

Tracked series (matched by Leaguepedia's ``League`` field, which is stable):
  LCK, LEC, LCS + LTA North/South, First Stand, MSI, Esports World Cup, Worlds.

``refresh_tracked`` refreshes the recent tournament catalog (so new splits are
discoverable), resolves the current-year editions of each tracked league, and
ingests each one via the shared idempotent ETL path.
"""
from __future__ import annotations

from datetime import date, datetime, timedelta
from typing import Callable

import pandas as pd
from sqlalchemy import bindparam, text
from sqlalchemy.engine import Engine

from config import LEAGUEPEDIA
from src.api import LeaguepediaClient
from src.dashboard import catalog
from src.db import get_engine
from src.etl.run import ingest_tournament_steps

# A finished tournament is re-ingested no more; grace days guard against
# last-day result corrections landing after the scheduled end date.
FINISHED_GRACE_DAYS = 2

# League names exactly as they appear in Tournaments.League / the catalog.
TRACKED_LEAGUES = [
    "LoL Champions Korea",                                    # LCK
    "LoL EMEA Championship",                                  # LEC
    "League of Legends Championship Series",                  # LCS (North America)
    "League of Legends Championship of The Americas",         # LTA (combined)
    "League of Legends Championship of The Americas North",   # LTA North
    "League of Legends Championship of The Americas South",   # LTA South
    "LCK Challengers League",                                 # LCK CL (Challengers)
    "First Stand",                                            # First Stand
    "Mid-Season Invitational",                               # MSI
    "Esports World Cup",                                      # EWC (main event only)
    "World Championship",                                     # Worlds
]

EventCB = Callable[[dict], None]


def tracked_tournaments(engine: Engine, year: int) -> pd.DataFrame:
    """(name, overviewpage) of the tracked leagues' tournaments for ``year``.

    Empty frame if the catalog isn't built yet. Excludes the EWC regional
    qualifiers (we only want the main international event).
    """
    df = catalog.load_catalog(engine)
    if df.empty:
        return pd.DataFrame(columns=["name", "overviewpage"])
    df = df[(df["year"].astype(str) == str(year)) & (df["league"].isin(TRACKED_LEAGUES))]
    is_ewc_qualifier = (df["league"] == "Esports World Cup") & df["name"].str.contains(
        "qualifier", case=False, na=False
    )
    df = df[~is_ewc_qualifier]
    return df[["name", "overviewpage"]].dropna(subset=["name", "overviewpage"])


def _as_date(v) -> date | None:
    if v is None:
        return None
    if isinstance(v, datetime):
        return v.date()
    if isinstance(v, date):
        return v
    try:
        return datetime.fromisoformat(str(v)[:10]).date()
    except ValueError:
        return None


def _db_status(engine: Engine, overviewpages: list[str]) -> tuple[dict, dict]:
    """Return {overviewpage: end_date} and {overviewpage: game_count}."""
    if not overviewpages:
        return {}, {}
    ends: dict = {}
    counts: dict = {}
    with engine.connect() as conn:
        q_end = text('SELECT overviewpage, "Date" AS enddate FROM tournaments '
                     "WHERE overviewpage IN :ops").bindparams(bindparam("ops", expanding=True))
        for r in conn.execute(q_end, {"ops": overviewpages}).mappings():
            ends[r["overviewpage"]] = r["enddate"]
        q_cnt = text("SELECT overviewpage, count(*) AS n FROM scoreboardgames "
                     "WHERE overviewpage IN :ops GROUP BY overviewpage").bindparams(
            bindparam("ops", expanding=True))
        for r in conn.execute(q_cnt, {"ops": overviewpages}).mappings():
            counts[r["overviewpage"]] = r["n"]
    return ends, counts


def refresh_tracked(
    *,
    years: list[int] | None = None,
    engine: Engine | None = None,
    on_event: EventCB | None = None,
) -> dict:
    """Refresh the catalog then ingest every tracked tournament for ``years``.

    ``on_event`` receives dicts describing progress so a UI can show live status:
      {"stage": "catalog", "ok": bool}
      {"stage": "plan", "total": int, "names": [...]}
      {"stage": "tournament", "name": str, "index": int, "total": int,
       "counts": {...}}  (or "error": str)
    """
    engine = engine or get_engine()
    years = years or [date.today().year]
    client = LeaguepediaClient(LEAGUEPEDIA.username, LEAGUEPEDIA.password)

    def emit(**kw):
        if on_event:
            on_event(kw)

    summary: dict = {"tournaments": [], "errors": [], "skipped": []}

    # 1) Refresh the recent catalog so newly-created splits are discoverable.
    try:
        cutoff = date.today().year - 2
        catalog.refresh_catalog(client, engine, where=f"T.Year >= {cutoff}")
        emit(stage="catalog", ok=True)
    except Exception as exc:  # rate limit etc. — keep going with the cached catalog
        summary["errors"].append(f"catalog: {exc}")
        emit(stage="catalog", ok=False, error=str(exc))

    # 2) Resolve tracked tournaments (dedup by overviewpage).
    frames = [tracked_tournaments(engine, y) for y in years]
    tdf = (pd.concat(frames, ignore_index=True) if frames else pd.DataFrame(columns=["name", "overviewpage"]))
    tdf = tdf.drop_duplicates(subset=["overviewpage"])

    # 3) Skip tournaments that already ended AND are already loaded — their data
    #    won't change, so there's no point re-ingesting them every launch.
    ends, counts = _db_status(engine, tdf["overviewpage"].tolist())
    cutoff = date.today() - timedelta(days=FINISHED_GRACE_DAYS)
    to_ingest: list[str] = []
    for _, row in tdf.iterrows():
        op, name = row["overviewpage"], row["name"]
        loaded = counts.get(op, 0) > 0
        end = _as_date(ends.get(op))
        finished = end is not None and end < cutoff
        if loaded and finished:
            summary["skipped"].append(name)
        else:
            to_ingest.append(name)

    summary["skipped_count"] = len(summary["skipped"])
    emit(stage="plan", total=len(to_ingest), names=to_ingest, skipped=len(summary["skipped"]))

    # 4) Ingest the rest (idempotent upserts).
    for i, name in enumerate(to_ingest, 1):
        try:
            counts_i: dict[str, int] = {}
            for label, rows in ingest_tournament_steps(name, client=client):
                counts_i[label] = rows
            summary["tournaments"].append({"name": name, "counts": counts_i})
            emit(stage="tournament", name=name, index=i, total=len(to_ingest), counts=counts_i)
        except Exception as exc:
            summary["errors"].append(f"{name}: {exc}")
            emit(stage="tournament", name=name, index=i, total=len(to_ingest), error=str(exc))

    return summary
