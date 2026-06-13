# LoL Esport — Data Pipeline for Debrief & Scouting

Pulls League of Legends esports data from the [Leaguepedia](https://lol.fandom.com)
Cargo API, stores it in PostgreSQL, and provides a foundation for **post-game
debriefs** and **opponent scouting**.

```
Leaguepedia Cargo API  ──►  pandas  ──►  PostgreSQL  ──►  analysis / viz (later)
        (src/api)                          (src/db)
                     orchestrated by src/etl/run.py
```

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
| `notebooks/` | Analysis / visualization notebooks (debrief, scouting). |

## What's different from the old version

- **Pagination** — Cargo caps responses at 500 rows; the client now pages
  through everything (essential for a team's full history).
- **Parametrized** — query any tournament, team, or player instead of
  hardcoded `LEC 2025 Spring`.
- **No hardcoded credentials** — everything comes from `.env`.
- **Idempotent loads** — natural keys + `ON CONFLICT` upserts.
- **DRY** — field definitions live in one place.

## Setup

This repo was set up on a machine with **Python 3.12** (installed to
`%LOCALAPPDATA%\Programs\Python\Python312`) and **PostgreSQL 14** (service
`postgresql-x64-14`, listening on `localhost:5432`). The virtualenv lives in
`.venv`. To reproduce from scratch elsewhere:

```powershell
# 1. Dependencies
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt

# 2. Configure
copy .env.example .env   # then edit .env: set PGPASSWORD to your postgres password

# 3. Create the database (once), then the tables.
#    psql/createdb ship with PostgreSQL but may not be on PATH; full path:
& "C:\Program Files\PostgreSQL\14\bin\createdb.exe" -U postgres lol_esport
python -m src.etl.run init-db
```

> **Note on JupyterLab:** the `jupyter` mega-package is intentionally left out of
> `requirements.txt` because its bundled files overflow Windows' 260-char path
> limit. `ipykernel` (included) is enough to run notebooks inside VS Code. For
> classic JupyterLab, enable long paths in an **elevated** PowerShell, then
> `pip install jupyterlab`:
> ```powershell
> Set-ItemProperty -Path "HKLM:\SYSTEM\CurrentControlSet\Control\FileSystem" `
>   -Name LongPathsEnabled -Value 1 -Type DWord
> ```

## Usage

```powershell
# Ingest a tournament (metadata + games + players)
python -m src.etl.run tournament "MSI 2025"

# Ingest a team's entire game history (scouting)
python -m src.etl.run team "G2 Esports"

# Refresh reference tables
python -m src.etl.run leagues
python -m src.etl.run current-leagues

# Oracle's Elixir advanced stats for a year (gold/xp/cs diffs at 10/15/20/25, etc.)
python -m src.etl.run oe 2026
```

### Oracle's Elixir notes

OE publishes one CSV per year in a public Google Drive folder, refreshed daily.
The loader downloads + caches it under `data/oracleselixir/` and loads it into
the `oe_match_data` table (schema mirrors the CSV; reloading a year replaces its
rows). Google Drive enforces a per-file "too many downloads recently" quota, so
a download can transiently fail — just retry later, or download the file
manually from the folder and drop it in `data/oracleselixir/`.

### Using the client directly (e.g. in a notebook)

```python
from src.api import LeaguepediaClient

api = LeaguepediaClient()
games   = api.games_for_team("T1")              # full history, all pages
players = api.players_for_tournament("MSI 2025")
champs  = players.groupby("Champion").size().sort_values(ascending=False)
```

## Roadmap

- [ ] Analysis layer (`src/analysis/`): champion pools, draft tendencies,
      side win-rates, objective control — for debrief & scouting.
- [ ] Visualization notebooks / dashboard.
