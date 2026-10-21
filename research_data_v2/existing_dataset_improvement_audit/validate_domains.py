"""Read-only range and domain checks for live model inputs and option rules."""
import csv
from pathlib import Path
import pandas as pd

root = Path(__file__).resolve().parents[2]
out = Path(__file__).resolve().parent
rows = []
def add(file, check, field, affected, total, detail=""):
    rows.append(dict(file=file,check=check,field=field,affected_count=int(affected),total_rows=int(total),detail=detail))
profile = "hybrid_simulation_v1/real_vendor_profiles.csv"
checks = {
    "stars": lambda s: (s < 1) | (s > 5),
    "review_count": lambda s: s < 0,
    "collected_review_count": lambda s: s < 0,
    "mean_review_rating": lambda s: (s < 1) | (s > 5),
    "rating_std": lambda s: s < 0,
    "risk_score": lambda s: (s < 0) | (s > 100),
}
total = 0
counts = {name: 0 for name in checks}
for frame in pd.read_csv(root / profile, usecols=list(checks), chunksize=10_000):
    total += len(frame)
    for name, fn in checks.items():
        counts[name] += int(fn(pd.to_numeric(frame[name],errors="coerce")).sum())
for name, count in counts.items():
    add(profile,"out_of_domain_numeric",name,count,total)
option = "hybrid_simulation_v1/synthetic_service_options.csv"
total = invalid_capacity = invalid_event_types = 0
for frame in pd.read_csv(root / option, usecols=["min_billable_guests","max_guests","supported_event_types","pricing_basis"],chunksize=10_000):
    total += len(frame)
    mask = frame["pricing_basis"].eq("per_person")
    invalid_capacity += int((frame.loc[mask,"max_guests"] < frame.loc[mask,"min_billable_guests"]).sum())
    allowed = {"wedding","birthday","corporate"}
    invalid_event_types += int(frame["supported_event_types"].fillna("").map(lambda value: not {part.strip().casefold() for part in str(value).split(";")} <= allowed).sum())
add(option,"max_capacity_below_minimum_billable","max_guests|min_billable_guests",invalid_capacity,total)
add(option,"unsupported_event_type_token","supported_event_types",invalid_event_types,total)
with (out / "data_quality_report.csv").open("a",newline="",encoding="utf-8") as stream:
    writer=csv.DictWriter(stream,fieldnames=["file","check","field","affected_count","total_rows","detail"])
    writer.writerows(rows)
print({row["field"]: row["affected_count"] for row in rows})