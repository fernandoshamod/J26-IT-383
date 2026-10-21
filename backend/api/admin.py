"""Read-only data endpoints for the academic Admin Workspace."""
import json
from functools import lru_cache
from pathlib import Path
from typing import Any

import pandas as pd
from fastapi import APIRouter, Query

from backend.db import list_events
from backend.engine.package_data_loader import load_service_options

router = APIRouter(prefix="/api/admin", tags=["admin-demo"])
PROJECT_ROOT = Path(__file__).resolve().parents[2]
VENDOR_FILE = PROJECT_ROOT / "hybrid_simulation_v1" / "real_vendor_profiles.csv"
SUMMARY_FILE = PROJECT_ROOT / "research_evaluation" / "evaluation_summary.json"

@lru_cache(maxsize=1)
def _vendors() -> pd.DataFrame:
    return pd.read_csv(VENDOR_FILE).fillna("")

@lru_cache(maxsize=1)
def _options() -> pd.DataFrame:
    return load_service_options().fillna("")

@lru_cache(maxsize=1)
def _evaluation() -> dict[str, Any]:
    with SUMMARY_FILE.open(encoding="utf-8") as handle:
        return json.load(handle)

def _page(frame: pd.DataFrame, page: int, page_size: int) -> dict[str, Any]:
    total = len(frame)
    start = (page - 1) * page_size
    return {"items": frame.iloc[start:start + page_size].to_dict(orient="records"), "page": page,
            "page_size": page_size, "total": total, "total_pages": max(1, (total + page_size - 1) // page_size)}

@router.get("/summary")
def admin_summary() -> dict[str, Any]:
    vendors, options = _vendors(), _options()
    evaluation = _evaluation()
    metrics, model = evaluation.get("metrics", {}), evaluation.get("model_evaluation", {})
    categories = sorted({item.strip() for value in options["service_category"].tolist()
                         for item in str(value).split(";",) if item.strip()})
    return {"vendor_profiles": len(vendors), "service_options": len(options), "saved_events": len(list_events()),
            "service_categories": categories,
            "data_labels": {"vendor_profiles": "historical research profile dataset", "service_options": "synthetic simulation data",
                            "saved_events": "operational SQLite records", "model": "verified research evaluation artifact"},
            "model": {"accuracy": model.get("accuracy"), "macro_f1": model.get("macro_f1"), "test_count": model.get("test_count"),
                      "features": model.get("features", []), "classes": model.get("classes", []), "class_support": model.get("class_support", {}),
                      "labels": model.get("labels"), "independent_real_world_validation": model.get("independent_real_world_validation"),
                      "events_evaluated": metrics.get("events_evaluated"), "recommendation_yield_rate": metrics.get("recommendation_yield_rate")},
            "authentication": {"enabled": False, "notice": "Academic administration demo; not a secured production admin portal."}}

@router.get("/vendors")
def admin_vendors(search: str = "", service: str = "", location: str = "", page: int = Query(1, ge=1), page_size: int = Query(25, ge=1, le=100)) -> dict[str, Any]:
    frame = _vendors()
    combined = frame[["name", "city", "state", "service_categories"]].astype(str).agg(" ".join, axis=1).str.lower()
    if search.strip(): frame = frame[combined.str.contains(search.strip().lower(), regex=False)]
    if service.strip(): frame = frame[frame["service_categories"].astype(str).str.contains(service.strip(), case=False, regex=False)]
    if location.strip(): frame = frame[(frame["city"].astype(str) + " " + frame["state"].astype(str)).str.contains(location.strip(), case=False, regex=False)]
    fields = ["business_id", "name", "service_categories", "city", "state", "stars", "review_count", "risk_level", "risk_score", "vendor_rank"]
    response = _page(frame[fields], page, page_size)
    response["categories"] = sorted({item.strip() for value in _vendors()["service_categories"].astype(str) for item in value.split(";") if item.strip()})
    return response

@router.get("/service-options")
def admin_service_options(category: str = "", location: str = "", page: int = Query(1, ge=1), page_size: int = Query(25, ge=1, le=100)) -> dict[str, Any]:
    frame = _options()
    if category.strip(): frame = frame[frame["service_category"].astype(str).str.contains(category.strip(), case=False, regex=False)]
    if location.strip():
        city_state = frame["simulated_service_city"].astype(str) + " " + frame["simulated_service_state"].astype(str)
        frame = frame[city_state.str.contains(location.strip(), case=False, regex=False)]
    fields = ["service_option_id", "business_id", "service_category", "option_tier", "supported_event_types", "unit_price_lkr", "pricing_basis",
              "min_billable_guests", "max_guests", "simulated_service_city", "simulated_service_state", "data_origin", "is_vendor_confirmed"]
    response = _page(frame[fields], page, page_size)
    response["categories"] = sorted(str(value) for value in _options()["service_category"].unique() if str(value).strip())
    response["locations"] = sorted({f"{city}, {state}" for city, state in zip(_options()["simulated_service_city"], _options()["simulated_service_state"]) if str(city).strip()})
    return response


