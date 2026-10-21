import json
import sqlite3
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path

from fastapi import FastAPI, HTTPException, Request

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from stage_e_api_v1 import verify_frozen_engine
from f2h_unified_dispatcher_v2 import dispatch

DEFAULT_DB = ROOT / "backend" / "data" / "stage_e_runs.sqlite3"


def connect(db_path):
    db_path = Path(db_path)
    db_path.parent.mkdir(parents=True, exist_ok=True)

    connection = sqlite3.connect(
        str(db_path), timeout=30
    )
    connection.row_factory = sqlite3.Row
    return connection


def initialize_db(db_path):
    with connect(db_path) as db:
        db.execute("""
            CREATE TABLE IF NOT EXISTS optimization_runs (
                id TEXT PRIMARY KEY,
                created_at TEXT NOT NULL,
                event_id TEXT NOT NULL,
                mode TEXT NOT NULL,
                status TEXT NOT NULL,
                candidate_count INTEGER NOT NULL,
                optimizer_evaluations INTEGER NOT NULL,
                response_json TEXT NOT NULL
            )
        """)
        db.commit()


def save_run(db_path, mode, response):
    run_id = uuid.uuid4().hex
    created = datetime.now(timezone.utc).isoformat()

    # Permission-denied outcomes must never persist layouts.
    if response["status"] == "denied":
        if response["candidate_layouts"]:
            raise RuntimeError("DENIED_LAYOUT_LEAK")

        if response["provenance"].get(
            "optimizer_evaluations", -1
        ) != 0:
            raise RuntimeError("DENIED_OPTIMIZER_EXECUTION")

    with connect(db_path) as db:
        db.execute(
            """
            INSERT INTO optimization_runs (
                id, created_at, event_id, mode, status,
                candidate_count, optimizer_evaluations,
                response_json
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                run_id,
                created,
                str(response.get("event_id", "")),
                mode,
                response["status"],
                len(response["candidate_layouts"]),
                int(response["provenance"].get(
                    "optimizer_evaluations", 0
                )),
                json.dumps(
                    response, allow_nan=False
                ),
            )
        )
        db.commit()

    return run_id


def create_app(db_path=DEFAULT_DB):
    db_path = Path(db_path)
    initialize_db(db_path)

    app = FastAPI(
        title="Stage E PP1 Research API V2",
        version="2.0.0",
        description="Local controlled synthetic prototype",
    )

    @app.get("/api/stage-e/health")
    def health():
        try:
            verify_frozen_engine()
        except Exception:
            raise HTTPException(
                status_code=503,
                detail="RESEARCH_INTEGRITY_CHECK_FAILED",
            )

        return {
            "status": "ready",
            "contract_id": "STAGE_E_PP1_V1",
            "persistence": "sqlite",
            "real_planner_authentication": False,
            "real_venue_supported": False,
            "controlled_synthetic_only": True,
        }

    @app.post("/api/stage-e/optimize")
    async def optimize(request: Request):
        try:
            verify_frozen_engine()
        except Exception:
            raise HTTPException(
                status_code=503,
                detail="RESEARCH_INTEGRITY_CHECK_FAILED",
            )

        try:
            payload = await request.json()
        except Exception:
            raise HTTPException(
                status_code=400,
                detail="INVALID_JSON",
            )

        if not isinstance(payload, dict):
            raise HTTPException(
                status_code=422,
                detail="INVALID_REQUEST",
            )

        try:
            response = dispatch(payload)
        except (ValueError, TypeError, KeyError) as exc:
            raise HTTPException(
                status_code=422,
                detail=str(exc),
            )
        except Exception:
            raise HTTPException(
                status_code=500,
                detail="RESEARCH_ENGINE_EXECUTION_FAILED",
            )

        try:
            run_id = save_run(
                db_path,
                payload["mode"],
                response,
            )
        except Exception:
            raise HTTPException(
                status_code=500,
                detail="RESULT_PERSISTENCE_FAILED",
            )

        # Storage ID is separate from the algorithm run ID.
        return {
            **response,
            "storage_run_id": run_id,
            "persisted": True,
        }

    @app.get("/api/stage-e/runs")
    def list_runs(limit: int = 20):
        if limit < 1 or limit > 100:
            raise HTTPException(
                status_code=422,
                detail="LIMIT_MUST_BE_1_TO_100",
            )

        with connect(db_path) as db:
            rows = db.execute(
                """
                SELECT
                    id, created_at, event_id, mode,
                    status, candidate_count,
                    optimizer_evaluations
                FROM optimization_runs
                ORDER BY created_at DESC, rowid DESC
                LIMIT ?
                """,
                (limit,),
            ).fetchall()

        return {
            "runs": [dict(row) for row in rows],
            "count": len(rows),
        }

    @app.get("/api/stage-e/runs/{run_id}")
    def get_run(run_id: str):
        with connect(db_path) as db:
            row = db.execute(
                """
                SELECT * FROM optimization_runs
                WHERE id = ?
                """,
                (run_id,),
            ).fetchone()

        if row is None:
            raise HTTPException(
                status_code=404,
                detail="RUN_NOT_FOUND",
            )

        return {
            "storage_run_id": row["id"],
            "created_at": row["created_at"],
            "mode": row["mode"],
            "status": row["status"],
            "response": json.loads(row["response_json"]),
        }

    return app


app = create_app()