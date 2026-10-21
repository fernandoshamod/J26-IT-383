"""Read-only, chunked inventory and quality audit of existing PlanoVision data."""
import csv
import json
import math
from collections import Counter, defaultdict
from pathlib import Path

import pandas as pd

from backend.engine.risk_signals import FEATURES, MODEL_SHA256, verified_model

ROOT = Path(__file__).resolve().parents[2]
OUT = Path(__file__).resolve().parent
SEARCH_DIRS = ["hybrid_simulation_v1", "research_data_v2", "data", "dataset"]
LIVE = {
    "hybrid_simulation_v1/synthetic_service_options.csv": "dynamic API",
    "hybrid_simulation_v1/real_vendor_profiles.csv": "dynamic API",
    "models/vendor_risk_random_forest.pkl": "dynamic API model",
    "vendor_compatibility_matrix.csv": "dynamic API",
    "hybrid_simulation_v1/synthetic_event_requirements.csv": "sample-event API",
    "hybrid_simulation_v1/synthetic_availability.csv": "feasibility API",
    "hybrid_simulation_v1/synthetic_collaboration_scenarios.csv": "feasibility API",
}
csv.field_size_limit(10_000_000)


def save_csv(name, rows, fields):
    with (OUT / name).open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def chunks(path):
    return pd.read_csv(path, dtype=str, chunksize=10_000, keep_default_na=False)


def missing(value):
    return value is None or str(value).strip() == "" or str(value).strip().casefold() in {"nan", "null", "none"}


inventory = []
for directory in SEARCH_DIRS:
    base = ROOT / directory
    if not base.exists():
        inventory.append(dict(path=directory, format="absent", size_bytes=0, rows="", columns="", schema="", backend_role="not used"))
        continue
    for path in sorted(base.rglob("*")):
        if not path.is_file() or path.suffix.casefold() not in {".csv", ".json"}:
            continue
        relative = path.relative_to(ROOT).as_posix()
        if OUT in path.parents:
            continue
        size = path.stat().st_size
        if path.suffix.casefold() == ".csv":
            with path.open(newline="", encoding="utf-8-sig", errors="replace") as stream:
                reader = csv.reader(stream)
                header = next(reader, [])
                count = sum(1 for _ in reader)
            schema = "|".join(header)
        else:
            with path.open(encoding="utf-8-sig", errors="replace") as stream:
                obj = json.load(stream)
            count = len(obj) if isinstance(obj, (dict, list)) else 1
            schema = "|".join(obj.keys()) if isinstance(obj, dict) else (",".join(obj[0].keys()) if obj and isinstance(obj[0], dict) else type(obj).__name__)
        inventory.append(dict(path=relative, format=path.suffix[1:], size_bytes=size, rows=count, columns=len(schema.split("|")) if schema else 0, schema=schema, backend_role=LIVE.get(relative, "not used by live backend")))
for relative, role in LIVE.items():
    if relative not in {item["path"] for item in inventory}:
        path = ROOT / relative
        inventory.append(dict(path=relative, format=path.suffix[1:], size_bytes=path.stat().st_size, rows="", columns="", schema="binary model" if path.suffix == ".pkl" else "", backend_role=role))
save_csv("dataset_inventory.csv", inventory, ["path", "format", "size_bytes", "rows", "columns", "schema", "backend_role"])
print("inventory", len(inventory), flush=True)

quality = []
def q(file, check, field, affected, total, detail=""):
    quality.append(dict(file=file, check=check, field=field, affected_count=affected, total_rows=total, detail=detail))

tables = {}
for relative in [name for name in LIVE if name.endswith(".csv")]:
    path = ROOT / relative
    nulls = Counter()
    counts = Counter()
    rows = 0
    collected = []
    for frame in chunks(path):
        rows += len(frame)
        collected.append(frame)
        for col in frame.columns:
            nulls[col] += int(frame[col].map(missing).sum())
            counts[col] += len(frame)
    table = pd.concat(collected, ignore_index=True)
    tables[relative] = table
    for col in table.columns:
        if nulls[col]:
            q(relative, "missing_value", col, nulls[col], rows, "Blank or null-like string; some blanks are structurally expected")
    q(relative, "row_count", "*", rows, rows)
options = tables["hybrid_simulation_v1/synthetic_service_options.csv"]
profiles = tables["hybrid_simulation_v1/real_vendor_profiles.csv"]
events = tables["hybrid_simulation_v1/synthetic_event_requirements.csv"]
availability = tables["hybrid_simulation_v1/synthetic_availability.csv"]
collaboration = tables["hybrid_simulation_v1/synthetic_collaboration_scenarios.csv"]
compat = tables["vendor_compatibility_matrix.csv"]

