"""
Three more public datasets, each testing or calibrating one assumption of
the event models (see scheduling_engine/public_datasets.py for what each
is and isn't):

  1. Sri Lanka Met Department rain gauges -> which months are rainy (calibrates RAINY_MONTHS)
  2. Olist, 99k real orders, promised vs actual -> late-supplier classifier on real data
  3. SiP, 12k real tasks, estimated vs actual  -> duration model on real data + planning fallacy

Each ML study runs the SAME protocol as the event models: chronological
split, 5-fold GroupKFold tuning on the same 8-point grid, XGBoost vs three
baselines including "today's practice", test set used once, SHAP.

Outputs: results/public_more/metrics.json and figures.
Run from the repository root (downloads ~45 MB on first run, no login):
    python -m examples.validate_on_more_public_data
"""

from __future__ import annotations

import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from sklearn.linear_model import LinearRegression, LogisticRegression
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

from examples.train_prediction_models import ACCENT, INK_MUTED, NEUTRAL, _comparison_bars, _importance_bars, _print_table, _style
from scheduling_engine import public_datasets as pds
from scheduling_engine.duration_prediction import (
    TrainedModel,
    _as_feature_frame,
    _linear_design,
    _new_estimator,
    _tune,
    classification_metrics,
    regression_metrics,
)
from scheduling_engine.history_generation import ASSUMED_RAINY_MONTHS, RAINY_MONTHS

ROOT = Path(__file__).resolve().parent.parent
RESULTS_DIR = ROOT / "results" / "public_more"
SIP_CACHE = Path.home() / ".cache" / "sip_dataset"
MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]


def hours_metrics(y_true, y_pred) -> dict[str, float]:
    """regression_metrics without its 'within 10 minutes' column (SiP is in hours)."""
    out = regression_metrics(y_true, y_pred)
    out.pop("within_10_min_pct")
    out["within_2_hours_pct"] = float(100 * np.mean(np.abs(np.asarray(y_true) - np.asarray(y_pred)) <= 2))
    return out


def fit_and_evaluate(kind: str, name: str, df: pd.DataFrame, categorical: list[str], numeric: list[str],
                     target: str, test_from: str, baselines, metric=None) -> TrainedModel:
    train = df[df["event_date"] < test_from].reset_index(drop=True)
    test = df[df["event_date"] >= test_from].reset_index(drop=True)
    print(f"   split at {test_from}: train {len(train)} rows, test {len(test)} rows")
    levels = {c: sorted(df[c].dropna().astype(str).unique().tolist()) for c in categorical}
    for frame in (train, test):
        for c in categorical:
            frame[c] = frame[c].astype("string")
    x_train = _as_feature_frame(train, categorical, numeric, levels)
    params, trees, cv, _ = _tune(kind, x_train, train[target], train["group"])
    est = _new_estimator(kind, params, trees, early_stopping=False).fit(x_train, train[target])
    model = TrainedModel(name, kind, est, categorical, numeric, target, levels, params, trees, cv)
    print(f"   best {params}, {trees} trees, CV {'Brier' if kind == 'classification' else 'MAE'} {cv:.3f}")

    predictions = baselines(train, test)
    predictions["XGBoost"] = model.predict(test)
    metric = metric or (classification_metrics if kind == "classification" else regression_metrics)
    model.test_metrics = {k: metric(test[target], v) for k, v in predictions.items()}
    model.test_predictions = test.assign(predicted=predictions["XGBoost"])
    return model


