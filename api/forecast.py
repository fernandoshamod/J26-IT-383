"""
ML forecasts for the demo day: the trained duration and late-vendor models
(scheduling_engine/duration_prediction.py, trained by
examples/train_prediction_models.py) applied to the dashboard's events.

Proposal Section 4.2.1: the gradient boosting model "supplies the duration
estimates the solver requires". Here that is literal: in "predicted" mode
the CP-SAT solver plans the day with these durations instead of the
planner's own guesses.

The event context (guest counts, venue, date) and the vendor profiles
(distance, past jobs, past lateness) below are DECLARED demo inputs, the
facts a planner would type in when booking. They are not measurements.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path

import pandas as pd

from scheduling_engine.duration_prediction import (
    EventContext,
    TrainedModel,
    VendorBooking,
    add_calendar_features,
    late_arrival_risk,
    predict_event_durations,
)
from scheduling_engine.models import Event, Schedule

MODEL_DIR = Path(__file__).resolve().parent.parent / "models"
EVENT_DATE = "2026-10-24"  # a Saturday in October (rainy month in Colombo)

CONTEXTS = {
    "wedding": EventContext(EVENT_DATE, "wedding", guest_count=250, venue_type="outdoor", crew_size=2),
    "corp_launch": EventContext(EVENT_DATE, "corporate", guest_count=120, venue_type="indoor", crew_size=2),
}
# Activity id -> the activity type the model was trained on. Activities
# with no trained type (the launch itself) keep the planner's duration:
# the model has never seen one, so it must not guess.
ACTIVITY_TYPES = {
    "venue_setup": "venue_setup", "decor": "decor", "sound_check": "sound_check",
    "catering_load_in": "catering_load_in", "guest_arrival": "guest_arrival", "ceremony": "ceremony",
    "photos": "photos", "dinner_service": "dinner_service", "speeches": "speeches",
    "entertainment": "entertainment", "strike": "strike", "corp_decor": "decor",
}
# Vendor resources and what the planner knows about each booking.
VENDOR_PROFILES = {
    "florist-1": dict(category="florist", vendor="Florist", distance_km=12.0, prior_jobs=40, prior_mean_lateness=3.1),
    "catering-1": dict(category="caterer", vendor="Caterer", distance_km=48.0, prior_jobs=35, prior_mean_lateness=19.4),
    "photographer-1": dict(category="photographer", vendor="Photographer", distance_km=25.0, prior_jobs=2,
                           prior_mean_lateness=None),
}
# What each vendor's experience means for the activities it delivers.
VENDOR_FOR_ACTIVITY = {"decor": "florist-1", "corp_decor": "florist-1", "catering_load_in": "catering-1",
                       "photos": "photographer-1"}
# Activities delivered by a vendor who isn't a scheduled resource in this
# demo (the band, the AV hire company): their experience is still booking
# information the planner has, and the model was trained with it present,
# so it is declared here rather than left missing.
OTHER_VENDOR_JOBS = {"entertainment": 60, "sound_check": 30}
CONTEXT_FEATURES = ["guest_count", "venue_type", "is_rainy_month", "crew_size", "vendor_prior_jobs",
                    "event_type", "is_weekend", "planned_start_hour"]
FEATURE_LABELS = {
    "guest_count": "guests", "venue_type": "venue", "is_rainy_month": "rainy month", "crew_size": "crew size",
    "vendor_prior_jobs": "vendor experience", "event_type": "event type", "is_weekend": "weekend",
    "planned_start_hour": "time of day",
}


@lru_cache(maxsize=1)
def models() -> tuple[TrainedModel, TrainedModel]:
    return TrainedModel.load(MODEL_DIR, "duration"), TrainedModel.load(MODEL_DIR, "lateness")


@lru_cache(maxsize=1)
def model_card() -> dict:
    d = json.loads((MODEL_DIR / "duration_meta.json").read_text())
    l = json.loads((MODEL_DIR / "lateness_meta.json").read_text())
    return dict(
        duration=dict(mae=d["test_metrics"]["XGBoost"]["MAE"],
                      planner_mae=d["test_metrics"]["B0 planner estimate (today's practice)"]["MAE"],
                      r2=d["test_metrics"]["XGBoost"]["R2"], params=d["best_params"], trees=d["n_trees"]),
        lateness=dict(auc=l["test_metrics"]["XGBoost"]["ROC_AUC"],
                      oracle_auc=l["test_metrics"].get("Oracle ceiling (knows hidden truth)", {}).get("ROC_AUC"),
                      params=l["best_params"], trees=l["n_trees"]),
    )


@dataclass
class Forecast:
    durations: list[dict] = field(default_factory=list)
    vendor_risk: list[dict] = field(default_factory=list)
    predicted: dict[str, int] = field(default_factory=dict)


def forecast(events: list[Event], planner_schedule: Schedule) -> Forecast:
    """Predict durations (with reasons) and vendor late-arrival risk.
    `planner_schedule` supplies each activity's planned hour of day."""
    duration_model, lateness_model = models()
    start_hours = {aid: s.start_minutes // 60 for aid, s in planner_schedule.activities.items()}
    vendor_jobs = {aid: VENDOR_PROFILES[rid]["prior_jobs"] for aid, rid in VENDOR_FOR_ACTIVITY.items()}
    vendor_jobs.update(OTHER_VENDOR_JOBS)
    out = Forecast()
    for event in events:
        context = CONTEXTS[event.id]
        predicted = predict_event_durations(duration_model, event, context, ACTIVITY_TYPES, start_hours, vendor_jobs)
        out.predicted.update(predicted)
        for a in event.activities:
            row = dict(id=a.id, name=a.name, event_id=event.id, planner=a.duration_minutes,
                       predicted=predicted.get(a.id), reasons=[])
            if a.id in predicted:
                frame = add_calendar_features(pd.DataFrame([dict(
                    activity_type=ACTIVITY_TYPES[a.id], event_type=context.event_type, venue_type=context.venue_type,
                    planned_duration_minutes=a.duration_minutes, guest_count=context.guest_count,
                    crew_size=context.crew_size, event_date=context.event_date,
                    planned_start_hour=start_hours[a.id], vendor_prior_jobs=vendor_jobs.get(a.id))]))
                # SHAP against the AVERAGE past event: the context features
                # explain why THIS event differs from a typical one.
                contrib = duration_model.contributions(frame)[CONTEXT_FEATURES].iloc[0]
                top = contrib.reindex(contrib.abs().sort_values(ascending=False).index)[:3]
                row["reasons"] = [dict(feature=FEATURE_LABELS[k], minutes=round(float(v), 1))
                                  for k, v in top.items() if abs(v) >= 0.5]
            out.durations.append(row)

    first_use: dict[str, int] = {}
    for aid, s in planner_schedule.activities.items():
        for rid in s.assigned_resource_ids:
            first_use[rid] = min(first_use.get(rid, s.start_minutes), s.start_minutes)
    bookings = [VendorBooking(rid, rid, p["category"], booked_arrival_hour=first_use[rid] // 60,
                              travel_distance_km=p["distance_km"], vendor_prior_jobs=p["prior_jobs"],
                              vendor_prior_mean_lateness=p["prior_mean_lateness"])
                for rid, p in VENDOR_PROFILES.items() if rid in first_use]
    risk = late_arrival_risk(lateness_model, bookings, EVENT_DATE)
    for b in bookings:
        p = VENDOR_PROFILES[b.vendor_id]
        out.vendor_risk.append(dict(resource_id=b.vendor_id, vendor=p["vendor"], category=p["category"],
                                    arrival=first_use[b.vendor_id], distance_km=p["distance_km"],
                                    prior_jobs=p["prior_jobs"], prior_mean_lateness=p["prior_mean_lateness"],
                                    probability=round(risk[b.vendor_id], 3)))
    out.vendor_risk.sort(key=lambda r: -r["probability"])
    return out
