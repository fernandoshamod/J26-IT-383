# PlanoVision research results

## Research objective

Evaluate bounded, fresh request-time vendor package recommendations against a cost-only reranking baseline on identical evaluated package pools. These are synthetic simulation experiments, not evidence of live vendor availability or real-world recommendation benefit.

## Evaluation methodology and dataset

30 existing synthetic event templates (dates shifted to 2099 for repeatability) and 5 additional synthetic scenarios produced 35 requests. The source option table contains 57549 synthetic service options; the profile table contains 18430 vendor profiles. Source names, sizes and SHA-256 values are in [evaluation_methodology.md](./evaluation_methodology.md). The two approaches share every captured, validated complete package pool. Production candidate selection, 12-option service cap, 5,000-node cap, top-K 10, and feasibility ordering were preserved. The baseline sorts by cost only after feasibility status.

## Actual results and performance

| Measure | Measured value |
|---|---:|
| HTTP request success rate | 0.9714 |
| Recommendation yield rate | 0.7429 |
| Required-service coverage | 1.0000 |
| Budget-feasible package rate | 1.0000 |
| Average packages/event | 5.7714 |
| Returned packages | 202 |
| Feasibility statuses | {'FAIL': 0, 'PASS_IN_SIMULATION': 0, 'VERIFICATION_REQUIRED': 202} |
| Known rule-risk mean | 70.3630 (202 known package scores) |
| Risk score min / median / p95 / max | 20.0000 / 60.0000 / 100.0000 / 100.0000 |
| Missing-risk vendor slots | 0.0000 (372 slots) |
| Known service compatibility mean | 92.0000 (50 known package scores) |
| Unknown multi-service compatibility | 0.5000 (100 multi-service packages) |
| Vendor diversity | 0.2527 |
| Search truncation frequency | 0.5714 |
| Complete combinations examined | 4653 |
| Request mean / median / p95 ms | 1986.38 / 1964.34 / 3181.12 |
| Request min / max ms | 629.74 / 3600.16 |

Candidate counts per service (pre-cap, priceable) are recorded in [evaluation_summary.json](./evaluation_summary.json) and [evaluation_results.csv](./evaluation_results.csv). Total experiment wall time, including paired replay, hashing and model audit but excluding output writing and report rendering: 142.11 seconds.

## Baseline comparison

Across 26 comparable events, mean top-K overlap was 0.7115; mean event-level rank shift among shared top-K packages was 1.7392 positions. The proposed minus baseline event-level mean recommendation cost was LKR 77258.32 across 26 comparable events. Positive means the proposed list costs more. See [baseline_comparison.csv](./baseline_comparison.csv) for per-event costs, known risk scores, compatibility, diversity and exact option IDs. The shared pool makes the ranking comparison fair conditional on production candidate selection; it does not show that either method is better for users.

| Measure | Cost-only baseline | PlanoVision |
|---|---:|---:|
| Mean event-level top-K cost LKR | 1241995.91 | 1319254.23 |
| Mean known rule-risk score | 61.8242 | 69.8755 |
| Mean known service compatibility | 92.0000 | 92.0000 |
| Mean event-level vendor diversity | 0.4917 | 0.4949 |

## Ranking sensitivity

| Configuration | Mean top-K overlap vs production | Mean absolute rank shift | Mean cost LKR | Mean known risk score | Mean known compatibility | Mean vendor diversity |
|---|---:|---:|---:|---:|---:|---:|
| balanced | 1.0000 | 0.0000 | 1319254.23 | 69.8755 | 92.0000 | 0.4949 |
| compatibility_focused | 0.9346 | 0.5796 | 1291011.04 | 68.6960 | 92.0000 | 0.4936 |
| cost_focused | 0.8923 | 0.9224 | 1276158.07 | 67.8242 | 92.0000 | 0.4981 |
| production | 1.0000 | 0.0000 | 1319254.23 | 69.8755 | 92.0000 | 0.4949 |
| risk_focused | 0.9538 | 0.3795 | 1365664.06 | 70.5421 | 92.0000 | 0.4897 |

These values are event-level means over nonempty or known observations, as appropriate. Exact option IDs, overlap and rank changes are in [ranking_sensitivity.csv](./ranking_sensitivity.csv). Compatibility depends only on the fixed service categories in an event, so changing its weight cannot distinguish packages within that event when its value is known and constant. When known, changing its weight cannot by itself change the order; observed changes reflect the altered cost-to-risk weight ratio. When unknown, the remaining weights are renormalized.

## Random Forest findings

The reconstructed notebook holdout accuracy was 1.0000; macro F1 was 1.0000. See [model_evaluation.md](./model_evaluation.md) for all class metrics and confusion matrix. These values measure prediction of deterministic review-derived labels, not verified vendor failure.

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
