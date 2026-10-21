# Research integrity check

Task 5 outputs were **read only** in Task 6. Their seven SHA-256 hashes matched the values recorded at the start of this audit. [The existing verifier](../research_evaluation/verify_results.py) recomputed aggregates from CSV and checked current source/model hashes. A separate direct pandas/NumPy check also reproduced the values below and checked representative numbers in the Markdown [results report](../research_evaluation/research_results_report.md).

## Recalculated results

| Measure | Direct CSV result | Saved result |
|---|---:|---:|
| Scenarios / HTTP 200 | 35 / 34 | 35 / 34 |
| Returned recommendations | 202 | 202 |
| Coverage and budget fit among returned packages | 100% / 100% | 100% / 100% |
| Feasibility VERIFICATION_REQUIRED | 202 | 202 |
| Search-truncated scenarios | 20/35 = 57.14% | 57.14% |
| Complete combinations examined | 4,653 | 4,653 |
| Mean / median / p95 TestClient request time | 1,986.38 / 1,964.34 / 3,181.12 ms | same |
| Baseline-to-proposed mean cost difference | +LKR 77,258.32 | same |
| Mean baseline/proposed top-K overlap | 0.7115 | same |
| Sensitivity configurations | 5 | 5 |

The [per-package/event CSV](../research_evaluation/evaluation_results.csv) has 202 recommendation rows plus placeholder rows for zero-result scenarios; [baseline comparison](../research_evaluation/baseline_comparison.csv) has 35 rows; [ranking sensitivity](../research_evaluation/ranking_sensitivity.csv) has 175 rows. The Task 5 [summary](../research_evaluation/evaluation_summary.json), [methodology](../research_evaluation/evaluation_methodology.md), [model report](../research_evaluation/model_evaluation.md) and results report were not regenerated or edited. Eight source/model files still matched the saved input manifest.

## Meaning of the existing risk score

The [research notebook](../notebooks/01_vendor_dataset_audit.ipynb) maps **Low risk label maps to 100**, **Medium maps to 60**, **High maps to 20**. A direct check found zero mismatches among all 18,430 profile rows. The production [ranking](../backend/engine/bounded_package_generator.py) maximizes this score. Thus larger values mean **more favorable rule-derived low-risk label**, not higher measured risk and not a probability of real-world success. The [React label](../frontend/src/App.jsx) and [recommendation explanation](../backend/engine/package_explanations.py) now state that direction explicitly.

The Random Forest predicts the existing rule label from related review features. The holdout reconstruction was rerun read-only from [the original checked training data](../data/cleaned/vendor_profiles_missingness_checked.csv) and [saved model](../models/vendor_risk_random_forest.pkl): 3,686 test records; accuracy and macro F1 both 1.0000; High/Low/Medium supports 576/408/2,702. The ordered source features and labels match the current profile file. Original held-out row IDs were not separately persisted. Perfect rule-label agreement **does not** validate predictions of vendor failure or demonstrate generalization to independently observed outcomes.

## Claim boundaries

- The 100% coverage and budget rates apply **only to returned recommendations**. The generator prefilters and prunes; they are not population-level success estimates.
- The cost-only baseline reranks the same examined, validated package pool, which makes the ranking comparison controlled. Production candidate selection itself reserves slots using risk scores; this is not a neutral full-vendor-universe comparison.
- Compatibility scores describe service-category pairs. Within one fixed event's required categories, the compatibility value is constant across packages and cannot independently distinguish vendors.
- Search caps truncated 20/35 scenarios; global optimality is unverified.
- All returned USER packages require availability, collaboration, scheduling or venue verification. No real quotation or booking was confirmed.
- Timing is in-process FastAPI TestClient on one machine. The separate three-request smoke measured 4,640.07, 5,347.72 and 2,660.39 ms. Neither experiment measures deployed network or concurrent performance.
- Task 6's source-record validation changes **only** the separate USER feasibility check endpoint. It does not alter Task 5's generated recommendation ranking or recorded evaluation results.
