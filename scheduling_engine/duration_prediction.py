"""
Activity-duration and vendor-lateness prediction (proposal Section 4.2.1;
Section 3.2 "gradient boosting is selected over deep sequence models
because the available data is tabular, heterogeneous and scarce"; WBS
task 3.6 "Feature engineering; gradient boosting model; evaluation").

Two supervised models, both XGBoost (Chen & Guestrin, 2016):

  DURATION model (regression)  — predicts an activity's ACTUAL duration
      in minutes from what the planner knows when planning: activity
      type, the planner's own estimate, guest count, venue, month, crew
      size, vendor experience.

  LATENESS model (classification) — predicts the PROBABILITY that a
      vendor arrives more than the digital twin's tolerance (10 min)
      late, from: vendor category, booked arrival hour, travel distance,
      month, and the vendor's own PAST record.
      Why classification and not "minutes late"? About 60% of arrivals
      are on time (0 min) and the rest have a long, noisy tail, so an
      exact-minutes regression barely beat "assume on time" (MAE 10.6 vs
      10.8 in our first experiment). The twin doesn't need exact minutes
      anyway — it needs "will this vendor cross my tolerance?", which is a
      yes/no question with a probability attached.

Where they plug in:
  * predicted durations replace the planner's guesses as the
    `duration_minutes` the CP-SAT solver schedules with (duration is
    input data to the solver; producing it is this module's job);
  * the late-arrival probability flags, before the event day, which
    vendor bookings are likely to trigger a twin divergence.

Evaluation design (each choice stops the model looking better than it is):
  * CHRONOLOGICAL split — train on 2022-2024 events, test on 2025. In real
    use the model predicts the future from the past; a random split would
    let it peek at "future" events.
  * GROUPED cross-validation for tuning (GroupKFold by event_id) — one
    event's activities share guest count, venue and weather, so splitting
    an event across train and validation would leak.
  * The test set is touched exactly ONCE, after tuning is finished.
  * Three baselines, including today's practice (trust the planned
    duration / assume the vendor is on time).
  * An ORACLE ceiling (synthetic data only): the best score any model
    could get, so "how good is good?" has an answer.
"""

from __future__ import annotations

import json
import math
from dataclasses import dataclass, field, replace
from itertools import product
from pathlib import Path

import numpy as np
import pandas as pd
import xgboost as xgb
from sklearn.linear_model import LinearRegression, LogisticRegression
from sklearn.metrics import (
    average_precision_score,
    brier_score_loss,
    mean_absolute_error,
    mean_squared_error,
    r2_score,
    roc_auc_score,
)
from sklearn.model_selection import GroupKFold

from scheduling_engine.history_generation import LATENESS_TOLERANCE_MINUTES, RAINY_MONTHS, RUSH_HOURS
from scheduling_engine.models import Event

TEST_FROM_DATE = "2025-01-01"
RANDOM_STATE = 42

# --- Feature lists --------------------------------------------------------
# Only information available at PLANNING time. The actual duration, the
# day-of weather, or anything recorded during the event is NOT a feature.

DURATION_CATEGORICAL = ["activity_type", "event_type", "venue_type"]
DURATION_NUMERIC = [
    "planned_duration_minutes",
    "guest_count",
    "crew_size",
    "is_rainy_month",
    "is_weekend",
    "planned_start_hour",
    "vendor_prior_jobs",
]
DURATION_TARGET = "actual_duration_minutes"

LATENESS_CATEGORICAL = ["vendor_category"]
LATENESS_NUMERIC = [
    "booked_arrival_hour",
    "is_rush_hour",
    "is_rainy_month",
    "is_weekend",
    "travel_distance_km",
    "vendor_prior_jobs",
    "vendor_prior_mean_lateness",
]
LATENESS_TARGET = "late_beyond_tolerance"  # 1 if lateness_minutes > tolerance

