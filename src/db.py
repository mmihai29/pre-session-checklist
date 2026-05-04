"""Persistence layer.

Dual-backend: when ``DATABASE_URL`` is set (env var or Streamlit secret) the
app talks to Postgres via psycopg3; otherwise it falls back to a local SQLite
file. Same public API in both modes — the caller never has to care.
"""
from __future__ import annotations

import os
import sqlite3
from contextlib import contextmanager
from datetime import datetime, date
from pathlib import Path

# ---------- backend selection ----------

def _resolve_database_url() -> str | None:
    url = os.environ.get("DATABASE_URL")
    if url:
        return url
    try:
        import streamlit as st  # local import: keeps tests free of streamlit
        secrets = getattr(st, "secrets", None)
        if secrets is not None and "DATABASE_URL" in secrets:
            return secrets["DATABASE_URL"]
    except Exception:
        pass
    return None


DATABASE_URL = _resolve_database_url()
USE_POSTGRES = bool(DATABASE_URL)
PH = "%s" if USE_POSTGRES else "?"  # parameter placeholder for the active backend

DB_PATH = Path(__file__).resolve().parent.parent / "data" / "sessions.db"

if USE_POSTGRES:
    import psycopg
    from psycopg.rows import dict_row


@contextmanager
def _connect():
    """Yield an open connection that auto-commits on success, rolls back on error."""
    if USE_POSTGRES:
        conn = psycopg.connect(DATABASE_URL, row_factory=dict_row, autocommit=False)
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()
    else:
        DB_PATH.parent.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        try:
            yield conn
            conn.commit()
        finally:
            conn.close()


def init_db():
    if USE_POSTGRES:
        ddl = [
            """CREATE TABLE IF NOT EXISTS sessions (
                id SERIAL PRIMARY KEY,
                date TEXT NOT NULL,
                pair TEXT NOT NULL,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                UNIQUE(date, pair)
            )""",
            """CREATE TABLE IF NOT EXISTS checklist_state (
                session_id INTEGER NOT NULL REFERENCES sessions(id) ON DELETE CASCADE,
                item_key TEXT NOT NULL,
                checked INTEGER NOT NULL DEFAULT 0,
                note TEXT NOT NULL DEFAULT '',
                PRIMARY KEY (session_id, item_key)
            )""",
            """CREATE TABLE IF NOT EXISTS pairs (
                name TEXT PRIMARY KEY
            )""",
        ]
        with _connect() as conn:
            with conn.cursor() as cur:
                for stmt in ddl:
                    cur.execute(stmt)
                cur.execute("SELECT COUNT(*) AS c FROM pairs")
                if cur.fetchone()["c"] == 0:
                    for p in ["EURUSD", "GBPUSD", "USDJPY", "XAUUSD", "AUDUSD", "USDCAD"]:
                        cur.execute("INSERT INTO pairs(name) VALUES (%s) ON CONFLICT DO NOTHING", (p,))
    else:
        with _connect() as conn:
            conn.executescript(
                """
                CREATE TABLE IF NOT EXISTS sessions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    date TEXT NOT NULL,
                    pair TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    UNIQUE(date, pair)
                );
                CREATE TABLE IF NOT EXISTS checklist_state (
                    session_id INTEGER NOT NULL,
                    item_key TEXT NOT NULL,
                    checked INTEGER NOT NULL DEFAULT 0,
                    note TEXT NOT NULL DEFAULT '',
                    PRIMARY KEY (session_id, item_key),
                    FOREIGN KEY (session_id) REFERENCES sessions(id) ON DELETE CASCADE
                );
                CREATE TABLE IF NOT EXISTS pairs (
                    name TEXT PRIMARY KEY
                );
                """
            )
            cur = conn.execute("SELECT COUNT(*) AS c FROM pairs")
            if cur.fetchone()["c"] == 0:
                conn.executemany(
                    "INSERT INTO pairs(name) VALUES (?)",
                    [(p,) for p in ["EURUSD", "GBPUSD", "USDJPY", "XAUUSD", "AUDUSD", "USDCAD"]],
                )


# ---------- helper for unified query execution ----------

def _execute(conn, sql: str, params: tuple = ()):
    """Execute a query and return the cursor (Postgres or SQLite)."""
    if USE_POSTGRES:
        cur = conn.cursor()
        cur.execute(sql, params)
        return cur
    return conn.execute(sql, params)


def _fetchone(conn, sql: str, params: tuple = ()):
    cur = _execute(conn, sql, params)
    row = cur.fetchone()
    if USE_POSTGRES:
        cur.close()
    return row


def _fetchall(conn, sql: str, params: tuple = ()):
    cur = _execute(conn, sql, params)
    rows = cur.fetchall()
    if USE_POSTGRES:
        cur.close()
    return rows


