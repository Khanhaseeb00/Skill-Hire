"""
Thin SQLite helper. In production, swap this module for a Postgres connection
(e.g. psycopg2 / SQLAlchemy) — every other file talks to the database only
through get_db(), so that's the only place that needs to change.
"""
import sqlite3
import os

# On a platform with an ephemeral filesystem (most free web-service tiers),
# anything written next to the code disappears on the next deploy/restart.
# Set DATABASE_PATH to a mounted persistent-disk path in production (the
# included render.yaml does this for you); it defaults to a local file for
# everyday development.
DB_PATH = os.environ.get("DATABASE_PATH", os.path.join(os.path.dirname(__file__), "kaamgar.db"))
SCHEMA_PATH = os.path.join(os.path.dirname(__file__), "schema.sql")


def get_db():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True) if os.path.dirname(DB_PATH) else None
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db():
    """Create tables if they don't exist yet. Safe to call every startup."""
    conn = get_db()
    with open(SCHEMA_PATH, "r") as f:
        conn.executescript(f.read())
    conn.commit()
    conn.close()


def row_to_dict(row):
    return dict(row) if row else None


def rows_to_list(rows):
    return [dict(r) for r in rows]
