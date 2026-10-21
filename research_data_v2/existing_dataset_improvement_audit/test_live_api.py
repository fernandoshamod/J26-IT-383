"""Read-only live API scenario audit using existing option records."""
import csv
import json
import math
import time
from pathlib import Path

import httpx
import pandas as pd

from backend.engine.validation_helpers import validate_service_option_lkr

ROOT = Path(__file__).resolve().parents[2]
OUT = Path(__file__).resolve().parent
SAVED = json.loads((ROOT / "research_data_v2/pp1_final_submission/pp1_demo_inputs_and_outputs.json").read_text(encoding="utf-8"))["request"]
DEFAULT = dict(event_type="Wedding", event_date="2026-11-16", start_time="10:00", end_time="18:00", guest_count=50, budget_lkr=1_000_000, top_k=3)
SCENARIOS = [("saved_philadelphia_exact", SAVED)]
VARIATIONS = [
    ("arabi_three_services", "Arabi", "LA", 150, 1_000_000, ["Decoration","Catering","Entertainment"], "Wedding"),
    ("arabi_catering_50", "Arabi", "LA", 50, 1_000_000, ["Catering"], "Wedding"),
    ("arabi_catering_150_higher_budget", "Arabi", "LA", 150, 2_000_000, ["Catering"], "Wedding"),
    ("philadelphia_catering_decor_150", "Philadelphia", "PA", 150, 1_000_000, ["Catering","Decoration"], "Wedding"),
    ("philadelphia_photo_decor_low_budget", "Philadelphia", "PA", 50, 250_000, ["Photography","Decoration"], "Wedding"),
    ("philadelphia_photo_decor_mid_budget", "Philadelphia", "PA", 50, 500_000, ["Photography","Decoration"], "Wedding"),
    ("philadelphia_birthday_decor_entertainment", "Philadelphia", "PA", 30, 1_000_000, ["Decoration","Entertainment"], "Birthday"),
    ("philadelphia_corporate_av_photo", "Philadelphia", "PA", 50, 1_000_000, ["Audio Visual","Photography"], "Corporate"),
    ("philadelphia_corporate_large_catering_av", "Philadelphia", "PA", 500, 1_000_000, ["Catering","Audio Visual"], "Corporate"),
    ("nashville_wedding_decor_photo", "Nashville", "TN", 50, 1_000_000, ["Decoration","Photography"], "Wedding"),
    ("nashville_large_catering_entertainment", "Nashville", "TN", 200, 1_000_000, ["Catering","Entertainment"], "Wedding"),
    ("tampa_wedding_av_decor", "Tampa", "FL", 50, 1_000_000, ["Audio Visual","Decoration"], "Wedding"),
    ("new_orleans_catering_entertainment", "New Orleans", "LA", 50, 1_000_000, ["Catering","Entertainment"], "Wedding"),
    ("bensalem_catering_entertainment", "Bensalem", "PA", 50, 1_000_000, ["Catering","Entertainment"], "Wedding"),
    ("belleville_three_services_150", "Belleville", "IL", 150, 1_000_000, ["Decoration","Catering","Entertainment"], "Wedding"),
    ("boise_equipment_photography", "Boise", "ID", 50, 1_000_000, ["Equipment Rental","Photography"], "Wedding"),
    ("indianapolis_catering_planning", "Indianapolis", "IN", 50, 1_000_000, ["Catering","Event Planning"], "Wedding"),
    ("berlin_birthday_decor_photo", "Berlin", "NJ", 50, 750_000, ["Decoration","Photography"], "Birthday"),
    ("blackwood_corporate_av_decor", "Blackwood", "NJ", 50, 1_000_000, ["Audio Visual","Decoration"], "Corporate"),
    ("philadelphia_five_services_2m", "Philadelphia", "PA", 50, 2_000_000, ["Audio Visual","Catering","Photography","Decoration","Entertainment"], "Wedding"),
    ("philadelphia_five_services_3m_100", "Philadelphia", "PA", 100, 3_000_000, ["Audio Visual","Catering","Photography","Decoration","Entertainment"], "Wedding"),
    ("tampa_birthday_catering_tight_budget", "Tampa", "FL", 20, 100_000, ["Catering"], "Birthday"),
]
for label, city, state, guests, budget, services, kind in VARIATIONS:
    request = dict(DEFAULT, city=city, state=state, guest_count=guests, budget_lkr=budget, required_services=services, event_type=kind)
    SCENARIOS.append((label, request))
if len(SCENARIOS) < 21:
    raise RuntimeError("Fewer than 20 additional scenarios")

# The same source file and filters used by the backend, read in bounded chunks.
source_counts = {}
for frame in pd.read_csv(ROOT / "hybrid_simulation_v1/synthetic_service_options.csv", usecols=["service_category"], chunksize=10_000):
    for name, count in frame["service_category"].value_counts().items():
        source_counts[name] = source_counts.get(name, 0) + int(count)