# ---------- public API ----------

def get_or_create_session(session_date: date, pair: str) -> int:
    now = datetime.utcnow().isoformat(timespec="seconds")
    date_str = session_date.isoformat()
    with _connect() as conn:
        row = _fetchone(
            conn,
            f"SELECT id FROM sessions WHERE date={PH} AND pair={PH}",
            (date_str, pair),
        )
        if row:
            return row["id"]
        if USE_POSTGRES:
            row = _fetchone(
                conn,
                f"INSERT INTO sessions(date, pair, created_at, updated_at) "
                f"VALUES ({PH},{PH},{PH},{PH}) RETURNING id",
                (date_str, pair, now, now),
            )
            return row["id"]
        cur = conn.execute(
            "INSERT INTO sessions(date, pair, created_at, updated_at) VALUES (?,?,?,?)",
            (date_str, pair, now, now),
        )
        return cur.lastrowid


def load_state(session_id: int) -> dict:
    with _connect() as conn:
        rows = _fetchall(
            conn,
            f"SELECT item_key, checked, note FROM checklist_state WHERE session_id={PH}",
            (session_id,),
        )
    return {r["item_key"]: {"checked": bool(r["checked"]), "note": r["note"]} for r in rows}


def upsert_item(session_id: int, item_key: str, checked: bool, note: str):
    now = datetime.utcnow().isoformat(timespec="seconds")
    sql = (
        f"INSERT INTO checklist_state(session_id, item_key, checked, note) "
        f"VALUES ({PH},{PH},{PH},{PH}) "
        f"ON CONFLICT(session_id, item_key) DO UPDATE SET "
        f"checked=EXCLUDED.checked, note=EXCLUDED.note"
    ) if USE_POSTGRES else (
        "INSERT INTO checklist_state(session_id, item_key, checked, note) "
        "VALUES (?,?,?,?) "
        "ON CONFLICT(session_id, item_key) DO UPDATE SET "
        "checked=excluded.checked, note=excluded.note"
    )
    with _connect() as conn:
        _execute(conn, sql, (session_id, item_key, 1 if checked else 0, note or ""))
        _execute(conn, f"UPDATE sessions SET updated_at={PH} WHERE id={PH}", (now, session_id))


def reset_session(session_id: int):
    with _connect() as conn:
        _execute(conn, f"DELETE FROM checklist_state WHERE session_id={PH}", (session_id,))


def list_sessions(limit: int = 50):
    sql = (
        "SELECT s.id, s.date, s.pair, s.updated_at, "
        "       COALESCE(SUM(cs.checked), 0) AS done, "
        "       COUNT(cs.item_key) AS total_items "
        "FROM sessions s "
        "LEFT JOIN checklist_state cs ON cs.session_id = s.id "
        "GROUP BY s.id "
        "ORDER BY s.date DESC, s.updated_at DESC "
        f"LIMIT {PH}"
    )
    with _connect() as conn:
        rows = _fetchall(conn, sql, (limit,))
    return [dict(r) for r in rows]


def list_pairs():
    with _connect() as conn:
        rows = _fetchall(conn, "SELECT name FROM pairs ORDER BY name")
    return [r["name"] for r in rows]


def add_pair(name: str):
    name = name.strip().upper()
    if not name:
        return
    sql = (
        f"INSERT INTO pairs(name) VALUES ({PH}) ON CONFLICT DO NOTHING"
        if USE_POSTGRES
        else "INSERT OR IGNORE INTO pairs(name) VALUES (?)"
    )
    with _connect() as conn:
        _execute(conn, sql, (name,))


def duplicate_session(source_id: int, target_id: int):
    upsert_sql = (
        f"INSERT INTO checklist_state(session_id, item_key, checked, note) "
        f"VALUES ({PH},{PH},{PH},{PH}) "
        f"ON CONFLICT(session_id, item_key) DO UPDATE SET "
        f"checked=EXCLUDED.checked, note=EXCLUDED.note"
    ) if USE_POSTGRES else (
        "INSERT INTO checklist_state(session_id, item_key, checked, note) "
        "VALUES (?,?,?,?) "
        "ON CONFLICT(session_id, item_key) DO UPDATE SET "
        "checked=excluded.checked, note=excluded.note"
    )
    with _connect() as conn:
        rows = _fetchall(
            conn,
            f"SELECT item_key, checked, note FROM checklist_state WHERE session_id={PH}",
            (source_id,),
        )
        for r in rows:
            _execute(conn, upsert_sql, (target_id, r["item_key"], r["checked"], r["note"]))


def backend_info() -> str:
    """Return a short string describing the active backend (for diagnostics / UI)."""
    return "Postgres (remote)" if USE_POSTGRES else f"SQLite ({DB_PATH.name})"
