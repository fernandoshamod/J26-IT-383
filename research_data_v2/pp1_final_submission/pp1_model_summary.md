# PP1 model summary

**Presentation claim:** PlanoVision has one saved, loading Random Forest classifier for Low / Medium / High **review-derived** vendor risk labels. It supports the dynamic recommendation route. It has no verified real-world vendor-failure target.

## Verified model

| Item | Evidence-backed value |
|---|---|
| Artifact | [vendor_risk_random_forest.pkl](../../models/vendor_risk_random_forest.pkl), SHA-256 `4eed156cfdf677b992b8c36350c21c968d7cb4d532a8afd302ca1b697aea3e6a` |
| Features in order | `stars`, `review_count`, `collected_review_count`, `mean_review_rating`, `rating_std` |
| Classes in artifact order | `High`, `Low`, `Medium` |
| Target | Stored rule-generated `risk_level`; all 18,430 profile labels match the reconstructed rule |
| Evaluation | Reconstructed 80/20 notebook split: 14,744 training-partition rows, 3,686 held-out rows; accuracy and macro F1 = 1.0 against rule labels |
| Confusion matrix | High 576/576, Low 408/408, Medium 2,702/2,702; no off-diagonal errors |
| Scope | Original held-out IDs not independently saved; operational failure outcomes absent |

The rule gives Low when mean review rating is at least 4, rating standard deviation below 1, and collected review count at least 20; otherwise Medium when mean rating is at least 3; otherwise High. These three rule inputs are present among the five model features. Thus 100% reconstructed rule-label agreement measures imitation of the rule, **not** 100% accuracy on real vendor failures. Model class probabilities are not calibrated failure probabilities. See [model status](../pp1_final_model_verification/model_status.md), [metrics](../pp1_final_model_verification/evaluation_metrics.csv), [classification report](../pp1_final_model_verification/classification_report.csv), and [limitations](../pp1_final_model_verification/limitations.md).

## Recommended visuals

1. [Confusion matrix](../pp1_final_model_verification/confusion_matrix.png): directly labeled as a reconstructed rule-label holdout.
2. [Feature importance](../pp1_final_model_verification/feature_importance.png): saved artifact impurity importances; mean review rating 0.4371 is highest. Do not interpret causally.
3. [Classification report CSV](../pp1_final_model_verification/classification_report.csv): use the per-class support and precision/recall/F1 table.
4. [Vendor Intelligence live-model capture](../pp1_final_model_verification/live_vendor_predictions.png): shows classes from a current API result, but its tiled narrow capture is difficult to read on slides. Prefer the live browser table for presentation and [prediction samples](../pp1_final_model_verification/prediction_samples.csv) or [current demo response](./pp1_demo_inputs_and_outputs.json) for readable numeric evidence. [Recommendation](../pp1_task6_presentation/screenshots/recommendations.png), [comparison](../pp1_task6_presentation/screenshots/comparison.png), and [feasibility](../pp1_task6_presentation/screenshots/feasibility.png) are the clearer existing UI flow captures.

## Runtime integration

The dynamic FastAPI route loads a SHA-pinned artifact and supplies per-vendor model classes to returned packages. Numeric package risk ranking uses a **rule-derived favorability score**; model/rule disagreement withholds that score. React package and Vendor Intelligence views display current response predictions. The AI Model dashboard shows saved metrics, not an on-navigation model run. See [integration trace](../pp1_final_model_verification/model_integration_trace.md), [prior direct-model comparison](../pp1_final_model_verification/fastapi_integration_probe.json), and [current event response](./pp1_demo_inputs_and_outputs.json).

**Suggested one-sentence spoken claim:** “Our saved Random Forest correctly reproduces review-derived Low, Medium and High labels on a reconstructed holdout and is called in the dynamic package flow; we have not measured accuracy for real vendor failures.”
