"""
Synthetic historical event records for training the duration and vendor-
lateness prediction models (proposal Section 4.2.1: "A gradient boosting
model predicts activity durations and vendor lateness from historical
data"; Section 3.3 "Historical outcome data: planned versus actual timings
for past events"; WBS task 3.6).

WHY SYNTHETIC. The proposal states that no public dataset of event
activity durations exists (Section 3.3.2). Until the industry partner's
(Blooming Moments) historical records are digitised, the models are
trained on records produced by the data-generating process (DGP) below.
Every effect in the DGP is a DECLARED ASSUMPTION, collected in the
constants at the top of this file so that each one can be:
  1. defended in the viva (each has a stated real-world reason), and
  2. replaced one by one with values estimated from real records.
No result from this data is presented as a real-world measurement.

ORACLE COLUMNS. Each row also carries `oracle_*` columns: the best
possible prediction, computed from the hidden DGP parameters (e.g. the
vendor's true typical lateness, which no model can see). They are NEVER
features — they exist only to measure the noise ceiling: how close the
trained model gets to the best accuracy any model could reach on this
data. Real records will not have them; the training script strips them
before saving the raw CSV.

WHY THIS IS STILL USEFUL. Because we wrote the DGP, we know the true
answer. That lets us check something real data cannot: whether the model
recovers the effects we planted (e.g. that guest count matters for
dinner service but not for a sound check). If the training pipeline can't
recover a known truth, it can't be trusted on unknown real data either.
When real records arrive, the SAME pipeline (cleaning -> features ->
training -> evaluation) runs on them unchanged; only this file is swapped.

DELIBERATE DIRT. Real records are messy, so the raw output is too:
inconsistent activity naming ("Catering Load-in" vs "catering_loadin"),
missing guest counts, and a few impossible rows (zero/negative or
typo-inflated durations). data_preparation.py has to clean these, which
exercises the "cleaning and normalisation ... resolution of inconsistent
activity naming" step promised in proposal Section 3.3.
"""

from __future__ import annotations

import math
import random
from datetime import date, timedelta

import pandas as pd

# ---------------------------------------------------------------------------
# Declared assumptions (DGP parameters). Each line says WHY it exists.
# ---------------------------------------------------------------------------

EVENT_TYPES = ["wedding", "engagement", "corporate", "birthday"]
EVENT_TYPE_WEIGHTS = [0.5, 0.15, 0.25, 0.10]  # wedding-heavy, like the partner's business

# Per activity type:
#   base   = typical planned duration (minutes) at 150 guests
#   bias   = planning-fallacy overrun: actual/planned on average
#            (Buehler, Griffin & Ross, 1994 â€” people underestimate task
#            time; social activities like speeches and photos overrun most)
#   guest  = how strongly duration grows with guest count (per +100 guests)
#   rain   = True if an outdoor activity slows down in the rainy months
#   crew   = True if more crew members make it faster
ACTIVITY_PROFILES = {
    "venue_setup":      dict(base=90, bias=1.10, guest=0.10, rain=True,  crew=True),
    "decor":            dict(base=60, bias=1.15, guest=0.05, rain=True,  crew=False),
    "sound_check":      dict(base=30, bias=1.05, guest=0.00, rain=False, crew=False),
    "catering_load_in": dict(base=45, bias=1.10, guest=0.20, rain=True,  crew=True),
    "guest_arrival":    dict(base=30, bias=1.20, guest=0.25, rain=True,  crew=False),
    "ceremony":         dict(base=30, bias=1.05, guest=0.00, rain=False, crew=False),
    "photos":           dict(base=45, bias=1.25, guest=0.10, rain=True,  crew=False),
    "dinner_service":   dict(base=60, bias=1.10, guest=0.30, rain=False, crew=True),
    "speeches":         dict(base=20, bias=1.35, guest=0.00, rain=False, crew=False),
    "entertainment":    dict(base=90, bias=1.00, guest=0.00, rain=False, crew=False),  # contracted slot
    "strike":           dict(base=60, bias=1.05, guest=0.10, rain=True,  crew=True),
}
ACTIVITY_ORDER = list(ACTIVITY_PROFILES)
CEREMONY_EVENT_TYPES = {"wedding", "engagement"}  # others have no ceremony

