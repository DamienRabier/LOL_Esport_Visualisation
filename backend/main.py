"""FastAPI backend for the LoL Esport dashboard.

Exposes the existing framework-agnostic query layer (``src/dashboard/queries``),
the tournament catalog, and the ETL ingestion as a JSON API consumed by the
React SPA in ``frontend/``. No business logic lives here — it's a thin, typed
HTTP wrapper around the same functions the old Streamlit app used.

Run (from the project root, venv active):
    uvicorn backend.main:app --reload --port 8000
"""
from __future__ import annotations

import math
import threading
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from typing import Any

import pandas as pd
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from config import LEAGUEPEDIA
from src import oracleselixir as oe
from src.api import LeaguepediaClient
from src.dashboard import catalog
from src.dashboard import oe_queries as oeq
from src.dashboard import queries as q
from src.db import get_engine, init_schema
from src.etl.run import ingest_tournament_steps
from src.etl.tracked import refresh_tracked


# ------------------------------------------------- auto-refresh (tracked leagues)
_refresh_lock = threading.Lock()
_refresh_state: dict = {
    "running": False,
    "started_at": None,
    "finished_at": None,
    "phase": None,         # human-readable current step
    "total": 0,
    "skipped": 0,          # finished + already-loaded tournaments not re-ingested
    "current": None,       # {"name", "index", "total"}
    "done": [],            # [{"name", "counts"}]
    "errors": [],
    "oe": None,            # Oracle's Elixir refresh result
}


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _run_refresh() -> None:
    """Body of the background refresh; only one runs at a time."""
    if not _refresh_lock.acquire(blocking=False):
        return  # already running
    try:
        _refresh_state.update(
            running=True, started_at=_now(), finished_at=None,
            phase="Loading Oracle's Elixir data…", total=0, skipped=0,
            current=None, done=[], errors=[], oe=None,
        )

        # Oracle's Elixir freshness (best effort; won't block Leaguepedia refresh).
        try:
            _refresh_state["oe"] = oe.refresh_oe()
        except Exception as exc:  # pragma: no cover - defensive
            _refresh_state["oe"] = {"error": str(exc)}

        _refresh_state["phase"] = "Refreshing tournament list…"

        def on_event(ev: dict) -> None:
            stage = ev.get("stage")
            if stage == "plan":
                _refresh_state["total"] = ev.get("total", 0)
                _refresh_state["skipped"] = ev.get("skipped", 0)
                _refresh_state["phase"] = "Ingesting tournaments"
            elif stage == "catalog" and not ev.get("ok"):
                _refresh_state["errors"].append(f"catalog: {ev.get('error')}")
            elif stage == "tournament_start":
                _refresh_state["current"] = {
                    "name": ev.get("name"), "index": ev.get("index"), "total": ev.get("total"),
                }
            elif stage == "tournament":
                if "error" in ev:
                    _refresh_state["errors"].append(f'{ev["name"]}: {ev["error"]}')
                else:
                    _refresh_state["done"].append({"name": ev["name"], "counts": ev.get("counts")})

        refresh_tracked(engine=_engine, on_event=on_event)
    except Exception as exc:  # pragma: no cover - defensive
        _refresh_state["errors"].append(str(exc))
    finally:
        _refresh_state.update(running=False, finished_at=_now(), current=None, phase=None)
        _refresh_lock.release()


def start_refresh_async() -> bool:
    """Kick off a refresh in a daemon thread. Returns False if already running."""
    if _refresh_state["running"]:
        return False
    threading.Thread(target=_run_refresh, daemon=True).start()
    return True


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Make sure tables exist so a fresh DB doesn't 500 on first query.
    init_schema()
    # Always refresh tracked leagues on launch, in the background so the API
    # stays responsive immediately while data updates.
    start_refresh_async()
    yield


app = FastAPI(title="LoL Esport API", version="1.0.0", lifespan=lifespan)

# Dev CORS: the Vite dev server (5173) calls the API (8000) cross-origin.
# In production the SPA is served same-origin, so this is harmless.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

# One engine for the process (SQLAlchemy pools connections internally).
_engine = get_engine()


