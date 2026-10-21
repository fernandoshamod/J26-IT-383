# Requirements traceability matrix

Status describes verified local behavior, not a claim of live vendor performance. Evidence is from the 43-test backend suite, TestClient smoke checks, source inspection, CSV recomputation and Vite build.

| Requirement | Implementation | Executed evidence | Status |
|---|---|---|---|
| Validate new event input | [dynamic request schema](../backend/schemas/dynamic_package_request.py), [package route](../backend/api/packages.py) | [edge-case tests](../tests/test_final_validation.py): bad type/location/date/time, zero/negative/non-finite budget, empty services | PASS |
| New USER ID per request | [dynamic service](../backend/engine/dynamic_package_service.py) | Three repeated requests: three distinct IDs; [repeatability test](../tests/test_final_validation.py) | PASS |
| Generate from current options, never saved packages | [option loader](../backend/engine/package_data_loader.py), [dynamic service](../backend/engine/dynamic_package_service.py) | Source call-path inspection and repeated-request ranking check | PASS |
| Filter category, type, location, simulated capacity | [candidate selection](../backend/engine/candidate_selection.py), [bounded generator](../backend/engine/bounded_package_generator.py) | [dynamic tests](../tests/test_dynamic_packages.py) and high-guest edge test | PASS WITH LIMITATIONS |
| Bound candidates and search | [bounded generator](../backend/engine/bounded_package_generator.py) | Existing cap tests; response search metadata; Task 5 reported 20/35 truncated | PASS |
| Exact required-service coverage and unique vendors | [bounded generator](../backend/engine/bounded_package_generator.py), [USER feasibility](../backend/engine/dynamic_feasibility.py) | [dynamic feasibility tests](../tests/test_dynamic_feasibility.py), duplicate-vendor API test | PASS |
| Recalculate option cost and remaining budget | [pricing helper](../backend/engine/validation_helpers.py), [bounded generator](../backend/engine/bounded_package_generator.py) | Smoke: breakdown rounds to LKR 305,535.41; remaining LKR 9,694,464.59; feasibility matches | PASS WITH LIMITATIONS |
| Match profile IDs and infer existing RF labels | [risk signals](../backend/engine/risk_signals.py) | [risk tests](../tests/test_risk_compatibility.py), saved model SHA-256 verified | PASS WITH LIMITATIONS |
| Interpret rule score direction correctly | [research notebook](../notebooks/01_vendor_dataset_audit.ipynb), [UI](../frontend/src/App.jsx), [explanations](../backend/engine/package_explanations.py) | All profile scores matched Low=100, Medium=60, High=20; [direction test](../tests/test_final_validation.py) | PASS |
| Service-category compatibility; unknown pairs | [compatibility service](../backend/engine/service_compatibility.py) | [pair tests](../tests/test_risk_compatibility.py) | PASS WITH LIMITATIONS |
| Validate USER event without SIMEVT evidence | [USER feasibility](../backend/engine/dynamic_feasibility.py), [route](../backend/api/feasibility.py) | Pending availability/collaboration tests and HTTP 200 USER smoke | PASS WITH LIMITATIONS |
| Reject forged submitted service options | [USER feasibility route](../backend/api/feasibility.py) | [tampering tests](../tests/test_final_validation.py): invented ID, price, vendor, location, type, capacity, oversized options | PASS |
| Exclude FAIL before top-K; prioritize simulated PASS | [bounded generator](../backend/engine/bounded_package_generator.py) | [feasibility/ranking tests](../tests/test_dynamic_feasibility.py) | PASS WITH LIMITATIONS |
| Explain cost, risk, compatibility and pending checks | [explanation builder](../backend/engine/package_explanations.py), [UI](../frontend/src/App.jsx) | Explanation fidelity test, source inspection, Vite build | PASS |
| Preserve legacy event-ID routes | [events](../backend/api/events.py), [packages](../backend/api/packages.py), [feasibility](../backend/api/feasibility.py) | Actual GET/POST smoke: all HTTP 200 | PASS |
| Reproduce research metrics and compare same pool | [evaluation runner](../research_evaluation/run_evaluation.py), [verifier](../research_evaluation/verify_results.py) | 35 scenarios; CSV-to-JSON/report recalculation; 35 baseline and 175 sensitivity rows | PASS WITH LIMITATIONS |
| Reconstruct RF notebook holdout without retraining | [model audit](../research_evaluation/model_audit.py), [model report](../research_evaluation/model_evaluation.md) | 3,686 test rows; accuracy and macro F1 1.0000; artifact unchanged | PASS WITH LIMITATIONS |
| Build React and connect UI to endpoints | [App.jsx](../frontend/src/App.jsx), [Vite proxy](../frontend/vite.config.js) | `npm run build` passed, TestClient routes passed | PASS WITH LIMITATIONS |
| Complete actual browser demonstration | [manual walkthrough](./demo_walkthrough.md) | No browser interaction executed in Task 6 | NOT VERIFIED |
| Verify live quotations, availability, collaboration and outcomes | [USER feasibility](../backend/engine/dynamic_feasibility.py), [limitations](./known_limitations.md) | No independent real-world evidence in current data | NOT VERIFIED |
