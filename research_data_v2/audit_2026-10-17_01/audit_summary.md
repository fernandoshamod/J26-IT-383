# PlanoVision PP1 Task 1 audit summary

**Audit date:** 2026-10-17. **Scope:** read-only project inspection, local data inventory/quality assessment, and public source review. No recommendation feature, application file, source dataset, model, or prior research output was edited. All new outputs are in this audit directory. This is a research-data preparation audit, not a fresh run of the recommendation engine.

## Existing system

The user-facing React [App](../../frontend/src/App.jsx) sends current event requirements to [generate-dynamic](../../backend/api/packages.py). [Request validation](../../backend/schemas/dynamic_package_request.py) checks event type, date, time, city/state text, guest count, positive finite LKR budget, service names and top-K. The [dynamic service](../../backend/engine/dynamic_package_service.py) reads current [synthetic service options](../../hybrid_simulation_v1/synthetic_service_options.csv), creates a UUID-based USER ID, filters by category/location/event support and catering capacity, then calls [bounded search](../../backend/engine/bounded_package_generator.py). Search uses a default 12 options per service and 5,000 nodes, checks distinct vendors and budget, validates each complete examined package before ranking, excludes FAIL and ranks simulation passes before pending packages. Default score weights are cost 0.4, review-rule risk favorability 0.4 and static category compatibility 0.2; missing score components are omitted and weights renormalized. [Explanations](../../backend/engine/package_explanations.py) cite these fields. The [USER feasibility route](../../backend/api/feasibility.py) resolves supplied IDs to current source options. The active [frontend client](../../frontend/src/services/api.js) uses dynamic endpoints. Separate historical event-ID routes remain in the backend.


The inspected React pages include Home, Methodology, Overview, Create Event, Recommendations, Compare Packages, Feasibility, and research/admin views for vendors, service options, model, analytics, category compatibility and reports. [App state](../../frontend/src/App.jsx) keeps the current USER event result for normal page navigation, while [package views](../../frontend/src/pages/PackageViews.jsx) display ranking and feasibility. This is a source-code observation, not a browser usability or accessibility test.
The dynamic path does not load saved packages. This was established by source trace, **not** by executing new smoke tests in this read-only task. Previously published [evaluation results](../../research_evaluation/evaluation_summary.json) describe 35 synthetic scenarios; those results were inspected, not regenerated.

## Data counts and boundaries

See [inventory](./dataset_inventory.csv), [quality report](./data_quality_report.csv) and [field provenance](./data_provenance_report.csv) for machine-readable detail.

| Local table | Rows | Interpretation |
|---|---:|---|
| Vendor profiles | 18,430 | Business/review-shaped records; public row lineage and reuse rights still need confirmation |
| Synthetic service options | 57,549 | Simulation prices, capacities, service areas, resources, event support |
| Synthetic event requirements | 30 | Historical SIMEVT scenarios, not USER requests |
| Synthetic availability | 191 | Historical event-specific simulation only |
| Synthetic collaboration | 330 | Random simulation outcomes, not verified vendor-pair history |
| Service-category compatibility | 15 | Static heuristic pairs; not vendor-to-vendor collaboration |
| Local Yelp-named business and review samples | 1,000 each | Local samples; exact acquisition and license unverified |
| Legacy availability, service detail, event requirement and venue constraint CSVs | 0 each | Headers only; no usable evidence rows |

The existing Random Forest predicts review-rule-derived High/Medium/Low labels from stars, review_count, collected_review_count, mean_review_rating and rating_std. Existing label-to-score direction is Low=100, Medium=60, High=20; higher is **more favorable review-rule signal**, not higher failure risk. The [model evaluation](../../research_evaluation/model_evaluation.md) reports a reconstructed holdout with 100% agreement, which does not validate real-world failure prediction.

## Measured data quality

The single-pass [quality report](./data_quality_report.csv) found seven option service categories (Audio Visual, Catering, Decoration, Entertainment, Equipment Rental, Event Planning, Photography) and 704 distinct **simulated** city/state service-area pairs; Philadelphia, PA has 5,454 option rows. Profile, option and synthetic-event candidate primary IDs have no blank or duplicate rows in the audited files. Every synthetic option business ID matched a profile ID. By contrast, the older [vendor risk dataset](../../vendor_risk_dataset.csv) has **235 rows in duplicate business-ID groups and 235 rows whose IDs do not match the current profile table**; these counts may describe overlapping rows and must not be added. The production risk inference reads the unique current profile table, rather than treating that older CSV as a clean key table.