# Small, explainable hyperparameter grid (8 combinations). n_estimators is
# NOT in the grid: early stopping on each validation fold picks it.
PARAM_GRID = {
    "max_depth": [3, 5],
    "learning_rate": [0.05, 0.1],
    "min_child_weight": [1, 5],
}
MAX_TREES = 1000
EARLY_STOPPING_ROUNDS = 50


# --- Feature engineering --------------------------------------------------

def add_calendar_features(df: pd.DataFrame) -> pd.DataFrame:
    d = pd.to_datetime(df["event_date"])
    out = df.assign(
        is_rainy_month=d.dt.month.isin(RAINY_MONTHS).astype(int),
        is_weekend=(d.dt.dayofweek >= 5).astype(int),
    )
    if "booked_arrival_hour" in out:
        out["is_rush_hour"] = out["booked_arrival_hour"].isin(RUSH_HOURS).astype(int)
    if "lateness_minutes" in out:
        out[LATENESS_TARGET] = (out["lateness_minutes"] > LATENESS_TOLERANCE_MINUTES).astype(int)
    return out


def _as_feature_frame(df: pd.DataFrame, categorical: list[str], numeric: list[str],
                      levels: dict[str, list[str]]) -> pd.DataFrame:
    """Fix column order and category levels so training and prediction
    always see the same encoding (an unseen level becomes missing)."""
    x = pd.DataFrame(index=df.index)
    for c in categorical:
        x[c] = pd.Categorical(df[c], categories=levels[c])
    for c in numeric:
        x[c] = pd.to_numeric(df[c], errors="coerce").astype(float)
    return x


# --- Metrics --------------------------------------------------------------

def regression_metrics(y_true, y_pred) -> dict[str, float]:
    y_true = np.asarray(y_true, dtype=float)
    y_pred = np.asarray(y_pred, dtype=float)
    return {
        "MAE": float(mean_absolute_error(y_true, y_pred)),
        "RMSE": float(math.sqrt(mean_squared_error(y_true, y_pred))),
        "R2": float(r2_score(y_true, y_pred)),
        "within_10_min_pct": float(100 * np.mean(np.abs(y_true - y_pred) <= 10)),
    }


def classification_metrics(y_true, p_pred) -> dict[str, float]:
    """ROC-AUC: how well the model RANKS risky bookings above safe ones
    (0.5 = coin flip, 1.0 = perfect). Average precision: same idea, but
    focused on the positive (late) class. Brier: mean squared error of the
    probability itself — lower is better, rewards honest probabilities."""
    y_true = np.asarray(y_true, dtype=int)
    p_pred = np.asarray(p_pred, dtype=float)
    return {
        "ROC_AUC": float(roc_auc_score(y_true, p_pred)),
        "avg_precision": float(average_precision_score(y_true, p_pred)),
        "Brier": float(brier_score_loss(y_true, p_pred)),
    }


# --- The trained-model wrapper --------------------------------------------

