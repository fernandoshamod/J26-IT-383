"""Read-only live HTTP smoke test; writes evidence only beside this script."""
import csv
import hashlib
import json
import math
import sys
from datetime import date, timedelta, datetime, timezone
from pathlib import Path
from time import perf_counter

import httpx

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
BASE = "http://127.0.0.1:8000"


def digest(path):
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1048576), b""):
            h.update(block)
    return h.hexdigest()


def inventoried():
    rows = []
    path = ROOT / "research_data_v2/audit_2026-10-17_01/dataset_inventory.csv"
    with path.open(newline="", encoding="utf-8-sig") as stream:
        for row in csv.DictReader(stream):
            target = ROOT / row["path"]
            rows.append({"path": row["path"], "expected_sha256": row["sha256"],
                         "actual_sha256": digest(target) if target.is_file() else None})
    return rows


def request(client, method, path, payload=None):
    begin = perf_counter()
    try:
        response = client.request(method, path, json=payload)
        elapsed = round((perf_counter() - begin) * 1000, 3)
        try:
            data = response.json()
        except ValueError:
            data = {"raw_excerpt": response.text[:500]}
        return {"http_status": response.status_code, "elapsed_ms": elapsed, "body": data}
    except Exception as exc:
        return {"http_status": None, "elapsed_ms": round((perf_counter() - begin) * 1000, 3),
                "error": type(exc).__name__ + ": " + str(exc)}


def summarize_package(package):
    return {
        "package_id": package.get("package_id"), "rank": package.get("rank"),
        "option_ids": package.get("option_ids"), "vendor_ids": package.get("vendor_ids"),
        "service_coverage": package.get("service_coverage"),
        "total_cost_lkr": package.get("total_cost_lkr"),
        "remaining_budget_lkr": package.get("remaining_budget_lkr"),
        "ranking_score": package.get("ranking_score"),
        "risk_status": package.get("risk", {}).get("status"),
        "risk_score": package.get("risk", {}).get("mean_rule_risk_score"),
        "risk_provenance": [v.get("risk_provenance") for v in package.get("risk", {}).get("vendors", [])],
        "compatibility_status": package.get("compatibility", {}).get("status"),
        "compatibility_score": package.get("compatibility", {}).get("score"),
        "feasibility_status": package.get("feasibility", {}).get("final_status"),
        "passed_checks": len(package.get("feasibility", {}).get("passed_checks", [])),
        "pending_checks": len(package.get("feasibility", {}).get("pending_checks", [])),
        "failed_checks": len(package.get("feasibility", {}).get("failed_checks", [])),
        "explanation_reasons": package.get("explanation", {}).get("reasons", []),
        "data_origin": package.get("data_origin"),
        "is_vendor_confirmed": package.get("is_vendor_confirmed"),
    }


def summarize_generation(result):
    if result.get("http_status") != 200:
        return {"http_status": result.get("http_status"), "elapsed_ms": result["elapsed_ms"],
                "detail": result.get("body", {}).get("detail"), "error": result.get("error")}
    data = result["body"]
    generation = data["generation"]
    return {
        "http_status": 200, "elapsed_ms": result["elapsed_ms"],
        "event_id": data["event_id"], "event": data["event"],
        "generation_mode": data["generation_mode"],
        "generation_status": generation["status"],
        "generation_message": generation["message"],
        "search": generation["search"], "candidate_counts": generation["candidate_counts"],
        "total_generated": generation["total_generated"],
        "package_count": len(generation["packages"]),
        "packages": [summarize_package(p) for p in generation["packages"]],
        "risk_data_audit": data["risk_data_audit"],
    }


