"""
The trained prediction models feeding the planning-phase scheduler
(proposal Section 4.2.1: the gradient boosting model "supplies the
duration estimates the solver requires").

Same eleven-activity Perera wedding as run_example.py, planned for a
250-guest OUTDOOR wedding in rainy October. Shows:
  1. planner's durations vs the duration model's predictions, with the
     top SHAP reasons for each change (why, not just what);
  2. the CP-SAT schedule solved with each, and the end-time difference;
  3. late-arrival risk for each vendor booking vs the twin's 10-minute
     tolerance — the bookings worth a reminder call the day before.

Run `python -m examples.train_prediction_models` first (it saves the
models), then from the repository root:
    python -m examples.run_prediction_example
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from examples.run_example import build_resources, build_wedding, format_minutes
from scheduling_engine import solve_planning_phase, verify_schedule
from scheduling_engine.duration_prediction import (
    EventContext,
    TrainedModel,
    VendorBooking,
    add_calendar_features,
    late_arrival_risk,
    predict_event_durations,
    with_predicted_durations,
)

MODEL_DIR = Path(__file__).resolve().parent.parent / "models"

CONTEXT = EventContext(event_date="2026-10-24", event_type="wedding", guest_count=250,
                       venue_type="outdoor", crew_size=2)

# Wedding activity ids happen to equal the trained activity types.
ACTIVITY_TYPES = {a.id: a.id for a in build_wedding().activities}

VENDOR_BOOKINGS = [
    VendorBooking("decor", "florist_03", "florist", booked_arrival_hour=9,
                  travel_distance_km=12.0, vendor_prior_jobs=40, vendor_prior_mean_lateness=3.1),
    VendorBooking("catering_load_in", "caterer_05", "caterer", booked_arrival_hour=11,
                  travel_distance_km=48.0, vendor_prior_jobs=35, vendor_prior_mean_lateness=19.4),
    VendorBooking("photos", "photographer_02", "photographer", booked_arrival_hour=17,
                  travel_distance_km=25.0, vendor_prior_jobs=2, vendor_prior_mean_lateness=None),
    VendorBooking("entertainment", "band_dj_06", "band_dj", booked_arrival_hour=18,
                  travel_distance_km=8.0, vendor_prior_jobs=60, vendor_prior_mean_lateness=6.0),
]
TWIN_TOLERANCE_MINUTES = 10
RISK_FLAG_PROBABILITY = 0.5


# SHAP values are measured against the AVERAGE training row. For "what
# activity is this" features (type, planned length) that average mixes
# 20-minute speeches with 90-minute setups, so their values aren't
# meaningful on their own. The CONTEXT features compare this event with a
# typical past event, which is the explanation a planner actually wants.
CONTEXT_FEATURES = ["guest_count", "venue_type", "is_rainy_month", "crew_size",
                    "vendor_prior_jobs", "event_type", "is_weekend", "planned_start_hour"]


def top_reasons(model: TrainedModel, row: pd.DataFrame, n: int = 3) -> str:
    contrib = model.contributions(row)[CONTEXT_FEATURES].iloc[0]
    top = contrib.reindex(contrib.abs().sort_values(ascending=False).index)[:n]
    return ", ".join(f"{k} {v:+.1f}m" for k, v in top.items() if abs(v) >= 0.5) or "-"


def main() -> None:
    duration_model = TrainedModel.load(MODEL_DIR, "duration")
    lateness_model = TrainedModel.load(MODEL_DIR, "lateness")
    wedding = build_wedding()
    resources = build_resources()

    planned_schedule = solve_planning_phase([wedding], resources)
    start_hours = {aid: s.start_minutes // 60 for aid, s in planned_schedule.activities.items()}
    vendor_jobs = {b.activity_id: b.vendor_prior_jobs for b in VENDOR_BOOKINGS}
    predicted = predict_event_durations(duration_model, wedding, CONTEXT, ACTIVITY_TYPES,
                                        start_hours, vendor_jobs)

    print(f"Context: {CONTEXT.guest_count} guests, {CONTEXT.venue_type}, {CONTEXT.event_date} (rainy month)\n")
    print(f"  {'activity':<18}{'planned':>9}{'predicted':>11}   context effects vs a typical past event (SHAP)")
    for a in wedding.activities:
        row = add_calendar_features(pd.DataFrame([dict(
            activity_type=a.id, event_type=CONTEXT.event_type, venue_type=CONTEXT.venue_type,
            planned_duration_minutes=a.duration_minutes, guest_count=CONTEXT.guest_count,
            crew_size=CONTEXT.crew_size, event_date=CONTEXT.event_date,
            planned_start_hour=start_hours[a.id], vendor_prior_jobs=vendor_jobs.get(a.id))]))
        print(f"  {a.id:<18}{a.duration_minutes:>9}{predicted[a.id]:>11}   {top_reasons(duration_model, row)}")

    predicted_wedding = with_predicted_durations(wedding, predicted)
    predicted_schedule = solve_planning_phase([predicted_wedding], resources)
    conflicts = verify_schedule(predicted_wedding.activities, resources, predicted_schedule.activities)

    end_planned = planned_schedule.activities["strike"].end_minutes
    end_predicted = predicted_schedule.activities["strike"].end_minutes
    print(f"\nSchedule with planner durations:   ends {format_minutes(end_planned)}")
    print(f"Schedule with predicted durations: ends {format_minutes(end_predicted)} "
          f"({end_predicted - end_planned:+d} min) | {predicted_schedule.status_name} | "
          f"{len(conflicts)} conflicts on independent verification")
    print(f"Fixed guest arrival (client-imposed): "
          f"{format_minutes(planned_schedule.activities['guest_arrival'].start_minutes)} planned, "
          f"{format_minutes(predicted_schedule.activities['guest_arrival'].start_minutes)} predicted — "
          "the solver absorbs longer setup before it and pushes only what follows it.")

    risk = late_arrival_risk(lateness_model, VENDOR_BOOKINGS, CONTEXT.event_date)
    print(f"\nVendor late-arrival risk: P(more than {TWIN_TOLERANCE_MINUTES} min late)")
    for b in VENDOR_BOOKINGS:
        flag = "  <- confirm the day before" if risk[b.activity_id] >= RISK_FLAG_PROBABILITY else ""
        print(f"  {b.activity_id:<18}{b.vendor_id:<17}{risk[b.activity_id]:>6.0%}{flag}")


if __name__ == "__main__":
    main()