@dataclass
class TrainedModel:
    """Everything needed to use, explain and re-load one trained model."""

    name: str
    kind: str  # "regression" or "classification"
    estimator: xgb.XGBModel
    categorical: list[str]
    numeric: list[str]
    target: str
    levels: dict[str, list[str]]
    best_params: dict
    n_trees: int
    cv_score: float
    test_metrics: dict[str, dict[str, float]] = field(default_factory=dict)
    test_predictions: pd.DataFrame | None = None

    @property
    def features(self) -> list[str]:
        return self.categorical + self.numeric

    def frame(self, df: pd.DataFrame) -> pd.DataFrame:
        return _as_feature_frame(df, self.categorical, self.numeric, self.levels)

    def predict(self, df: pd.DataFrame) -> np.ndarray:
        """Minutes (regression, never negative) or probability (classification)."""
        if self.kind == "classification":
            return self.estimator.predict_proba(self.frame(df))[:, 1]
        return np.clip(self.estimator.predict(self.frame(df)), 0, None)

    def contributions(self, df: pd.DataFrame) -> pd.DataFrame:
        """Per-feature contribution to each prediction — exact TreeSHAP
        values computed by XGBoost itself (Lundberg & Lee, 2017). For the
        regression model the unit is minutes; for the classifier it is
        log-odds. Row sum (including 'bias') = the raw prediction."""
        dm = xgb.DMatrix(self.frame(df), enable_categorical=True)
        values = self.estimator.get_booster().predict(dm, pred_contribs=True)
        return pd.DataFrame(values, columns=self.features + ["bias"], index=df.index)

    def feature_importance(self, df: pd.DataFrame | None = None) -> pd.Series:
        """Mean |SHAP| (on the test set by default): how much, on average,
        each feature moves a prediction. Easier to explain than XGBoost's
        built-in 'gain'."""
        df = self.test_predictions if df is None else df
        return self.contributions(df).drop(columns="bias").abs().mean().sort_values(ascending=False)

    def save(self, directory: Path) -> None:
        directory.mkdir(parents=True, exist_ok=True)
        self.estimator.save_model(directory / f"{self.name}_xgb.json")
        meta = dict(name=self.name, kind=self.kind, categorical=self.categorical,
                    numeric=self.numeric, target=self.target, levels=self.levels,
                    best_params=self.best_params, n_trees=self.n_trees,
                    cv_score=self.cv_score, test_metrics=self.test_metrics)
        (directory / f"{self.name}_meta.json").write_text(json.dumps(meta, indent=2))

    @classmethod
    def load(cls, directory: Path, name: str) -> "TrainedModel":
        meta = json.loads((directory / f"{name}_meta.json").read_text())
        estimator_cls = xgb.XGBClassifier if meta["kind"] == "classification" else xgb.XGBRegressor
        estimator = estimator_cls(enable_categorical=True)
        estimator.load_model(directory / f"{name}_xgb.json")
        return cls(name=name, kind=meta["kind"], estimator=estimator,
                   categorical=meta["categorical"], numeric=meta["numeric"],
                   target=meta["target"], levels=meta["levels"],
                   best_params=meta["best_params"], n_trees=meta["n_trees"],
                   cv_score=meta["cv_score"], test_metrics=meta["test_metrics"])


# --- Training -------------------------------------------------------------

def _new_estimator(kind: str, params: dict, n_estimators: int, early_stopping: bool) -> xgb.XGBModel:
    common = dict(
        tree_method="hist",
        enable_categorical=True,
        n_estimators=n_estimators,
        early_stopping_rounds=EARLY_STOPPING_ROUNDS if early_stopping else None,
        subsample=0.8,          # each tree sees 80% of rows ...
        colsample_bytree=0.8,   # ... and 80% of features: less overfitting
        random_state=RANDOM_STATE,
        n_jobs=4,
        **params,
    )
    if kind == "classification":
        return xgb.XGBClassifier(objective="binary:logistic", eval_metric="logloss", **common)
    # Optimise MAE directly: robust to the long right tail of overruns.
    return xgb.XGBRegressor(objective="reg:absoluteerror", **common)


def _validation_score(kind: str, y_true, model, x) -> float:
    """Lower is better for both kinds."""
    if kind == "classification":
        return brier_score_loss(y_true, model.predict_proba(x)[:, 1])
    return mean_absolute_error(y_true, model.predict(x))


def _tune(kind: str, x: pd.DataFrame, y: pd.Series, groups: pd.Series) -> tuple[dict, int, float, list[dict]]:
    """Grid search with 5-fold GroupKFold + early stopping. Returns the
    best params, the tree count to use, its mean CV score, and the full
    table of every combination tried (for the report)."""
    folds = list(GroupKFold(n_splits=5).split(x, y, groups))
    table = []
    for values in product(*PARAM_GRID.values()):
        params = dict(zip(PARAM_GRID, values))
        scores, trees = [], []
        for train_idx, val_idx in folds:
            model = _new_estimator(kind, params, MAX_TREES, early_stopping=True)
            model.fit(x.iloc[train_idx], y.iloc[train_idx],
                      eval_set=[(x.iloc[val_idx], y.iloc[val_idx])], verbose=False)
            scores.append(_validation_score(kind, y.iloc[val_idx], model, x.iloc[val_idx]))
            trees.append(model.best_iteration + 1)
        table.append(dict(params, cv_score=float(np.mean(scores)), trees=int(np.mean(trees))))
    best = min(table, key=lambda r: r["cv_score"])
    return {k: best[k] for k in PARAM_GRID}, best["trees"], best["cv_score"], table


