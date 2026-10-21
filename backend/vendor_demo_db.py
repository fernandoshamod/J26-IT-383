"""Operational SQLite storage for the isolated PP1 vendor portal demo."""

import sqlite3
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

from backend.db import DATABASE_PATH

DEMO_VENDOR_ID = "DEMO-VENDOR-001"


def _connect() -> sqlite3.Connection:
    connection = sqlite3.connect(DATABASE_PATH)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    return connection


def _now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def init_vendor_demo_db() -> None:
    with _connect() as connection:
        connection.executescript(
            """
            CREATE TABLE IF NOT EXISTS demo_vendor_profiles (
                vendor_id TEXT PRIMARY KEY,
                business_name TEXT NOT NULL,
                description TEXT NOT NULL DEFAULT '',
                email TEXT NOT NULL,
                phone TEXT NOT NULL,
                city TEXT NOT NULL,
                state TEXT NOT NULL,
                verification_status TEXT NOT NULL DEFAULT 'demo_unverified',
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS vendor_services (
                service_id TEXT PRIMARY KEY,
                vendor_id TEXT NOT NULL,
                service_name TEXT NOT NULL,
                description TEXT NOT NULL DEFAULT '',
                price_lkr REAL NOT NULL CHECK(price_lkr >= 0),
                active INTEGER NOT NULL DEFAULT 1 CHECK(active IN (0, 1)),
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                FOREIGN KEY(vendor_id) REFERENCES demo_vendor_profiles(vendor_id) ON DELETE CASCADE
            );
            CREATE TABLE IF NOT EXISTS vendor_availability (
                availability_id TEXT PRIMARY KEY,
                vendor_id TEXT NOT NULL,
                availability_date TEXT NOT NULL,
                status TEXT NOT NULL CHECK(status IN ('available', 'unavailable')),
                note TEXT NOT NULL DEFAULT '',
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                UNIQUE(vendor_id, availability_date),
                FOREIGN KEY(vendor_id) REFERENCES demo_vendor_profiles(vendor_id) ON DELETE CASCADE
            );
            """
        )
        now = _now()
        connection.execute(
            """
            INSERT OR IGNORE INTO demo_vendor_profiles
            (vendor_id, business_name, description, email, phone, city, state,
             verification_status, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                DEMO_VENDOR_ID,
                "Willow & Pine Demo Events",
                "A clearly labelled operational demo profile for the PP1 vendor portal.",
                "demo.vendor@example.test",
                "+1 215 555 0147",
                "Philadelphia",
                "PA",
                "demo_unverified",
                now,
                now,
            ),
        )
        if not connection.execute("SELECT 1 FROM vendor_services WHERE vendor_id = ?", (DEMO_VENDOR_ID,)).fetchone():
            connection.executemany(
                "INSERT INTO vendor_services VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                [
                    ("VSVC-DEMO-001", DEMO_VENDOR_ID, "Event Photography", "Demo service record; pricing is illustrative.", 125000, 1, now, now),
                    ("VSVC-DEMO-002", DEMO_VENDOR_ID, "Reception Styling", "Demo service record; pricing is illustrative.", 95000, 1, now, now),
                ],
            )
        if not connection.execute("SELECT 1 FROM vendor_availability WHERE vendor_id = ?", (DEMO_VENDOR_ID,)).fetchone():
            connection.executemany(
                "INSERT INTO vendor_availability VALUES (?, ?, ?, ?, ?, ?, ?)",
                [
                    ("VAVL-DEMO-001", DEMO_VENDOR_ID, "2027-03-20", "available", "Demo availability record.", now, now),
                    ("VAVL-DEMO-002", DEMO_VENDOR_ID, "2027-04-10", "unavailable", "Demo hold; not a live booking calendar.", now, now),
                ],
            )


def get_profile() -> dict[str, Any]:
    init_vendor_demo_db()
    with _connect() as connection:
        row = connection.execute("SELECT * FROM demo_vendor_profiles WHERE vendor_id = ?", (DEMO_VENDOR_ID,)).fetchone()
    return dict(row) if row else {}


def update_profile(values: dict[str, Any]) -> dict[str, Any]:
    init_vendor_demo_db()
    with _connect() as connection:
        connection.execute(
            "UPDATE demo_vendor_profiles SET business_name=?, description=?, email=?, phone=?, city=?, state=?, updated_at=? WHERE vendor_id=?",
            (values["business_name"], values["description"], values["email"], values["phone"], values["city"], values["state"], _now(), DEMO_VENDOR_ID),
        )
    return get_profile()


def _service(row: sqlite3.Row) -> dict[str, Any]:
    value = dict(row)
    value["active"] = bool(value["active"])
    return value


def list_services() -> list[dict[str, Any]]:
    init_vendor_demo_db()
    with _connect() as connection:
        rows = connection.execute("SELECT * FROM vendor_services WHERE vendor_id=? ORDER BY created_at", (DEMO_VENDOR_ID,)).fetchall()
    return [_service(row) for row in rows]


def create_service(values: dict[str, Any]) -> dict[str, Any]:
    init_vendor_demo_db()
    now = _now()
    service_id = f"VSVC-{uuid4().hex[:10].upper()}"
    with _connect() as connection:
        connection.execute("INSERT INTO vendor_services VALUES (?, ?, ?, ?, ?, ?, ?, ?)", (service_id, DEMO_VENDOR_ID, values["service_name"], values["description"], values["price_lkr"], int(values["active"]), now, now))
        row = connection.execute("SELECT * FROM vendor_services WHERE service_id=?", (service_id,)).fetchone()
    return _service(row)


def update_service(service_id: str, values: dict[str, Any]) -> dict[str, Any] | None:
    init_vendor_demo_db()
    with _connect() as connection:
        result = connection.execute("UPDATE vendor_services SET service_name=?, description=?, price_lkr=?, active=?, updated_at=? WHERE service_id=? AND vendor_id=?", (values["service_name"], values["description"], values["price_lkr"], int(values["active"]), _now(), service_id, DEMO_VENDOR_ID))
        if result.rowcount == 0:
            return None
        row = connection.execute("SELECT * FROM vendor_services WHERE service_id=?", (service_id,)).fetchone()
    return _service(row)


def delete_service(service_id: str) -> bool:
    init_vendor_demo_db()
    with _connect() as connection:
        return connection.execute("DELETE FROM vendor_services WHERE service_id=? AND vendor_id=?", (service_id, DEMO_VENDOR_ID)).rowcount > 0


def list_availability() -> list[dict[str, Any]]:
    init_vendor_demo_db()
    with _connect() as connection:
        rows = connection.execute("SELECT * FROM vendor_availability WHERE vendor_id=? ORDER BY availability_date", (DEMO_VENDOR_ID,)).fetchall()
    return [dict(row) for row in rows]


def create_availability(values: dict[str, Any]) -> dict[str, Any]:
    init_vendor_demo_db()
    now = _now()
    availability_id = f"VAVL-{uuid4().hex[:10].upper()}"
    with _connect() as connection:
        connection.execute("INSERT INTO vendor_availability VALUES (?, ?, ?, ?, ?, ?, ?)", (availability_id, DEMO_VENDOR_ID, values["availability_date"].isoformat(), values["status"], values["note"], now, now))
        row = connection.execute("SELECT * FROM vendor_availability WHERE availability_id=?", (availability_id,)).fetchone()
    return dict(row)


def update_availability(availability_id: str, values: dict[str, Any]) -> dict[str, Any] | None:
    init_vendor_demo_db()
    with _connect() as connection:
        result = connection.execute("UPDATE vendor_availability SET availability_date=?, status=?, note=?, updated_at=? WHERE availability_id=? AND vendor_id=?", (values["availability_date"].isoformat(), values["status"], values["note"], _now(), availability_id, DEMO_VENDOR_ID))
        if result.rowcount == 0:
            return None
        row = connection.execute("SELECT * FROM vendor_availability WHERE availability_id=?", (availability_id,)).fetchone()
    return dict(row)


def delete_availability(availability_id: str) -> bool:
    init_vendor_demo_db()
    with _connect() as connection:
        return connection.execute("DELETE FROM vendor_availability WHERE availability_id=? AND vendor_id=?", (availability_id, DEMO_VENDOR_ID)).rowcount > 0


def dashboard() -> dict[str, Any]:
    profile = get_profile()
    services = list_services()
    availability = list_availability()
    fields = [profile.get(key) for key in ("business_name", "description", "email", "phone", "city", "state")]
    available = [item for item in availability if item["status"] == "available"]
    return {
        "vendor_id": DEMO_VENDOR_ID,
        "business_name": profile.get("business_name"),
        "profile_completion_percent": round(sum(bool(value) for value in fields) / len(fields) * 100),
        "active_services": sum(1 for service in services if service["active"]),
        "available_dates": len(available),
        "next_available_date": min((item["availability_date"] for item in available), default=None),
        "verification_status": profile.get("verification_status"),
        "data_origin": "operational_demo_vendor_tables",
    }
