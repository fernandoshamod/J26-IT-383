# PlanoVision — Vendor Intelligence & Smart Package Recommendation Engine

**Group ID:** J26-IT-383
**Research phase:** PP1 completed; PP2/final validation preparation
**Component status:** research prototype for supervised academic demonstration

## Scope and evidence boundary

This document describes only the Vendor Intelligence & Smart Package Recommendation Engine found in this repository. It is based on the current implementation under `backend/`, `frontend/`, `hybrid_simulation_v1/`, `research_evaluation/`, `research_data_v2/`, `models/` and `tests/`.

The system uses a mixture of profile/review-derived vendor data and synthetic service-option data. Prices, capacity, service areas, availability, collaboration and venue checks are not established as live vendor facts. A package labelled `PASS_IN_SIMULATION` is not a real booking confirmation; new USER-event packages normally remain `VERIFICATION_REQUIRED` when event-specific evidence is missing.

## Research problem and objectives

Event planners must select multiple service providers while satisfying event type, location, date/time, guest count, budget and service coverage. A naïve independent search can return incompatible, duplicate-vendor or over-budget combinations. This component investigates a transparent request-time pipeline that filters candidate options, incorporates a vendor risk signal, searches combinations under bounded computation, validates constraints, ranks packages and explains the result.

### Objectives

- Generate packages that cover each requested service exactly once.
- Enforce distinct vendors, supported event types, simulated location, capacity and budget constraints.
- Include an auditable vendor risk signal without fabricating missing risk data.
- Represent known/unknown service-category compatibility.
- Avoid unbounded Cartesian-product search through candidate and node limits.
- Return score factors, warnings, verification requirements and search metadata.
- Evaluate the workflow against a cost-only reranking baseline on an identical examined pool.

### Contribution and novelty boundary

The implemented contribution is the integration of transparent candidate selection, rule-derived model inference, bounded DFS, pre-ranking feasibility validation and weighted ranking in one FastAPI/React workflow. The current evidence does not justify claims of novel real-world risk prediction, live vendor intelligence, verified collaboration, or global optimization.

## System overview

```mermaid
flowchart TD
  A[React Event Wizard] --> B[DynamicPackageRequest]
  B --> C[FastAPI /api/packages/generate-dynamic]
  C --> D[Load synthetic service options]
  D --> E[Filter by service, location, event type, capacity]
  E --> F[Join vendor profiles]
  F --> G[Hash-checked Random Forest inference]
  E --> H[Static category compatibility]
  G --> I[Bounded DFS package search]
  H --> I
  I --> J[Dynamic feasibility per complete combination]
  J --> K[Weighted ranking and explanations]
  K --> L[Top-K response]
  L --> M[React recommendations/comparison]
  M --> N[/api/feasibility/validate-dynamic]
  O[(SQLite saved events)] <--> C
```

The main implementation trace is `frontend/src/services/api.js` → `backend/api/packages.py` → `backend/engine/dynamic_package_service.py` → `candidate_selection.py`, `risk_signals.py`, `service_compatibility.py`, `bounded_package_generator.py`, `dynamic_feasibility.py` and `package_explanations.py`.

## Repository structure