def chronological_split(df: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    is_test = df["event_date"] >= TEST_FROM_DATE
    return df[~is_test].reset_index(drop=True), df[is_test].reset_index(drop=True)


def _linear_design(train: pd.DataFrame, test: pd.DataFrame, categorical: list[str],
                   numeric: list[str]) -> tuple[pd.DataFrame, pd.DataFrame]:
    """One-hot categories + median-imputed numbers, for the linear baselines
    (which, unlike XGBoost, can't handle missing values or categories)."""
    medians = train[numeric].apply(pd.to_numeric, errors="coerce").median()

    def design(df: pd.DataFrame) -> pd.DataFrame:
        nums = df[numeric].apply(pd.to_numeric, errors="coerce").fillna(medians)
        cats = pd.get_dummies(df[categorical].astype(str), dtype=float)
        return pd.concat([nums, cats], axis=1)

    x_train = design(train)
    return x_train, design(test).reindex(columns=x_train.columns, fill_value=0.0)


def _fit(kind: str, name: str, df: pd.DataFrame, categorical: list[str], numeric: list[str],
         target: str) -> tuple[TrainedModel, pd.DataFrame, pd.DataFrame, list[dict]]:
    train, test = chronological_split(df)
    levels = {c: sorted(df[c].dropna().unique().tolist()) for c in categorical}
    x_train = _as_feature_frame(train, categorical, numeric, levels)
    best_params, trees, cv_score, table = _tune(kind, x_train, train[target], train["event_id"])
    estimator = _new_estimator(kind, best_params, trees, early_stopping=False).fit(x_train, train[target])
    model = TrainedModel(name, kind, estimator, categorical, numeric, target, levels,
                         best_params, trees, cv_score)
    return model, train, test, table


def train_duration_model(activities: pd.DataFrame) -> tuple[TrainedModel, list[dict]]:
    df = add_calendar_features(activities)
    model, train, test, table = _fit("regression", "duration", df, DURATION_CATEGORICAL,
                                     DURATION_NUMERIC, DURATION_TARGET)
    y = train[DURATION_TARGET]

    # Baselines, all fitted on TRAIN only.
    # B1 "photos usually take 1.25x what we plan", learned per activity type.
    ratio = (y / train["planned_duration_minutes"]).groupby(train["activity_type"]).mean()
    x_lin_train, x_lin_test = _linear_design(train, test, DURATION_CATEGORICAL, DURATION_NUMERIC)
    predictions = {
        "B0 planner estimate (today's practice)": test["planned_duration_minutes"].to_numpy(float),
        "B1 per-activity overrun ratio": (test["planned_duration_minutes"]
                                          * test["activity_type"].map(ratio).fillna(1.0)).to_numpy(float),
        "B2 linear regression": np.clip(LinearRegression().fit(x_lin_train, y).predict(x_lin_test), 0, None),
        "XGBoost": model.predict(test),
    }
    if "oracle_duration_minutes" in test:
        predictions["Oracle ceiling (knows hidden truth)"] = test["oracle_duration_minutes"].to_numpy(float)
    model.test_metrics = {k: regression_metrics(test[DURATION_TARGET], v) for k, v in predictions.items()}
    model.test_predictions = test.assign(predicted=predictions["XGBoost"])
    return model, table


def train_lateness_model(arrivals: pd.DataFrame) -> tuple[TrainedModel, list[dict]]:
    df = add_calendar_features(arrivals)
    model, train, test, table = _fit("classification", "lateness", df, LATENESS_CATEGORICAL,
                                     LATENESS_NUMERIC, LATENESS_TARGET)
    y = train[LATENESS_TARGET]

    # B0 has no ranking at all (every booking gets the same score), so its
    # AUC is exactly 0.5; we give it the training late-rate as its
    # probability so its Brier score is the fair "know nothing" reference.
    # B1 "this vendor is often late": the vendor's own past late-rate.
    vendor_rate = y.groupby(train["vendor_id"]).mean()
    x_lin_train, x_lin_test = _linear_design(train, test, LATENESS_CATEGORICAL, LATENESS_NUMERIC)
    logistic = LogisticRegression(max_iter=2000).fit(x_lin_train, y)
    predictions = {
        "B0 no information (today's practice)": np.full(len(test), y.mean()),
        "B1 vendor's past late-rate": test["vendor_id"].map(vendor_rate).fillna(y.mean()).to_numpy(float),
        "B2 logistic regression": logistic.predict_proba(x_lin_test)[:, 1],
        "XGBoost": model.predict(test),
    }
    if "oracle_p_late_beyond_tolerance" in test:
        predictions["Oracle ceiling (knows hidden truth)"] = test["oracle_p_late_beyond_tolerance"].to_numpy(float)
    model.test_metrics = {k: classification_metrics(test[LATENESS_TARGET], v) for k, v in predictions.items()}
    model.test_predictions = test.assign(predicted=predictions["XGBoost"])
    return model, table


# --- Using the models in the scheduling pipeline --------------------------

@dataclass(frozen=True)
class EventContext:
    """What the planner knows about an upcoming event."""

    event_date: str          # "2026-10-24"
    event_type: str          # "wedding"
    guest_count: int | None
    venue_type: str          # "indoor" / "outdoor"
    crew_size: int = 2


def predict_event_durations(model: TrainedModel, event: Event, context: EventContext,
                            activity_types: dict[str, str], start_hours: dict[str, int] | None = None,
                            vendor_prior_jobs: dict[str, int] | None = None) -> dict[str, int]:
    """Predicted minutes per activity id. `activity_types` maps each
    activity id to one of the trained activity types; activities with no
    mapping keep their planned duration (the model has never seen them,
    so it shouldn't guess)."""
    start_hours = start_hours or {}
    vendor_prior_jobs = vendor_prior_jobs or {}
    rows = []
    for a in event.activities:
        if a.id not in activity_types:
            continue
        rows.append(dict(
            activity_id=a.id, activity_type=activity_types[a.id], event_type=context.event_type,
            venue_type=context.venue_type, planned_duration_minutes=a.duration_minutes,
            guest_count=context.guest_count, crew_size=context.crew_size,
            event_date=context.event_date, planned_start_hour=start_hours.get(a.id, 12),
            vendor_prior_jobs=vendor_prior_jobs.get(a.id),
        ))
    if not rows:
        return {}
    df = add_calendar_features(pd.DataFrame(rows))
    # Round UP to the next 5 minutes: a slot slightly too long is cheap,
    # one slightly too short starts a cascade.
    predicted = np.ceil(model.predict(df) / 5.0) * 5
    return {aid: int(p) for aid, p in zip(df["activity_id"], predicted)}


def with_predicted_durations(event: Event, predicted: dict[str, int]) -> Event:
    """A copy of `event` whose activity durations are the predictions."""
    return replace(event, activities=[
        replace(a, duration_minutes=predicted.get(a.id, a.duration_minutes)) for a in event.activities
    ])


@dataclass(frozen=True)
class VendorBooking:
    """One upcoming vendor booking to risk-score."""

    activity_id: str
    vendor_id: str
    vendor_category: str
    booked_arrival_hour: int
    travel_distance_km: float | None
    vendor_prior_jobs: int
    vendor_prior_mean_lateness: float | None


def late_arrival_risk(model: TrainedModel, bookings: list[VendorBooking], event_date: str) -> dict[str, float]:
    """P(vendor arrives more than the twin's tolerance late), per activity id."""
    df = add_calendar_features(pd.DataFrame([{**b.__dict__, "event_date": event_date} for b in bookings]))
    return {aid: float(p) for aid, p in zip(df["activity_id"], model.predict(df))}
