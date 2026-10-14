"""
Three more public datasets, each used to TEST or CALIBRATE one specific
assumption of the event models — never mixed into the event training data
(no public event-duration dataset exists; proposal Section 3.3.2).

  1. Sri Lanka rainfall (Department of Meteorology rain gauges, via Kaggle
     ivantha/sri-lanka-weather-dataset; cross-checked against
     rasulmah/sri-lanka-weather-dataset, which is model/reanalysis data)
     -> CALIBRATES which months count as rainy in Colombo
        (history_generation.RAINY_MONTHS).

  2. Olist Brazilian e-commerce (Kaggle olistbr/brazilian-ecommerce;
     ~99k real orders with a PROMISED and an ACTUAL delivery date)
     -> TESTS the late-vendor classifier on real "late against a promise"
        data, and the assumption that a supplier's own past lateness is the
        strongest predictor of future lateness.

  3. SiP effort estimation (Derek Jones & Stephen Cullum,
     github.com/Derek-Jones/SiP_dataset; 12,299 real commercial tasks with
     an ESTIMATED and an ACTUAL duration; CC BY-NC-ND 4.0 — research use,
     downloaded at run time, not redistributed)
     -> TESTS the duration model on real planned-vs-actual data, and the
        "planning fallacy" shape the event generator assumes.

What each one does NOT show is stated next to its results: Brazilian
parcels and software tasks are not wedding activities. They test the
METHOD and the STRUCTURE of the assumptions, not event-specific numbers.
"""

from __future__ import annotations

import glob
import io
import math
import urllib.request
from pathlib import Path

import numpy as np
import pandas as pd

# ---------------------------------------------------------------------------
# 1. Sri Lanka rainfall
# ---------------------------------------------------------------------------

RAINFALL_GAUGE_HANDLE = "ivantha/sri-lanka-weather-dataset"
RAINFALL_MODEL_HANDLE = "rasulmah/sri-lanka-weather-dataset"
# Colombo-area gauges with 2012-2018 daily records.
COLOMBO_GAUGES = ["dehiwala", "ratmalana", "homagama"]
WET_DAY_MM = 1.0   # standard meteorological "rain day" threshold
RAINY_MONTH_RULE = 0.5  # a month is "rainy" if it rains on more than half of its days


def load_colombo_gauges() -> pd.DataFrame:
    import kagglehub

    folder = kagglehub.dataset_download(RAINFALL_GAUGE_HANDLE)
    files = [f for f in glob.glob(str(Path(folder) / "*_rf_*.csv"))
             if any(g in Path(f).name for g in COLOMBO_GAUGES)]
    df = pd.concat([pd.read_csv(f) for f in files], ignore_index=True)
    return df.rename(columns={"obs_val": "rain_mm"})[["station_name", "year", "month", "day", "rain_mm"]]


def monthly_rain_climatology(gauges: pd.DataFrame) -> pd.DataFrame:
    """Per calendar month: mean monthly total (mm) and P(wet day)."""
    g = gauges.dropna(subset=["rain_mm"])
    out = g.groupby("month").agg(
        mean_daily_mm=("rain_mm", "mean"),
        wet_day_probability=("rain_mm", lambda s: float((s >= WET_DAY_MM).mean())),
        station_days=("rain_mm", "size"),
    )
    out["mean_monthly_mm"] = out["mean_daily_mm"] * 30.4
    out["rainy_by_rule"] = out["wet_day_probability"] > RAINY_MONTH_RULE
    return out


def load_colombo_model_data() -> pd.DataFrame:
    import kagglehub

    folder = kagglehub.dataset_download(RAINFALL_MODEL_HANDLE)
    df = pd.read_csv(Path(folder) / "SriLanka_Weather_Dataset.csv")
    df = df[df["city"] == "Colombo"].copy()
    df["month"] = pd.to_datetime(df["time"]).dt.month
    return df


# ---------------------------------------------------------------------------
# 2. Olist: real lateness against a promised date
# ---------------------------------------------------------------------------

OLIST_HANDLE = "olistbr/brazilian-ecommerce"
OLIST_TEST_FROM = "2018-06-01"
OLIST_CATEGORICAL = ["seller_state", "customer_state", "product_category"]
OLIST_NUMERIC = [
    "promised_days",
    "distance_km",
    "same_state",
    "freight_value",
    "price",
    "weight_kg",
    "n_items",
    "purchase_month",
    "purchase_dow",
    "purchase_hour",
    "seller_prior_orders",
    "seller_prior_late_rate",
]
OLIST_TARGET = "late"


def _haversine_km(lat1, lon1, lat2, lon2):
    lat1, lon1, lat2, lon2 = map(np.radians, (lat1, lon1, lat2, lon2))
    a = np.sin((lat2 - lat1) / 2) ** 2 + np.cos(lat1) * np.cos(lat2) * np.sin((lon2 - lon1) / 2) ** 2
    return 6371.0 * 2 * np.arcsin(np.sqrt(a))


