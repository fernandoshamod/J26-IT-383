"""Focused read-only API checks for PP1 technical audit."""
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from fastapi.testclient import TestClient
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from backend.main import app

BASE = {
    "event_type": "Corporate", "event_date": "2026-11-26",
    "start_time": "10:00", "end_time": "18:00",
    "guest_count": 50, "budget_lkr": 1000000,
    "required_services": ["Catering", "Entertainment"], "top_k": 3,
}
SCENARIOS = [
    ("bensalem_50", {**BASE, "city": "Bensalem", "state": "PA"}),
    ("bensalem_500", {**BASE, "city": "Bensalem", "state": "PA", "guest_count": 500}),
    ("belle_chasse_50", {**BASE, "city": "Belle Chasse", "state": "LA"}),
]
results = []
with TestClient(app) as client:
    for name, payload in SCENARIOS:
        response = client.post("/api/packages/generate-dynamic", json=payload)
        data = response.json()
        packages = data.get("generation", {}).get("packages", [])
        results.append({
            "scenario": name, "request": payload,
            "http_status": response.status_code,
            "event_id": data.get("event_id"),
            "generation_status": data.get("generation", {}).get("status"),
            "package_count": len(packages),
            "search": data.get("generation", {}).get("search"),
            "diagnostic_reason_codes": [r.get("code") for r in (data.get("diagnostics") or {}).get("reasons", [])],
            "first_package": ({
                "package_id": packages[0].get("package_id"),
                "total_cost_lkr": packages[0].get("total_cost_lkr"),
                "feasibility_status": packages[0].get("feasibility", {}).get("final_status"),
                "model_classes": [v.get("predicted_risk_level") for v in packages[0].get("risk", {}).get("vendors", [])],
            } if packages else None),
        })
out = {
    "checked_at_utc": datetime.now(timezone.utc).isoformat(),
    "method": "FastAPI TestClient, current backend.main:app, read-only",
    "results": results,
    "scope": "Synthetic option prices and capacities; no real-world vendor confirmation.",
}
(Path(__file__).resolve().parent/"focused_api_results.json").write_text(json.dumps(out, indent=2), encoding="utf-8")
print(json.dumps([{k:v for k,v in r.items() if k in ("scenario","http_status","generation_status","package_count","diagnostic_reason_codes")} for r in results], indent=2))
