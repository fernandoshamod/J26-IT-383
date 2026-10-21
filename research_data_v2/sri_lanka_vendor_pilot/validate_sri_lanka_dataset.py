"""Validate the isolated Sri Lankan vendor pilot without editing input data."""
from __future__ import annotations

import argparse
import csv
import json
import math
import re
import sys
import unicodedata
from collections import Counter
from datetime import datetime
from pathlib import Path
from urllib.parse import urlparse

COLUMNS = (
    "vendor_id", "vendor_name", "service_category", "city", "district",
    "province", "country", "rating", "review_count", "mean_review_rating",
    "rating_std", "collected_review_count", "price_lkr", "guest_capacity",
    "service_area", "availability_status", "source_name", "source_url",
    "collected_at", "verification_status", "data_type",
)
CATEGORIES = ("Photography", "Decoration", "Catering", "Entertainment", "Audio Visual")
REQUIRED = (
    "vendor_id", "vendor_name", "service_category", "country", "source_name",
    "source_url", "collected_at", "verification_status", "data_type",
)
DATA_TYPES = {"licensed_open_data", "vendor_submitted", "permission_based_export", "synthetic"}
VERIFICATION = {"unverified", "vendor_confirmed", "source_confirmed"}

def normalize(value: str) -> str:
    return " ".join(unicodedata.normalize("NFKC", value).casefold().split())

def validate(path: Path) -> dict:
    errors, warnings = [], []
    counts, missing = Counter(), Counter()
    seen_ids, seen_names = {}, {}
    rows = real_rows = 0
    try:
        handle = path.open("r", encoding="utf-8-sig", newline="")
    except OSError as exc:
        return {"status": "FAIL", "rows": 0, "declared_real_rows": 0,
                "category_counts": {}, "missing_field_counts": {},
                "errors": [str(exc)], "warnings": []}
    with handle:
        reader = csv.DictReader(handle)
        if reader.fieldnames is None:
            errors.append("CSV is empty; the exact header is required")
        elif tuple(reader.fieldnames) != COLUMNS:
            errors.append(f"CSV header differs from required columns and order: {reader.fieldnames!r}")
        if reader.fieldnames is not None:
            try:
                for line_number, raw in enumerate(reader, start=2):
                    rows += 1
                    row = {key: (raw.get(key) or "").strip() for key in COLUMNS}
                    if None in raw or any(raw.get(key) is None for key in COLUMNS):
                        errors.append(f"line {line_number}: wrong number of CSV fields")
                    for field in COLUMNS:
                        if not row[field]:
                            missing[field] += 1
                    for field in REQUIRED:
                        if not row[field]:
                            errors.append(f"line {line_number}: missing required {field}")
                    category = row["service_category"]
                    if category:
                        counts[category] += 1
                        if category not in CATEGORIES:
                            errors.append(f"line {line_number}: invalid service_category {category!r}")
                    for field, seen in (("vendor_id", seen_ids), ("vendor_name", seen_names)):
                        value = normalize(row[field])
                        if value and value in seen:
                            errors.append(f"line {line_number}: duplicate {field} (first on line {seen[value]})")
                        elif value:
                            seen[value] = line_number
                    if row["country"] and normalize(row["country"]) not in {"sri lanka", "lk"}:
                        errors.append(f"line {line_number}: country must be Sri Lanka or LK")
                    if not row["city"]:
                        warnings.append(f"line {line_number}: city unknown; location filtering unavailable")
                    if bool(row["district"]) != bool(row["province"]):
                        warnings.append(f"line {line_number}: district/province pair incomplete; verify location")
                    if normalize(row["service_area"]) == "unknown":
                        warnings.append(f"line {line_number}: use blank for unknown service_area")
                    for field in ("rating", "mean_review_rating", "rating_std", "price_lkr"):
                        if not row[field]:
                            continue
                        try:
                            number = float(row[field])
                        except ValueError:
                            errors.append(f"line {line_number}: {field} is not numeric")
                            continue
                        if not math.isfinite(number):
                            errors.append(f"line {line_number}: {field} must be finite")
                        elif field in {"rating", "mean_review_rating", "rating_std"} and not 0 <= number <= 5:
                            errors.append(f"line {line_number}: {field} outside 0..5")
                        elif field == "price_lkr" and number <= 0:
                            errors.append(f"line {line_number}: price_lkr must be positive")
                    for field in ("review_count", "collected_review_count", "guest_capacity"):
                        if not row[field]:
                            continue
                        if not re.fullmatch(r"[0-9]+", row[field]):
                            errors.append(f"line {line_number}: {field} must be a nonnegative integer")
                        elif field == "guest_capacity" and int(row[field]) == 0:
                            errors.append(f"line {line_number}: guest_capacity must be positive")
                    if (row["mean_review_rating"] or row["rating_std"]) and not row["collected_review_count"]:
                        warnings.append(f"line {line_number}: review statistics lack collected_review_count")
                    if row["availability_status"]:
                        warnings.append(f"line {line_number}: availability needs event-date evidence; this schema has no date-specific verification field")
                    if row["data_type"]:
                        if row["data_type"] not in DATA_TYPES:
                            errors.append(f"line {line_number}: invalid data_type {row['data_type']!r}")
                        elif row["data_type"] != "synthetic":
                            real_rows += 1
                        else:
                            warnings.append(f"line {line_number}: synthetic record excluded from collected count")
                    if row["verification_status"] and row["verification_status"] not in VERIFICATION:
                        errors.append(f"line {line_number}: invalid verification_status {row['verification_status']!r}")
                    if row["source_url"]:
                        parsed = urlparse(row["source_url"])
                        if parsed.scheme != "https" or not parsed.netloc:
                            errors.append(f"line {line_number}: source_url must be an absolute HTTPS URL")
                        elif row["source_name"] == "OpenStreetMap" and not re.fullmatch(
                            r"(www\.)?openstreetmap\.org", parsed.netloc.casefold()
                        ):
                            errors.append(f"line {line_number}: OpenStreetMap source URL host mismatch")
                    if row["collected_at"]:
                        try:
                            stamp = datetime.fromisoformat(row["collected_at"].replace("Z", "+00:00"))
                            if stamp.tzinfo is None:
                                warnings.append(f"line {line_number}: collected_at has no timezone")
                        except ValueError:
                            errors.append(f"line {line_number}: collected_at must be ISO 8601")
            except csv.Error as exc:
                errors.append(f"CSV parse error: {exc}")
    status = "FAIL" if errors else "TEMPLATE_ONLY" if rows == 0 else (
        "VALID_WITH_WARNINGS" if warnings else "VALID"
    )
    return {
        "status": status, "rows": rows, "declared_real_rows": real_rows,
        "category_counts": {category: counts.get(category, 0) for category in CATEGORIES},
        "missing_field_counts": dict(sorted(missing.items())),
        "errors": errors, "warnings": warnings,
    }

def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("csv_path", nargs="?", type=Path,
                        default=Path(__file__).with_name("sri_lanka_vendor_profiles.csv"))
    result = validate(parser.parse_args().csv_path)
    print(json.dumps(result, indent=2, ensure_ascii=False))
    return 1 if result["status"] == "FAIL" else 0

if __name__ == "__main__":
    sys.exit(main())


