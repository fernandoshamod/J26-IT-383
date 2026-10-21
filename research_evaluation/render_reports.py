"""Render research narratives from measured CSV and JSON values."""

import csv
from pathlib import Path

from research_evaluation.metrics import mean

OUTPUT = Path(__file__).resolve().parent


def fmt(value, digits=4):
    return "undefined" if value is None else f"{value:.{digits}f}"


def rows(name):
    with (OUTPUT / name).open(newline="", encoding="utf-8") as stream:
        return list(csv.DictReader(stream))


def number(value):
    return None if value in ("", None) else float(value)


METRIC_DEFINITIONS = [
    ("Request success rate", "HTTP 200 requests / all evaluated requests", "all scenarios", "No missing values; HTTP errors count as unsuccessful", "Endpoint completion, not recommendation quality."),
    ("Required-service coverage rate", "Top-K packages with every required service exactly once / all returned packages", "returned packages", "Undefined if none returned", "Checks coverage of displayed recommendations."),
    ("Budget-feasible package rate", "Top-K packages with estimated cost <= submitted budget / all returned packages", "returned packages", "Undefined if none returned", "Selection-conditioned; search prunes over-budget branches."),
    ("Average recommended packages", "Sum of returned package counts / all scenarios", "all scenarios", "Empty and HTTP-error scenarios contribute zero packages", "Yield of the bounded system."),
    ("Feasibility distribution", "Count in status / all returned packages", "returned packages", "Undefined proportions if no packages", "Pending means essential evidence is missing."),
    ("Vendor risk score", "Mean and min/median/p95/max of known package mean rule-risk scores", "packages with complete known scores", "Unknown scores excluded; count reported", "Rule-label signal only, not observed vendor failures."),
    ("Missing-risk percentage", "Vendor slots without usable rule score / vendor slots in returned packages", "returned-package vendor slots", "Undefined if no vendor slots", "Coverage of rule-derived risk evidence."),
    ("Service compatibility score", "Mean of known package service-category rule scores", "packages with complete known pair scores", "Unknown and single-service not-applicable omitted", "Service-category heuristic, not collaboration."),
    ("Unknown compatibility percentage", "Multi-service packages with partial/unknown pair rules / multi-service returned packages", "multi-service returned packages", "Undefined if no multi-service packages", "Coverage of compatibility matrix."),
    ("Vendor diversity", "Distinct vendor IDs / all vendor slots in returned top-K packages", "returned-package vendor slots", "Undefined if no vendor slots", "Across-event aggregate of displayed recommendations."),
    ("Package overlap", "Common option-ID tuples / min(baseline K, proposed K)", "paired nonempty event top-K lists", "Undefined if either list empty", "Fraction of one list shared by the other."),
    ("Ranking difference", "Mean of each event's mean absolute position difference among common option-ID tuples", "events with at least one shared top-K package", "Undefined for events with no shared packages", "Equal-event-weight position movement, not a utility gain."),
    ("Mean execution time", "Sum of measured TestClient request durations / all scenarios", "all scenarios", "No missing durations", "In-process latency, not deployment latency."),
    ("Median execution time", "50th percentile of request durations", "all scenarios", "Undefined if no requests", "Typical measured latency."),
    ("P95 execution time", "Linear-interpolated 95th percentile of request durations", "all scenarios", "Undefined if no requests", "Upper-tail measured latency."),
    ("Min/max execution time", "Minimum and maximum of measured request durations", "all scenarios", "Undefined if no requests", "Observed range only."),
    ("Search truncation frequency", "Events with candidate or node cap reached / all scenarios", "all scenarios", "HTTP errors count as not observed truncated", "How often results may omit eligible combinations."),
    ("Candidate counts per service", "Mean/min/max priceable candidates per service across events requesting that service", "service-event observations with HTTP 200", "Absent service observations omitted", "Pre-cap candidate supply."),
    ("Evaluated combinations", "Sum of complete combinations examined by bounded search", "all scenarios", "HTTP errors contribute zero", "Does not count pruned partial branches."),
    ("Top-K overlap baseline/proposed", "Mean event-level package overlap coefficient", "events with two nonempty rankings", "Empty events omitted", "Ranking similarity on the exact same pool."),
    ("Average cost difference", "Mean event-level (proposed top-K mean cost - baseline top-K mean cost)", "events with two nonempty rankings", "Empty events omitted", "Positive means proposed recommendations cost more."),
]


