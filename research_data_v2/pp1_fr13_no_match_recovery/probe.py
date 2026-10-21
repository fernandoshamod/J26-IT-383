import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from fastapi.testclient import TestClient
from backend.main import app

client = TestClient(app)
request = {
    "event_type": "Corporate",
    "event_date": "2026-11-26",
    "start_time": "10:00",
    "end_time": "18:00",
    "city": "Belle Chasse",
    "state": "LA",
    "guest_count": 50,
    "budget_lkr": 1000000,
    "required_services": ["Entertainment", "Catering"],
    "top_k": 3,
}
response = client.post("/api/packages/generate-dynamic", json=request)
print("http", response.status_code)
if response.status_code == 200:
    data = response.json()
    print("status", data["generation"]["status"])
    print("packages", len(data["generation"]["packages"]))
    print("diagnostics", data.get("diagnostics"))
else:
    print(response.text[:1000])