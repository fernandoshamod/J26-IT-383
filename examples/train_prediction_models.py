"""
End-to-end ML pipeline for the duration and vendor-lateness models
(proposal Section 4.2.1, WBS task 3.6):

    generate raw history -> clean -> feature engineering -> tune (GroupKFold)
    -> train -> evaluate once on the held-out 2025 events -> explain -> save

Outputs (all regenerated on every run, same seed -> same numbers):
    data/historical/raw_activity_records.csv   raw, messy records (as exported)
    data/historical/raw_vendor_arrivals.csv
    models/duration_xgb.json + duration_meta.json
    models/lateness_xgb.json + lateness_meta.json
    results/ml/metrics.json                     every number printed below
    results/ml/*.png                            figures for the report/slides

Run from the repository root:
    python -m examples.train_prediction_models
"""

from __future__ import annotations

import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.ticker
import numpy as np
from sklearn.metrics import roc_curve

from scheduling_engine.data_preparation import clean_activity_records, clean_arrival_records
from scheduling_engine.duration_prediction import (
    TEST_FROM_DATE,
    TrainedModel,
    _new_estimator,
    add_calendar_features,
    chronological_split,
    regression_metrics,
    train_duration_model,
    train_lateness_model,
)
from scheduling_engine.history_generation import generate_history

ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / "data" / "historical"
MODEL_DIR = ROOT / "models"
RESULTS_DIR = ROOT / "results" / "ml"

# Chart colours (validated reference palette): one accent for our model,
# neutral grey for everything it's compared against.
ACCENT = "#2a78d6"
NEUTRAL = "#b4b2a9"
INK = "#0b0b0b"
INK_MUTED = "#52514e"
GRID = "#e6e5e0"


def _style(ax, title: str, xlabel: str = "", ylabel: str = "") -> None:
    ax.set_title(title, loc="left", fontsize=12, color=INK, fontweight="bold")
    ax.set_xlabel(xlabel, color=INK_MUTED)
    ax.set_ylabel(ylabel, color=INK_MUTED)
    ax.tick_params(colors=INK_MUTED)
    for side in ("top", "right"):
        ax.spines[side].set_visible(False)
    for side in ("left", "bottom"):
        ax.spines[side].set_color(GRID)
    ax.grid(axis="both", color=GRID, linewidth=0.8)
    ax.set_axisbelow(True)


def _comparison_bars(path: Path, metrics: dict, metric: str, title: str, xlabel: str) -> None:
    names = [n for n in metrics if not n.startswith("Oracle")]
    values = [metrics[n][metric] for n in names]
    oracle = next((metrics[n][metric] for n in metrics if n.startswith("Oracle")), None)
    fig, ax = plt.subplots(figsize=(8, 3.6))
    colors = [ACCENT if n == "XGBoost" else NEUTRAL for n in names]
    bars = ax.barh(names[::-1], values[::-1], color=colors[::-1], height=0.55)
    for bar, v in zip(bars, values[::-1]):
        ax.text(bar.get_width(), bar.get_y() + bar.get_height() / 2, f"  {v:.3g}",
                va="center", color=INK, fontsize=10)
    if oracle is not None:
        ax.axvline(oracle, color=INK_MUTED, linestyle="--", linewidth=1.2)
        ax.text(oracle, -0.75, f" theoretical best {oracle:.3g}",
                color=INK_MUTED, fontsize=9, va="center")
        ax.set_ylim(-1.0, len(names) - 0.5)
    _style(ax, title, xlabel)
    ax.grid(axis="y", visible=False)
    fig.tight_layout()
    fig.savefig(path, dpi=160)
    plt.close(fig)


def _importance_bars(path: Path, importance, title: str, xlabel: str) -> None:
    fig, ax = plt.subplots(figsize=(7, 3.8))
    ax.barh(importance.index[::-1], importance.values[::-1], color=ACCENT, height=0.55)
    _style(ax, title, xlabel)
    ax.grid(axis="y", visible=False)
    fig.tight_layout()
    fig.savefig(path, dpi=160)
    plt.close(fig)


