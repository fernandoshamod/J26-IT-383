"""
External validation + calibration on a PUBLIC dataset (Kaggle Food
Delivery Dataset, 45,593 deliveries — see scheduling_engine/public_data.py
for what it is, what it isn't, and its provenance caveat).

  A. Same pipeline as our event models, on data we did not generate:
     clean -> chronological split -> GroupKFold tuning (grouped by day) ->
     XGBoost vs 3 baselines on held-out last 1.5 weeks -> SHAP.
  B. Calibration: multiplicative traffic / weather / distance effects on
     travel time (log-linear regression, bootstrap 95% CI), compared with
     the values history_generation.py originally ASSUMED for vendor
     lateness and now uses.

Outputs: results/public/metrics.json and figures.

Run from the repository root (downloads ~2 MB on first run, no login):
    python -m examples.validate_on_public_data
"""

from __future__ import annotations

import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from sklearn.linear_model import LinearRegression

from examples.train_prediction_models import ACCENT, INK, INK_MUTED, NEUTRAL, _comparison_bars, _importance_bars, _print_table, _style
from scheduling_engine import public_data as pub
from scheduling_engine.duration_prediction import (
    TrainedModel,
    _as_feature_frame,
    _linear_design,
    _new_estimator,
    _tune,
    regression_metrics,
)
from scheduling_engine.history_generation import (
    ASSUMED_BEFORE_CALIBRATION,
    DISTANCE_KM_PER_DOUBLING,
    RAINY_MONTH_LATENESS_FACTOR,
    RUSH_HOUR_LATENESS_FACTOR,
)

RESULTS_DIR = Path(__file__).resolve().parent.parent / "results" / "public"


def _effects_plot(path: Path, effects: list[pub.EffectEstimate]) -> None:
    """Estimated factors with 95% CI; our before/after generator values marked."""
    compare = {
        "traffic = Jam": ("rush hour", ASSUMED_BEFORE_CALIBRATION["RUSH_HOUR_LATENESS_FACTOR"],
                          RUSH_HOUR_LATENESS_FACTOR),
        "weather = Stormy": ("rainy month", ASSUMED_BEFORE_CALIBRATION["RAINY_MONTH_LATENESS_FACTOR"],
                             RAINY_MONTH_LATENESS_FACTOR),
        "+10 km distance": ("+10 km", 2 ** (10 / ASSUMED_BEFORE_CALIBRATION["DISTANCE_KM_PER_DOUBLING"]),
                            2 ** (10 / DISTANCE_KM_PER_DOUBLING)),
    }
    fig, ax = plt.subplots(figsize=(8, 4.6))
    names = [e.name for e in effects][::-1]
    for i, e in enumerate(effects[::-1]):
        ax.plot([e.ci_low, e.ci_high], [i, i], color=ACCENT, linewidth=2)
        ax.plot(e.factor, i, "o", color=ACCENT, markersize=7)
        if e.name in compare:
            label, before, after = compare[e.name]
            ax.plot(before, i, "x", color=INK_MUTED, markersize=8, markeredgewidth=2)
            ax.text(before, i + 0.25, f"assumed {before:.2f}", color=INK_MUTED, fontsize=8, ha="center")
    ax.axvline(1.0, color=NEUTRAL, linewidth=1)
    ax.set_yticks(range(len(names)))
    ax.set_yticklabels(names)
    _style(ax, "Travel-time multipliers in 45,593 public deliveries",
           "times longer than reference (Low traffic, Sunny), other factors held fixed")
    ax.grid(axis="y", visible=False)
    ax.plot([], [], "o-", color=ACCENT, label="estimate with 95% CI")
    ax.plot([], [], "x", color=INK_MUTED, markeredgewidth=2, label="our original assumption")
    ax.legend(frameon=False, loc="lower right")
    fig.tight_layout()
    fig.savefig(path, dpi=160)
    plt.close(fig)


