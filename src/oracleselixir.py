"""Oracle's Elixir loader: download the yearly match-data CSV and load it to Postgres.

Oracle's Elixir (https://oracleselixir.com) publishes one CSV per year of
analyst-grade LoL esports stats — crucially the lane-diff metrics
(gold/xp/cs diff at 10/15/20/25, etc.) that Leaguepedia does not expose. These
complement the Leaguepedia data for debrief and scouting.

Hosting reality (verified 2026-06): the files live ONLY in a public Google
Drive folder, named ``{year}_LoL_esports_match_data_from_OraclesElixir.csv`` and
refreshed daily. Drive enforces a per-file "too many downloads recently" quota,
so downloads can transiently fail — this module surfaces that clearly and
caches files locally so you only download once per refresh.

Design choices that keep this robust to OE changing its schema:
  * We never hardcode the ~160 column names. The Postgres table is created from
    whatever columns the CSV actually has (via pandas ``to_sql``).
  * Loading is idempotent per year: we DELETE that year's rows then re-insert,
    matching OE's "one full file per year, replaced daily" model.
"""
from __future__ import annotations

from pathlib import Path

import gdown
import pandas as pd
from sqlalchemy import text

from src.db import get_engine

FOLDER_URL = "https://drive.google.com/drive/folders/1gLSw0RLjBbtaNy0dgnGQDAZOHIgCe-HH"
DATA_DIR = Path(__file__).resolve().parent.parent / "data" / "oracleselixir"
OE_TABLE = "oe_match_data"

# Stable per-file Drive IDs (captured 2026-06). Used as a fast path so we don't
# scrape the folder every time; if an ID goes stale we fall back to resolving
# the folder listing by filename.
KNOWN_FILE_IDS = {
    2018: "1GsNetJQOMx0QJ6_FN8M1kwGvU_GPPcPZ",
    2019: "11eKtScnZcpfZcD3w3UrD7nnpfLHvj9_t",
    2020: "1dlSIczXShnv1vIfGNvBjgk-thMKA5j7d",
    2021: "1fzwTTz77hcnYjOnO9ONeoPrkWCoOSecA",
    2022: "1EHmptHyzY8owv0BAcNKtkQpMwfkURwRy",
    2023: "1XXk2LO0CsNADBB1LRGOV5rUpyZdEZ8s2",
    2024: "1IjIEhLc9n8eLKeY-yh_YigKVWbhgGBsN",
    2025: "1v6LRphp2kYciU4SXp0PCjEMuev1bDejc",
    2026: "1hnpbrUpBMS1TZI7IovfpKeZfWJH1Aptm",
}


def _filename(year: int) -> str:
    return f"{year}_LoL_esports_match_data_from_OraclesElixir.csv"


def _resolve_file_id(year: int) -> str | None:
    """Look up the Drive file id for a year by scraping the folder listing."""
    files = gdown.download_folder(url=FOLDER_URL, skip_download=True, quiet=True)
    wanted = _filename(year)
    for f in files:
        if Path(f.path).name == wanted:
            return f.id
    return None


def download_year(year: int, *, force: bool = False, use_cookies: bool = True) -> Path:
    """Download a year's CSV to ``data/oracleselixir/`` and return its path.

    Cached: skips download if the file already exists unless ``force=True``.
    Raises a clear error if Google Drive's download quota is hit.
    """
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    out = DATA_DIR / _filename(year)
    if out.exists() and not force:
        print(f"[oe] using cached {out.name} ({out.stat().st_size / 1e6:.1f} MB)")
        return out

    file_id = KNOWN_FILE_IDS.get(year) or _resolve_file_id(year)
    if not file_id:
        raise ValueError(f"No Oracle's Elixir file found for {year}.")

    try:
        gdown.download(id=file_id, output=str(out), quiet=False, use_cookies=use_cookies)
    except gdown.exceptions.FileURLRetrievalError as exc:
        raise RuntimeError(
            f"Google Drive blocked the {year} download (per-file quota). This is "
            f"transient - retry in a while, or download it manually from\n  {FOLDER_URL}\n"
            f"and save it as {out}. Original error: {str(exc).splitlines()[0]}"
        ) from exc

    if not out.exists() or out.stat().st_size == 0:
        raise RuntimeError(f"Download produced no data for {year} (quota or network).")
    print(f"[oe] downloaded {out.name} ({out.stat().st_size / 1e6:.1f} MB)")
    return out


def load_csv(path: str | Path) -> pd.DataFrame:
    """Read an Oracle's Elixir CSV into a DataFrame."""
    return pd.read_csv(path, low_memory=False)


def to_postgres(df: pd.DataFrame, year: int, *, chunksize: int = 5000) -> int:
    """Idempotently load one year's rows into ``oe_match_data``.

    Creates the table from the CSV's own columns on first run, then replaces
    that year's rows (DELETE + INSERT) so daily refreshes stay clean.
    """
    if df.empty:
        print(f"[oe] {year}: empty frame, nothing to load.")
        return 0

    engine = get_engine()
    with engine.begin() as conn:
        table_exists = conn.dialect.has_table(conn, OE_TABLE)
        if table_exists:
            conn.execute(text(f"DELETE FROM {OE_TABLE} WHERE year = :y"), {"y": year})

    # Append (creates the table from df dtypes if it doesn't exist yet).
    df.to_sql(OE_TABLE, engine, if_exists="append", index=False, chunksize=chunksize, method="multi")
    print(f"[oe] {year}: loaded {len(df)} rows into {OE_TABLE}.")
    return len(df)


def ingest_year(year: int, *, force: bool = False) -> int:
    """Convenience: download (if needed) + load a year into Postgres."""
    path = download_year(year, force=force)
    return to_postgres(load_csv(path), year)
