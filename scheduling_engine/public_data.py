"""
External public dataset: Kaggle "Food Delivery Dataset" (Gaurav Malik,
kaggle.com/datasets/gauravmalik26/food-delivery-dataset; 45,593 labelled
deliveries in Indian cities, Feb-Apr 2022).

WHAT IT IS AND ISN'T. It is NOT event data — no public event-duration
dataset exists (proposal Section 3.3.2). It is the closest public
analogue of one part of our problem: a vendor travelling to a site
through South Asian traffic and weather. We use it for two things only:

  A. EXTERNAL VALIDATION — run the same pipeline used for our models
     (clean -> chronological split -> grouped CV tuning -> XGBoost vs
     baselines -> SHAP) on data we did not generate, to show the method
     works on real, messy, independent records.
  B. CALIBRATION — estimate how much heavy traffic and bad weather
     multiply travel time, holding distance and other factors fixed, and
     compare/ground the vendor-lateness assumptions in
     history_generation.py (RUSH_HOUR_LATENESS_FACTOR,
     RAINY_MONTH_LATENESS_FACTOR) against those numbers.

Its rows are never mixed into the event training data.

PROVENANCE CAVEAT. The uploader doesn't document how the data was
collected, and some properties suggest it is partly simulated: the six
weather categories are almost exactly equally frequent, times are bounded
to 10-54 minutes, and delivery coordinates sit at fixed offsets from the
restaurant. It is a widely used public benchmark, not a guaranteed field
measurement, and is described that way wherever it is reported.

Download (no Kaggle login needed for this public dataset):
    import kagglehub; kagglehub.dataset_download("gauravmalik26/food-delivery-dataset")
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field

import numpy as np
import pandas as pd

KAGGLE_HANDLE = "gauravmalik26/food-delivery-dataset"
TEST_FROM_DATE = "2022-03-28"  # last ~1.5 weeks held out, as in the event models
MAX_PLAUSIBLE_KM = 50.0        # city food delivery; longer = coordinate error
MAX_RATING = 5.0

CATEGORICAL = ["weather", "traffic", "city", "vehicle_type", "order_type", "festival"]
NUMERIC = [
    "distance_km",
    "order_hour",
    "pickup_wait_min",
    "multiple_deliveries",
    "vehicle_condition",
    "courier_age",
    "courier_rating",
    "day_of_week",
]
TARGET = "time_taken_min"


def download() -> str:
    """Path of the downloaded dataset folder (cached by kagglehub)."""
    import kagglehub

    return kagglehub.dataset_download(KAGGLE_HANDLE)


@dataclass
class PublicCleaningReport:
    rows_in: int = 0
    text_nan_converted: int = 0
    invalid_ratings_set_missing: int = 0
    negative_coordinates_sign_fixed: int = 0
    implausible_distance_set_missing: int = 0
    missing_after_cleaning: dict[str, int] = field(default_factory=dict)
    rows_out: int = 0

    def lines(self) -> list[str]:
        out = [
            f"rows in:                             {self.rows_in}",
            f"'NaN' text values -> real missing:   {self.text_nan_converted}",
            f"ratings > {MAX_RATING:g} set missing:            {self.invalid_ratings_set_missing}",
            f"negative coordinates sign-fixed:     {self.negative_coordinates_sign_fixed}",
            f"implausible distance set missing:    {self.implausible_distance_set_missing}",
        ]
        for column, count in self.missing_after_cleaning.items():
            if count:
                out.append(f"missing {column + ':':<29}{count}")
        out.append(f"rows out:                            {self.rows_out}")
        return out


def _haversine_km(lat1, lon1, lat2, lon2):
    lat1, lon1, lat2, lon2 = map(np.radians, (lat1, lon1, lat2, lon2))
    a = np.sin((lat2 - lat1) / 2) ** 2 + np.cos(lat1) * np.cos(lat2) * np.sin((lon2 - lon1) / 2) ** 2
    return 6371.0 * 2 * np.arcsin(np.sqrt(a))


def _minutes_of_day(text: pd.Series) -> pd.Series:
    t = pd.to_datetime(text, format="%H:%M:%S", errors="coerce")
    return t.dt.hour * 60 + t.dt.minute


def clean(raw: pd.DataFrame) -> tuple[pd.DataFrame, PublicCleaningReport]:
    """Turn the raw Kaggle train.csv into a typed, analysable table.

    Every rule is countable and reported:
      * strip trailing spaces; the literal text 'NaN' becomes a real missing value
      * '(min) 24' -> 24; 'conditions Sunny' -> 'Sunny'
      * courier rating > 5 is impossible -> missing
      * coordinates: all locations are in India (positive lat/lon), so a
        negative sign is a data-entry error -> flipped; a zero coordinate
        is unknown -> distance missing; > 50 km for a city delivery ->
        missing
      * missing values are kept (XGBoost handles them), not imputed
    """
    report = PublicCleaningReport(rows_in=len(raw))
    df = raw.copy()
    for c in df.select_dtypes(include=["object", "string"]).columns:
        df[c] = df[c].str.strip()
    is_text_nan = df.isin(["NaN", "conditions NaN"])
    report.text_nan_converted = int(is_text_nan.to_numpy().sum())
    df = df.mask(is_text_nan)

    out = pd.DataFrame(index=df.index)
    out["order_date"] = pd.to_datetime(df["Order_Date"], format="%d-%m-%Y")
    out["day_of_week"] = out["order_date"].dt.dayofweek
    out["weather"] = df["Weatherconditions"].str.replace("conditions ", "", regex=False)
    out["traffic"] = df["Road_traffic_density"]
    out["city"] = df["City"]
    out["vehicle_type"] = df["Type_of_vehicle"]
    out["order_type"] = df["Type_of_order"]
    out["festival"] = df["Festival"]
    out["multiple_deliveries"] = pd.to_numeric(df["multiple_deliveries"], errors="coerce")
    out["vehicle_condition"] = pd.to_numeric(df["Vehicle_condition"], errors="coerce")
    out["courier_age"] = pd.to_numeric(df["Delivery_person_Age"], errors="coerce")
    rating = pd.to_numeric(df["Delivery_person_Ratings"], errors="coerce")
    report.invalid_ratings_set_missing = int((rating > MAX_RATING).sum())
    out["courier_rating"] = rating.where(rating <= MAX_RATING)
    out["courier_id"] = df["Delivery_person_ID"]

    ordered = _minutes_of_day(df["Time_Orderd"])
    picked = _minutes_of_day(df["Time_Order_picked"])
    out["order_hour"] = ordered // 60
    out["pickup_wait_min"] = (picked - ordered) % (24 * 60)  # wraps past midnight

    coords = df[["Restaurant_latitude", "Restaurant_longitude",
                 "Delivery_location_latitude", "Delivery_location_longitude"]].astype(float)
    report.negative_coordinates_sign_fixed = int((coords < 0).any(axis=1).sum())
    coords = coords.abs()
    distance = _haversine_km(*(coords[c] for c in coords.columns))
    unknown = (coords == 0).any(axis=1)
    implausible = ~unknown & (distance > MAX_PLAUSIBLE_KM)
    report.implausible_distance_set_missing = int(implausible.sum())
    out["distance_km"] = distance.where(~unknown & ~implausible)

    out[TARGET] = pd.to_numeric(df["Time_taken(min)"].str.extract(r"(\d+)")[0], errors="coerce")
    out = out.dropna(subset=[TARGET]).reset_index(drop=True)

    report.missing_after_cleaning = {c: int(out[c].isna().sum()) for c in CATEGORICAL + NUMERIC}
    report.rows_out = len(out)
    return out, report


def chronological_split(df: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    is_test = df["order_date"] >= TEST_FROM_DATE
    return df[~is_test].reset_index(drop=True), df[is_test].reset_index(drop=True)


@dataclass(frozen=True)
class EffectEstimate:
    """A multiplicative effect on travel time with a bootstrap 95% CI."""

    name: str
    factor: float
    ci_low: float
    ci_high: float


def multiplicative_effects(df: pd.DataFrame, n_boot: int = 200, seed: int = 0) -> list[EffectEstimate]:
    """Log-linear regression: log(time) = b0 + b_traffic + b_weather + ...
    + b_distance * km. exp(b) is then "how many times longer", HOLDING
    EVERYTHING ELSE IN THE MODEL FIXED — unlike a raw ratio of group
    medians, which would mix the traffic effect with e.g. jams being more
    common at dinner time. Reference levels: traffic 'Low', weather 'Sunny'.
    Uncertainty: bootstrap (resample rows, refit, take the 2.5/97.5
    percentiles)."""
    from sklearn.linear_model import LinearRegression

    data = df.dropna(subset=["traffic", "weather", "distance_km", "festival",
                             "multiple_deliveries", "courier_rating", "courier_age"])
    numeric = data[["distance_km", "multiple_deliveries", "vehicle_condition",
                    "courier_rating", "courier_age"]].astype(float)
    dummies = pd.concat([
        pd.get_dummies(data["traffic"], prefix="traffic", dtype=float).drop(columns="traffic_Low"),
        pd.get_dummies(data["weather"], prefix="weather", dtype=float).drop(columns="weather_Sunny"),
        pd.get_dummies(data["festival"], prefix="festival", dtype=float).drop(columns="festival_No"),
        pd.get_dummies(data["city"].fillna("unknown"), prefix="city", dtype=float),
    ], axis=1)
    x = pd.concat([numeric, dummies], axis=1).to_numpy()
    columns = list(numeric.columns) + list(dummies.columns)
    y = np.log(data[TARGET].to_numpy(float))

    def fit(rows):
        return LinearRegression().fit(x[rows], y[rows]).coef_

    point = fit(np.arange(len(y)))
    rng = np.random.default_rng(seed)
    boots = np.array([fit(rng.integers(0, len(y), len(y))) for _ in range(n_boot)])
    wanted = [c for c in columns if c.startswith(("traffic_", "weather_", "festival_"))]
    wanted.append("distance_km")
    out = []
    for c in wanted:
        i = columns.index(c)
        scale = 10.0 if c == "distance_km" else 1.0  # report distance per +10 km
        lo, hi = np.percentile(boots[:, i] * scale, [2.5, 97.5])
        name = "+10 km distance" if c == "distance_km" else c.replace("_", " = ", 1)
        out.append(EffectEstimate(name, math.exp(point[i] * scale), math.exp(lo), math.exp(hi)))
    return out