```text
Vendor-Intelligence-System/
├── backend/
│   ├── main.py                         FastAPI app and router registration
│   ├── db.py                           SQLite saved-event persistence
│   ├── vendor_demo_db.py               Vendor-demo persistence
│   ├── api/                            HTTP route modules
│   │   ├── packages.py                 Legacy and dynamic package routes
│   │   ├── feasibility.py              Legacy and USER feasibility routes
│   │   ├── events.py                   Saved/legacy event routes
│   │   ├── locations.py                Simulated location route
│   │   ├── admin.py                    Research/admin read-only routes
│   │   └── vendor_demo.py               Vendor portal demo CRUD routes
│   ├── engine/                         Recommendation and validation logic
│   │   ├── dynamic_package_service.py  Request-time orchestration
│   │   ├── candidate_selection.py      Candidate filtering
│   │   ├── bounded_package_generator.py Capped DFS and ranking
│   │   ├── dynamic_feasibility.py      USER-event checks
│   │   ├── risk_signals.py             Verified model loading/inference
│   │   ├── service_compatibility.py    Category-pair scoring
│   │   ├── package_explanations.py     Deterministic explanations
│   │   └── package_data_loader.py      CSV loading and USD→LKR conversion
│   └── schemas/                        Pydantic request/response models
├── frontend/
│   ├── package.json                    React/Vite scripts and dependencies
│   └── src/                            UI pages, API client and view models
├── hybrid_simulation_v1/               Simulation-v1 data and provenance
├── models/                             Persisted Random Forest artifact
├── data/cleaned/                       Checked profile training source
├── notebooks/                          Dataset audit notebook
├── research_evaluation/                Saved metrics, baselines and reports
├── research_data_v2/                   PP1 evidence and audit records
├── tests/                              Python regression/unit tests
├── final_validation/                   Existing integrity and readiness reports
└── docs/                               This audit and README draft
```

## Technologies

- Frontend: React 19, React DOM, Vite and oxlint (`frontend/package.json`).
- Backend: FastAPI with Pydantic schemas, pandas-based CSV processing and SQLite (`backend/`).
- ML: scikit-learn `RandomForestClassifier`, persisted with joblib (`models/vendor_risk_random_forest.pkl`).
- Data: CSV-based simulation-v1 tables. The loader applies `USD_TO_LKR = 330.777` (`backend/engine/package_data_loader.py`).

No root Python dependency manifest or verified backend launch script was found. Frontend scripts are verified: `npm run dev`, `npm run build`, `npm run lint` and `npm run preview` from `frontend/`. A historical validation report records a local venv and a successful build/test run, but this README draft does not claim those commands were rerun here.

## Algorithms and implementation

### Random Forest vendor signal

`backend/engine/risk_signals.py` loads five review/profile features and checks the persisted model’s SHA-256, feature names, class order and target metadata. It predicts only complete unique profile rows. Missing, duplicate or incomplete profile matches remain unknown. The model target is `risk_level`, a deterministic label derived from related review features.

The implementation maps Low → 100, Medium → 60 and High → 20. In ranking, a higher value is more favorable under this rule-derived convention. It is not a probability of vendor failure, safety or booking success.

### Candidate selection

`backend/engine/candidate_selection.py` filters each required service by service category, simulated city/state, supported event type and catering guest capacity. The result is a candidate group for each service.

### Bounded DFS package generation

`backend/engine/bounded_package_generator.py` validates priceability and capacity, caps each service at 12 selected candidates by default, and caps traversal at 5,000 nodes by default. It reserves candidates from low-cost and high rule-derived-risk pools, then recursively selects one option per service, rejecting duplicate vendors and partial totals over budget. Every complete combination reached by the search is passed through dynamic feasibility before ranking.

The algorithm is bounded, not globally exhaustive. The response includes `candidate_limit_reached`, `node_limit_reached`, `nodes_visited`, `combinations_evaluated`, selected search-space upper bound and minimum possible cost so consumers can see when completeness is limited.

### Compatibility

`backend/engine/service_compatibility.py` averages static scores for unordered service-category pairs in `vendor_compatibility_matrix.csv`. Unknown pairs produce no package-level compatibility score. The matrix is explicitly not vendor collaboration evidence.

### Feasibility

`backend/engine/dynamic_feasibility.py` checks coverage, unique vendors, event timing, event type, simulated location, synthetic price, capacity, budget, availability, scheduling, collaboration and venue suitability. Availability, scheduling, collaboration and venue checks are pending because the required event-specific evidence is not present.

### Ranking

Default weights are cost 0.4, rule-derived risk 0.4 and compatibility 0.2. The cost component is `1 - cost/budget`; risk and compatibility are normalized to 0–1. Unknown components are omitted and active weights are renormalized. The final score is scaled to 0–100. The result contains score factors, warnings, evidence scope and a deterministic explanation.

