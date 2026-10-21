"""Focused, read-only PP1 demonstration probe."""
import json
from datetime import datetime, timezone
from pathlib import Path
from fastapi.testclient import TestClient
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from backend.main import app

OUT = Path(__file__).resolve().parent
payload = {
    "event_type": "Wedding",
    "event_date": "2026-11-16",
    "start_time": "10:00",
    "end_time": "18:00",
    "city": "Philadelphia",
    "state": "PA",
    "guest_count": 50,
    "budget_lkr": 1000000,
    "required_services": ["Photography", "Decoration"],
    "top_k": 3,
}
with TestClient(app) as client:
    response = client.post("/api/packages/generate-dynamic", json=payload)
    data = response.json()
    packages = data.get("generation", {}).get("packages", [])
    feasibility = None
    if response.status_code == 200 and packages:
        feas_response = client.post("/api/feasibility/validate-dynamic", json={
            "event": data["event"],
            "package_options": packages[0]["package_options"],
        })
        feas_data = feas_response.json()
        feasibility = {
            "http_status": feas_response.status_code,
            "status": feas_data.get("final_status"),
            "passed_checks": feas_data.get("passed_checks"),
            "pending_checks": feas_data.get("pending_checks"),
            "failed_checks": feas_data.get("failed_checks"),
            "response": feas_data if feas_response.status_code != 200 else None,
        }

fields = ("package_id", "rank", "total_cost_lkr", "remaining_budget_lkr",
          "ranking_score", "feasibility_status", "service_coverage",
          "passed_checks", "pending_checks", "failed_checks")
observed = []
for pkg in packages:
    observed.append({
        **{key: (pkg.get("feasibility", {}).get("final_status") if key == "feasibility_status" else len(pkg.get("feasibility", {}).get(key, [])) if key in ("passed_checks", "pending_checks", "failed_checks") else pkg.get(key)) for key in fields},
        "option_ids": [option.get("service_option_id") for option in pkg.get("package_options", [])],
        "vendor_ids": [option.get("business_id") for option in pkg.get("package_options", [])],
        "model_predictions": [{
            "vendor_id": item.get("vendor_id"),
            "predicted_risk_level": item.get("predicted_risk_level"),
            "rule_risk_level": item.get("rule_risk_level"),
            "risk_provenance": item.get("risk_provenance"),
        } for item in pkg.get("risk", {}).get("vendors", [])],
        "service_categories": [option.get("service_category") for option in pkg.get("package_options", [])],
    })
result = {
    "checked_at_utc": datetime.now(timezone.utc).isoformat(),
    "method": "FastAPI TestClient against current backend.main:app; read-only",
    "route": "POST /api/packages/generate-dynamic",
    "request": payload,
    "http_status": response.status_code,
    "event_id": data.get("event", {}).get("event_id"),
    "generation_status": data.get("generation", {}).get("status"),
    "search": data.get("generation", {}).get("search"),
    "candidate_counts": data.get("generation", {}).get("candidate_counts"),
    "package_count": len(packages),
    "packages": observed,
    "top_package_feasibility_rerun": feasibility,
    "risk_data_audit": data.get("risk_data_audit"),
    "comparison_of_first_two": {
        "available": len(observed) >= 2,
        "different_option_ids": len(observed) >= 2 and observed[0]["option_ids"] != observed[1]["option_ids"],
        "different_total_cost": len(observed) >= 2 and observed[0]["total_cost_lkr"] != observed[1]["total_cost_lkr"],
    },
    "claim_scope": "Local in-process simulation; no vendor booking, quotation, capacity confirmation, or actual availability verified.",
}
(OUT / "pp1_demo_inputs_and_outputs.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
print(json.dumps({"http_status": response.status_code, "package_count": len(packages),
                  "feasibility_http_status": feasibility and feasibility["http_status"],
                  "event_id": result["event_id"]}, indent=2))
