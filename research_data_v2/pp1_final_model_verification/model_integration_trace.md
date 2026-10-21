# Production model integration trace

## Verified dynamic request path

1. [POST /api/packages/generate-dynamic](../../backend/api/packages.py) accepts a [DynamicPackageRequest](../../backend/schemas/dynamic_package_request.py) through the router registered in [main.py](../../backend/main.py).
2. [generate_dynamic_packages](../../backend/engine/dynamic_package_service.py) selects options and collects candidate business IDs, then calls [load_risk_signals](../../backend/engine/risk_signals.py).
3. [verified_model](../../backend/engine/risk_signals.py) SHA-256 checks [the artifact](../../models/vendor_risk_random_forest.pkl), loads it through joblib, checks packaged and model feature order, classes, target, and rule-derived label metadata. It predicts only unique profile rows with all five features.
4. The risk lookup carries `predicted_risk_level`, `rule_risk_level`, `rule_risk_score`, status, and provenance. A model/rule disagreement yields `model_rule_disagreement` and withholds the numeric rule score.
5. [bounded_package_generator.py](../../backend/engine/bounded_package_generator.py) uses available **rule-derived favorability scores** for candidate choice and risk ranking, and carries model classes into `service_breakdown` and package `risk.vendors`. The class itself is not converted to a failure probability or directly used as a numeric rank factor. The model can indirectly affect ranking by gating score availability when it disagrees with a rule label.
6. The frontend [API client](../../frontend/src/services/api.js) POSTs to the dynamic endpoint. [App.jsx](../../frontend/src/App.jsx) stores the returned response in `result`. [PackageViews.jsx](../../frontend/src/pages/PackageViews.jsx) shows `option.predicted_risk_level` in package research details; [VendorIntelligence](../../frontend/src/pages/AdminPages.jsx) shows the same current-response field in the vendor table.

**Runtime evidence:** [fastapi_integration_probe.json](./fastapi_integration_probe.json) records a FastAPI TestClient HTTP 200 response for Corporate, Bensalem PA, 50 guests, 4 hours, Catering + Entertainment, LKR 1,000,000. It returned three packages; all 62 requested candidate IDs had available risk signals. The first package's two model classes matched direct predictions from the loaded artifact. This is an in-process ASGI route test, not a deployed-server availability test.

## Browser evidence and saved values

An existing compiled frontend build was served read-only via [temporary audit probe server](./readonly_frontend_probe_server.py), forwarding /api to the existing FastAPI app. No fresh frontend build was made. A browser-generated Wedding/Philadelphia/50-guest Photography + Decoration request returned packages and displayed 10 vendor rows with model Low/Medium classes in [live_vendor_predictions.png](./live_vendor_predictions.png). Those table rows are from the current `result.generation.packages[].service_breakdown`, not the saved evaluation JSON.

The separate [ModelMonitoring](../../frontend/src/pages/AdminPages.jsx) view reads `summary.model_evaluation` from [evaluation_summary.json](../../frontend/src/data/evaluation_summary.json) through [catalog.js](../../frontend/src/data/catalog.js). Its 100% accuracy, 3,686 test count, and confusion matrix are **precomputed historical snapshot values**. [model_monitoring_saved_snapshot.png](./model_monitoring_saved_snapshot.png) documents this page. The displayed figures agree with this audit's reconstruction, but navigating to that page does not rerun the model.

The browser screen also showed broad source-category classifications such as Trader Joe's under Decoration and matt-hair under Photography. These are **review candidates**, not proven errors or ML misclassifications: the model predicts the stored review-rule risk label, while service category assignment occurs upstream. Manual category validation remains a PP1 presentation priority.

The audit servers were stopped after screenshots. The legacy `POST /api/packages/generate` synthetic-event route follows a separate [package_service.py](../../backend/engine/package_service.py) path; this audit's runtime integration claim applies to the dynamic USER route.