for relative, table, key in [
    ("hybrid_simulation_v1/real_vendor_profiles.csv", profiles, "business_id"),
    ("hybrid_simulation_v1/synthetic_service_options.csv", options, "service_option_id"),
    ("hybrid_simulation_v1/synthetic_event_requirements.csv", events, "event_id"),
    ("hybrid_simulation_v1/synthetic_collaboration_scenarios.csv", collaboration, "simulated_collaboration_id"),
]:
    q(relative, "duplicate_primary_id_rows", key, int(table[key].duplicated(keep=False).sum()), len(table))
q("hybrid_simulation_v1/synthetic_service_options.csv", "repeated_vendor_ids_expected", "business_id", int(options["business_id"].duplicated(keep=False).sum()), len(options), "Multiple option tiers per vendor are intentional; distinct option IDs are the key")
profile_ids = set(profiles["business_id"])
event_ids = set(events["event_id"])
q("hybrid_simulation_v1/synthetic_service_options.csv", "vendor_id_without_profile", "business_id", int((~options["business_id"].isin(profile_ids)).sum()), len(options))
q("hybrid_simulation_v1/synthetic_availability.csv", "event_id_without_sample_event", "event_id", int((~availability["event_id"].isin(event_ids)).sum()), len(availability))
q("hybrid_simulation_v1/synthetic_availability.csv", "vendor_id_without_profile", "business_id", int((~availability["business_id"].isin(profile_ids)).sum()), len(availability))
q("hybrid_simulation_v1/synthetic_collaboration_scenarios.csv", "event_id_without_sample_event", "event_id", int((~collaboration["event_id"].isin(event_ids)).sum()), len(collaboration))
for field in ["vendor_a_id", "vendor_b_id"]:
    q("hybrid_simulation_v1/synthetic_collaboration_scenarios.csv", "vendor_id_without_profile", field, int((~collaboration[field].isin(profile_ids)).sum()), len(collaboration))
for relative, table, fields in [
    ("hybrid_simulation_v1/synthetic_service_options.csv", options, ["unit_price", "min_billable_guests", "max_guests", "min_billable_hours"]),
    ("hybrid_simulation_v1/real_vendor_profiles.csv", profiles, [*FEATURES, "risk_score"]),
    ("hybrid_simulation_v1/synthetic_event_requirements.csv", events, ["guest_count", "budget", "duration_hours"]),
    ("vendor_compatibility_matrix.csv", compat, ["base_score"]),
]:
    for field in fields:
        series = table[field]
        present = ~series.map(missing)
        numeric = pd.to_numeric(series[present], errors="coerce")
        invalid = int((~numeric.map(math.isfinite)).sum())
        q(relative, "invalid_numeric_nonblank", field, invalid, len(table))
        if field in {"unit_price", "guest_count", "budget"}:
            q(relative, "nonpositive_numeric", field, int((numeric <= 0).sum()), len(table))
q("hybrid_simulation_v1/synthetic_service_options.csv", "unknown_pricing_basis", "pricing_basis", int((~options["pricing_basis"].isin(["per_person", "fixed_package", "per_hour"])).sum()), len(options))
q("hybrid_simulation_v1/synthetic_service_options.csv", "non_USD_currency", "currency", int((options["currency"] != "USD").sum()), len(options))
q("hybrid_simulation_v1/real_vendor_profiles.csv", "incomplete_five_model_features", "|".join(FEATURES), int(profiles[list(FEATURES)].apply(lambda row: any(missing(v) for v in row), axis=1).sum()), len(profiles))
option_profile = options[["service_option_id", "business_id", "service_category"]].merge(profiles[["business_id", "service_categories", "matched_categories"]], on="business_id", how="left")
service_mismatch = option_profile.apply(lambda row: row["service_category"] not in {part.strip() for part in str(row["service_categories"]).split(";")}, axis=1)
q("hybrid_simulation_v1/synthetic_service_options.csv", "option_category_not_in_profile_service_categories", "service_category", int(service_mismatch.sum()), len(options), "Profile category mapping is Yelp-derived/heuristic, not verified offering")
save_csv("data_quality_report.csv", quality, ["file", "check", "field", "affected_count", "total_rows", "detail"])

service_counts = options.groupby("service_category").agg(option_rows=("service_option_id", "size"), unique_vendors=("business_id", "nunique"), cities=("simulated_service_city", "nunique")).reset_index()
service_counts.to_csv(OUT / "service_coverage.csv", index=False)
locations = options.groupby(["simulated_service_city", "simulated_service_state"]).agg(option_rows=("service_option_id", "size"), unique_vendors=("business_id", "nunique"), category_count=("service_category", "nunique")).reset_index()
service_names = sorted(options["service_category"].unique())
matrix = pd.crosstab(index=[options["simulated_service_city"], options["simulated_service_state"]], columns=options["service_category"]).reset_index()
locations = locations.merge(matrix, on=["simulated_service_city", "simulated_service_state"], how="left")
locations["supports_at_least_3_of_7"] = locations["category_count"] >= 3
locations["supports_at_least_5_of_7"] = locations["category_count"] >= 5
locations["supports_all_7"] = locations["category_count"] == len(service_names)
locations.to_csv(OUT / "location_coverage.csv", index=False)

