# Saved model to package ranking to React

## Actual active flow

1. [vendor_risk_random_forest.pkl](../../models/vendor_risk_random_forest.pkl) is a saved 100-tree classifier with ordered inputs `stars`, `review_count`, `collected_review_count`, `mean_review_rating`, `rating_std`. [model_status.md](../pp1_final_model_verification/model_status.md) verified its SHA-256, classes and direct predictions.
2. [POST /api/packages/generate-dynamic](../../backend/api/packages.py) invokes [generate_dynamic_packages](../../backend/engine/dynamic_package_service.py). It loads current options, filters candidates, then calls [load_risk_signals](../../backend/engine/risk_signals.py) for candidate business IDs.
3. [verified_model](../../backend/engine/risk_signals.py) checks the SHA-256 and metadata, loads the artifact and predicts a `predicted_risk_level` for complete unique profiles. It also reads stored `risk_level` and `risk_score`. If model class disagrees with the stored rule label, the numeric `rule_risk_score` is withheld with `model_rule_disagreement`.
4. [generate_bounded_packages](../../backend/engine/bounded_package_generator.py) uses **rule_risk_score** for risk-favored candidate selection, computes the mean over selected vendors and uses that mean in package ranking. Default configured weights: cost 0.4, review-rule favorability 0.4, category compatibility 0.2; unknown components are omitted and remaining weights renormalized. `predicted_risk_level` is carried into `service_breakdown` and `risk.vendors`.
5. The frontend [API client](../../frontend/src/services/api.js) receives the result; [App.jsx](../../frontend/src/App.jsx) stores it; [PackageViews.jsx](../../frontend/src/pages/PackageViews.jsx) and [VendorIntelligence](../../frontend/src/pages/AdminPages.jsx) display current-response model classes. The AI Model dashboard separately displays saved metrics from [evaluation_summary.json](../../frontend/src/data/evaluation_summary.json). See the prior [integration trace](../pp1_final_model_verification/model_integration_trace.md).

## Does the model influence rank?

**Conditionally, indirectly.** The class is **not** transformed into the rank score. The numeric input is a **precomputed, rule-derived favorability score**. Model agreement gates whether that score is available; a disagreement removes the risk component and can change candidate selection, effective weights and rank. This gate also makes successful model loading a dependency of the dynamic route.

A focused, inference-only pass over all 18,430 complete current profiles found **0 model-versus-stored-rule disagreements**. In the present data, therefore, the gate does not withhold any numeric score. **No distinct rank change attributable to model class was observed or established.** The accurate PP1 claim is that the model runs and its output gates/appears in recommendations, while the current ordering is numerically driven by stored review-rule scores, cost and category heuristics. Do not claim that the Random Forest itself supplies an independent risk score or measured failure probability.

The [current demo result](../pp1_final_submission/pp1_demo_inputs_and_outputs.json) includes Low/Medium model classes. The [existing test](../../tests/test_risk_compatibility.py) verifies that *numeric rule-risk* changes deterministic ordering; it does not prove an incremental change from the model's class under current agreement. A separate counterfactual disagreement test would be useful after PP1, without retraining.

**Scientific boundary:** The reconstructed 100% held-out score is agreement with deterministic labels derived from review inputs. Real vendor failure outcomes are absent: **NOT_VERIFIED**. [Limitations](../pp1_final_model_verification/limitations.md).