def _predicted_vs_actual(path: Path, model: TrainedModel) -> None:
    df = model.test_predictions
    fig, ax = plt.subplots(figsize=(5.2, 5.2))
    ax.scatter(df["actual_duration_minutes"], df["predicted"], s=9, alpha=0.35, color=ACCENT,
               edgecolors="none", label="XGBoost")
    ax.scatter(df["actual_duration_minutes"], df["planned_duration_minutes"], s=9, alpha=0.25,
               color=NEUTRAL, edgecolors="none", label="Planner estimate")
    lim = [0, float(df["actual_duration_minutes"].quantile(0.995)) * 1.05]
    ax.plot(lim, lim, color=INK_MUTED, linestyle="--", linewidth=1, label="perfect prediction")
    ax.set_xlim(lim)
    ax.set_ylim(lim)
    _style(ax, "Predicted vs actual duration (2025 test events)", "actual minutes", "predicted minutes")
    ax.legend(frameon=False, loc="upper left")
    fig.tight_layout()
    fig.savefig(path, dpi=160)
    plt.close(fig)


def _roc(path: Path, model: TrainedModel) -> None:
    df = model.test_predictions
    y = df[model.target]
    fig, ax = plt.subplots(figsize=(5.2, 5.2))
    if "oracle_p_late_beyond_tolerance" in df:
        fpr, tpr, _ = roc_curve(y, df["oracle_p_late_beyond_tolerance"])
        ax.plot(fpr, tpr, color=INK_MUTED, linestyle="--", linewidth=1.5,
                label=f"theoretical best (AUC {model.test_metrics['Oracle ceiling (knows hidden truth)']['ROC_AUC']:.3f})")
    fpr, tpr, _ = roc_curve(y, df["predicted"])
    ax.plot(fpr, tpr, color=ACCENT, linewidth=2,
            label=f"XGBoost (AUC {model.test_metrics['XGBoost']['ROC_AUC']:.3f})")
    ax.plot([0, 1], [0, 1], color=NEUTRAL, linewidth=1, label="no information (AUC 0.5)")
    _style(ax, "Late-vendor risk: ROC curve (2025 test)", "false-alarm rate", "late vendors caught")
    ax.legend(frameon=False, loc="lower right")
    fig.tight_layout()
    fig.savefig(path, dpi=160)
    plt.close(fig)


def learning_curve(activities, model: TrainedModel) -> list[dict]:
    """How does test MAE change with the number of past EVENTS trained on?
    Answers 'is the dataset big enough?' — if the curve has flattened,
    more data of the same kind won't help much. Uses the tuned params
    (no re-tuning) and random event subsets of the training years."""
    df = add_calendar_features(activities)
    train, test = chronological_split(df)
    events = train["event_id"].unique()
    rng = np.random.default_rng(0)
    rows = []
    for n in [25, 50, 100, 200, 400, len(events)]:
        maes = []
        for _ in range(3 if n < len(events) else 1):
            chosen = rng.choice(events, size=n, replace=False)
            sub = train[train["event_id"].isin(chosen)]
            est = _new_estimator("regression", model.best_params, model.n_trees, early_stopping=False)
            est.fit(model.frame(sub), sub[model.target])
            maes.append(regression_metrics(test[model.target], np.clip(est.predict(model.frame(test)), 0, None))["MAE"])
        rows.append(dict(training_events=int(n), test_MAE=float(np.mean(maes))))
    return rows


