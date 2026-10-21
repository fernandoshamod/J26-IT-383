"""Durable SQLite store for user-entered PlanoVision events."""
import json
import os
import sqlite3
from pathlib import Path
from typing import Any

DATABASE_PATH = Path(os.getenv("PLANOVISION_DB_PATH", Path(__file__).resolve().parent / "planovision.db"))

def _connect() -> sqlite3.Connection:
    connection = sqlite3.connect(DATABASE_PATH)
    connection.row_factory = sqlite3.Row
    return connection

def init_db() -> None:
    DATABASE_PATH.parent.mkdir(parents=True, exist_ok=True)
    with _connect() as connection:
        connection.execute("""CREATE TABLE IF NOT EXISTS events (
            event_id TEXT PRIMARY KEY, event_type TEXT NOT NULL, event_date TEXT NOT NULL,
            start_time TEXT NOT NULL, end_time TEXT NOT NULL, city TEXT NOT NULL, state TEXT NOT NULL,
            guest_count INTEGER NOT NULL, budget_lkr REAL NOT NULL, top_k INTEGER NOT NULL,
            required_services TEXT NOT NULL, created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP)""")

def _record(row: sqlite3.Row | None) -> dict[str, Any] | None:
    if row is None: return None
    value = dict(row)
    value["required_services"] = json.loads(value["required_services"])
    return value

def list_events() -> list[dict[str, Any]]:
    init_db()
    with _connect() as connection: rows = connection.execute("SELECT * FROM events ORDER BY updated_at DESC, created_at DESC").fetchall()
    return [_record(row) for row in rows]

def get_event(event_id: str) -> dict[str, Any] | None:
    init_db()
    with _connect() as connection: row = connection.execute("SELECT * FROM events WHERE event_id = ?", (event_id,)).fetchone()
    return _record(row)

def save_event(event_id: str, event: dict[str, Any]) -> dict[str, Any]:
    init_db()
    values = (event_id, event["event_type"], event["event_date"], event["start_time"], event["end_time"], event["city"], event["state"], event["guest_count"], event["budget_lkr"], event["top_k"], json.dumps(event["required_services"]))
    with _connect() as connection:
        connection.execute("""INSERT INTO events (event_id, event_type, event_date, start_time, end_time, city, state, guest_count, budget_lkr, top_k, required_services)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(event_id) DO UPDATE SET event_type=excluded.event_type, event_date=excluded.event_date,
            start_time=excluded.start_time, end_time=excluded.end_time, city=excluded.city, state=excluded.state,
            guest_count=excluded.guest_count, budget_lkr=excluded.budget_lkr, top_k=excluded.top_k,
            required_services=excluded.required_services, updated_at=CURRENT_TIMESTAMP""", values)
    return get_event(event_id)  # type: ignore[return-value]

def delete_event(event_id: str) -> bool:
    init_db()
    with _connect() as connection:
        cursor = connection.execute("DELETE FROM events WHERE event_id = ?", (event_id,))
    return cursor.rowcount == 1