def main() -> None:
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    folder = pub.download()
    raw = pd.read_csv(Path(folder) / "train.csv")
    print(f"Kaggle '{pub.KAGGLE_HANDLE}': {len(raw)} rows, {raw.shape[1]} columns "
          "(test.csv has no labels, so only train.csv is used)\n")

    df, report = pub.clean(raw)
    print("1. Cleaning (real, messy public data)")
    for line in report.lines():
        print("   " + line)

    train, test = pub.chronological_split(df)
    print(f"\n2. Chronological split at {pub.TEST_FROM_DATE}: train {len(train)} rows "
          f"({train['order_date'].nunique()} days), test {len(test)} rows ({test['order_date'].nunique()} days)")

    levels = {c: sorted(df[c].dropna().unique().tolist()) for c in pub.CATEGORICAL}
    x_train = _as_feature_frame(train, pub.CATEGORICAL, pub.NUMERIC, levels)
    print("\n3. Tuning: same 8-point grid, 5-fold GroupKFold grouped by DAY (same-day orders share conditions)")
    best_params, trees, cv_mae, grid = _tune("regression", x_train, train[pub.TARGET], train["order_date"])
    estimator = _new_estimator("regression", best_params, trees, early_stopping=False).fit(x_train, train[pub.TARGET])
    model = TrainedModel("public_delivery", "regression", estimator, pub.CATEGORICAL, pub.NUMERIC,
                         pub.TARGET, levels, best_params, trees, cv_mae)
    print(f"   best {best_params}, {trees} trees, CV MAE {cv_mae:.2f} min")

    y = train[pub.TARGET]
    lookup = y.groupby([train["traffic"], train["weather"]]).median()
    keys = list(zip(test["traffic"], test["weather"]))
    x_lin_train, x_lin_test = _linear_design(train, test, pub.CATEGORICAL, pub.NUMERIC)
    predictions = {
        "B0 overall median": np.full(len(test), y.median()),
        "B1 median by traffic x weather": np.array([lookup.get(k, y.median()) for k in keys], dtype=float),
        "B2 linear regression": np.clip(LinearRegression().fit(x_lin_train, y).predict(x_lin_test), 0, None),
        "XGBoost": model.predict(test),
    }
    model.test_metrics = {k: regression_metrics(test[pub.TARGET], v) for k, v in predictions.items()}
    model.test_predictions = test.assign(predicted=predictions["XGBoost"])
    _print_table("4. Held-out test (last 1.5 weeks) — delivery time, minutes", model.test_metrics)

    importance = model.feature_importance()
    print("\n5. SHAP importance (minutes): " + ", ".join(f"{k} {v:.2f}" for k, v in importance.items()))

    print("\n6. Calibration: multiplicative effects, other factors held fixed (bootstrap 95% CI)")
    effects = pub.multiplicative_effects(df)
    for e in effects:
        print(f"   {e.name:<22} x{e.factor:.3f}  [{e.ci_low:.3f}, {e.ci_high:.3f}]")
    print("\n   Generator constants (history_generation.py):")
    print(f"     RUSH_HOUR_LATENESS_FACTOR    assumed {ASSUMED_BEFORE_CALIBRATION['RUSH_HOUR_LATENESS_FACTOR']}"
          f" -> calibrated {RUSH_HOUR_LATENESS_FACTOR}   (traffic = Jam)")
    print(f"     RAINY_MONTH_LATENESS_FACTOR  assumed {ASSUMED_BEFORE_CALIBRATION['RAINY_MONTH_LATENESS_FACTOR']}"
          f" -> calibrated {RAINY_MONTH_LATENESS_FACTOR}   (weather = Stormy)")
    print(f"     DISTANCE_KM_PER_DOUBLING     assumed {ASSUMED_BEFORE_CALIBRATION['DISTANCE_KM_PER_DOUBLING']}"
          f"  -> calibrated {DISTANCE_KM_PER_DOUBLING}    (+10 km effect)")

    _comparison_bars(RESULTS_DIR / "public_model_comparison.png", model.test_metrics, "MAE",
                     "Public delivery data: prediction error on held-out weeks",
                     "mean absolute error (minutes) — lower is better")
    _importance_bars(RESULTS_DIR / "public_feature_importance.png", importance,
                     "What drives delivery time? (public data)", "mean |SHAP| (minutes)")
    _effects_plot(RESULTS_DIR / "public_calibration_effects.png", effects)
    (RESULTS_DIR / "metrics.json").write_text(json.dumps(dict(
        dataset=dict(kaggle=pub.KAGGLE_HANDLE, rows=len(raw)),
        cleaning=report.__dict__,
        split=dict(test_from=pub.TEST_FROM_DATE, train_rows=len(train), test_rows=len(test)),
        best_params=best_params, n_trees=trees, cv_mae=cv_mae, grid=grid,
        test=model.test_metrics,
        shap_importance=importance.round(4).to_dict(),
        effects=[e.__dict__ for e in effects],
    ), indent=2, default=float))
    print(f"\nSaved figures + metrics.json to results/public/")


if __name__ == "__main__":
    main()