def main():
    today = date.today()
    base = {
        "start_time": "10:00", "end_time": "18:00", "city": "Philadelphia",
        "state": "PA", "budget_lkr": 1000000, "top_k": 3,
    }
    scenarios = {
        "A_wedding": {**base, "event_type": "Wedding",
                      "event_date": (today + timedelta(days=5)).isoformat(),
                      "guest_count": 50,
                      "required_services": ["Photography", "Decoration"]},
        "B_corporate": {**base, "event_type": "Corporate",
                        "event_date": (today + timedelta(days=6)).isoformat(),
                        "start_time": "09:00", "end_time": "17:00",
                        "guest_count": 40,
                        "required_services": ["Photography", "Audio Visual"]},
        "C_low_budget": {**base, "event_type": "Wedding",
                         "event_date": (today + timedelta(days=7)).isoformat(),
                         "guest_count": 50, "budget_lkr": 1,
                         "required_services": ["Photography", "Decoration"]},
    }
    with (HERE / "demo_scenarios.json").open("x", encoding="utf-8") as stream:
        json.dump({"generated_on": today.isoformat(), "data_class": "SYNTHETIC_TEST",
                   "scenarios": scenarios}, stream, indent=2)

    before = inventoried()
    watched = [
        "backend/main.py", "backend/api/packages.py", "backend/api/feasibility.py",
        "backend/engine/dynamic_package_service.py",
        "backend/engine/bounded_package_generator.py",
        "frontend/src/App.jsx", "frontend/src/services/api.js",
    ]
    code_before = {name: digest(ROOT / name) for name in watched}
    output = {"executed_at_utc": datetime.now(timezone.utc).isoformat(),
              "interpreter": sys.executable, "base_url": BASE,
              "mode": "live_http_existing_server", "scenarios": {},
              "checks": {}, "api": {}}
    with httpx.Client(base_url=BASE, timeout=90.0) as client:
        for name, method, path in [
            ("root", "GET", "/"), ("health", "GET", "/health"),
            ("locations", "GET", "/api/locations"), ("openapi", "GET", "/openapi.json"),
            ("legacy_event_read", "GET", "/api/events/SIMEVT-0000"),
        ]:
            got = request(client, method, path)
            body = got.get("body", {})
            output["api"][name] = {"http_status": got["http_status"],
                                   "elapsed_ms": got["elapsed_ms"],
                                   "error": got.get("error")}
            if name == "locations" and got["http_status"] == 200:
                output["api"][name]["location_count"] = len(body.get("locations", []))
                output["api"][name]["philadelphia_present"] = any(
                    x.get("city") == "Philadelphia" and x.get("state") == "PA"
                    for x in body.get("locations", []))
            if name == "openapi" and got["http_status"] == 200:
                output["api"][name]["paths"] = sorted(body.get("paths", {}))
        raw = {}
        for name, scenario in scenarios.items():
            raw[name] = request(client, "POST", "/api/packages/generate-dynamic", scenario)
            output["scenarios"][name] = summarize_generation(raw[name])
        repeat = request(client, "POST", "/api/packages/generate-dynamic", scenarios["A_wedding"])
        output["scenarios"]["A_repeat"] = summarize_generation(repeat)
        for name, payload in {
            "invalid_zero_budget": {**scenarios["A_wedding"], "budget_lkr": 0},
            "invalid_location": {**scenarios["A_wedding"], "city": "Nowhere", "state": "ZZ"},
            "invalid_service": {**scenarios["A_wedding"], "required_services": ["Unlisted"]},
        }.items():
            got = request(client, "POST", "/api/packages/generate-dynamic", payload)
            output["api"][name] = {"http_status": got["http_status"],
                                   "elapsed_ms": got["elapsed_ms"],
                                   "detail": got.get("body", {}).get("detail"),
                                   "error": got.get("error")}
        if raw["A_wedding"].get("http_status") == 200:
            data = raw["A_wedding"]["body"]
            packages = data["generation"]["packages"]
            if packages:
                body = {"event": data["event"], "package_options": packages[0]["package_options"]}
                feasibility = request(client, "POST", "/api/feasibility/validate-dynamic", body)
                output["api"]["dynamic_feasibility"] = {
                    "http_status": feasibility["http_status"],
                    "elapsed_ms": feasibility["elapsed_ms"],
                    "status": feasibility.get("body", {}).get("final_status"),
                    "event_id": feasibility.get("body", {}).get("event_id"),
                    "total_cost_lkr": feasibility.get("body", {}).get("total_cost_lkr"),
                    "passed_checks": len(feasibility.get("body", {}).get("passed_checks", [])),
                    "pending_checks": len(feasibility.get("body", {}).get("pending_checks", [])),
                    "failed_checks": len(feasibility.get("body", {}).get("failed_checks", [])),
                    "error": feasibility.get("error"),
                }
                altered = json.loads(json.dumps(body))
                altered["package_options"][0]["unit_price_lkr"] = 1
                tampered = request(client, "POST", "/api/feasibility/validate-dynamic", altered)
                output["api"]["tampered_price"] = {
                    "http_status": tampered["http_status"],
                    "elapsed_ms": tampered["elapsed_ms"],
                    "detail": tampered.get("body", {}).get("detail"),
                    "error": tampered.get("error"),
                }

    a, b, c, repeat = (output["scenarios"][name] for name in
                       ("A_wedding", "B_corporate", "C_low_budget", "A_repeat"))
    positives = [a, b]
    output["checks"] = {
        "positive_requests_http_200": all(x.get("http_status") == 200 for x in positives),
        "positive_requests_have_packages": all(x.get("package_count", 0) > 0 for x in positives),
        "fresh_user_ids": all(str(x.get("event_id", "")).startswith("USER-")
                              for x in (a, b, repeat))
                          and len({a.get("event_id"), b.get("event_id"), repeat.get("event_id")}) == 3,
        "repeat_same_requirements_same_options": a.get("http_status") == repeat.get("http_status") == 200
            and [p["option_ids"] for p in a.get("packages", [])] ==
                [p["option_ids"] for p in repeat.get("packages", [])],
        "changed_requirements_change_services": a.get("http_status") == b.get("http_status") == 200
            and all(set(p["service_coverage"]) == {"Photography", "Decoration"} for p in a.get("packages", []))
            and all(set(p["service_coverage"]) == {"Photography", "Audio Visual"} for p in b.get("packages", [])),
        "coverage_budget_unique_vendors": all(
            len(p["service_coverage"]) == len(set(p["service_coverage"]))
            and len(p["vendor_ids"]) == len(set(p["vendor_ids"]))
            and p["total_cost_lkr"] <= x["event"]["budget_lkr"]
            and math.isclose(p["remaining_budget_lkr"],
                             x["event"]["budget_lkr"] - p["total_cost_lkr"], abs_tol=0.01)
            for x in positives for p in x.get("packages", [])),
        "no_fail_recommendations": all(p["feasibility_status"] != "FAIL"
                                        for x in positives for p in x.get("packages", [])),
        "risk_signal_present": any(p["risk_status"] == "complete" and
                                   p["risk_score"] is not None for x in positives
                                   for p in x.get("packages", [])),
        "compatibility_signal_present": all(p["compatibility_status"] == "complete"
                                            and p["compatibility_score"] is not None
                                            for x in positives for p in x.get("packages", [])),
        "explanations_present": all(p["explanation_reasons"]
                                    for x in positives for p in x.get("packages", [])),
        "low_budget_no_combinations": c.get("http_status") == 200
            and c.get("generation_status") == "no_budget_feasible_combinations"
            and c.get("package_count") == 0,
        "invalid_inputs_422": all(output["api"][name]["http_status"] == 422 for name in
                                  ("invalid_zero_budget", "invalid_location", "invalid_service")),
        "feasibility_http_200": output["api"].get("dynamic_feasibility", {}).get("http_status") == 200,
        "tampered_price_rejected": output["api"].get("tampered_price", {}).get("http_status") == 422,
    }
    after = inventoried()
    code_after = {name: digest(ROOT / name) for name in watched}
    output["integrity"] = {
        "task1_inventory_count": len(after),
        "task1_inventory_matching": sum(x["actual_sha256"] == x["expected_sha256"] for x in after),
        "inventory_unchanged_during_run": before == after,
        "watched_code_unchanged_during_run": code_before == code_after,
        "watched_code_sha256": code_after,
    }
    with (HERE / "demo_execution_results.json").open("x", encoding="utf-8") as stream:
        json.dump(output, stream, indent=2)
    print(json.dumps({
        "scenarios": {k: {"http_status": v.get("http_status"),
                          "generation_status": v.get("generation_status"),
                          "package_count": v.get("package_count"),
                          "elapsed_ms": v.get("elapsed_ms")}
                      for k, v in output["scenarios"].items()},
        "checks": output["checks"], "integrity": {
            k: v for k, v in output["integrity"].items() if k != "watched_code_sha256"
        },
    }, indent=2))


if __name__ == "__main__":
    main()