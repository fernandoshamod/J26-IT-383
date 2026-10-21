# Dynamic-only frontend validation

**Date:** 2026-10-17 (Asia/Colombo). **Scope:** active React frontend, FastAPI contracts, legacy dependencies and historical package files.

## Outcome

The current frontend already had no [Legacy Demo page](./src/pages/), sidebar item, route entry or legacy API client functions when this task began. No deletion of a source file was needed. A direct visit to `/#/legacy` normalized to `/#home` and displayed the public landing page. The 14 remaining navigation destinations opened in the browser; none showed a Legacy Demo item. The compiled JavaScript contained neither `Legacy Demo` nor `SIMEVT-0000`. The active [API client](./src/services/api.js) calls only the locations, dynamic generation and dynamic USER feasibility endpoints.

The [research reports view](./src/pages/AdminPages.jsx) now explicitly labels historical SIMEVT IDs in its downloadable evaluation CSVs as research records, never sources of current recommendations. The [frontend implementation report](./FRONTEND_IMPLEMENTATION_REPORT.md) now identifies its earlier legacy browser test as historical and lists only current active pages and API integrations.

## Request-time path

[App.jsx](./src/App.jsx) submits event requirements through `generateDynamic`. [The dynamic backend service](../backend/engine/dynamic_package_service.py) loads [current service options](../backend/engine/package_data_loader.py), creates a new UUID-based USER event, selects eligible candidates, obtains risk and compatibility signals, and invokes [bounded package search](../backend/engine/bounded_package_generator.py). The search validates examined combinations before ranking and returns new package results. The dynamic path has no reference to the historical package recommendation CSVs. Frontend package IDs such as PKG-0001 are transient identifiers within a response; the same ID text may appear in different requests without indicating reuse of a saved package.

A local FastAPI TestClient smoke sent the same Philadelphia, PA Wedding request twice (Photography + Decoration, 50 guests, LKR 10,000,000, top-K 2). Both generation calls returned HTTP **200** and different IDs: `USER-0D8F57C1DD2F` and `USER-D459B9C94CDB`. The response stated `generation_mode=dynamic_user_request`. Its first package used source option IDs `SIMOPT-000111-B` and `SIMOPT-001022-S`, estimated **LKR 305,535.41**. POST `/api/feasibility/validate-dynamic` on those actual options returned HTTP **200**, `VERIFICATION_REQUIRED`, and the same cost. Availability and collaboration remain unverified.

## Backend and historical data retained

The legacy backend endpoints remain registered because [backend package routes](../backend/api/packages.py), [legacy feasibility](../backend/api/feasibility.py), and [sample event lookup](../backend/api/events.py) are still asserted by [regression tests](../tests/test_final_validation.py), [evaluation tests](../tests/test_research_evaluation.py) and [dynamic feasibility tests](../tests/test_dynamic_feasibility.py). They are no longer called by the active frontend. Removing them would require a separate backend compatibility and documentation change.

Eight historical package recommendation/detail CSVs remain in [data/cleaned/](../data/cleaned/). Every one is referenced by the [research notebook](../notebooks/01_vendor_dataset_audit.ipynb). They were neither deleted nor moved: moving them would break historical notebook paths and weaken reproducibility. They are not read by the dynamic recommendation service. The files are:

- `combined_package_recommendations.csv`
- `combined_package_recommendations_eligibility_enhanced.csv`
- `combined_package_recommendations_feasibility_enhanced.csv`
- `combined_package_recommendations_full_evidence.csv`
- `combined_package_recommendations_geo_enhanced.csv`
- `combined_package_vendor_details.csv`
- `final_package_recommendations.csv`
- `final_package_vendor_details.csv`

## Executed checks

| Check | Result |
|---|---|
| Complete backend unittest suite, project venv | **43 passed, 0 failures**, 107.094 seconds |
| React production build, Vite 8.3.4 | **PASS**, 28 modules, 4.84 seconds after the documentation notice update |
| Frontend lint (oxlint) | **PASS**, no findings |
| Dynamic generation smoke | HTTP 200 twice; two distinct USER IDs |
| Dynamic USER feasibility smoke | HTTP 200, VERIFICATION_REQUIRED, matching LKR cost |
| Browser `/#/legacy` | Redirected to `/#home`; no legacy page or navigation item |
| Browser current navigation | All **14** destinations opened |
| Source/model and Task 5 output SHA-256 checks | **8 + 7 matched**, no mismatches |
| Active frontend source search | No legacy generation, sample-event or legacy feasibility call sites |
| Historical package files | All eight remain in place and have notebook references |

## Remaining limits

The old backend routes remain callable directly for test and historical compatibility, though the active UI does not expose them. Research report downloads still contain historical SIMEVT scenario IDs and recorded package identifiers; they are clearly labeled historical data. Dynamic packages still use synthetic option prices and simulated eligibility. A fresh USER event does not prove real vendor availability, collaboration or booking.

