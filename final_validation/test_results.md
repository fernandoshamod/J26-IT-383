# Task 6 executed test results

**Environment:** Windows PowerShell; D:\Vendor-Intelligence-System\venv\Scripts\python.exe; FastAPI 0.143.0, Pydantic 2.14.1, pandas 3.0.6 and uvicorn 0.54.0. HTTP checks used local FastAPI TestClient, not a deployed server or browser.

## Regression and build

| Check | Command or method | Actual result |
|---|---|---|
| Complete backend suite | Project venv Python: -m unittest discover -s tests -v | **43 tests, 0 failures, 0 errors**, 36.598 seconds |
| Task 6 edge tests | Project venv Python: -m unittest tests.test_final_validation -v | **9 passed** |
| React production build | npm run build from [frontend/](../frontend/) | **PASS**, Vite 8.3.4, 17 modules, 1.04 seconds; regenerated [dist/](../frontend/dist/) |
| Editor diagnostics | Problems check for changed source/test files | No diagnostics reported |
| Saved evaluation verification | [Task 5 verifier](../research_evaluation/verify_results.py) and independent CSV recalculation | PASS: 35 scenarios, 202 recommendations, saved metrics and input hashes consistent |

The nine [new focused tests](../tests/test_final_validation.py) cover empty/duplicate services, unsupported type/location, invalid/past dates and times, zero/negative/non-finite budgets, high guest count and low budget, repeated requests, risk-score direction, forged/oversized options, duplicate vendors and legitimate source pricing. Existing [dynamic feasibility tests](../tests/test_dynamic_feasibility.py) now submit real source option IDs and pass.

## API smoke checks

| Request | HTTP status | Observed result |
|---|---:|---|
| GET /health | 200 | Backend healthy |
| GET /api/locations | 200 | Philadelphia, PA present |
| POST /api/packages/generate-dynamic; Philadelphia Wedding, Photography + Decoration, 50 guests | 200 × 3 | Three distinct USER IDs, identical deterministic option ranking; top package LKR 305,535.41; remaining LKR 9,694,464.59 |
| POST /api/feasibility/validate-dynamic on genuine returned USER package | 200 | Matching cost; VERIFICATION_REQUIRED |
| GET /api/events/SIMEVT-0000 | 200 | Legacy sample event available |
| POST /api/packages/generate | 200 | Legacy package API available |
| POST /api/feasibility/validate | 200 | Legacy feasibility API available |

Before the narrow fixes, an invented USER package with LKR 1 option prices returned HTTP 200, and NaN/infinite request budgets caused response serialization errors. After the fixes, forged option IDs/material fields and non-finite budgets return **422**. Genuine USER package submissions still return **200**. These are local TestClient outcomes.

## Repeat-request timing

Three identical representative TestClient requests measured **4,640.07 ms**, **5,347.72 ms** and **2,660.39 ms**. Each received a distinct USER ID. The saved 35-scenario Task 5 run reported mean/median/p95 **1,986.38/1,964.34/3,181.12 ms**; see its [methodology](../research_evaluation/evaluation_methodology.md). Neither measures deployed or browser end-to-end latency.

## Scope

Source inspection and tests support the search and eligibility invariants. No real browser interaction, live vendor contact, independently verified quotation, external security test, or concurrency/load test was completed. One initial smoke assertion compared raw binary floating-point sums to the rounded LKR total; it was corrected to compare cents, and the smoke then passed. See the [audit](./final_audit_report.md) and [manual walkthrough](./demo_walkthrough.md).