# Planners DO scale their estimates with guest count, but only by half the
# true effect â€” so the bigger the event, the bigger the underestimate.
PLANNER_GUEST_SCALING = 0.5
PLANNER_ESTIMATE_NOISE_SIGMA = 0.08  # planners' estimates differ from each other
ACTUAL_DURATION_NOISE_SIGMA = 0.12   # irreducible event-day randomness
RAINY_MONTH_OUTDOOR_SLOWDOWN = 0.15  # +15% for rain-sensitive outdoor work
CREW_SIZE_EXPONENT = 0.3             # crew of 3 is faster than 2, but not 1.5x faster
NOVICE_VENDOR_JOBS = 10              # vendors with fewer past jobs than this...
NOVICE_VENDOR_SLOWDOWN = 0.10        # ...take 10% longer

# Rainy months in Colombo, CALIBRATED from Sri Lanka Department of
# Meteorology rain gauges (Dehiwala, Ratmalana, Homagama, 2012-2018; see
# public_datasets.py): a month counts as rainy if it rains (>= 1 mm) on
# more than half its days. The original guess (south-west monsoon May-June
# + October-November) missed September, which the gauges show is wetter
# than June (264 mm vs 210 mm a month).
ASSUMED_RAINY_MONTHS = {5, 6, 10, 11}
RAINY_MONTHS = {5, 6, 9, 10, 11}
# Colombo commuter traffic peaks.
RUSH_HOURS = {7, 8, 16, 17, 18}

# Activities delivered by an external vendor, and the vendor category.
VENDOR_ACTIVITIES = {
    "decor": "florist",
    "sound_check": "av_vendor",
    "catering_load_in": "caterer",
    "photos": "photographer",
    "entertainment": "band_dj",
}
VENDORS_PER_CATEGORY = 8

# Vendor lateness (minutes after the booked arrival time):
#   each vendor has a hidden "typical lateness" (some are chronically late);
#   P(on time) falls with that typical lateness, rush hour and rain;
#   if late, the amount scales with rush hour, rain and travel distance.
VENDOR_TYPICAL_LATENESS_MEDIAN = 8.0
VENDOR_TYPICAL_LATENESS_SIGMA = 0.6
#
# The three travel-related factors below are CALIBRATED, not assumed: they
# were estimated from 45,593 public deliveries (Kaggle Food Delivery
# Dataset; see public_data.py and examples/validate_on_public_data.py) with
# a log-linear model holding the other factors fixed:
#   traffic Jam vs Low      x1.30 (95% CI 1.30-1.31) -> rush hour
#   weather Stormy vs Sunny x1.16 (95% CI 1.15-1.17) -> rainy month
#   +10 km distance         x1.13 -> doubling every ~55 km
# Assumption carried over: a vendor's lateness grows with traffic, rain and
# distance the way delivery travel time does. The original guesses are
# kept below so the before/after is on record.
ASSUMED_BEFORE_CALIBRATION = {
    "RUSH_HOUR_LATENESS_FACTOR": 1.6,
    "RAINY_MONTH_LATENESS_FACTOR": 1.4,
    "DISTANCE_KM_PER_DOUBLING": 40.0,
}
RUSH_HOUR_LATENESS_FACTOR = 1.30
RAINY_MONTH_LATENESS_FACTOR = 1.16
DISTANCE_KM_PER_DOUBLING = 55.0  # 55 km further away -> twice as late
# Same as OperationalDigitalTwin's default_tolerance_minutes: a vendor more
# than this late is what the twin would flag as a disruption.
LATENESS_TOLERANCE_MINUTES = 10

# Data-quality defects deliberately injected into the RAW file.
MISSING_GUEST_COUNT_RATE = 0.03
MISSING_DISTANCE_RATE = 0.04
IMPOSSIBLE_DURATION_RATE = 0.005
NAME_VARIANTS = {
    "venue_setup": ["Venue Setup", "venue set-up", "VENUE_SETUP", "setup venue"],
    "decor": ["Decor", "Floral & Decor", "decoration", "decor install"],
    "sound_check": ["Sound Check", "sound-check", "AV check", "soundcheck"],
    "catering_load_in": ["Catering Load-in", "catering_loadin", "Catering load in", "food load in"],
    "guest_arrival": ["Guest Arrival", "guests arriving", "welcome", "guest-arrival"],
    "ceremony": ["Ceremony", "poruwa ceremony", "CEREMONY", "main ceremony"],
    "photos": ["Photos", "photography", "photo session", "Photo Shoot"],
    "dinner_service": ["Dinner Service", "dinner", "buffet service", "Dinner"],
    "speeches": ["Speeches", "speech", "toasts", "Speeches & Toasts"],
    "entertainment": ["Entertainment", "band", "DJ set", "dancing"],
    "strike": ["Strike", "load-out", "Breakdown", "strike & load out"],
}
NAME_VARIANT_RATE = 0.25  # a quarter of rows use a non-canonical name

