import json
import sys
from pathlib import Path

from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from stage_e_api_v1 import app

OUT = ROOT / "outputs"
client = TestClient(app)


def read(filename):
    return json.loads(
        (OUT / filename).read_text(encoding="utf-8")
    )


print("=== B1 BACKEND API TESTS ===")

health = client.get("/api/stage-e/health")
assert health.status_code == 200, health.text
assert health.json()["status"] == "ready"
print("1. Frozen research engine integrity: PASS")

invalid = client.post(
    "/api/stage-e/optimize",
    json={"contract_id": "INVALID", "mode": "initial_design"},
)
assert invalid.status_code == 422
print("2. Invalid contract rejected: PASS")

denied = client.post(
    "/api/stage-e/optimize",
    json=read("f2d_denied_request_v1.json"),
)
assert denied.status_code == 200, denied.text
assert denied.json()["status"] == "denied"
assert denied.json()["candidate_layouts"] == []
assert denied.json()["provenance"]["optimizer_evaluations"] == 0
print("3. Unauthorized optimization blocked: PASS")

initial = client.post(
    "/api/stage-e/optimize",
    json=read("f2b_test_request_v1.json"),
)
assert initial.status_code == 200, initial.text
assert initial.json()["status"] == "success"
assert initial.json()["provenance"]["optimizer_evaluations"] == 1200
assert len(initial.json()["candidate_layouts"][0]["objects"]) == 183
print("4. Live initial NSGA-II API execution: PASS")

adaptive = client.post(
    "/api/stage-e/optimize",
    json=read("f2d_approved_request_v1.json"),
)
assert adaptive.status_code == 200, adaptive.text
assert adaptive.json()["status"] == "success"
assert adaptive.json()["provenance"]["optimizer_evaluations"] == 1680
assert len(adaptive.json()["candidate_layouts"]) == 2
assert all(
    len(layout["objects"]) == 183
    and layout["constraint_results"]["synthetic_geometry_pass"]
    for layout in adaptive.json()["candidate_layouts"]
)
print("5. Live adaptive NSGA-II API execution: PASS")

print("=== BACKEND B1 SUMMARY ===")
print("API tests: 5/5 PASS")
print("Research source hashes checked: YES")
print("Live research engine integrated: YES")
print("Real planner authentication: NO")
print("Real venue validation: NO")
print("B1 BACKEND API VALIDATION COMPLETE")