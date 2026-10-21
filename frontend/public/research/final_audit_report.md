# PlanoVision final implementation audit

**Audit date:** 2026-10-16. **Scope:** local research prototype and FastAPI TestClient; no live vendor verification or browser walkthrough. **Overall: PASS WITH LIMITATIONS for a controlled academic demonstration.** It is not production-ready.

## End-to-end trace

The React [Event Planning UI](../frontend/src/App.jsx) submits validated requirements to the [dynamic package route](../backend/api/packages.py). The [request schema](../backend/schemas/dynamic_package_request.py) checks date, type, location text, budget, guest count and services. The [dynamic service](../backend/engine/dynamic_package_service.py) creates a new `USER-*` ID, loads current [service-option records](../backend/engine/package_data_loader.py), applies [candidate filters](../backend/engine/candidate_selection.py), obtains [verified local-model inference](../backend/engine/risk_signals.py), and computes [service-category rules](../backend/engine/service_compatibility.py). The [bounded generator](../backend/engine/bounded_package_generator.py) prices and searches new combinations, runs [USER-event feasibility](../backend/engine/dynamic_feasibility.py) on each complete examined combination before ranking, excludes FAIL, prioritizes PASS_IN_SIMULATION, ranks with unchanged 0.4/0.4/0.2 weights, and builds [deterministic explanations](../backend/engine/package_explanations.py). The UI renders costs, vendor IDs, score components, feasibility, explanations, and verification needs.

No saved-package lookup appears on this dynamic path. Three identical smoke requests returned three distinct USER IDs and identical option rankings; deterministic output does not imply package reuse. The legacy event-ID route remains separate and returned HTTP 200.

## Findings

| Finding | Status | Evidence and decision |
|---|---|---|
| Fresh request-time packages | PASS | Dynamic service loads option records and calls bounded search; repeated requests produced distinct USER IDs. |
| Coverage, unique vendors, budget, capacity, event type and location | PASS WITH LIMITATIONS | Generator prunes budget/duplicate branches and feasibility checks complete combinations. Non-applicable vendor capacity remains pending. Exact cost is rounded to LKR cents. |
| Feasibility before ranking; FAIL excluded; status priority | PASS WITH LIMITATIONS | Source trace and tests verify order. All 202 returned packages in the saved experiment were VERIFICATION_REQUIRED; PASS priority is tested with a controlled fixture, not observed for a new real event. |
| Search caps and truncation | PASS | 12 candidates/service and 5,000 search nodes by default; response exposes both caps, counts and truncation. The saved experiment truncated 20/35 scenarios. |
| Risk signal direction and provenance | PASS WITH LIMITATIONS | Source mapping is Low=100, Medium=60, High=20, confirmed for all 18,430 profile rows. Higher means more favorable *rule-derived low-risk score*, not a lower measured failure probability. UI and explanation wording were clarified. |
| Service compatibility | PASS WITH LIMITATIONS | Static category-pair rules; missing pairs unknown. These are not vendor collaboration observations. |
| Client-submitted feasibility option integrity | PASS after critical fix | Before fix, invented options priced at LKR 1 returned HTTP 200 and an LKR 2 estimate. The USER endpoint now requires source option IDs, rejects altered material fields, prices canonical current records and bounds submitted option count. Tests cover tampering. |
| Non-finite request budgets | PASS after critical fix | Pydantic rejected raw NaN/infinity, but its error body caused a server serialization error. A finite JSON validation-error response now returns HTTP 422; tests cover NaN, Infinity and -Infinity. |
| Existing APIs and frontend build | PASS | Health, locations, dynamic generation, USER feasibility, legacy event/package/feasibility returned HTTP 200 in smoke checks. All 43 backend tests and the Vite build passed. |
| Prior research outputs | PASS | Direct CSV recalculation matched JSON and report values. All seven Task 5 output hashes and eight source/model hashes were unchanged during this audit. |
| Real browser workflow | NOT VERIFIED | Source, route integration and production build were checked; no browser automation walkthrough was performed. Use the [manual demo walkthrough](./demo_walkthrough.md). |
| Live vendor feasibility or real-world model validity | NOT VERIFIED | Synthetic prices/areas/capacities, pending availability/collaboration/venue/scheduling, rule-derived labels and no independent outcomes prohibit those claims. |

## Confirmed changes

Only narrow fixes were made in [the USER feasibility route](../backend/api/feasibility.py), [validation error handling](../backend/main.py), [explanation wording](../backend/engine/package_explanations.py), and [React risk labels](../frontend/src/App.jsx). [USER feasibility regression tests](../tests/test_dynamic_feasibility.py) were adjusted to use actual source option IDs; [final edge-case tests](../tests/test_final_validation.py) were added. The six files in [final_validation/](./) are audit deliverables. The Vite build regenerated routine [dist/](../frontend/dist/) output. No source dataset, model artifact, production ranking weight or Task 5 evaluation file was modified.

## Readiness decision

**PASS WITH LIMITATIONS:** Ready to demonstrate fresh synthetic package creation, transparent scoring, pending feasibility, a fair within-pool baseline comparison and reproducible outputs in a supervised academic setting. **NOT VERIFIED:** live vendor suitability, model prediction of real outcomes, production security, deployed latency and the visual browser flow. See [requirements traceability](./requirements_traceability_matrix.md), [research integrity](./research_integrity_check.md), [test results](./test_results.md) and [known limitations](./known_limitations.md).
