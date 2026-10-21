import json
import sys
import tempfile
from pathlib import Path

from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from stage_e_api_v2 import create_app

OUT = ROOT / "outputs"


def load(name):
    return json.loads(
        (OUT / name).read_text(encoding="utf-8")
    )


print("=== BACKEND B2 PERSISTENCE TESTS ===")

with tempfile.TemporaryDirectory() as folder:
    database = Path(folder) / "test_runs.sqlite3"
    client = TestClient(create_app(database))

    # Test 1: research engine integrity.
    health = client.get("/api/stage-e/health")
    assert health.status_code == 200, health.text
    assert health.json()["status"] == "ready"
    print("1. Research engine health: PASS")

    # Test 2: invalid request must not be persisted.
    invalid = client.post(
        "/api/stage-e/optimize",
        json={"contract_id": "INVALID", "mode": "initial_design"},
    )
    assert invalid.status_code == 422

    history = client.get("/api/stage-e/runs")
    assert history.status_code == 200
    assert history.json()["count"] == 0
    print("2. Invalid request not persisted: PASS")

    # Test 3: denied revision is stored without layouts.
    denied = client.post(
        "/api/stage-e/optimize",
        json=load("f2d_denied_request_v1.json"),
    )

    assert denied.status_code == 200, denied.text
    denied_data = denied.json()

    assert denied_data["status"] == "denied"
    assert denied_data["candidate_layouts"] == []
    assert denied_data["persisted"] is True
    assert denied_data["provenance"]["optimizer_evaluations"] == 0

    denied_id = denied_data["storage_run_id"]

    saved_denied = client.get(
        f"/api/stage-e/runs/{denied_id}"
    )
    assert saved_denied.status_code == 200
    assert saved_denied.json()["response"]["candidate_layouts"] == []
    print("3. Denied run stored without layouts: PASS")

    # Test 4: initial NSGA-II execution and persistence.
    initial = client.post(
        "/api/stage-e/optimize",
        json=load("f2b_test_request_v1.json"),
    )

    assert initial.status_code == 200, initial.text
    initial_data = initial.json()

    assert initial_data["status"] == "success"
    assert initial_data["persisted"] is True
    assert initial_data["provenance"]["optimizer_evaluations"] == 1200

    initial_id = initial_data["storage_run_id"]

    retrieved = client.get(
        f"/api/stage-e/runs/{initial_id}"
    )
    assert retrieved.status_code == 200
    assert retrieved.json()["mode"] == "initial_design"

    stored_initial = retrieved.json()["response"]
    assert len(
        stored_initial["candidate_layouts"][0]["objects"]
    ) == 183

    # The optimizer result itself must be identical.
    actual_engine_response = {
        k: v for k, v in initial_data.items()
        if k not in ("storage_run_id", "persisted")
    }
    assert stored_initial == actual_engine_response

    print("4. Initial layout saved and retrieved: PASS")

    # Test 5: adaptive revision and persistence.
    adaptive = client.post(
        "/api/stage-e/optimize",
        json=load("f2d_approved_request_v1.json"),
    )

    assert adaptive.status_code == 200, adaptive.text
    adaptive_data = adaptive.json()

    assert adaptive_data["status"] == "success"
    assert adaptive_data["provenance"]["optimizer_evaluations"] == 1680
    assert len(adaptive_data["candidate_layouts"]) == 2

    adaptive_id = adaptive_data["storage_run_id"]
    stored_adaptive = client.get(
        f"/api/stage-e/runs/{adaptive_id}"
    )

    assert stored_adaptive.status_code == 200
    assert len(
        stored_adaptive.json()["response"]["candidate_layouts"]
    ) == 2

    assert all(
        len(layout["objects"]) == 183
        for layout in stored_adaptive.json()[
            "response"
        ]["candidate_layouts"]
    )
    print("5. Adaptive alternatives saved: PASS")

    # Test 6: history listing.
    history = client.get("/api/stage-e/runs")
    assert history.status_code == 200

    rows = history.json()["runs"]
    assert len(rows) == 3
    assert len({row["id"] for row in rows}) == 3
    assert {
        row["status"] for row in rows
    } == {"success", "denied"}
    print("6. Run history and unique IDs: PASS")

    # Test 7: missing run and bad pagination.
    missing = client.get(
        "/api/stage-e/runs/nonexistent-run-id"
    )
    assert missing.status_code == 404

    bad_limit = client.get(
        "/api/stage-e/runs?limit=0"
    )
    assert bad_limit.status_code == 422
    print("7. Missing runs and invalid limits: PASS")

    # Test 8: saved data survives app recreation.
    second_client = TestClient(create_app(database))
    restored = second_client.get(
        f"/api/stage-e/runs/{initial_id}"
    )

    assert restored.status_code == 200
    assert len(
        restored.json()["response"][
            "candidate_layouts"
        ][0]["objects"]
    ) == 183

    print("8. SQLite persistence across app instances: PASS")

print("=== BACKEND B2 SUMMARY ===")
print("Tests: 8/8 PASS")
print("Initial NSGA-II execution: PASS")
print("Adaptive NSGA-II execution: PASS")
print("Denied runs have zero layouts: PASS")
print("Saved layout retrieval: PASS")
print("Run history persistence: PASS")
print("Real planner authentication: NOT IMPLEMENTED")
print("Real venue validation: NOT DONE")
print("B2 BACKEND PERSISTENCE COMPLETE")