def seller_history(df: pd.DataFrame, time_col: str, known_col: str, outcome_col: str,
                   key: str) -> pd.DataFrame:
    """For each row, the key's number of earlier outcomes and their mean,
    counting ONLY outcomes already KNOWN at this row's `time_col`.

    The subtlety (and why this isn't a simple running mean): an order
    placed earlier isn't known to be late until it is DELIVERED. If a
    seller's order from Monday is delivered on Friday, an order placed on
    Wednesday must not see it. So the history at time t counts outcomes
    whose `known_col` time is < t — not just rows that started before t.
    Shared by the Olist (known = delivered) and SiP (known = completed)
    studies.
    """
    events = pd.concat([
        pd.DataFrame({key: df[key], "t": df[known_col], "kind": 0, "value": df[outcome_col], "row": -1}),
        pd.DataFrame({key: df[key], "t": df[time_col], "kind": 1, "value": np.nan, "row": df.index}),
    ]).sort_values([key, "t", "kind"], kind="stable")  # outcomes known at the same instant count
    prior_n = np.zeros(len(df))
    prior_mean = np.full(len(df), np.nan)
    position = {idx: i for i, idx in enumerate(df.index)}
    current_key, n, total = None, 0, 0.0
    for k, kind, value, row in zip(events[key], events["kind"], events["value"], events["row"]):
        if k != current_key:
            current_key, n, total = k, 0, 0.0
        if kind == 0:
            n += 1
            total += value
        else:
            i = position[row]
            prior_n[i] = n
            prior_mean[i] = total / n if n else np.nan
    return pd.DataFrame({"prior_n": prior_n, "prior_mean": prior_mean}, index=df.index)


def load_olist() -> pd.DataFrame:
    import kagglehub

    folder = Path(kagglehub.dataset_download(OLIST_HANDLE))
    read = lambda name: pd.read_csv(folder / f"olist_{name}_dataset.csv")
    return dict(orders=read("orders"), items=read("order_items"), products=read("products"),
                sellers=read("sellers"), customers=read("customers"), geolocation=read("geolocation"),
                categories=pd.read_csv(folder / "product_category_name_translation.csv"))


def build_olist(tables: dict) -> tuple[pd.DataFrame, dict]:
    """One row per delivered single-seller order, features known at purchase."""
    report = {}
    orders = tables["orders"]
    report["orders_in"] = len(orders)
    for c in ["order_purchase_timestamp", "order_delivered_customer_date", "order_estimated_delivery_date"]:
        orders[c] = pd.to_datetime(orders[c])
    orders = orders[(orders["order_status"] == "delivered")
                    & orders["order_delivered_customer_date"].notna()]
    report["dropped_not_delivered_or_no_date"] = report["orders_in"] - len(orders)

    items = tables["items"].merge(tables["products"], on="product_id", how="left")
    per_order = items.groupby("order_id").agg(
        n_sellers=("seller_id", "nunique"), seller_id=("seller_id", "first"),
        n_items=("order_item_id", "size"), price=("price", "sum"), freight_value=("freight_value", "sum"),
        weight_kg=("product_weight_g", lambda s: s.sum(min_count=1) / 1000),
        product_category=("product_category_name", "first"),
    )
    df = orders.merge(per_order, on="order_id", how="inner")
    multi = df["n_sellers"] > 1
    report["dropped_multi_seller"] = int(multi.sum())
    df = df[~multi]
    translation = dict(zip(tables["categories"]["product_category_name"],
                           tables["categories"]["product_category_name_english"]))
    df["product_category"] = df["product_category"].map(translation)

    geo = tables["geolocation"].groupby("geolocation_zip_code_prefix")[["geolocation_lat", "geolocation_lng"]].mean()
    sellers = tables["sellers"].set_index("seller_id")
    customers = tables["customers"].set_index("customer_id")
    df["seller_state"] = df["seller_id"].map(sellers["seller_state"])
    df["customer_state"] = df["customer_id"].map(customers["customer_state"])
    s_zip = df["seller_id"].map(sellers["seller_zip_code_prefix"])
    c_zip = df["customer_id"].map(customers["customer_zip_code_prefix"])
    df["distance_km"] = _haversine_km(s_zip.map(geo["geolocation_lat"]), s_zip.map(geo["geolocation_lng"]),
                                      c_zip.map(geo["geolocation_lat"]), c_zip.map(geo["geolocation_lng"]))
    report["missing_distance_kept"] = int(df["distance_km"].isna().sum())
    df["same_state"] = (df["seller_state"] == df["customer_state"]).astype(int)

    p = df["order_purchase_timestamp"]
    df["promised_days"] = (df["order_estimated_delivery_date"] - p).dt.total_seconds() / 86400
    df["purchase_month"] = p.dt.month
    df["purchase_dow"] = p.dt.dayofweek
    df["purchase_hour"] = p.dt.hour
    df[OLIST_TARGET] = (df["order_delivered_customer_date"].dt.normalize()
                        > df["order_estimated_delivery_date"].dt.normalize()).astype(int)
    df["days_late"] = (df["order_delivered_customer_date"] - df["order_estimated_delivery_date"]).dt.total_seconds() / 86400

    df = df.reset_index(drop=True)
    hist = seller_history(df, "order_purchase_timestamp", "order_delivered_customer_date", OLIST_TARGET, "seller_id")
    df["seller_prior_orders"] = hist["prior_n"]
    df["seller_prior_late_rate"] = hist["prior_mean"]
    df["event_date"] = p.dt.strftime("%Y-%m-%d")       # for the shared chronological split
    df["group"] = p.dt.strftime("%G-%V")                # ISO week, for GroupKFold
    report["rows_out"] = len(df)
    report["late_rate"] = float(df[OLIST_TARGET].mean())
    return df, report


