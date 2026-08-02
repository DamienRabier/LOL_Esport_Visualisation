# 🎮 LoL Esport — Debrief & Scouting

Pull League of Legends esports data from the [Leaguepedia](https://lol.fandom.com)
Cargo API, store it in PostgreSQL, and explore it in an interactive Streamlit
dashboard built for **post-game debriefs** and **opponent scouting**.

```
Leaguepedia Cargo API ─► pandas ─► PostgreSQL ─► FastAPI  ─►  React SPA
       (src/api)                     (src/db)   (backend/)    (frontend/)
                    orchestrated by src/etl/run.py
```

The app is a **React single-page app** (Vite + Recharts) talking to a **FastAPI**
backend that wraps the shared Python query layer. A legacy Streamlit version
(`app.py`) is kept during the migration.

**Contents:** [Features](#features) · [Quick start](#quick-start) ·
[First-time setup](#first-time-setup) · [Loading data](#loading-data) ·
[Project layout](#project-layout) · [Notes](#notes) · [Roadmap](#roadmap)

---

## Features

- **📊 Overview** — tournament KPIs, most-picked and most-banned champions.
- **🎮 Games** — pick any game for its full player scoreboard, team objectives,
  bans and picks.
- **🛡️ Team scouting** — record, side win-rates, objective control, champion
  pool and bans.
- **🧍 Player** — KDA, win rate, champion pool and game log.
- **🚫 Draft** — pick / ban tables.
- **➕ In-app ingestion** — load tournaments straight from the sidebar, no
  command line required (works even on an empty database).
- **Win/loss & ban-rate bars** — champion charts show a green/red win-loss split
  and a ban-rate bar, with percentages written on each segment.
- **Idempotent loads** — natural keys + `ON CONFLICT` upserts, so re-ingesting a
  tournament updates rows instead of duplicating them.

---

## Quick start

The app has **two processes** — the API and the web frontend. Run each in its
own terminal from the project root.

**1. Backend (FastAPI)** — must be in a **PowerShell** prompt:

```powershell
.\.venv\Scripts\Activate.ps1
uvicorn backend.main:app --reload --port 8000
```

**2. Frontend (React)** — first time, install deps; then start the dev server:

```powershell
cd frontend
npm install        # first time only
npm run dev        # opens http://localhost:5173
```

Open **http://localhost:5173**. The Vite dev server proxies `/api` to the
backend on :8000.

- If the database is **empty**, the app opens on a welcome screen with the
  **➕ Add data** panel — load a tournament to unlock the other views.
- Otherwise, pick a tournament in the **sidebar** and browse Overview, Games,
  Team scouting, Player and Draft.

> **Note (PowerShell):** if `Activate.ps1` is blocked by an execution-policy
> error, run once: `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned`. And
> `npm` requires **Node.js** on your PATH — open a fresh terminal after
> installing it.

<details>
<summary>Legacy Streamlit dashboard</summary>

The original single-file dashboard still works:

```powershell
.\.venv\Scripts\Activate.ps1
streamlit run app.py     # opens http://localhost:8501
```
</details>

---

## First-time setup

This repo was set up with **Python 3.12** (installed to
`%LOCALAPPDATA%\Programs\Python\Python312`), **PostgreSQL 16** (service
`postgresql-16`, listening on `localhost:5432`), and **Node.js LTS** (for the
React frontend). The virtualenv lives in `.venv`. To reproduce from scratch:

**1. Install dependencies**

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

**2. Configure the connection**

```powershell
copy .env.example .env   # then edit .env and set PGPASSWORD to your postgres password
```

**3. Create the database and tables**

`createdb` / `psql` ship with PostgreSQL but may not be on `PATH`, so the full
path is shown below.

```powershell
& "C:\Program Files\PostgreSQL\16\bin\createdb.exe" -U postgres lol_esport
python -m src.etl.run init-db
```

**4. Install frontend dependencies**

```powershell
cd frontend
npm install
cd ..
```

You're ready — jump to [Quick start](#quick-start) to launch the app.

> **Note (JupyterLab):** the `jupyter` mega-package is intentionally left out of
> `requirements.txt` because its bundled files overflow Windows' 260-char path
> limit. `ipykernel` (included) is enough to run notebooks inside VS Code. For
> classic JupyterLab, enable long paths in an **elevated** PowerShell, then
> `pip install jupyterlab`:
> ```powershell
> Set-ItemProperty -Path "HKLM:\SYSTEM\CurrentControlSet\Control\FileSystem" `
>   -Name LongPathsEnabled -Value 1 -Type DWord
> ```

---

## Loading data

### From the dashboard (recommended)

Open the **➕ Add data** page from the sidebar button. You can:

- **⚡ Load recent** — fetch the last few years of tournaments in one request,
  then filter by region / year and search for the one you want.
- **Type the name manually** — enter the exact Leaguepedia name (e.g.
  `MSI 2026`) for very new tournaments.

This is the primary path and works even when the database is empty.

> **Note:** anonymous access to Leaguepedia is rate-limited. To avoid throttling,
> add bot credentials to `.env` (`LEAGUEPEDIA_USERNAME` / `LEAGUEPEDIA_PASSWORD`).
> Create a bot password at
> [Special:BotPasswords](https://lol.fandom.com/wiki/Special:BotPasswords);
> the username must look like `YourFandomName@botlabel`.

### From the command line (advanced)

```powershell
# Ingest a tournament (metadata + games + players)
python -m src.etl.run tournament "MSI 2026"

# Ingest a team's entire game history (scouting)
python -m src.etl.run team "G2 Esports"

# Refresh reference tables
python -m src.etl.run leagues
python -m src.etl.run current-leagues

# Oracle's Elixir advanced stats for a year (gold/xp/cs diffs at 10/15/20/25, etc.)
python -m src.etl.run oe 2026
```

### Using the client directly (e.g. in a notebook)

```python
from src.api import LeaguepediaClient

api = LeaguepediaClient()
games   = api.games_for_team("T1")              # full history, all pages
players = api.players_for_tournament("MSI 2026")
champs  = players.groupby("Champion").size().sort_values(ascending=False)
```

---

## Project layout

| Path | Purpose |
|------|---------|
| `config.py` | Loads settings from `.env` (DB credentials, optional Leaguepedia login). |
| `src/api/leaguepedia.py` | Paginated, parametrized Cargo client. |
| `src/api/fields.py` | Cargo field lists, declared once. |
| `src/db/schema.sql` | PostgreSQL schema with natural keys + indexes. |
| `src/db/connection.py` | Connections + schema bootstrap. |
| `src/db/loader.py` | Idempotent upserts (re-running won't duplicate rows). |
| `src/oracleselixir.py` | Oracle's Elixir loader (advanced lane-diff stats). |
| `src/etl/run.py` | CLI: fetch a tournament/team and load it to the DB. |
| `src/dashboard/` | Shared query layer + tournament catalog (used by API & Streamlit). |
| `backend/main.py` | FastAPI app exposing the query layer + ingestion as JSON. |
| `frontend/` | React + Vite + Recharts single-page app (the main UI). |
| `app.py` | Legacy Streamlit dashboard (kept during migration). |
| `notebooks/` | Analysis / visualization notebooks (debrief, scouting). |

---

## Notes

**Filtering key.** The dashboard filters on `overviewpage` (the Leaguepedia page
id), not the `tournament` display column: Cargo leaves
`ScoreboardPlayers.tournament` empty, but both tables carry a populated
`overviewpage`. The UI maps the friendly tournament name to its `overviewpage`.

**Oracle's Elixir.** OE publishes one CSV per year in a public Google Drive
folder, refreshed daily. The loader downloads + caches it under
`data/oracleselixir/` and loads it into the `oe_match_data` table (reloading a
year replaces its rows). Google Drive enforces a per-file download quota, so a
download can transiently fail — retry later, or download the file manually from
the folder and drop it in `data/oracleselixir/`.

---

## Roadmap

- [ ] Analysis layer (`src/analysis/`): champion pools, draft tendencies,
      side win-rates, objective control — for debrief & scouting.
- [ ] More visualization notebooks.