# --------------------------------------------------------------- serialization
def _clean(value: Any) -> Any:
    """Make a single value JSON-safe (NaN/NaT -> None, numpy -> native)."""
    if value is None or value is pd.NaT or value is pd.NA:
        return None
    if isinstance(value, float) and math.isnan(value):
        return None
    if isinstance(value, (list, tuple)):
        return [_clean(v) for v in value]
    if hasattr(value, "item"):  # numpy scalar
        try:
            return value.item()
        except Exception:  # pragma: no cover - defensive
            return value
    if isinstance(value, pd.Timestamp):
        return value.isoformat()
    return value


def _records(df: pd.DataFrame) -> list[dict]:
    """DataFrame -> list of JSON-safe row dicts."""
    return [{k: _clean(v) for k, v in row.items()} for row in df.to_dict("records")]


def _row(d: dict) -> dict:
    """Single result dict -> JSON-safe."""
    return {k: _clean(v) for k, v in d.items()}


# ------------------------------------------------------------------- meta
@app.get("/api/health")
def health() -> dict:
    return {"status": "ok"}


# ------------------------------------------------------------------ filters
@app.get("/api/tournaments")
def tournaments() -> list[dict]:
    return _records(q.tournaments(_engine))


@app.get("/api/teams")
def teams(op: str | None = None) -> list[str]:
    return q.teams(_engine, op)


@app.get("/api/teams-leaderboard")
def teams_leaderboard(op: str | None = None, year: str | None = None) -> list[dict]:
    df = q.teams_leaderboard(_engine, op)
    if year:
        try:
            df = oeq.attach_team_gd15(_engine, df, year)
        except Exception:
            pass
    return _records(df)


@app.get("/api/players")
def players(op: str | None = None, team: str | None = None) -> list[str]:
    return q.players(_engine, op, team)


@app.get("/api/players-leaderboard")
def players_leaderboard(op: str | None = None) -> list[dict]:
    df = q.players_leaderboard(_engine, op)
    try:
        df = oeq.attach_players_gd15(_engine, df, op)
    except Exception:
        pass
    return _records(df)


# ------------------------------------------------------------------ overview
@app.get("/api/overview")
def overview(op: str | None = None, year: str | None = None) -> dict:
    picks = q.top_picks(_engine, op)
    if year:
        try:
            picks = oeq.attach_champion_gd15(_engine, picks, year)
        except Exception:
            pass
    try:
        top_gd15 = _records(oeq.top_players_gd15(_engine, op))
    except Exception:
        top_gd15 = []
    return {
        "kpis": _row(q.overview_kpis(_engine, op)),
        "top_picks": _records(picks),
        "top_bans": _records(q.top_bans(_engine, op)),
        "top_kda": _records(q.top_players_kda(_engine, op)),
        "top_dpm": _records(q.top_players_dpm(_engine, op)),
        "top_gd15": top_gd15,
    }


# ------------------------------------------------------------- game by game
@app.get("/api/games")
def games(op: str | None = None) -> list[dict]:
    return _records(q.games_list(_engine, op))


@app.get("/api/game")
def game(gameid: str = Query(...)) -> dict:
    # gameid contains slashes (e.g. "LCK/2026 Season/..."), so it's a query
    # param rather than a path segment.
    detail = q.game_detail(_engine, gameid)
    if not detail:
        raise HTTPException(status_code=404, detail="Game not found")
    players = q.game_players(_engine, gameid)
    # Best-effort overlay of OE early-game diffs (matched by player+champion+date).
    try:
        date_str = str(detail.get("datetime_utc"))[:10]
        players = oeq.attach_game_earlygame(_engine, players, date_str,
                                            detail.get("team1"), detail.get("team2"))
    except Exception:
        pass
    return {"detail": _row(detail), "players": _records(players)}


# ----------------------------------------------------------- team scouting
@app.get("/api/team")
def team(name: str = Query(...), op: str | None = None, year: str | None = None) -> dict:
    pool = q.team_champion_pool(_engine, name, op)
    games = q.team_games(_engine, name, op)
    if year:
        try:
            pool = oeq.attach_champion_gd15(_engine, pool, year)
            games = oeq.attach_team_games(_engine, games, name, year)
        except Exception:
            pass
    return {
        "record": _row(q.team_record(_engine, name, op)),
        "objectives": _row(q.team_objectives(_engine, name, op)),
        "champion_pool": _records(pool),
        "bans": _records(q.team_bans(_engine, name, op)),
        "games": _records(games),
    }


