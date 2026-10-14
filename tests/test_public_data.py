"""Cleaning rules for the public Kaggle delivery data, on a handmade sample
with the same quirks (no download needed)."""

import numpy as np
import pandas as pd
import pytest

from scheduling_engine import public_data as pub


def _raw_row(**overrides):
    row = {
        "ID": "0x1", "Delivery_person_ID": "CITYRES01DEL01", "Delivery_person_Age": "30",
        "Delivery_person_Ratings": "4.5", "Restaurant_latitude": 12.90, "Restaurant_longitude": 77.60,
        "Delivery_location_latitude": 12.95, "Delivery_location_longitude": 77.65,
        "Order_Date": "19-03-2022", "Time_Orderd": "11:30:00", "Time_Order_picked": "11:45:00",
        "Weatherconditions": "conditions Sunny", "Road_traffic_density": "Low ", "Vehicle_condition": 2,
        "Type_of_order": "Snack ", "Type_of_vehicle": "motorcycle ", "multiple_deliveries": "1",
        "Festival": "No ", "City": "Urban ", "Time_taken(min)": "(min) 24",
    }
    row.update(overrides)
    return row


def test_clean_parses_text_fields_and_strips_spaces():
    df, _ = pub.clean(pd.DataFrame([_raw_row()]))
    row = df.iloc[0]
    assert row["time_taken_min"] == 24
    assert row["weather"] == "Sunny"
    assert row["traffic"] == "Low"
    assert row["pickup_wait_min"] == 15
    assert row["order_hour"] == 11
    assert row["distance_km"] == pytest.approx(7.6, abs=0.3)


def test_clean_turns_text_nan_into_real_missing_values():
    df, report = pub.clean(pd.DataFrame([_raw_row(Road_traffic_density="NaN ", Weatherconditions="conditions NaN",
                                                  Delivery_person_Age="NaN ")]))
    assert pd.isna(df.iloc[0]["traffic"])
    assert pd.isna(df.iloc[0]["weather"])
    assert np.isnan(df.iloc[0]["courier_age"])
    assert report.text_nan_converted == 3


def test_clean_fixes_negative_coordinates_and_drops_zero_ones():
    fixed, report = pub.clean(pd.DataFrame([_raw_row(Restaurant_latitude=-12.90)]))
    assert fixed.iloc[0]["distance_km"] == pytest.approx(7.6, abs=0.3)
    assert report.negative_coordinates_sign_fixed == 1
    unknown, _ = pub.clean(pd.DataFrame([_raw_row(Restaurant_latitude=0.0)]))
    assert np.isnan(unknown.iloc[0]["distance_km"])


def test_clean_sets_impossible_ratings_missing():
    df, report = pub.clean(pd.DataFrame([_raw_row(Delivery_person_Ratings="6")]))
    assert np.isnan(df.iloc[0]["courier_rating"])
    assert report.invalid_ratings_set_missing == 1


def test_multiplicative_effects_recover_a_planted_traffic_effect():
    """If jams make every delivery exactly 1.5x longer, the estimate must say 1.5."""
    rng = np.random.default_rng(0)
    rows = []
    for i in range(400):
        traffic = "Jam " if i % 2 else "Low "
        weather = "conditions Sunny" if i % 3 else "conditions Fog"
        lat = 12.90 + rng.uniform(0.01, 0.1)
        base = 20 * (1.5 if traffic == "Jam " else 1.0) * (1.2 if "Fog" in weather else 1.0)
        rows.append(_raw_row(Road_traffic_density=traffic, Weatherconditions=weather,
                             Delivery_location_latitude=lat, Delivery_person_Age=str(rng.integers(20, 40)),
                             **{"Time_taken(min)": f"(min) {round(base)}"}))
    df, _ = pub.clean(pd.DataFrame(rows))
    effects = {e.name: e for e in pub.multiplicative_effects(df, n_boot=20)}
    assert effects["traffic = Jam"].factor == pytest.approx(1.5, abs=0.02)
    assert effects["weather = Fog"].factor == pytest.approx(1.2, abs=0.02)
