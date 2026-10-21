"""Reproducible local TestClient PP1 scenario runner; writes only sibling JSON evidence."""
import json
import sys
from pathlib import Path
from time import perf_counter

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from fastapi.testclient import TestClient  # noqa: E402
from backend.main import app  # noqa: E402

HERE = Path(__file__).resolve().parent
BASE = {
    "event_date": "2026-11-26", "start_time": "10:00",
    "end_time": "18:00", "top_k": 3,
}
SCENARIOS = [
    ("A_wedding_success", {**BASE, "event_type": "Wedding", "city": "Philadelphia",
        "state": "PA", "guest_count": 50, "budget_lkr": 1000000,
        "required_services": ["Photography", "Decoration"]}),
    ("B_corporate_success", {**BASE, "event_type": "Corporate", "city": "Philadelphia",
        "state": "PA", "guest_count": 40, "budget_lkr": 1000000,
        "required_services": ["Photography", "Audio Visual"]}),
    ("C_belle_chasse_no_match", {**BASE, "event_type": "Corporate", "city": "Belle Chasse",
        "state": "LA", "guest_count": 50, "budget_lkr": 1000000,
        "required_services": ["Entertainment", "Catering"]}),
    ("D_edit_location_recovery", {**BASE, "event_type": "Corporate", "city": "Bensalem",
        "state": "PA", "guest_count": 50, "budget_lkr": 1000000,
        "required_services": ["Entertainment", "Catering"]}),
    ("E_insufficient_budget", {**BASE, "event_type": "Corporate", "city": "Bensalem",
        "state": "PA", "guest_count": 50, "budget_lkr": 1,
        "required_services": ["Entertainment", "Catering"]}),
    ("F_invalid_zero_budget", {**BASE, "event_type": "Corporate", "city": "Bensalem",
        "state": "PA", "guest_count": 50, "budget_lkr": 0,
        "required_services": ["Entertainment", "Catering"]}),
]

def main():
    (HERE / "demo_scenarios.json").write_text(
        json.dumps([{"id": name, "request": body} for name, body in SCENARIOS], indent=2),
        encoding="utf-8",
    )
    client = TestClient(app)
    results = []
    for name, body in SCENARIOS:
        start = perf_counter()
        try:
            response = client.post("/api/packages/generate-dynamic", json=body)
            elapsed = (perf_counter() - start) * 1000
            payload = response.json()
            generation = payload.get("generation", {})
            packages = generation.get("packages", [])
            diagnostic = payload.get("diagnostics") or {}
            reason_codes = {item.get("code") for item in diagnostic.get("reasons", [])}
            expected = (
                response.status_code == 200 and len(packages) > 0
                if name in {"A_wedding_success", "B_corporate_success", "D_edit_location_recovery"}
                else response.status_code == 200 and not packages and "NO_SERVICE_COVERAGE" in reason_codes
                if name == "C_belle_chasse_no_match"
                else response.status_code == 200 and not packages and "BUDGET_INSUFFICIENT" in reason_codes
                if name == "E_insufficient_budget"
                else response.status_code == 422
            )
            results.append({
                "verification_status": "PASS" if expected else "FAIL",
                "identity_note": (
                    "No USER event created for invalid request." if response.status_code == 422
                    else "Independent API request received a fresh USER ID; client edit lineage is verified separately in browser evidence."
                ),
                "id": name, "request": body, "http_status": response.status_code,
                "elapsed_ms_local_testclient": round(elapsed, 3),
                "event_id": payload.get("event_id"),
                "generation_status": generation.get("status"),
                "candidate_counts": generation.get("candidate_counts"),
                "selected_candidate_counts": generation.get("selected_candidate_counts"),
                "search": generation.get("search"),
                "diagnostic_reasons": diagnostic.get("reasons", []),
                "service_stages": diagnostic.get("service_stages"),
                "packages_returned": len(packages),
                "top_package": ({
                    "package_id": packages[0]["package_id"],
                    "vendor_ids": packages[0]["vendor_ids"],
                    "option_ids": packages[0]["option_ids"],
                    "total_cost_lkr": packages[0]["total_cost_lkr"],
                    "remaining_budget_lkr": packages[0]["remaining_budget_lkr"],
                    "feasibility_status": packages[0]["feasibility"]["final_status"],
                } if packages else None),
                "error_detail": payload.get("detail"),
            })
        except Exception as exc:
            results.append({
                "id": name, "request": body, "status": "FAIL",
                "exception": type(exc).__name__ + ": " + str(exc),
            })
        print(name, results[-1].get("http_status"), results[-1].get("generation_status"),
              results[-1].get("packages_returned"), results[-1].get("elapsed_ms_local_testclient"))
    (HERE / "demo_test_results.json").write_text(
        json.dumps(results, indent=2, default=str), encoding="utf-8",
    )

if __name__ == "__main__":
    main()