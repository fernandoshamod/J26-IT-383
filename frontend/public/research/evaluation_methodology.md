# PlanoVision evaluation methodology

## Design

Evaluated 35 event requests: 30 existing synthetic event templates converted into new USER requests and 5 explicitly defined synthetic scenarios. Source template dates were moved to year 2099, preserving month, day and time, so API future-date validation remains repeatable after 2027; original and submitted dates are recorded in the CSV. This changes the synthetic date but does not introduce sample-event availability or collaboration evidence. All other template fields are retained. Both ranking approaches use the same submitted event. Each request generated fresh option combinations. Synthetic event IDs were only input templates, never keys for saved package retrieval.

Each scenario was sent through the FastAPI TestClient once for latency and again to capture the exact validated complete package pool via an evaluation-only explanation hook. The hook records package fields and returns the original explanation unchanged. We checked that replay had identical search counts and that reranking the captured pool reproduced the API top-K option IDs. Baseline and sensitivity approaches rerank that same pool, with identical feasibility priority, budget filtering, candidate caps, search cap and top-K size. This isolates ranking differences **conditional on the production-selected candidate universe**. The candidate selection itself reserves risk-signal slots, so this is not a neutral full-universe cost baseline. A larger existing rule-risk score is treated by the production ranking as more favorable; it is not a probability of success.

The measured duration includes in-process HTTP routing, data loading, model inference, search and serialization. One warm-up request was excluded. It excludes network and browser rendering. The capture replay and report generation are excluded from per-request latency; total experiment duration includes them.

## Configuration and provenance

- Evaluation UTC: 2026-10-16T17:59:20.910074+00:00
- The runner checks that effective production weights and search caps equal the recorded defaults; it aborts if environment overrides differ. API-generated USER IDs are random but do not affect candidate selection or ordering.
- Python: 3.13.8; pandas: 3.0.6; scikit-learn: 1.9.1; FastAPI: 0.143.0
- Candidate cap: 12 per service; search cap: 5000 nodes; top-K: 10
- Production weights: {'compatibility': 0.2, 'cost': 0.4, 'risk': 0.4}; synthetic-data generation seed: 42; model split seed: 42
- Currency: LKR, using the existing simulated USD-to-LKR factor 330.777. Prices are estimates, not quotations.
- Input identities (SHA-256, bytes, CSV row count):

| Input | Rows | Bytes | SHA-256 |
|---|---:|---:|---|
| data/cleaned/vendor_profiles_missingness_checked.csv | 18430 | 23270305 | `adcd1ff530283b9f9965f243dadc345d768220ed5892764dfc7fce7fce12fc9a` |
| hybrid_simulation_v1/real_vendor_profiles.csv | 18430 | 22894128 | `47d380f2972eb9377610c7587b246835cdd0475492ee9518be6044b9e354d392` |
| hybrid_simulation_v1/synthetic_event_requirements.csv | 30 | 4106 | `fab7d42651b3f388be51fa6251695ed916746bd0a6ae479f1c433cdb123fa5d4` |
| hybrid_simulation_v1/synthetic_service_options.csv | 57549 | 18639627 | `94d01e9bdcb48da9c15c5054c9a734ecd1b927d0ab42fb674a6a24a2d24659df` |
| models/vendor_risk_random_forest.pkl | n/a | 448937 | `4eed156cfdf677b992b8c36350c21c968d7cb4d532a8afd302ca1b697aea3e6a` |
| vendor_compatibility_matrix.csv | 15 | 447 | `de72d8483871813f1c18113b66a8882465e98f4ba51b31388fb7751edf741aba` |
| vendor_risk_dataset.csv | 18430 | 21478484 | `c2541345862895114fd2795b3badfc42600d6d289d68fb3841bf07e743259ae6` |
| vendor_risk_model.pkl | n/a | 381185 | `b496170292cb622c69af3908db94e67d3723e6905fc4cc3952e7c5a4a2c11ad7` |

## Metric definitions