def rainfall_study() -> dict:
    print("\n=== 1. Sri Lanka rainfall: which months are rainy in Colombo? ===")
    gauges = pds.load_colombo_gauges()
    clim = pds.monthly_rain_climatology(gauges)
    print(f"   {len(gauges)} station-days from {gauges['station_name'].nunique()} Met Department gauges "
          f"({gauges['year'].min()}-{gauges['year'].max()}), {int(gauges['rain_mm'].isna().sum())} missing readings dropped")
    model = pds.load_colombo_model_data()
    model_monthly = model.groupby("month")["precipitation_sum"].mean() * 30.4
    model_wet = model.groupby("month")["precipitation_sum"].apply(lambda s: (s >= pds.WET_DAY_MM).mean())
    corr = float(np.corrcoef(clim["mean_monthly_mm"], model_monthly)[0, 1])
    print(f"   {'month':<6}{'gauge mm':>10}{'P(wet day)':>12}{'rainy?':>8}{'model mm':>10}{'model P(wet)':>14}")
    for m, row in clim.iterrows():
        print(f"   {MONTHS[m - 1]:<6}{row['mean_monthly_mm']:>10.0f}{row['wet_day_probability']:>12.2f}"
              f"{'yes' if row['rainy_by_rule'] else '':>8}{model_monthly[m]:>10.0f}{model_wet[m]:>14.2f}")
    data_months = sorted(int(m) for m in clim.index[clim["rainy_by_rule"]])
    print(f"\n   Rule: rainy if it rains (>= {pds.WET_DAY_MM:g} mm) on more than half the days.")
    print(f"   Assumed before: {sorted(ASSUMED_RAINY_MONTHS)} -> data says {data_months} -> generator now uses {sorted(RAINY_MONTHS)}")
    print(f"   Model/reanalysis data agrees on the seasonal SHAPE (monthly-total correlation r = {corr:.2f}) but reports "
          f"rain on {model_wet.mean():.0%} of days vs {clim['wet_day_probability'].mean():.0%} at the gauges — "
          "so the gauges are used, the model data only as a cross-check.")

    fig, ax = plt.subplots(figsize=(8, 3.8))
    colors = [ACCENT if r else NEUTRAL for r in clim["rainy_by_rule"]]
    ax.bar(MONTHS, clim["wet_day_probability"], color=colors, width=0.6)
    ax.axhline(pds.RAINY_MONTH_RULE, color=INK_MUTED, linestyle="--", linewidth=1)
    ax.text(-0.4, pds.RAINY_MONTH_RULE + 0.01, "rain on half the days", color=INK_MUTED, fontsize=9, ha="left", va="bottom")
    _style(ax, "Colombo: share of days with rain (Met Dept gauges, 2012-2018)", "", "P(rain >= 1 mm)")
    ax.grid(axis="x", visible=False)
    fig.tight_layout()
    fig.savefig(RESULTS_DIR / "colombo_rainy_months.png", dpi=160)
    plt.close(fig)
    return dict(station_days=len(gauges), climatology=clim.round(4).reset_index().to_dict("records"),
                assumed_rainy_months=sorted(ASSUMED_RAINY_MONTHS), data_rainy_months=data_months,
                gauge_vs_model_monthly_correlation=corr)


def olist_study() -> dict:
    print("\n=== 2. Olist: real supplier lateness against a promised date ===")
    df, report = pds.build_olist(pds.load_olist())
    for k, v in report.items():
        print(f"   {k}: {v:.3f}" if isinstance(v, float) else f"   {k}: {v}")

    def baselines(train, test):
        y = train[pds.OLIST_TARGET]
        x_tr, x_te = _linear_design(train, test, pds.OLIST_CATEGORICAL, pds.OLIST_NUMERIC)
        return {
            "B0 no information (base rate)": np.full(len(test), y.mean()),
            "B1 seller's past late-rate": test["seller_prior_late_rate"].fillna(y.mean()).to_numpy(float),
            "B2 logistic regression": make_pipeline(StandardScaler(), LogisticRegression(max_iter=3000))
                                      .fit(x_tr, y).predict_proba(x_te)[:, 1],
        }

    model = fit_and_evaluate("classification", "olist_late", df, pds.OLIST_CATEGORICAL, pds.OLIST_NUMERIC,
                             pds.OLIST_TARGET, pds.OLIST_TEST_FROM, baselines)
    _print_table("   Held-out test (orders from 2018-06): P(delivered after the promised date)", model.test_metrics)
    imp = model.feature_importance()
    rank = list(imp.index).index("seller_prior_late_rate") + 1
    print("   SHAP (log-odds): " + ", ".join(f"{k} {v:.2f}" for k, v in imp.items()))
    print(f"   seller_prior_late_rate ranks #{rank} of {len(imp)}.")
    _comparison_bars(RESULTS_DIR / "olist_model_comparison.png", model.test_metrics, "ROC_AUC",
                     "Real supplier lateness (Olist): ranking quality on held-out months", "ROC-AUC — higher is better")
    _importance_bars(RESULTS_DIR / "olist_feature_importance.png", imp,
                     "What predicts a late delivery? (Olist, real)", "mean |SHAP| (log-odds)")
    return dict(report=report, test=model.test_metrics, shap_importance=imp.round(4).to_dict(),
                seller_history_rank=rank, best_params=model.best_params)


