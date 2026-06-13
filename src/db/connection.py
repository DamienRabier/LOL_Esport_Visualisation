"""Database connection helpers and schema bootstrap.

Credentials come from config.DB (loaded from .env) — never hardcoded.
"""
from __future__ import annotations

from pathlib import Path

import psycopg2
from sqlalchemy import create_engine
from sqlalchemy.engine import Engine

from config import DB

SCHEMA_PATH = Path(__file__).with_name("schema.sql")


def get_connection() -> "psycopg2.extensions.connection":
    """Raw psycopg2 connection (used by the loader for fast upserts)."""
    return psycopg2.connect(**DB.psycopg2_kwargs())


def get_engine() -> Engine:
    """SQLAlchemy engine (handy for pandas read_sql in analysis)."""
    return create_engine(DB.sqlalchemy_url)


def init_schema() -> None:
    """Create all tables/indexes from schema.sql if they don't exist."""
    sql = SCHEMA_PATH.read_text(encoding="utf-8")
    with get_connection() as conn, conn.cursor() as cur:
        cur.execute(sql)
        conn.commit()
    print("Schema initialised (tables created if absent).")


if __name__ == "__main__":
    init_schema()