# ---------------------------------------------------------------------------
# 3. SiP: real estimated vs actual task durations
# ---------------------------------------------------------------------------

SIP_BASE = "https://raw.githubusercontent.com/Derek-Jones/SiP_dataset/master/"
SIP_TEST_FROM = "2012-01-01"
SIP_CATEGORICAL = ["category", "sub_category", "project"]
SIP_NUMERIC = ["hours_estimate", "priority", "estimate_month", "developer_prior_tasks",
               "developer_prior_log_ratio"]
SIP_TARGET = "hours_actual"
# Status codes meaning the work was done (others: CHRONICLE, CANCELLED,
# ESTIMATED, TEMPLATE, AUTHORISE — not a completed estimate-vs-actual pair).
SIP_DONE_STATUSES = {"FINISHED", "COMPLETED", "RELEASED"}
# Columns derived FROM the actual hours — using them would be leakage.
SIP_LEAKY_COLUMNS = ["TaskPerformance", "DeveloperPerformance", "DeveloperHoursActual"]


def load_sip(cache_dir: Path) -> tuple[pd.DataFrame, pd.DataFrame]:
    cache_dir.mkdir(parents=True, exist_ok=True)
    frames = []
    for name in ["Sip-task-info.csv", "est-act-dates.csv"]:
        path = cache_dir / name
        if not path.exists():
            with urllib.request.urlopen(SIP_BASE + name) as response:  # public GitHub raw file
                path.write_bytes(response.read())
        frames.append(pd.read_csv(path, encoding="latin-1"))
    return frames[0], frames[1]


def build_sip(tasks: pd.DataFrame, dates: pd.DataFrame) -> tuple[pd.DataFrame, dict]:
    report = {"tasks_in": len(tasks)}
    # One row per developer on multi-developer tasks; HoursEstimate and
    # HoursActual are task-level, so keep one row per task.
    tasks = tasks.drop(columns=SIP_LEAKY_COLUMNS).drop_duplicates(subset="TaskNumber")
    report["unique_tasks"] = len(tasks)
    df = tasks.merge(dates.drop_duplicates(subset="TaskNumber"), on="TaskNumber", how="inner")
    ok = df["StatusCode"].isin(SIP_DONE_STATUSES) & (df["HoursEstimate"] > 0) & (df["HoursActual"] > 0)
    report["dropped_not_done"] = int((~ok).sum())
    df = df[ok].copy()
    for c in ["EstimateOn", "CompletedOn"]:
        df[c] = pd.to_datetime(df[c], format="%d-%b-%y", errors="coerce")
    df = df.dropna(subset=["EstimateOn", "CompletedOn"]).reset_index(drop=True)

    df["hours_estimate"] = df["HoursEstimate"].astype(float)
    df[SIP_TARGET] = df["HoursActual"].astype(float)
    df["log_ratio"] = np.log(df[SIP_TARGET] / df["hours_estimate"])
    df["category"] = df["Category"]
    df["sub_category"] = df["SubCategory"]
    df["project"] = df["ProjectCode"]
    df["priority"] = df["Priority"]
    df["estimate_month"] = df["EstimateOn"].dt.month
    # A developer's track record, from tasks COMPLETED before this estimate was made.
    hist = seller_history(df, "EstimateOn", "CompletedOn", "log_ratio", "DeveloperID")
    df["developer_prior_tasks"] = hist["prior_n"]
    df["developer_prior_log_ratio"] = hist["prior_mean"]
    df["event_date"] = df["EstimateOn"].dt.strftime("%Y-%m-%d")
    df["group"] = df["EstimateOn"].dt.strftime("%Y-%m")
    report["rows_out"] = len(df)
    return df, report


def planning_fallacy_summary(df: pd.DataFrame) -> dict:
    ratio = np.exp(df["log_ratio"])
    return {
        "tasks": len(df),
        "share_overrun": float((ratio > 1).mean()),
        "share_exact": float((ratio == 1).mean()),
        "share_underrun": float((ratio < 1).mean()),
        "median_ratio": float(ratio.median()),
        "mean_ratio": float(ratio.mean()),
        "p90_ratio": float(ratio.quantile(0.9)),
        "log_ratio_sd": float(df["log_ratio"].std()),
    }
