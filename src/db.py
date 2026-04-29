import sqlite3
from pathlib import Path
from datetime import datetime, date

DB_PATH = Path(__file__).resolve().parent.parent / "data" / "sessions.db"


def _connect():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db():
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
        # Seed default pairs if empty
        cur = conn.execute("SELECT COUNT(*) AS c FROM pairs")
        if cur.fetchone()["c"] == 0:
            defaults = ["EURUSD", "GBPUSD", "USDJPY", "XAUUSD", "AUDUSD", "USDCAD"]
            conn.executemany("INSERT INTO pairs(name) VALUES (?)", [(p,) for p in defaults])


def get_or_create_session(session_date: date, pair: str) -> int:
    now = datetime.utcnow().isoformat(timespec="seconds")
    date_str = session_date.isoformat()
    with _connect() as conn:
        row = conn.execute(
            "SELECT id FROM sessions WHERE date=? AND pair=?", (date_str, pair)
        ).fetchone()
        if row:
            return row["id"]
        cur = conn.execute(
            "INSERT INTO sessions(date, pair, created_at, updated_at) VALUES (?,?,?,?)",
            (date_str, pair, now, now),
        )
        return cur.lastrowid


def load_state(session_id: int) -> dict:
    with _connect() as conn:
        rows = conn.execute(
            "SELECT item_key, checked, note FROM checklist_state WHERE session_id=?",
            (session_id,),
        ).fetchall()
    return {r["item_key"]: {"checked": bool(r["checked"]), "note": r["note"]} for r in rows}


def upsert_item(session_id: int, item_key: str, checked: bool, note: str):
    now = datetime.utcnow().isoformat(timespec="seconds")
    with _connect() as conn:
        conn.execute(
            """
            INSERT INTO checklist_state(session_id, item_key, checked, note)
            VALUES (?,?,?,?)
            ON CONFLICT(session_id, item_key) DO UPDATE SET
                checked=excluded.checked,
                note=excluded.note
            """,
            (session_id, item_key, 1 if checked else 0, note or ""),
        )
        conn.execute("UPDATE sessions SET updated_at=? WHERE id=?", (now, session_id))


def reset_session(session_id: int):
    with _connect() as conn:
        conn.execute("DELETE FROM checklist_state WHERE session_id=?", (session_id,))


def list_sessions(limit: int = 50):
    with _connect() as conn:
        rows = conn.execute(
            """
            SELECT s.id, s.date, s.pair, s.updated_at,
                   COALESCE(SUM(cs.checked), 0) AS done,
                   COUNT(cs.item_key) AS total_items
            FROM sessions s
            LEFT JOIN checklist_state cs ON cs.session_id = s.id
            GROUP BY s.id
            ORDER BY s.date DESC, s.updated_at DESC
            LIMIT ?
            """,
            (limit,),
        ).fetchall()
    return [dict(r) for r in rows]


def list_pairs():
    with _connect() as conn:
        rows = conn.execute("SELECT name FROM pairs ORDER BY name").fetchall()
    return [r["name"] for r in rows]


def add_pair(name: str):
    name = name.strip().upper()
    if not name:
        return
    with _connect() as conn:
        conn.execute("INSERT OR IGNORE INTO pairs(name) VALUES (?)", (name,))


def duplicate_session(source_id: int, target_id: int):
    """Copy checked-state and notes from source session into target session."""
    with _connect() as conn:
        rows = conn.execute(
            "SELECT item_key, checked, note FROM checklist_state WHERE session_id=?",
            (source_id,),
        ).fetchall()
        for r in rows:
            conn.execute(
                """
                INSERT INTO checklist_state(session_id, item_key, checked, note)
                VALUES (?,?,?,?)
                ON CONFLICT(session_id, item_key) DO UPDATE SET
                    checked=excluded.checked,
                    note=excluded.note
                """,
                (target_id, r["item_key"], r["checked"], r["note"]),
            )