def write_reports(summary):
    m = summary["metrics"]
    model = summary["model_evaluation"]
    manifest = summary["input_manifest"]
    config = summary["configuration"]
    definitions = "\n".join(
        f"| {name} | {formula} | {denom} | {missing} | {meaning} |"
        for name, formula, denom, missing, meaning in METRIC_DEFINITIONS)
    methodology = f"""# PlanoVision evaluation methodology

## Design

Evaluated {summary['scenario_counts']['total']} event requests: {summary['scenario_counts']['existing_synthetic_event_templates']} existing synthetic event templates converted into new USER requests and {summary['scenario_counts']['additional_explicit_synthetic_scenarios']} explicitly defined synthetic scenarios. Source template dates were moved to year 2099, preserving month, day and time, so API future-date validation remains repeatable after 2027; original and submitted dates are recorded in the CSV. This changes the synthetic date but does not introduce sample-event availability or collaboration evidence. All other template fields are retained. Both ranking approaches use the same submitted event. Each request generated fresh option combinations. Synthetic event IDs were only input templates, never keys for saved package retrieval.

Each scenario was sent through the FastAPI TestClient once for latency and again to capture the exact validated complete package pool via an evaluation-only explanation hook. The hook records package fields and returns the original explanation unchanged. We checked that replay had identical search counts and that reranking the captured pool reproduced the API top-K option IDs. Baseline and sensitivity approaches rerank that same pool, with identical feasibility priority, budget filtering, candidate caps, search cap and top-K size. This isolates ranking differences **conditional on the production-selected candidate universe**. The candidate selection itself reserves risk-signal slots, so this is not a neutral full-universe cost baseline. A larger existing rule-risk score is treated by the production ranking as more favorable; it is not a probability of success.

The measured duration includes in-process HTTP routing, data loading, model inference, search and serialization. One warm-up request was excluded. It excludes network and browser rendering. The capture replay and report generation are excluded from per-request latency; total experiment duration includes them.

## Configuration and provenance

- Evaluation UTC: {summary['evaluation_date_utc']}
- The runner checks that effective production weights and search caps equal the recorded defaults; it aborts if environment overrides differ. API-generated USER IDs are random but do not affect candidate selection or ordering.
- Python: {summary['runtime']['python']}; pandas: {summary['runtime']['pandas']}; scikit-learn: {summary['runtime']['scikit_learn']}; FastAPI: {summary['runtime']['fastapi']}
- Candidate cap: {config['max_candidates_per_service']} per service; search cap: {config['max_search_nodes']} nodes; top-K: {config['top_k']}
- Production weights: {config['production_weights']}; synthetic-data generation seed: {config['simulation_seed']}; model split seed: {config['model_split_seed']}
- Currency: LKR, using the existing simulated USD-to-LKR factor {config['synthetic_usd_to_lkr']}. Prices are estimates, not quotations.
- Input identities (SHA-256, bytes, CSV row count):

| Input | Rows | Bytes | SHA-256 |
|---|---:|---:|---|
""" + "\n".join(
        f"| {name} | {item.get('rows', 'n/a')} | {item['bytes']} | `{item['sha256']}` |"
        for name, item in manifest.items()
    ) + f"""

## Metric definitions

| Metric | Formula | Denominator | Missing-value handling | Interpretation |
|---|---|---|---|---|
{definitions}

**Status policy:** FAIL packages are excluded. PASS_IN_SIMULATION ranks before VERIFICATION_REQUIRED. New USER events have no event-specific availability, collaboration, scheduling or venue evidence, so a nonfailed package normally remains VERIFICATION_REQUIRED.

**Ranking policy:** Production uses 100 × weighted mean of available normalized components: cost = 1 − cost/budget, risk = mean existing rule-risk score/100, compatibility = known service-pair rule mean/100. Missing components are omitted and remaining weights renormalized. Feasibility status is sorted first. The cost-only baseline sorts by feasibility status, cost and option IDs. Sensitivity variants use the same score calculation with evaluation-only weights.

**Missing-data policy:** Undefined ratios and means are JSON null and blank CSV cells, never zero. Known-only risk and compatibility averages disclose their observation counts. Multi-service compatibility is constant across packages for the same fixed service set because the matrix has service-category pairs, not vendor pairs.

## Reproduction

From the project root, use `venv/Scripts/python.exe -m research_evaluation.run_evaluation`. The script verifies source and model hashes before and after execution and stops if pool replay differs. It overwrites only the seven research output files in this directory. No production code, source data or model artifact is changed by the experiment.
"""
    (OUTPUT / "evaluation_methodology.md").write_text(methodology, encoding="utf-8")
    if model["status"] == "reconstructed_notebook_holdout":
        class_rows = "\n".join(
            f"| {label} | {int(values['support'])} | {fmt(values['precision'])} | {fmt(values['recall'])} | {fmt(values['f1-score'])} |"
            for label, values in model["per_class"].items())
        matrix = "\n".join(
            f"| {label} | " + " | ".join(str(value) for value in values) + " |"
            for label, values in zip(model["classes"], model["confusion_matrix"]))
        model_text = f"""# Random Forest artifact evaluation

The original notebook specifies `train_test_split(test_size=0.20, random_state=42, stratify=y)` on `data/cleaned/vendor_profiles_missingness_checked.csv`. The checked source and current profile rows match exactly on IDs, five features and labels, in the same order. The saved artifact contains the same feature order, class labels and rule-derived target metadata. This is a **reconstruction of the notebook holdout**, not an independent real-world test. Original held-out row IDs were not stored separately, so the split identity rests on the notebook recipe and unchanged ordered input.

Training rows: {model['train_count']}; reconstructed test rows: {model['test_count']}. Features: {model['features']}. Model SHA-256: `{model['model_sha256']}`.

| Metric | Value |
|---|---:|
| Accuracy | {fmt(model['accuracy'])} |
| Macro precision | {fmt(model['macro_precision'])} |
| Macro recall | {fmt(model['macro_recall'])} |
| Macro F1 | {fmt(model['macro_f1'])} |
| Weighted F1 | {fmt(model['weighted_f1'])} |

| Class | Support | Precision | Recall | F1 |
|---|---:|---:|---:|---:|
{class_rows}

Confusion matrix, rows=true and columns=predicted, order {model['classes']}:

| True / predicted | """ + " | ".join(model["classes"]) + f""" |
|---|""" + "|".join("---:" for _ in model["classes"]) + f"""|
{matrix}

**Interpretation:** Risk labels were deterministic rules derived from related review features. A perfect score can indicate learning those rules, label leakage or circular evaluation. It does not establish ability to predict verified real-world vendor failures. The vendor risk CSV also has known ID anomalies; production inference joins to unique profile IDs. No retraining was performed.
"""
    else:
        model_text = f"# Random Forest artifact evaluation\n\nNot reported: {model['reason']}\n"
    (OUTPUT / "model_evaluation.md").write_text(model_text, encoding="utf-8")

    comparisons = rows("baseline_comparison.csv")
    paired = [row for row in comparisons if row["top_k_overlap"] != ""]
    sensitivity = rows("ranking_sensitivity.csv")
    baseline_summary = {
        "baseline_cost": mean(number(r["baseline_mean_cost_lkr"]) for r in paired),
        "proposed_cost": mean(number(r["proposed_mean_cost_lkr"]) for r in paired),
        "baseline_risk": mean(number(r["baseline_mean_risk_score_known"]) for r in paired),
        "proposed_risk": mean(number(r["proposed_mean_risk_score_known"]) for r in paired),
        "baseline_compatibility": mean(number(r["baseline_mean_compatibility_score_known"]) for r in paired),
        "proposed_compatibility": mean(number(r["proposed_mean_compatibility_score_known"]) for r in paired),
        "baseline_diversity": mean(number(r["baseline_vendor_diversity"]) for r in paired),
        "proposed_diversity": mean(number(r["proposed_vendor_diversity"]) for r in paired),
    }
    sensitivity_lines = []
    for name in config["sensitivity_weights"]:
        group = [row for row in sensitivity if row["configuration"] == name]
        sensitivity_lines.append(
            f"| {name} | {fmt(mean(number(r['top_k_overlap_vs_production']) for r in group))} | "
            f"{fmt(mean(number(r['mean_absolute_rank_shift_vs_production']) for r in group))} | "
            f"{fmt(mean(number(r['mean_cost_lkr']) for r in group), 2)} | "
            f"{fmt(mean(number(r['mean_risk_score_known']) for r in group))} | "
            f"{fmt(mean(number(r['mean_compatibility_score_known']) for r in group))} | "
            f"{fmt(mean(number(r['vendor_diversity']) for r in group))} |")
    report = f"""# PlanoVision research results

## Research objective

Evaluate bounded, fresh request-time vendor package recommendations against a cost-only reranking baseline on identical evaluated package pools. These are synthetic simulation experiments, not evidence of live vendor availability or real-world recommendation benefit.

## Evaluation methodology and dataset

{summary['scenario_counts']['existing_synthetic_event_templates']} existing synthetic event templates (dates shifted to 2099 for repeatability) and {summary['scenario_counts']['additional_explicit_synthetic_scenarios']} additional synthetic scenarios produced {m['events_evaluated']} requests. The source option table contains {manifest['hybrid_simulation_v1/synthetic_service_options.csv']['rows']} synthetic service options; the profile table contains {manifest['hybrid_simulation_v1/real_vendor_profiles.csv']['rows']} vendor profiles. Source names, sizes and SHA-256 values are in [evaluation_methodology.md](./evaluation_methodology.md). The two approaches share every captured, validated complete package pool. Production candidate selection, 12-option service cap, 5,000-node cap, top-K 10, and feasibility ordering were preserved. The baseline sorts by cost only after feasibility status.

## Actual results and performance

| Measure | Measured value |
|---|---:|
| HTTP request success rate | {fmt(m['request_success_rate'])} |
| Recommendation yield rate | {fmt(m['recommendation_yield_rate'])} |
| Required-service coverage | {fmt(m['required_service_coverage_rate'])} |
| Budget-feasible package rate | {fmt(m['budget_feasible_package_rate'])} |
| Average packages/event | {fmt(m['average_recommended_packages_per_event'])} |
| Returned packages | {m['recommended_package_count']} |
| Feasibility statuses | {m['feasibility_status_counts']} |
| Known rule-risk mean | {fmt(m['mean_vendor_risk_score_known'])} ({m['risk_known_package_count']} known package scores) |
| Risk score min / median / p95 / max | {fmt(m['risk_score_distribution_known']['min'])} / {fmt(m['risk_score_distribution_known']['median'])} / {fmt(m['risk_score_distribution_known']['p95'])} / {fmt(m['risk_score_distribution_known']['max'])} |
| Missing-risk vendor slots | {fmt(m['missing_risk_fraction'])} ({m['vendor_slot_count']} slots) |
| Known service compatibility mean | {fmt(m['mean_service_compatibility_score_known'])} ({m['compatibility_known_package_count']} known package scores) |
| Unknown multi-service compatibility | {fmt(m['unknown_compatibility_fraction'])} ({m['multiservice_package_count']} multi-service packages) |
| Vendor diversity | {fmt(m['vendor_diversity_top_k'])} |
| Search truncation frequency | {fmt(m['search_truncation_frequency'])} |
| Complete combinations examined | {m['evaluated_package_combinations']} |
| Request mean / median / p95 ms | {fmt(m['mean_execution_ms'], 2)} / {fmt(m['median_execution_ms'], 2)} / {fmt(m['p95_execution_ms'], 2)} |
| Request min / max ms | {fmt(m['min_execution_ms'], 2)} / {fmt(m['max_execution_ms'], 2)} |

Candidate counts per service (pre-cap, priceable) are recorded in [evaluation_summary.json](./evaluation_summary.json) and [evaluation_results.csv](./evaluation_results.csv). Total experiment wall time, including paired replay, hashing and model audit but excluding output writing and report rendering: {fmt(summary['evaluation_execution_seconds'], 2)} seconds.

## Baseline comparison

Across {m['baseline_proposed_overlap_event_count']} comparable events, mean top-K overlap was {fmt(m['baseline_proposed_top_k_overlap_mean'])}; mean event-level rank shift among shared top-K packages was {fmt(m['mean_absolute_rank_shift_common'])} positions. The proposed minus baseline event-level mean recommendation cost was LKR {fmt(m['average_recommended_package_cost_difference_lkr'], 2)} across {m['cost_difference_event_count']} comparable events. Positive means the proposed list costs more. See [baseline_comparison.csv](./baseline_comparison.csv) for per-event costs, known risk scores, compatibility, diversity and exact option IDs. The shared pool makes the ranking comparison fair conditional on production candidate selection; it does not show that either method is better for users.

| Measure | Cost-only baseline | PlanoVision |
|---|---:|---:|
| Mean event-level top-K cost LKR | {fmt(baseline_summary['baseline_cost'], 2)} | {fmt(baseline_summary['proposed_cost'], 2)} |
| Mean known rule-risk score | {fmt(baseline_summary['baseline_risk'])} | {fmt(baseline_summary['proposed_risk'])} |
| Mean known service compatibility | {fmt(baseline_summary['baseline_compatibility'])} | {fmt(baseline_summary['proposed_compatibility'])} |
| Mean event-level vendor diversity | {fmt(baseline_summary['baseline_diversity'])} | {fmt(baseline_summary['proposed_diversity'])} |

## Ranking sensitivity

| Configuration | Mean top-K overlap vs production | Mean absolute rank shift | Mean cost LKR | Mean known risk score | Mean known compatibility | Mean vendor diversity |
|---|---:|---:|---:|---:|---:|---:|
""" + "\n".join(sensitivity_lines) + f"""

These values are event-level means over nonempty or known observations, as appropriate. Exact option IDs, overlap and rank changes are in [ranking_sensitivity.csv](./ranking_sensitivity.csv). Compatibility depends only on the fixed service categories in an event, so changing its weight cannot distinguish packages within that event when its value is known and constant. When known, changing its weight cannot by itself change the order; observed changes reflect the altered cost-to-risk weight ratio. When unknown, the remaining weights are renormalized.

## Random Forest findings

The reconstructed notebook holdout accuracy was {fmt(model.get('accuracy'))}; macro F1 was {fmt(model.get('macro_f1'))}. See [model_evaluation.md](./model_evaluation.md) for all class metrics and confusion matrix. These values measure prediction of deterministic review-derived labels, not verified vendor failure.

## Discussion, limitations and threats to validity

- Synthetic prices, capacity, service area and event requirements are illustrative. No price quotation, vendor availability, venue or collaboration has been independently confirmed. USER-event packages remain verification-required where essential evidence is missing.
- The model target is derived from related input features. Circular labels and potential leakage severely limit external validity; a high classifier score cannot support a real-world reliability claim.
- Baseline and proposed rankings use the same evaluated pool, but that pool was selected partly using risk signals. This favors the production candidate policy and limits claims about the complete vendor universe.
- Candidate and node caps mean top-K results may miss better combinations. Truncation frequency is reported; exact global optimality is not claimed.
- The compatibility matrix describes service-category rules, not vendor pair experience. Its score is constant within a fixed service set.
- In-process TestClient timing on one machine is not server throughput or deployed end-to-end latency. No concurrent load, repeated timing trials, confidence intervals or user study was performed.
- A source notebook recipe supports holdout reconstruction, but separately persisted test IDs were unavailable. No independent outcomes or external validation set was available.

## Future improvements

Collect consented, verified vendor quotations, capacity, availability and outcomes; establish an independent outcome label and frozen external test set; compare against a truly neutral full-universe baseline; and measure deployment latency under concurrency. Preserve fresh request-time generation while doing so.
"""
    (OUTPUT / "research_results_report.md").write_text(report, encoding="utf-8")