Profile missingness includes 2,805 blank `caters`, 3,543 blank `price_range`, 155 blank `attributes`, and 1,014 blank `hours` out of 18,430 rows. Synthetic option blank counts include 9,114 `max_guests` and `min_billable_guests`, and 57,087 `min_billable_hours` out of 57,549; many are pricing-basis inapplicability, so blank does not automatically mean an erroneous record. All 191 availability event/vendor references and 330 collaboration event/vendor references matched their historical sample tables, but that does **not** validate their simulated statuses for a new USER event. Local 1,000-business sample missingness includes 41 addresses and 152 hours. The machine-readable report records denominators and other blank fields. All synthetic option unit prices were finite and positive in this scan, and the 15 category pairs had no duplicate unordered pair. Blank/duplicate/FK checks do not establish semantic correctness, genuine identity, current operation, or valid market prices.

Two existing pickle artifacts were inventoried by hash: [active Random Forest](../../models/vendor_risk_random_forest.pkl) and [older model artifact](../../vendor_risk_model.pkl). The active [inference module](../../backend/engine/risk_signals.py) checks the former's pinned SHA-256, five feature names and class labels before use. The older artifact is not referenced by that dynamic inference path; its internal metadata was not deserialized in this read-only audit. No model was retrained or loaded here.
## Proposal and public sources

No official proposal PDF was found locally, so exact FR1–FR13 and stated targets are **not verified**. [Provisional gap analysis](./proposal_gap_analysis.md) identifies what source code supports and what data is missing. [Source review](./public_dataset_sources.md) assesses UCSD Google Local, Yelp and OpenStreetMap without downloading data. The named Yelp open-dataset page was inaccessible in this environment, and its current license terms remain unverified. OpenStreetMap is useful for geospatial checks subject to ODbL; none of the sources confirms event quotations, bookings, collaboration or operational incidents.

## Priority and next task

P1: obtain the proposal/permissions; establish provenance and a fair individual-vendor baseline definition; collect/adjudicate vendor-pair and conflict evidence; agree the [venue contract](./venue_integration_contract.md) with the separate team; keep new USER availability unknown absent event-specific evidence. P2: preference validation, broader alternatives, independent risk outcome research, response-time experiments, and user/SUS study. The [roadmap](./implementation_roadmap.md) sequences these dependencies.

**Exact recommended Task 2:** implement an isolated provenance-aware vendor-pair evidence and conflict-test-case layer with symmetric pair lookup, explicit unknown-as-pending behavior, and deterministic resource-conflict fixtures. Preserve the production category matrix and ranking until independently reviewed evidence and tests justify integration. Do not implement the venue team's component.

## Validation boundary

Existing Python tests and frontend build were **skipped**: importing Python can generate bytecode under backend/tests and Vite writes dist/cache outside the permitted output directory. Existing test code was inspected for side effects, including a temporary CSV write in the risk tests. Static source inspection, CSV inventory/hash generation, quality calculation, and schema validation are the permitted checks in this task. The staging helper was inspected but not executed on external data. No new API or browser behavior is claimed as freshly tested.


## Final isolated validation

Executed: parsed all 22 inventory rows and 44 quality checks; parsed the 15 provenance groups; parsed `schema_definitions.json` and confirmed eight entities; confirmed eight header-only schema CSV templates have zero data rows; confirmed all inventory classifications are one of REAL_PUBLIC, DERIVED, SYNTHETIC_TEST or UNKNOWN; parsed all three audit PowerShell scripts with zero syntax errors; verified the staging helper rejects a header-only template and creates no staged data. Recomputed SHA-256 for all 22 inventoried source/model/research files after writing this audit: **0 mismatches**. This verifies the enumerated inputs, not an all-files filesystem snapshot. No existing project file was intentionally changed. Existing backend tests, frontend lint/build, and API smoke tests were not run because their imports/build output can write outside this task's allowed directory.
