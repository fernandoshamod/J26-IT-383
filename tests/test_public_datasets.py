"""Leakage-safe history features and the public-dataset helpers (no downloads)."""

import numpy as np
import pandas as pd
import pytest

from scheduling_engine import public_datasets as pds


def test_history_only_counts_outcomes_already_known():
    """Order B is placed while order A is still in transit, so B must not
    see A's outcome; order C is placed after A arrived, so C must."""
    df = pd.DataFrame({
        "seller": ["s", "s", "s"],
        "placed": pd.to_datetime(["2018-01-01", "2018-01-03", "2018-01-10"]),
        "delivered": pd.to_datetime(["2018-01-05", "2018-01-12", "2018-01-15"]),
        "late": [1, 0, 0],
    })
    hist = pds.seller_history(df, "placed", "delivered", "late", "seller")
    assert hist["prior_n"].tolist() == [0, 0, 1]
    assert np.isnan(hist["prior_mean"].iloc[0]) and np.isnan(hist["prior_mean"].iloc[1])
    assert hist["prior_mean"].iloc[2] == 1.0


def test_history_is_kept_separate_per_seller():
    df = pd.DataFrame({
        "seller": ["a", "b", "a"],
        "placed": pd.to_datetime(["2018-01-01", "2018-01-02", "2018-02-01"]),
        "delivered": pd.to_datetime(["2018-01-03", "2018-01-04", "2018-02-03"]),
        "late": [1, 0, 0],
    })
    hist = pds.seller_history(df, "placed", "delivered", "late", "seller")
    assert hist["prior_n"].tolist() == [0, 0, 1]
    assert hist["prior_mean"].iloc[2] == 1.0  # only seller a's own earlier order


def test_rainy_months_follow_the_wet_day_rule():
    rows = []
    for month in (1, 5):
        for day in range(1, 11):
            wet = day <= (8 if month == 5 else 2)  # May: 80% wet days, Jan: 20%
            rows.append(dict(station_name="X", year=2015, month=month, day=day, rain_mm=5.0 if wet else 0.0))
    clim = pds.monthly_rain_climatology(pd.DataFrame(rows))
    assert clim.loc[5, "rainy_by_rule"] and not clim.loc[1, "rainy_by_rule"]
    assert clim.loc[5, "wet_day_probability"] == pytest.approx(0.8)


def test_sip_drops_leaky_columns_and_unfinished_tasks():
    tasks = pd.DataFrame({
        "TaskNumber": [1, 1, 2, 3], "StatusCode": ["FINISHED", "FINISHED", "CANCELLED", "COMPLETED"],
        "HoursEstimate": [2.0, 2.0, 1.0, 4.0], "HoursActual": [3.0, 3.0, 1.0, 4.0],
        "Category": "Development", "SubCategory": "Enhancement", "ProjectCode": "PC1", "Priority": 1,
        "DeveloperID": [7, 8, 7, 7], "TaskPerformance": 0.0, "DeveloperPerformance": 0.0,
        "DeveloperHoursActual": 1.0,
    })
    dates = pd.DataFrame({"TaskNumber": [1, 2, 3], "EstimateOn": ["01-Jan-10", "02-Jan-10", "03-Jan-10"],
                          "StartedOn": "01-Jan-10", "CompletedOn": ["02-Jan-10", "03-Jan-10", "05-Jan-10"]})
    df, report = pds.build_sip(tasks, dates)
    assert sorted(df["TaskNumber"]) == [1, 3]  # duplicate developer row and cancelled task gone
    assert not set(pds.SIP_LEAKY_COLUMNS) & set(df.columns)
    assert not set(pds.SIP_LEAKY_COLUMNS) & set(pds.SIP_NUMERIC + pds.SIP_CATEGORICAL)
    # Task 3 was estimated on 3 Jan, after task 1 completed on 2 Jan: it sees one prior task.
    assert df.set_index("TaskNumber").loc[3, "developer_prior_tasks"] == 1
