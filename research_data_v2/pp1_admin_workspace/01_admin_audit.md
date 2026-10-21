# PP1 Admin Audit

## Verified existing system

- Frontend: React + Vite in `frontend/src/`; hash navigation is controlled by `frontend/src/App.jsx` and the navigation definitions in `frontend/src/data/navigation.js`.
- Backend: FastAPI in `backend/main.py`; existing routers include events, feasibility, package generation and locations.
- Database: SQLite at `backend/planovision.db` by default, configurable with `PLANOVISION_DB_PATH`. The existing `events` table is maintained by `backend/db.py` and CRUD routes in `backend/api/events.py`.
- Vendor data: `hybrid_simulation_v1/real_vendor_profiles.csv` (18,430 rows) is historical research profile data and is not editable through this demo.
- Service options: `hybrid_simulation_v1/synthetic_service_options.csv` (57,549 rows) are synthetic simulation inputs loaded by `backend/engine/package_data_loader.py`.
- Evaluation evidence: `research_evaluation/evaluation_summary.json` and the existing research reports. The Random Forest and bounded DFS package generator remain unchanged.

## Gaps found

There was no authenticated admin API, vendor CRUD API, service-option CRUD API or report/PDF endpoint. Existing research pages were useful for evidence but did not provide paginated inspection of the full vendor and service-option datasets.

## Safe decision

A focused read-only academic admin data surface was added. It reads the existing loaders and SQLite event store, does not write research CSV files, does not claim authentication, and does not alter model or recommendation logic.