stage = {(label, service): dict(scenario_id=label, service=service, source_rows=source_counts.get(service,0), location_rows=0, event_type_rows=0, capacity_eligible_rows=0, priceable_rows=0, individually_affordable_rows=0) for label, req in SCENARIOS for service in req["required_services"]}
usecols = ["service_option_id","business_id","service_category","simulated_service_city","simulated_service_state","supported_event_types","max_guests","unit_price","pricing_basis","min_billable_guests","min_billable_hours","guest_capacity_applicability","data_origin"]
for frame in pd.read_csv(ROOT / "hybrid_simulation_v1/synthetic_service_options.csv", usecols=usecols, chunksize=10_000):
    frame["unit_price_lkr"] = (frame["unit_price"] * 330.777).round(2)
    norm_city = frame["simulated_service_city"].astype(str).str.strip().str.casefold()
    norm_state = frame["simulated_service_state"].astype(str).str.strip().str.casefold()
    for label, req in SCENARIOS:
        local = frame.loc[norm_city.eq(req["city"].strip().casefold()) & norm_state.eq(req["state"].strip().casefold())]
        if local.empty:
            continue
        for service in req["required_services"]:
            row = stage[(label, service)]
            group = local.loc[local["service_category"].eq(service)]
            row["location_rows"] += len(group)
            if group.empty:
                continue
            event_group = group.loc[group["supported_event_types"].fillna("").map(lambda value: req["event_type"].casefold() in [x.strip().casefold() for x in str(value).split(";")])]
            row["event_type_rows"] += len(event_group)
            eligible = event_group if service != "Catering" else event_group.loc[event_group["max_guests"].ge(req["guest_count"])]
            row["capacity_eligible_rows"] += len(eligible)
            for option in eligible.to_dict("records"):
                result = validate_service_option_lkr(option, guest_count=req["guest_count"], duration_hours=8, budget_lkr=req["budget_lkr"])
                cost = result.get("estimated_cost_lkr")
                if cost is not None and math.isfinite(float(cost)) and result.get("capacity_status") != "Fail":
                    row["priceable_rows"] += 1
                    if cost <= req["budget_lkr"]:
                        row["individually_affordable_rows"] += 1
with (OUT / "candidate_filter_stages.csv").open("w", newline="", encoding="utf-8") as stream:
    writer = csv.DictWriter(stream, fieldnames=list(next(iter(stage.values()))))
    writer.writeheader()
    writer.writerows(stage.values())
print("offline filter stages measured", len(stage), flush=True)

rows = []
endpoint = "http://127.0.0.1:8000/api/packages/generate-dynamic"
with httpx.Client(timeout=120) as client, (OUT / "api_response_evidence.jsonl").open("w", encoding="utf-8") as evidence:
    for index, (label, request) in enumerate(SCENARIOS, 1):
        started = time.perf_counter()
        try:
            response = client.post(endpoint, json=request)
            elapsed = round((time.perf_counter() - started) * 1000, 2)
            data = response.json()
            generation = data.get("generation", {}) if isinstance(data, dict) else {}
            diagnostic = data.get("diagnostics") or {} if isinstance(data, dict) else {}
            search = generation.get("search") or {}
            counts = data.get("candidate_counts") or generation.get("candidate_counts") or {}
            reasons = diagnostic.get("reasons") or []
            evidence.write(json.dumps(dict(scenario_id=label, request=request, http_status=response.status_code, elapsed_ms=elapsed, response=data), ensure_ascii=False) + "\n")
            row = dict(scenario_id=label, input_json=json.dumps(request, sort_keys=True), http_status=response.status_code, runtime_ms=elapsed, event_id=data.get("event_id", ""), package_count=len(generation.get("packages") or []), generation_status=generation.get("status", ""), eligible_candidate_counts_json=json.dumps(counts, sort_keys=True), selected_candidate_counts_json=json.dumps(generation.get("selected_candidate_counts") or {}, sort_keys=True), failure_diagnostics_json=json.dumps(reasons, sort_keys=True), missing_services_json=json.dumps(generation.get("missing_services") or []), search_limit_status="candidate" if search.get("candidate_limit_reached") else ("node" if search.get("node_limit_reached") else "none"), nodes_visited=search.get("nodes_visited", ""), combinations_evaluated=search.get("combinations_evaluated", ""), error="" if response.status_code == 200 else str(data.get("detail", data))[:500])
        except Exception as exc:
            elapsed = round((time.perf_counter() - started) * 1000, 2)
            row = dict(scenario_id=label, input_json=json.dumps(request, sort_keys=True), http_status="", runtime_ms=elapsed, event_id="", package_count="", generation_status="", eligible_candidate_counts_json="", selected_candidate_counts_json="", failure_diagnostics_json="", missing_services_json="", search_limit_status="", nodes_visited="", combinations_evaluated="", error=repr(exc))
            evidence.write(json.dumps(dict(scenario_id=label, request=request, elapsed_ms=elapsed, error=repr(exc))) + "\n")
        rows.append(row)
        with (OUT / "package_generation_test_results.csv").open("w", newline="", encoding="utf-8") as stream:
            writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
            writer.writeheader()
            writer.writerows(rows)
        evidence.flush()
        print(f"{index}/{len(SCENARIOS)} {label} HTTP={row['http_status']} packages={row['package_count']} status={row['generation_status']} ms={elapsed}", flush=True)