HISTORY_START = date(2022, 1, 1)
HISTORY_DAYS = 4 * 365  # 2022-2025


def _sigmoid(x: float) -> float:
    return 1.0 / (1.0 + math.exp(-x))


def _round_to_5(minutes: float) -> int:
    return max(5, int(round(minutes / 5.0)) * 5)


def generate_history(n_events: int = 800, seed: int = 42) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Generate RAW historical records.

    Returns two tables, both one row per observation:
      activities: one row per activity performed at a past event, with the
                  planner's planned duration and the actual duration.
      arrivals:   one row per vendor booking, with how late the vendor
                  arrived relative to the booked arrival time.

    Rows are produced in date order. Vendor history features
    (`vendor_prior_jobs`, `vendor_prior_mean_lateness`) are computed only
    from STRICTLY EARLIER events â€” the information a planner would really
    have had when planning that event â€” so they leak nothing from the
    future.
    """
    rng = random.Random(seed)

    vendors = []
    for category in sorted(set(VENDOR_ACTIVITIES.values())):
        for i in range(1, VENDORS_PER_CATEGORY + 1):
            vendors.append(dict(
                vendor_id=f"{category}_{i:02d}",
                category=category,
                typical_lateness=VENDOR_TYPICAL_LATENESS_MEDIAN
                * math.exp(rng.gauss(0, VENDOR_TYPICAL_LATENESS_SIGMA)),
                base_distance_km=rng.uniform(3, 60),
            ))
    vendors_by_category: dict[str, list[dict]] = {}
    for v in vendors:
        vendors_by_category.setdefault(v["category"], []).append(v)
    vendor_jobs: dict[str, int] = {v["vendor_id"]: 0 for v in vendors}
    vendor_lateness_sum: dict[str, float] = {v["vendor_id"]: 0.0 for v in vendors}

    event_dates = sorted(
        HISTORY_START + timedelta(days=rng.randrange(HISTORY_DAYS)) for _ in range(n_events)
    )

    activity_rows = []
    arrival_rows = []
    for e, event_date in enumerate(event_dates):
        event_id = f"E{e:04d}"
        event_type = rng.choices(EVENT_TYPES, EVENT_TYPE_WEIGHTS)[0]
        guests = int(min(600, max(40, rng.lognormvariate(math.log(180), 0.45))))
        outdoor = rng.random() < 0.35
        rainy = event_date.month in RAINY_MONTHS
        weekend = event_date.weekday() >= 5
        crew_size = rng.choice([1, 2, 2, 2, 3, 3])
        clock_hour = rng.uniform(7, 13)  # setup starts in the morning

        vendor_updates = []  # applied AFTER the event, so same-event rows can't see each other
        for activity_type in ACTIVITY_ORDER:
            if activity_type == "ceremony" and event_type not in CEREMONY_EVENT_TYPES:
                continue
            if activity_type == "speeches" and rng.random() < 0.2:
                continue
            p = ACTIVITY_PROFILES[activity_type]
            guest_delta = (guests - 150) / 100.0

            planned = _round_to_5(
                p["base"]
                * (1 + PLANNER_GUEST_SCALING * p["guest"] * guest_delta)
                * math.exp(rng.gauss(0, PLANNER_ESTIMATE_NOISE_SIGMA))
            )

            vendor = None
            if activity_type in VENDOR_ACTIVITIES:
                vendor = rng.choice(vendors_by_category[VENDOR_ACTIVITIES[activity_type]])

            true_multiplier = p["bias"] * (1 + p["guest"] * guest_delta)
            if p["rain"] and outdoor and rainy:
                true_multiplier *= 1 + RAINY_MONTH_OUTDOOR_SLOWDOWN
            if p["crew"]:
                true_multiplier *= (2 / crew_size) ** CREW_SIZE_EXPONENT
            if vendor is not None and vendor_jobs[vendor["vendor_id"]] < NOVICE_VENDOR_JOBS:
                true_multiplier *= 1 + NOVICE_VENDOR_SLOWDOWN
            # The true duration is driven by the activity's real workload
            # (base), not by the planner's guess; the guess is just a noisy,
            # under-scaled estimate of the same thing.
            actual = p["base"] * true_multiplier * math.exp(rng.gauss(0, ACTUAL_DURATION_NOISE_SIGMA))
            actual = int(round(actual))
            # Lognormal noise has median 1, so the median actual duration —
            # the best possible guess under absolute-error loss — is:
            oracle_duration = p["base"] * true_multiplier

            activity_rows.append(dict(
                event_id=event_id,
                event_date=event_date.isoformat(),
                event_type=event_type,
                guest_count=guests,
                venue_type="outdoor" if outdoor else "indoor",
                activity_name=activity_type,
                planned_start_hour=int(clock_hour),
                planned_duration_minutes=planned,
                crew_size=crew_size,
                vendor_id=vendor["vendor_id"] if vendor else None,
                vendor_prior_jobs=vendor_jobs[vendor["vendor_id"]] if vendor else None,
                actual_duration_minutes=actual,
                oracle_duration_minutes=round(oracle_duration, 2),
            ))

            if vendor is not None:
                vid = vendor["vendor_id"]
                booked_hour = int(clock_hour)
                rush = booked_hour in RUSH_HOURS
                distance = max(1.0, vendor["base_distance_km"] + rng.gauss(0, 5))
                typical = vendor["typical_lateness"]
                p_on_time = _sigmoid(1.2 - 0.08 * typical - 0.6 * rush - 0.4 * rainy)
                scale = typical
                if rush:
                    scale *= RUSH_HOUR_LATENESS_FACTOR
                if rainy:
                    scale *= RAINY_MONTH_LATENESS_FACTOR
                scale *= 2 ** (distance / DISTANCE_KM_PER_DOUBLING)
                if rng.random() < p_on_time:
                    lateness = 0
                else:
                    lateness = int(round(scale * rng.gammavariate(2.0, 0.5)))  # mean 1, right-skewed
                # True P(lateness > tolerance): P(late) * P(scale * G >= tol + 0.5),
                # using the Gamma(shape 2, scale 0.5) survival function
                # P(G >= x) = exp(-2x)(1 + 2x).
                x = (LATENESS_TOLERANCE_MINUTES + 0.5) / scale
                oracle_p_late = (1 - p_on_time) * math.exp(-2 * x) * (1 + 2 * x)
                prior_jobs = vendor_jobs[vid]
                arrival_rows.append(dict(
                    event_id=event_id,
                    event_date=event_date.isoformat(),
                    activity_name=activity_type,
                    vendor_id=vid,
                    vendor_category=vendor["category"],
                    booked_arrival_hour=booked_hour,
                    travel_distance_km=round(distance, 1),
                    vendor_prior_jobs=prior_jobs,
                    vendor_prior_mean_lateness=(
                        round(vendor_lateness_sum[vid] / prior_jobs, 2) if prior_jobs else None
                    ),
                    lateness_minutes=lateness,
                    oracle_p_late_beyond_tolerance=round(oracle_p_late, 4),
                ))
                vendor_updates.append((vid, lateness))

            clock_hour += planned / 60.0

        for vid, lateness in vendor_updates:
            vendor_jobs[vid] += 1
            vendor_lateness_sum[vid] += lateness

    activities = pd.DataFrame(activity_rows)
    arrivals = pd.DataFrame(arrival_rows)
    _inject_data_quality_defects(activities, arrivals, rng)
    return activities, arrivals


def _inject_data_quality_defects(activities: pd.DataFrame, arrivals: pd.DataFrame, rng: random.Random) -> None:
    """Make the raw tables look like real exported records (in place)."""
    # Inconsistent naming of the same activity.
    for i in activities.index:
        if rng.random() < NAME_VARIANT_RATE:
            canonical = activities.at[i, "activity_name"]
            activities.at[i, "activity_name"] = rng.choice(NAME_VARIANTS[canonical])
    for i in arrivals.index:
        if rng.random() < NAME_VARIANT_RATE:
            canonical = arrivals.at[i, "activity_name"]
            arrivals.at[i, "activity_name"] = rng.choice(NAME_VARIANTS[canonical])

    # Missing guest counts: whole events, since it's an event-level field.
    missing_events = {e for e in activities["event_id"].unique() if rng.random() < MISSING_GUEST_COUNT_RATE}
    activities["guest_count"] = activities["guest_count"].astype("Int64")
    activities.loc[activities["event_id"].isin(missing_events), "guest_count"] = pd.NA

    # Missing travel distances.
    for i in arrivals.index:
        if rng.random() < MISSING_DISTANCE_RATE:
            arrivals.at[i, "travel_distance_km"] = None

    # Impossible durations: data-entry errors (0, negative, or a typo x10).
    for i in activities.index:
        if rng.random() < IMPOSSIBLE_DURATION_RATE:
            activities.at[i, "actual_duration_minutes"] = rng.choice(
                [0, -activities.at[i, "actual_duration_minutes"], activities.at[i, "actual_duration_minutes"] * 10]
            )
