"""Load pandas DataFrames into PostgreSQL with idempotent upserts.

Re-running an ingest for the same tournament/team updates existing rows instead
of creating duplicates, thanks to ON CONFLICT on each table's natural key.
"""
from __future__ import annotations

import math

import pandas as pd
from psycopg2.extras import execute_values

from .connection import get_connection

# Natural keys defined in schema.sql, used as the ON CONFLICT target.
PRIMARY_KEYS = {
    "scoreboardgames": "gameid",
    "scoreboardplayers": "uniqueline",
    "tournaments": "overviewpage",
    "leagues": "league",
    "currentleagues": "overviewpage",
}


# Postgres types that accept an empty string as a legitimate value. For every
# other type (integer, real, date, boolean, ...) Cargo's empty-string "missing"
# marker must become NULL or the insert fails.
_TEXT_TYPES = {"text", "character varying", "character", "citext"}


def _clean(value, is_text: bool):
    """Normalise pandas/NumPy/Cargo values into something psycopg2 accepts."""
    if isinstance(value, list):
        return value  # maps to a Postgres array
    if value is None or value is pd.NaT:
        return None
    if isinstance(value, float) and math.isnan(value):
        return None
    # Cargo returns "" (sometimes whitespace) for missing values; only text
    # columns may keep it, everything else becomes NULL.
    if isinstance(value, str) and not is_text and value.strip() == "":
        return None
    return value


def _norm(name: str) -> str:
    """Normalise a Cargo field/alias to match a DB column.

    Cargo echoes field names with underscores turned into spaces (e.g.
    'StandardName_Redirect' comes back as 'StandardName Redirect'), so fold both.
    """
    return name.lower().replace(" ", "_")


def _actual_columns(cur, table: str) -> dict[str, tuple[str, str]]:
    """Map normalised name -> (actual column name, data_type) for a table.

    Needed because Cargo returns mixed-case field names (Event, OverviewPage)
    while unquoted DDL folds identifiers to lowercase; matching this way avoids
    "column does not exist" errors and lets us NULL empty values by type.
    """
    cur.execute(
        "SELECT column_name, data_type FROM information_schema.columns "
        "WHERE table_schema = 'public' AND lower(table_name) = lower(%s)",
        (table,),
    )
    return {_norm(row[0]): (row[0], row[1]) for row in cur.fetchall()}


def upsert_dataframe(df: pd.DataFrame, table: str) -> int:
    """Insert/update every row of ``df`` into ``table``. Returns row count.

    DataFrame columns are matched to the table's real columns case-insensitively;
    columns absent from the table are skipped. The conflict target is the table's
    natural key; all other columns are overwritten.
    """
    if df.empty:
        print(f"[{table}] nothing to load (empty frame).")
        return 0

    key = PRIMARY_KEYS.get(table.lower())
    if key is None:
        raise ValueError(f"No primary key registered for table '{table}'.")

    with get_connection() as conn, conn.cursor() as cur:
        actual = _actual_columns(cur, table)
        if not actual:
            raise ValueError(f"Table '{table}' not found in the database.")

        # Keep only DataFrame columns that exist in the table; remap to the
        # real (correctly-cased) column names.
        usable = [c for c in df.columns if _norm(c) in actual]
        skipped = [c for c in df.columns if _norm(c) not in actual]
        if skipped:
            print(f"[{table}] skipping columns not in table: {skipped}")
        df = df[usable].rename(columns={c: actual[_norm(c)][0] for c in usable})
        columns = list(df.columns)

        key_entry = actual.get(_norm(key))
        key_col = key_entry[0] if key_entry else None
        if key_col is None or key_col not in columns:
            raise ValueError(f"Key column '{key}' not present for '{table}'.")

        # Drop rows missing the key and de-duplicate within the batch (last wins),
        # since ON CONFLICT can't handle the same key twice in one statement.
        df = df.dropna(subset=[key_col]).drop_duplicates(subset=[key_col], keep="last")

        # Per-column flag: may this column keep an empty string, or must "" -> NULL?
        is_text = [actual[_norm(c)][1] in _TEXT_TYPES for c in columns]

        col_sql = ", ".join(f'"{c}"' for c in columns)
        update_cols = [c for c in columns if c != key_col]
        update_sql = ", ".join(f'"{c}" = EXCLUDED."{c}"' for c in update_cols)
        conflict = (
            f'ON CONFLICT ("{key_col}") DO UPDATE SET {update_sql}'
            if update_cols else f'ON CONFLICT ("{key_col}") DO NOTHING'
        )
        query = f'INSERT INTO {table} ({col_sql}) VALUES %s {conflict}'

        rows = [
            tuple(_clean(v, t) for v, t in zip(row, is_text))
            for row in df.itertuples(index=False, name=None)
        ]
        execute_values(cur, query, rows)
        conn.commit()

    print(f"[{table}] upserted {len(rows)} rows.")
    return len(rows)
