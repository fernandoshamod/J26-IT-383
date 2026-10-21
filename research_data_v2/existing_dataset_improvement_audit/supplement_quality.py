"""Append source-layer ID and normalized-location checks; production files stay read-only."""
import csv
from collections import Counter, defaultdict
from pathlib import Path
import pandas as pd

root = Path(__file__).resolve().parents[2]
out = Path(__file__).resolve().parent
rows = []
def add(file, check, field, affected, total, detail=""):
    rows.append(dict(file=file, check=check, field=field, affected_count=affected, total_rows=total, detail=detail))
for relative, key in [
    ("data/raw/vendor_recommendation_dataset_ids_repaired.csv", "business_id"),
    ("data/cleaned/vendor_profiles_missingness_checked.csv", "business_id"),
    ("data/cleaned/vendor_recommendation_ids_verified.csv", "business_id"),
    ("dataset/yelp_business_1000.csv", "business_id"),
    ("dataset/yelp_reviews_1000.csv", "review_id"),
]:
    counts = Counter()
    missing = 0
    total = 0
    for part in pd.read_csv(root / relative, usecols=[key], dtype=str, chunksize=10_000):
        total += len(part)
        values = part[key].fillna("").astype(str).str.strip()
        missing += int((values == "").sum())
        counts.update(values[values != ""])
    duplicates = sum(count for count in counts.values() if count > 1)
    add(relative, "duplicate_primary_id_rows", key, duplicates, total)
    add(relative, "missing_primary_id", key, missing, total)
# Raw Yelp business/review subsets may be independent samples, so this is a subset
# relationship check only and is not evidence of broken full-source lineage.
businesses = set()
for part in pd.read_csv(root / "dataset/yelp_business_1000.csv", usecols=["business_id"], dtype=str, chunksize=10_000):
    businesses.update(part["business_id"].dropna())
unmatched = total_reviews = 0
for part in pd.read_csv(root / "dataset/yelp_reviews_1000.csv", usecols=["business_id"], dtype=str, chunksize=10_000):
    total_reviews += len(part)
    unmatched += int((~part["business_id"].isin(businesses)).sum())
add("dataset/yelp_reviews_1000.csv", "business_id_absent_from_1000_business_sample", "business_id", unmatched, total_reviews, "Independent small samples; not a live-backend foreign-key failure")
location_file = root / "hybrid_simulation_v1/synthetic_service_options.csv"
raw = set()
norm = defaultdict(set)
for part in pd.read_csv(location_file, usecols=["simulated_service_city","simulated_service_state"], dtype=str, chunksize=10_000):
    for city, state in zip(part["simulated_service_city"], part["simulated_service_state"]):
        raw.add((city, state))
        norm[(city.strip().casefold(), state.strip().casefold())].add((city, state))
variant_rows = sum(len(forms) for forms in norm.values() if len(forms) > 1)
add("hybrid_simulation_v1/synthetic_service_options.csv", "raw_location_pairs", "city|state", len(raw), len(raw))
add("hybrid_simulation_v1/synthetic_service_options.csv", "normalized_location_pairs", "city|state", len(norm), len(raw), "Same casefold/strip normalization as candidate selection")
add("hybrid_simulation_v1/synthetic_service_options.csv", "location_labels_in_variant_groups", "city|state", variant_rows, len(raw), f"{sum(len(forms)>1 for forms in norm.values())} normalized locations have multiple raw labels")
with (out / "data_quality_report.csv").open("a", newline="", encoding="utf-8") as stream:
    writer = csv.DictWriter(stream, fieldnames=["file","check","field","affected_count","total_rows","detail"])
    writer.writerows(rows)
print("supplemental checks", len(rows))