# ----------------------------------------------------------------- player
@app.get("/api/player")
def player(name: str = Query(...), op: str | None = None, year: str | None = None) -> dict:
    games = q.player_games(_engine, name, op)
    if year:  # overlay OE early-game diffs per game (best effort)
        try:
            games = oeq.attach_player_games(_engine, games, name, year)
        except Exception:
            pass
    return {
        "summary": _row(q.player_summary(_engine, name, op)),
        "champions": _records(q.player_champions(_engine, name, op)),
        "games": _records(games),
    }


# ------------------------------------------------------------------- draft
@app.get("/api/draft")
def draft(op: str | None = None, year: str | None = None) -> dict:
    picks = q.top_picks(_engine, op)
    if year:
        try:
            picks = oeq.attach_champion_gd15(_engine, picks, year)
        except Exception:
            pass
    return {
        "picks": _records(picks),
        "bans": _records(q.top_bans(_engine, op)),
    }


# --------------------------------------------------------------- ingestion
@app.get("/api/catalog")
def get_catalog() -> list[dict]:
    return _records(catalog.load_catalog(_engine))


@app.post("/api/catalog/refresh")
def refresh_catalog(scope: str = Query("recent", pattern="^(recent|full)$")) -> dict:
    """Rebuild the tournament autocomplete catalog. ``scope=recent`` is fast."""
    client = LeaguepediaClient(LEAGUEPEDIA.username, LEAGUEPEDIA.password)
    kwargs: dict = {}
    if scope == "recent":
        from datetime import date
        kwargs["where"] = f"T.Year >= {date.today().year - 2}"
    try:
        n = catalog.refresh_catalog(client, _engine, **kwargs)
    except Exception as exc:  # rate limits etc. surfaced to the client
        raise HTTPException(status_code=502, detail=str(exc))
    return {"count": n}


# --------------------------------------------------------------- early game (OE)
_oe_lock = threading.Lock()
_oe_state: dict = {"running": False, "started_at": None, "finished_at": None, "result": None}


def _run_oe_refresh() -> None:
    if not _oe_lock.acquire(blocking=False):
        return
    try:
        _oe_state.update(running=True, started_at=_now(), finished_at=None, result=None)
        _oe_state["result"] = oe.refresh_oe(fresh_hours=0)  # always try a fresh download
    except Exception as exc:  # pragma: no cover - defensive
        _oe_state["result"] = {"error": str(exc)}
    finally:
        _oe_state.update(running=False, finished_at=_now())
        _oe_lock.release()


@app.post("/api/oe/refresh")
def oe_refresh() -> dict:
    if _oe_state["running"]:
        return {"started": False, "running": True}
    threading.Thread(target=_run_oe_refresh, daemon=True).start()
    return {"started": True, "running": True}


@app.get("/api/oe/refresh/status")
def oe_refresh_status() -> dict:
    return _oe_state


@app.get("/api/oe/team-profile")
def oe_team_profile(team: str = Query(...), year: str = Query(...)) -> list[dict]:
    return _records(oeq.oe_team_profile(_engine, team, year))


@app.get("/api/oe/player-profile")
def oe_player_profile(player: str = Query(...), year: str = Query(...)) -> dict:
    return _row(oeq.oe_player_profile(_engine, player, year))


@app.get("/api/refresh/status")
def refresh_status() -> dict:
    return _refresh_state


@app.post("/api/refresh")
def trigger_refresh() -> dict:
    started = start_refresh_async()
    return {"started": started, "running": _refresh_state["running"]}


@app.post("/api/ingest")
def ingest(name: str = Query(...)) -> JSONResponse:
    """Ingest a tournament by exact Leaguepedia name; returns per-step counts."""
    steps: list[dict] = []
    try:
        for label, rows in ingest_tournament_steps(name):
            steps.append({"label": label, "rows": rows})
            if label == "Tournament metadata" and rows == 0:
                return JSONResponse(
                    status_code=404,
                    content={"ok": False, "steps": steps,
                             "error": f'No tournament named "{name}" found.'},
                )
    except Exception as exc:
        raise HTTPException(status_code=502, detail=str(exc))
    return JSONResponse(content={"ok": True, "steps": steps})