def _learning_curve_plot(path: Path, rows: list[dict], planner_mae: float, oracle_mae: float | None) -> None:
    fig, ax = plt.subplots(figsize=(7, 3.8))
    x = [r["training_events"] for r in rows]
    y = [r["test_MAE"] for r in rows]
    ax.plot(x, y, color=ACCENT, linewidth=2, marker="o", markersize=7, label="XGBoost")
    ax.axhline(planner_mae, color=NEUTRAL, linewidth=1.5, label=f"planner estimate ({planner_mae:.1f})")
    if oracle_mae is not None:
        ax.axhline(oracle_mae, color=INK_MUTED, linestyle="--", linewidth=1.2,
                   label=f"theoretical best ({oracle_mae:.1f})")
    ax.set_xscale("log")
    ax.set_xticks(x)
    ax.set_xticklabels([str(v) for v in x])
    ax.xaxis.set_minor_locator(matplotlib.ticker.NullLocator())
    _style(ax, "How much history is enough? (duration model)", "past events used for training (log scale)",
           "test MAE (minutes)")
    ax.legend(frameon=False)
    fig.tight_layout()
    fig.savefig(path, dpi=160)
    plt.close(fig)


def _print_table(title: str, metrics: dict) -> None:
    print(f"\n{title}")
    keys = list(next(iter(metrics.values())))
    widths = [max(12, len(k) + 2) for k in keys]
    print(f"  {'model':<44}" + "".join(f"{k:>{w}}" for k, w in zip(keys, widths)))
    for name, m in metrics.items():
        print(f"  {name:<44}" + "".join(f"{m[k]:>{w}.3f}" for k, w in zip(keys, widths)))


