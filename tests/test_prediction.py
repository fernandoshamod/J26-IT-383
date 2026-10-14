"""Tests for the historical-data generator, cleaning, and prediction models."""

import pandas as pd
import pytest

from scheduling_engine import duration_prediction as dp
from scheduling_engine.data_preparation import (
    canonical_activity,
    clean_activity_records,
    clean_arrival_records,
)
from scheduling_engine.history_generation import ACTIVITY_PROFILES, NAME_VARIANTS, generate_history
from scheduling_engine.models import Activity, Event


@pytest.fixture(scope="module")
def history():
    activities, arrivals = generate_history(n_events=200, seed=7)
    return clean_activity_records(activities)[0], clean_arrival_records(arrivals)[0]


@pytest.fixture(scope="module")
def models(history):
    # One grid point keeps the test fast; the full grid runs in the script.
    original = dp.PARAM_GRID
    dp.PARAM_GRID = {"max_depth": [3], "learning_rate": [0.1], "min_child_weight": [5]}
    try:
        yield dp.train_duration_model(history[0])[0], dp.train_lateness_model(history[1])[0]
    finally:
        dp.PARAM_GRID = original


def test_generator_is_deterministic_for_a_seed():
    a1, v1 = generate_history(n_events=30, seed=3)
    a2, v2 = generate_history(n_events=30, seed=3)
    pd.testing.assert_frame_equal(a1, a2)
    pd.testing.assert_frame_equal(v1, v2)


def test_vendor_history_features_only_use_earlier_events():
    """A vendor's prior-job count must start at 0 and only ever grow over
    time — otherwise the feature is leaking information from the future."""
    _, arrivals = generate_history(n_events=150, seed=11)
    for _, rows in arrivals.groupby("vendor_id"):
        jobs = rows.sort_values(["event_date", "event_id"])["vendor_prior_jobs"].tolist()
        assert jobs[0] == 0
        assert jobs == list(range(len(jobs)))
        assert pd.isna(rows.sort_values(["event_date", "event_id"])["vendor_prior_mean_lateness"].iloc[0])


def test_every_injected_name_variant_maps_back_to_its_activity():
    for canonical, variants in NAME_VARIANTS.items():
        assert canonical_activity(canonical) == canonical
        for variant in variants:
            assert canonical_activity(variant) == canonical, variant


def test_cleaning_drops_impossible_and_unknown_rows_but_keeps_missing_values():
    raw = pd.DataFrame([
        dict(activity_name="Catering Load-in", planned_duration_minutes=45, actual_duration_minutes=50, guest_count=100),
        dict(activity_name="dinner", planned_duration_minutes=60, actual_duration_minutes=0, guest_count=100),
        dict(activity_name="dinner", planned_duration_minutes=60, actual_duration_minutes=700, guest_count=100),
        dict(activity_name="fireworks", planned_duration_minutes=10, actual_duration_minutes=10, guest_count=100),
        dict(activity_name="Photos", planned_duration_minutes=45, actual_duration_minutes=55, guest_count=None),
    ])
    clean, report = clean_activity_records(raw)
    assert clean["activity_type"].tolist() == ["catering_load_in", "photos"]
    assert report.dropped_impossible_duration == 2
    assert report.dropped_unknown_name == 1
    assert report.missing_values_kept["guest_count"] == 1
    assert set(clean["activity_type"]) <= set(ACTIVITY_PROFILES)


def test_features_never_include_targets_or_oracle_columns():
    for features, target in [
        (dp.DURATION_CATEGORICAL + dp.DURATION_NUMERIC, dp.DURATION_TARGET),
        (dp.LATENESS_CATEGORICAL + dp.LATENESS_NUMERIC, dp.LATENESS_TARGET),
    ]:
        assert target not in features
        assert "lateness_minutes" not in features
        assert "actual_duration_minutes" not in features
        assert not any(f.startswith("oracle_") for f in features)


def test_chronological_split_has_no_overlap(history):
    train, test = dp.chronological_split(history[0])
    assert train["event_date"].max() < test["event_date"].min()
    assert not set(train["event_id"]) & set(test["event_id"])


def test_duration_model_beats_the_planners_estimate(models):
    metrics = models[0].test_metrics
    assert metrics["XGBoost"]["MAE"] < metrics["B0 planner estimate (today's practice)"]["MAE"]
    # ... but can't beat the theoretical best by more than noise.
    assert metrics["XGBoost"]["MAE"] > metrics["Oracle ceiling (knows hidden truth)"]["MAE"] * 0.95


def test_lateness_model_ranks_better_than_chance(models):
    assert models[1].test_metrics["XGBoost"]["ROC_AUC"] > 0.65


def test_shap_contributions_sum_to_the_prediction(models):
    duration = models[0]
    sample = duration.test_predictions.head(20)
    total = duration.contributions(sample).sum(axis=1).to_numpy()
    assert total == pytest.approx(duration.estimator.predict(duration.frame(sample)), abs=1e-3)


def test_save_and_load_give_identical_predictions(models, tmp_path):
    for model in models:
        model.save(tmp_path)
        loaded = dp.TrainedModel.load(tmp_path, model.name)
        sample = model.test_predictions.head(50)
        assert loaded.predict(sample) == pytest.approx(model.predict(sample))


def test_predicted_durations_round_up_to_5_and_skip_unknown_activities(models):
    event = Event("e", "Test", [
        Activity("setup", "e", "Setup", 90),
        Activity("magic_show", "e", "Magic show", 25),
    ])
    context = dp.EventContext("2026-10-24", "wedding", 250, "outdoor")
    predicted = dp.predict_event_durations(models[0], event, context, {"setup": "venue_setup"})
    assert set(predicted) == {"setup"}
    assert predicted["setup"] % 5 == 0

    updated = dp.with_predicted_durations(event, predicted)
    assert updated.activities[0].duration_minutes == predicted["setup"]
    assert updated.activities[1].duration_minutes == 25
    assert event.activities[0].duration_minutes == 90  # original untouched