## Data and model audit

The simulation manifest records:

| Table | Rows | Evidence status |
|---|---:|---|
| `real_vendor_profiles.csv` | 18,430 | Profile/review-feature table; risk fields derived. |
| `synthetic_service_options.csv` | 57,549 | Synthetic service, pricing, capacity and location options. |
| `synthetic_event_requirements.csv` | 30 | Synthetic event templates. |
| `synthetic_availability.csv` | 191 | Synthetic availability scenarios. |
| `synthetic_collaboration_scenarios.csv` | 330 | Synthetic collaboration scenarios, not observed collaboration. |

### Saved Random Forest evaluation

The saved evaluation reconstructs the notebook split with `test_size=0.20`, `random_state=42`, stratification, 14,744 training rows and 3,686 test rows. Reported accuracy, macro precision, macro recall, macro F1 and weighted F1 are all 1.0000, with diagonal class supports High 576, Low 408 and Medium 2,702.

This is a rule-label reconstruction, not independent validation. The labels are derived from related review features, creating leakage/circularity risk. The evidence does not establish prediction of real vendor failures or quality outcomes. Original holdout IDs were not separately persisted.

## API reference

| Method | Endpoint | Purpose | Status |
|---|---|---|---|
| GET | `/health` | Backend health response | IMPLEMENTED |
| GET/POST | `/api/events` | List/create SQLite saved events | IMPLEMENTED |
| GET/PUT/DELETE | `/api/events/{event_id}` | Read/update/delete event or read legacy synthetic event | IMPLEMENTED |
| POST | `/api/packages/generate` | Generate from an existing synthetic event ID | IMPLEMENTED, legacy |
| POST | `/api/packages/generate-dynamic` | Generate fresh packages from user requirements | IMPLEMENTED |
| POST | `/api/feasibility/validate` | Legacy synthetic feasibility | IMPLEMENTED, legacy |
| POST | `/api/feasibility/validate-dynamic` | Validate source-bound USER package options | IMPLEMENTED |
| GET | `/api/locations` | List simulated locations | IMPLEMENTED |
| GET | `/api/admin/summary` | Research summary and model metrics | IMPLEMENTED, unauthenticated demo |
| GET | `/api/admin/vendors` | Paged/filterable profiles | IMPLEMENTED |
| GET | `/api/admin/service-options` | Paged/filterable service options | IMPLEMENTED |
| GET | `/api/vendor-demo/dashboard` | Vendor demo dashboard | IMPLEMENTED, demo |
| GET/PUT | `/api/vendor-demo/profile` | Vendor demo profile | IMPLEMENTED, demo |
| GET/POST/PUT/DELETE | `/api/vendor-demo/services[/{service_id}]` | Vendor demo service CRUD | IMPLEMENTED, demo |
| GET/POST/PUT/DELETE | `/api/vendor-demo/availability[/{availability_id}]` | Vendor demo availability CRUD | IMPLEMENTED, demo |

Request schemas are defined under `backend/schemas/`; route behavior and error handling are in `backend/api/`. The dynamic request accepts supported event types Wedding, Birthday and Corporate, positive budget/guest count, future date, duration up to 24 hours, supported services and `top_k` from 1–50. The dynamic feasibility endpoint requires a `USER-*` event ID and checks submitted option IDs/material fields against current source records.

## Current PP1 progress

### Implemented

- Dynamic request-time package generation.
- Synthetic option loading and currency transformation.
- Candidate filtering and bounded search.
- Model artifact verification and inference.
- Compatibility and feasibility result structures.
- Weighted ranking, warnings and explanations.
- React event creation, recommendation, comparison and feasibility views.
- SQLite saved-event workflow.
- Research/admin/vendor-demo pages and API routes.
- Unit/integration-style test files and persisted evaluation reports.

### Partial or constrained