def main() -> None:
    for d in (DATA_DIR, MODEL_DIR, RESULTS_DIR):
        d.mkdir(parents=True, exist_ok=True)

    print("1. Generating synthetic historical records (declared DGP, seed 42)")
    raw_activities, raw_arrivals = generate_history(n_events=800, seed=42)
    # Save what a real export would look like: no oracle columns.
    raw_activities.drop(columns=[c for c in raw_activities if c.startswith("oracle_")]) \
        .to_csv(DATA_DIR / "raw_activity_records.csv", index=False)
    raw_arrivals.drop(columns=[c for c in raw_arrivals if c.startswith("oracle_")]) \
        .to_csv(DATA_DIR / "raw_vendor_arrivals.csv", index=False)
    print(f"   {raw_activities['event_id'].nunique()} events, {len(raw_activities)} activity rows, "
          f"{len(raw_arrivals)} vendor-arrival rows")

    print("\n2. Cleaning")
    activities, act_report = clean_activity_records(raw_activities)
    arrivals, arr_report = clean_arrival_records(raw_arrivals)
    print("   activity records:")
    for line in act_report.lines():
        print("     " + line)
    print("   vendor-arrival records:")
    for line in arr_report.lines():
        print("     " + line)

    train_a, test_a = chronological_split(activities)
    print(f"\n3. Chronological split at {TEST_FROM_DATE}: "
          f"train {train_a['event_id'].nunique()} events / {len(train_a)} rows, "
          f"test {test_a['event_id'].nunique()} events / {len(test_a)} rows")

    print("\n4. Tuning + training (5-fold GroupKFold by event, 8-combination grid, early stopping)")
    duration, duration_grid = train_duration_model(activities)
    lateness, lateness_grid = train_lateness_model(arrivals)
    print(f"   duration: best {duration.best_params}, {duration.n_trees} trees, CV MAE {duration.cv_score:.2f} min")
    print(f"   lateness: best {lateness.best_params}, {lateness.n_trees} trees, CV Brier {lateness.cv_score:.3f}")

    _print_table("5a. DURATION model — 2025 test events (MAE/RMSE in minutes; lower is better)",
                 duration.test_metrics)
    _print_table("5b. LATE-VENDOR model — P(lateness > 10 min) on 2025 test bookings "
                 "(AUC/AP higher is better, Brier lower)", lateness.test_metrics)

    b0 = duration.test_metrics["B0 planner estimate (today's practice)"]["MAE"]
    xg = duration.test_metrics["XGBoost"]["MAE"]
    oracle_d = duration.test_metrics.get("Oracle ceiling (knows hidden truth)", {}).get("MAE")
    auc = lateness.test_metrics["XGBoost"]["ROC_AUC"]
    oracle_auc = lateness.test_metrics.get("Oracle ceiling (knows hidden truth)", {}).get("ROC_AUC")
    summary = {"duration_mae_reduction_vs_planner_pct": 100 * (b0 - xg) / b0}
    print(f"\n   Duration error cut by {summary['duration_mae_reduction_vs_planner_pct']:.1f}% vs the planner's estimate")
    if oracle_d is not None:
        summary["duration_gap_closed_to_oracle_pct"] = 100 * (b0 - xg) / (b0 - oracle_d)
        summary["lateness_auc_gap_closed_to_oracle_pct"] = 100 * (auc - 0.5) / (oracle_auc - 0.5)
        print(f"   Duration: closes {summary['duration_gap_closed_to_oracle_pct']:.0f}% of the gap "
              f"between today's practice and the theoretical best")
        print(f"   Lateness: closes {summary['lateness_auc_gap_closed_to_oracle_pct']:.0f}% of the AUC gap "
              f"between no information and the theoretical best")

    print("\n6. Explanation — mean |SHAP| per feature (duration: minutes; lateness: log-odds)")
    dur_imp = duration.feature_importance()
    late_imp = lateness.feature_importance()
    for name, imp in (("duration", dur_imp), ("lateness", late_imp)):
        print(f"   {name}: " + ", ".join(f"{k} {v:.2f}" for k, v in imp.items()))

    print("\n7. Learning curve (duration model)")
    curve = learning_curve(activities, duration)
    for r in curve:
        print(f"   {r['training_events']:>4} events -> test MAE {r['test_MAE']:.2f} min")

    duration.save(MODEL_DIR)
    lateness.save(MODEL_DIR)

    _comparison_bars(RESULTS_DIR / "duration_model_comparison.png", duration.test_metrics, "MAE",
                     "Activity duration: prediction error on 2025 events", "mean absolute error (minutes) — lower is better")
    _comparison_bars(RESULTS_DIR / "lateness_model_comparison.png", lateness.test_metrics, "ROC_AUC",
                     "Late-vendor risk: ranking quality on 2025 bookings", "ROC-AUC — higher is better")
    _importance_bars(RESULTS_DIR / "duration_feature_importance.png", dur_imp,
                     "What drives activity duration?", "mean |SHAP| (minutes)")
    _importance_bars(RESULTS_DIR / "lateness_feature_importance.png", late_imp,
                     "What drives vendor lateness?", "mean |SHAP| (log-odds)")
    _predicted_vs_actual(RESULTS_DIR / "duration_predicted_vs_actual.png", duration)
    _roc(RESULTS_DIR / "lateness_roc.png", lateness)
    _learning_curve_plot(RESULTS_DIR / "duration_learning_curve.png", curve, b0, oracle_d)

    (RESULTS_DIR / "metrics.json").write_text(json.dumps(dict(
        cleaning=dict(activities=act_report.__dict__, arrivals=arr_report.__dict__),
        split=dict(test_from=TEST_FROM_DATE,
                   train_events=int(train_a["event_id"].nunique()),
                   test_events=int(test_a["event_id"].nunique())),
        duration=dict(best_params=duration.best_params, n_trees=duration.n_trees,
                      cv_mae=duration.cv_score, test=duration.test_metrics,
                      shap_importance=dur_imp.round(4).to_dict(), grid=duration_grid),
        lateness=dict(best_params=lateness.best_params, n_trees=lateness.n_trees,
                      cv_brier=lateness.cv_score, test=lateness.test_metrics,
                      shap_importance=late_imp.round(4).to_dict(), grid=lateness_grid),
        learning_curve=curve,
        summary=summary,
    ), indent=2))
    print(f"\nSaved models to {MODEL_DIR.relative_to(ROOT)}/, figures + metrics.json to {RESULTS_DIR.relative_to(ROOT)}/")


if __name__ == "__main__":
    main()