def sip_study() -> dict:
    print("\n=== 3. SiP: real estimated vs actual task durations ===")
    tasks, dates = pds.load_sip(SIP_CACHE)
    df, report = pds.build_sip(tasks, dates)
    for k, v in report.items():
        print(f"   {k}: {v}")
    print(f"   excluded as leakage (computed from actual hours): {', '.join(pds.SIP_LEAKY_COLUMNS)}")
    fallacy = pds.planning_fallacy_summary(df)
    print(f"   planning fallacy: {fallacy['share_overrun']:.0%} overrun, {fallacy['share_exact']:.0%} exact, "
          f"{fallacy['share_underrun']:.0%} underrun; actual/estimate median {fallacy['median_ratio']:.2f}, "
          f"mean {fallacy['mean_ratio']:.2f}, 90th pct {fallacy['p90_ratio']:.2f}")

    def baselines(train, test):
        y = train[pds.SIP_TARGET]
        ratio = np.exp(train["log_ratio"].groupby(train["category"]).median())
        x_tr, x_te = _linear_design(train, test, pds.SIP_CATEGORICAL, pds.SIP_NUMERIC)
        return {
            "B0 developer's estimate (today's practice)": test["hours_estimate"].to_numpy(float),
            "B1 estimate x category median ratio": (test["hours_estimate"]
                                                    * test["category"].map(ratio).fillna(1.0)).to_numpy(float),
            "B2 linear regression": np.clip(LinearRegression().fit(x_tr, y).predict(x_te), 0, None),
        }

    model = fit_and_evaluate("regression", "sip_duration", df, pds.SIP_CATEGORICAL, pds.SIP_NUMERIC,
                             pds.SIP_TARGET, pds.SIP_TEST_FROM, baselines, metric=hours_metrics)
    _print_table("   Held-out test (tasks estimated from 2012): actual hours", model.test_metrics)
    imp = model.feature_importance()
    print("   SHAP (hours): " + ", ".join(f"{k} {v:.2f}" for k, v in imp.items()))
    _comparison_bars(RESULTS_DIR / "sip_model_comparison.png", model.test_metrics, "MAE",
                     "Real task durations (SiP): error on held-out years", "mean absolute error (hours) — lower is better")
    _importance_bars(RESULTS_DIR / "sip_feature_importance.png", imp,
                     "What predicts actual task time? (SiP, real)", "mean |SHAP| (hours)")
    return dict(report=report, planning_fallacy=fallacy, test=model.test_metrics,
                shap_importance=imp.round(4).to_dict(), best_params=model.best_params)


def main() -> None:
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    results = dict(rainfall=rainfall_study(), olist=olist_study(), sip=sip_study())
    (RESULTS_DIR / "metrics.json").write_text(json.dumps(results, indent=2, default=float))
    print(f"\nSaved figures + metrics.json to {RESULTS_DIR.relative_to(ROOT)}/")


if __name__ == "__main__":
    main()