- Risk intelligence is derived from review features and rule labels.
- Service compatibility is category-level, static and often constant across packages for one event.
- Event-specific availability, scheduling, collaboration and venue suitability remain pending.
- Search is bounded and may truncate.
- Admin/demo routes have no authentication or authorization.
- Historical test/build artifacts exist, but a fresh run and browser walkthrough are not claimed by this document.

## Evaluation summary

Saved `research_evaluation/` artifacts report 35 synthetic scenarios, 202 returned packages, 100% required-service coverage and budget fit among returned packages, 4,653 examined complete combinations, 20/35 search-truncated scenarios, and 202 `VERIFICATION_REQUIRED` statuses. TestClient timing was mean 1,986.38 ms, median 1,964.34 ms and p95 3,181.12 ms on one local machine.

The controlled baseline reranked the same examined package pool by cost. Across 26 comparable events, mean top-K overlap was 0.7115 and the proposed minus baseline mean recommendation cost was +LKR 77,258.32. This comparison is conditional on the shared, production-selected pool and cannot establish superiority over all possible vendor combinations.

## Limitations and threats to validity

- Synthetic prices and service options are not current vendor quotations.
- Synthetic availability and collaboration rows are not observations.
- Model labels are deterministic and related to input features; perfect accuracy is not real-world reliability.
- Search caps can omit better combinations; global optimality is unverified.
- Compatibility does not observe named-vendor cooperation.
- Returned-package rates do not describe all possible combinations or zero-result scenarios.
- TestClient timing is not deployed latency or throughput.
- No independent external test set, field outcome validation, fairness study, security audit or user study is evidenced.
- Admin and vendor-demo interfaces are not production-secured.

## PP2 and final research priorities

1. Establish field provenance and collect verified, timestamped quotations, availability, capacity, travel, venue and collaboration evidence.
2. Define an independent outcome label and frozen external test set before evaluating risk or recommendation quality.
3. Add NLP sentiment only with a documented annotation policy and ablation against the current rule-derived model.
4. Improve requirement matching with structured constraints and, where justified, NLP parsing; test ambiguity and missing-field behavior.
5. Compare bounded DFS with an explicit constraint solver or neutral full-universe baseline; report optimality/search regret.
6. Add explanation attribution for hard constraints, score components, evidence provenance and unknowns.
7. Support adaptive package reconfiguration only after re-running all constraints and recording revisions.
8. Add real vendor/API connectors with authentication, authorization, rate limits, freshness and provenance.
9. Run independent real-world evaluation, concurrent performance testing, calibration, subgroup analysis and reproducible final validation.

## Reproducibility and setup status

Verified from source: frontend scripts are in `frontend/package.json`; Vite proxies `/api` and `/health` to `http://127.0.0.1:8000`; backend database initialization is performed by `backend/db.py` when event operations occur; model loading is performed by `backend/engine/risk_signals.py` on dynamic generation.

Not verified from repository configuration: a canonical Python install command, backend startup command, database migration command, live vendor/API credentials and a complete clean-environment reproduction procedure. Treat the saved evaluation environment metadata as historical evidence, not as an installation guarantee.

## Citation map for reviewers

- Application entry and routes: `backend/main.py`, `backend/api/`.
- Algorithms: `backend/engine/`.
- Schemas: `backend/schemas/`.
- Frontend integration: `frontend/src/services/api.js`, `frontend/src/App.jsx`.
- Simulation provenance: `hybrid_simulation_v1/dataset_manifest.json`, `field_provenance.csv`.
- Model audit: `research_evaluation/model_evaluation.md`, `research_data_v2/pp1_final_model_verification/`.
- Evaluation: `research_evaluation/research_results_report.md`, `evaluation_summary.json`, `baseline_comparison.csv`, `ranking_sensitivity.csv`.
- Tests: `tests/` and saved report `final_validation/test_results.md`.

**Readiness statement:** Suitable for a supervised academic demonstration of synthetic, transparent package recommendation. Not production-ready and not evidence of live vendor or real-world model reliability.