| Metric | Formula | Denominator | Missing-value handling | Interpretation |
|---|---|---|---|---|
| Request success rate | HTTP 200 requests / all evaluated requests | all scenarios | No missing values; HTTP errors count as unsuccessful | Endpoint completion, not recommendation quality. |
| Required-service coverage rate | Top-K packages with every required service exactly once / all returned packages | returned packages | Undefined if none returned | Checks coverage of displayed recommendations. |
| Budget-feasible package rate | Top-K packages with estimated cost <= submitted budget / all returned packages | returned packages | Undefined if none returned | Selection-conditioned; search prunes over-budget branches. |
| Average recommended packages | Sum of returned package counts / all scenarios | all scenarios | Empty and HTTP-error scenarios contribute zero packages | Yield of the bounded system. |
| Feasibility distribution | Count in status / all returned packages | returned packages | Undefined proportions if no packages | Pending means essential evidence is missing. |
| Vendor risk score | Mean and min/median/p95/max of known package mean rule-risk scores | packages with complete known scores | Unknown scores excluded; count reported | Rule-label signal only, not observed vendor failures. |
| Missing-risk percentage | Vendor slots without usable rule score / vendor slots in returned packages | returned-package vendor slots | Undefined if no vendor slots | Coverage of rule-derived risk evidence. |
| Service compatibility score | Mean of known package service-category rule scores | packages with complete known pair scores | Unknown and single-service not-applicable omitted | Service-category heuristic, not collaboration. |
| Unknown compatibility percentage | Multi-service packages with partial/unknown pair rules / multi-service returned packages | multi-service returned packages | Undefined if no multi-service packages | Coverage of compatibility matrix. |
| Vendor diversity | Distinct vendor IDs / all vendor slots in returned top-K packages | returned-package vendor slots | Undefined if no vendor slots | Across-event aggregate of displayed recommendations. |
| Package overlap | Common option-ID tuples / min(baseline K, proposed K) | paired nonempty event top-K lists | Undefined if either list empty | Fraction of one list shared by the other. |
| Ranking difference | Mean of each event's mean absolute position difference among common option-ID tuples | events with at least one shared top-K package | Undefined for events with no shared packages | Equal-event-weight position movement, not a utility gain. |
| Mean execution time | Sum of measured TestClient request durations / all scenarios | all scenarios | No missing durations | In-process latency, not deployment latency. |
| Median execution time | 50th percentile of request durations | all scenarios | Undefined if no requests | Typical measured latency. |
| P95 execution time | Linear-interpolated 95th percentile of request durations | all scenarios | Undefined if no requests | Upper-tail measured latency. |
| Min/max execution time | Minimum and maximum of measured request durations | all scenarios | Undefined if no requests | Observed range only. |
| Search truncation frequency | Events with candidate or node cap reached / all scenarios | all scenarios | HTTP errors count as not observed truncated | How often results may omit eligible combinations. |
| Candidate counts per service | Mean/min/max priceable candidates per service across events requesting that service | service-event observations with HTTP 200 | Absent service observations omitted | Pre-cap candidate supply. |
| Evaluated combinations | Sum of complete combinations examined by bounded search | all scenarios | HTTP errors contribute zero | Does not count pruned partial branches. |
| Top-K overlap baseline/proposed | Mean event-level package overlap coefficient | events with two nonempty rankings | Empty events omitted | Ranking similarity on the exact same pool. |
| Average cost difference | Mean event-level (proposed top-K mean cost - baseline top-K mean cost) | events with two nonempty rankings | Empty events omitted | Positive means proposed recommendations cost more. |

**Status policy:** FAIL packages are excluded. PASS_IN_SIMULATION ranks before VERIFICATION_REQUIRED. New USER events have no event-specific availability, collaboration, scheduling or venue evidence, so a nonfailed package normally remains VERIFICATION_REQUIRED.

**Ranking policy:** Production uses 100 × weighted mean of available normalized components: cost = 1 − cost/budget, risk = mean existing rule-risk score/100, compatibility = known service-pair rule mean/100. Missing components are omitted and remaining weights renormalized. Feasibility status is sorted first. The cost-only baseline sorts by feasibility status, cost and option IDs. Sensitivity variants use the same score calculation with evaluation-only weights.

**Missing-data policy:** Undefined ratios and means are JSON null and blank CSV cells, never zero. Known-only risk and compatibility averages disclose their observation counts. Multi-service compatibility is constant across packages for the same fixed service set because the matrix has service-category pairs, not vendor pairs.

## Reproduction

From the project root, use `venv/Scripts/python.exe -m research_evaluation.run_evaluation`. The script verifies source and model hashes before and after execution and stops if pool replay differs. It overwrites only the seven research output files in this directory. No production code, source data or model artifact is changed by the experiment.
