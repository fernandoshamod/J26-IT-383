# 01 Existing system audit

Date verified: 2026-10-20. Scope: live source in `D:\Vendor-Intelligence-System`.

## Findings

- Before this change, there was no database configuration or database connection. `backend/api/events.py` read the static event CSV through `backend/engine/package_data_loader.py`; the React create flow kept the current event and recommendation response in React state.
- The research datasets are CSV files. The existing Random Forest artifact is `models/vendor_risk_random_forest.pkl`; bounded search is implemented in `backend/engine/bounded_package_generator.py`.
- The original event API exposed only `GET /api/events/{event_id}` for synthetic CSV events. No user-event Create, Update, Delete or list endpoint existed.
- The dynamic package service generated a `USER-*` identifier at request time and returned recommendations without persisting the event or generated recommendations.
- There is no authentication, session ownership, user identity or authorization control. The new SQLite CRUD endpoints therefore provide single-workspace demonstration persistence, not multi-user security.

## Verified source paths

- Backend app: `backend/main.py`
- Event routes and static-event fallback: `backend/api/events.py`
- New database connection/store: `backend/db.py`
- Event validation schema: `backend/schemas/event.py`
- Dynamic request schema: `backend/schemas/dynamic_package_request.py`
- Package endpoint: `backend/api/packages.py`
- Dynamic service: `backend/engine/dynamic_package_service.py`
- Existing generator preserved: `backend/engine/bounded_package_generator.py`
- Frontend state and orchestration: `frontend/src/App.jsx`
- Create form: `frontend/src/pages/EventWizard.jsx`
- Persisted event list: `frontend/src/pages/SavedEvents.jsx`
- API client: `frontend/src/services/api.js`

## Recommended changes completed

A minimal SQLite store was added because no persistent database existed. The existing research engine and datasets were not changed. The UI now has a My Events page, backend-backed save/update/delete actions, technical IDs under expandable details, responsive cards, loading/error/empty states and destructive-action confirmation.
