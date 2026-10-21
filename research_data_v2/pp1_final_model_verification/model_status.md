# PP1 Random Forest model status

Verified 2026-10-18 using the project Python 3.13.8 virtual environment. This task loaded the existing artifact and ran inference; it did not train, replace, or modify a model or production file.

## Decision

| Question | Finding | Evidence |
|---|---|---|
| Technically complete artifact? | **YES** for the defined task of classifying existing review-rule Low/Medium/High labels. Saved 100-tree RandomForestClassifier with five ordered features and three classes. | [runtime metadata](./model_runtime_metadata.json), [source hashes](./source_hashes.csv) |
| Does it load and predict? | **YES**. The pinned SHA-256 matched, verified_model loaded it, held-out rows were predicted, and 30 valid held-out sample predictions with class probabilities were saved. | [prediction samples](./prediction_samples.csv), [verification log](./verification_log.json) |
| FastAPI integrated? | **YES for the dynamic package endpoint.** In-process POST returned HTTP 200, three packages, 62 available risk signals, and model predictions matching direct artifact inference for sampled package vendors. | [FastAPI probe](./fastapi_integration_probe.json) |
| React shows model outputs? | **YES in the current vendor and package views.** The browser-generated event showed 10 vendor rows with Low/Medium model classes. The AI Model page shows a **saved evaluation snapshot**, not a fresh model run. | [live browser screenshot](./live_vendor_predictions.png), [saved snapshot screenshot](./model_monitoring_saved_snapshot.png), [integration trace](./model_integration_trace.md) |
| Metrics reproducible? | **YES for the reconstructed notebook holdout against deterministic rule-derived labels.** Accuracy and macro F1 were 1.0 on 3,686 rows, with diagonal confusion matrix. The original held-out row IDs were not separately saved. | [evaluation metrics](./evaluation_metrics.csv), [holdout details](./holdout_details.json), [confusion matrix](./confusion_matrix.png) |
| Real vendor failure prediction validated? | **NO / NOT_VERIFIED.** There are no independent operational-failure outcomes. | [limitations](./limitations.md) |

## Artifact and data

- Saved artifact: [vendor_risk_random_forest.pkl](../../models/vendor_risk_random_forest.pkl), SHA-256 `4eed156cfdf677b992b8c36350c21c968d7cb4d532a8afd302ca1b697aea3e6a`; matches the pin in [risk_signals.py](../../backend/engine/risk_signals.py).
- Training source: [vendor_profiles_missingness_checked.csv](../../data/cleaned/vendor_profiles_missingness_checked.csv), 18,430 rows. Its ordered business IDs, five features and risk labels equal the current [real_vendor_profiles.csv](../../hybrid_simulation_v1/real_vendor_profiles.csv).
- Feature order: `stars`, `review_count`, `collected_review_count`, `mean_review_rating`, `rating_std`. Classes in artifact order: `High`, `Low`, `Medium`.
- Training logic: [notebook](../../notebooks/01_vendor_dataset_audit.ipynb), cells 15/16/18, defines stratified 80/20 split with random_state=42, 100-tree Random Forest and a guarded artifact save. [model_audit.py](../../research_evaluation/model_audit.py) reproduces the split without training.
- The full target-rule reconstruction matches **all 18,430 labels**: Low when mean review rating >= 4, standard deviation < 1, and collected review count >= 20; otherwise Medium when mean rating >= 3; otherwise High.
- The model's saved impurity-based feature importances are plotted in [feature_importance.png](./feature_importance.png) and tabulated in [feature_importance.csv](./feature_importance.csv). Mean review rating is highest (0.4371); importance is not causal evidence.

## Reconstructed holdout

The ordered input equality supports replaying the notebook's split. There are 14,744 training-partition rows and 3,686 test-partition rows. This verification **did not fit a model**. It loaded the saved artifact and predicted on the reconstructed test rows. Original test IDs/training membership were not saved as a separate immutable split manifest, so exact historical split membership cannot be proven independently of the notebook recipe and matching ordered input. The result is a valid reconstruction of rule-label evaluation, not an independent operational-risk test.

| True \ predicted | High | Low | Medium |
|---|---:|---:|---:|
| High | 576 | 0 | 0 |
| Low | 0 | 408 | 0 |
| Medium | 0 | 0 | 2,702 |

**PP1 position:** one working saved ML model is available for a clearly qualified academic demo. Present its output as *classification of review-derived rules*, never as a measured probability of real vendor failure.