option_cost = pd.to_numeric(options["unit_price"], errors="coerce") * 330.777
guests = 50
hours = 8
basis = options["pricing_basis"]
min_guests = pd.to_numeric(options["min_billable_guests"], errors="coerce").fillna(guests)
min_hours = pd.to_numeric(options["min_billable_hours"], errors="coerce").fillna(hours)
option_cost = option_cost.where(basis == "fixed_package", option_cost * min_guests.clip(lower=guests))
option_cost = option_cost.where(basis != "per_hour", pd.to_numeric(options["unit_price"], errors="coerce") * 330.777 * min_hours.clip(lower=hours))
options["_estimated_cost_50_8_lkr"] = option_cost
options["_max_guests_numeric"] = pd.to_numeric(options["max_guests"], errors="coerce")
budget_rows = []
for service, group in options.groupby("service_category"):
    costs = group["_estimated_cost_50_8_lkr"].dropna()
    capacities = group["_max_guests_numeric"].dropna()
    budget_rows.append(dict(service_category=service, option_rows=len(group), pricing_basis_counts=json.dumps(group["pricing_basis"].value_counts().to_dict()), cost_lkr_p10_50guests_8h=round(costs.quantile(.1),2), cost_lkr_median_50guests_8h=round(costs.median(),2), cost_lkr_p90_50guests_8h=round(costs.quantile(.9),2), options_under_1m_50guests_8h=int((costs <= 1_000_000).sum()), capacity_rows=len(capacities), capacity_median=round(capacities.median(),2) if len(capacities) else "", capacity_p10=round(capacities.quantile(.1),2) if len(capacities) else "", capacity_p90=round(capacities.quantile(.9),2) if len(capacities) else "", capacity_below_150=int((capacities < 150).sum()), capacity_rule_applicable_rows=int((group["guest_capacity_applicability"] == "simulated_catering_limit").sum())))
save_csv("budget_capacity_analysis.csv", budget_rows, list(budget_rows[0]))

from backend.engine import risk_signals
model = verified_model()
feature_values = profiles[list(FEATURES)].apply(pd.to_numeric, errors="coerce")
complete = feature_values.notna().all(axis=1) & feature_values.apply(lambda col: col.map(math.isfinite)).all(axis=1)
samples = model.predict(feature_values.loc[complete].head(5)) if complete.any() else []
metrics = {
    "inventory_files": len(inventory),
    "live_files": list(LIVE),
    "profile_rows": len(profiles),
    "option_rows": len(options),
    "service_names": service_names,
    "location_count": len(locations),
    "cities_at_least_3": int(locations["supports_at_least_3_of_7"].sum()),
    "cities_at_least_5": int(locations["supports_at_least_5_of_7"].sum()),
    "cities_all_7": int(locations["supports_all_7"].sum()),
    "model_hash_expected": MODEL_SHA256,
    "model_loaded": True,
    "model_features": list(FEATURES),
    "feature_complete_profiles": int(complete.sum()),
    "feature_incomplete_profiles": int((~complete).sum()),
    "sample_predictions": list(map(str, samples)),
    "rule_derived_labels": profiles["risk_level"].value_counts().to_dict(),
    "availability_rows": len(availability),
    "availability_event_id_prefixes": availability["event_id"].str.split("-").str[0].value_counts().to_dict(),
    "availability_statuses": availability["availability_status"].value_counts().to_dict(),
    "availability_date_min": availability["event_date"].min(),
    "availability_date_max": availability["event_date"].max(),
    "availability_interval_top": availability.groupby(["checked_interval_start","checked_interval_end"]).size().sort_values(ascending=False).head(5).rename_axis(["start","end"]).reset_index(name="rows").to_dict("records"),
    "collaboration_rows": len(collaboration),
    "synthetic_option_origin_counts": options["data_origin"].value_counts().to_dict(),
    "profile_source_categories": profiles["service_categories"].value_counts().to_dict(),
}
(OUT / "audit_metrics.json").write_text(json.dumps(metrics, indent=2), encoding="utf-8")
print("analysis complete", json.dumps({k: metrics[k] for k in ["profile_rows","option_rows","location_count","cities_at_least_3","cities_at_least_5","cities_all_7","feature_incomplete_profiles"]}), flush=True)