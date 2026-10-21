# Discovered system and demonstration path

## Entry points and startup

Backend app: `../../backend/main.py`, exported as `app`. Existing server was listening on port 8000 and GET `/health` returned HTTP 200. A fresh-start command, not executed in this audit, is:

```powershell
cd D:\Vendor-Intelligence-System
& .\venv\Scripts\python.exe -m uvicorn backend.main:app --host 127.0.0.1 --port 8000
```

Frontend: `../../frontend/package.json` exposes `npm run dev`; `../../frontend/vite.config.js` binds `127.0.0.1:5173` and proxies `/api` to port 8000. The shared browser loaded the existing Vite server. A fresh-start command, not executed here, is `cd frontend; npm run dev`. Check the two ports before starting new processes.

## Registered HTTP routes

GET `/` and `/health` in `../../backend/main.py`; GET `/api/locations` in `../../backend/api/locations.py`; GET `/api/events/{event_id}` in `../../backend/api/events.py`; POST `/api/packages/generate-dynamic` and historical `/api/packages/generate` in `../../backend/api/packages.py`; POST `/api/feasibility/validate-dynamic` and historical `/api/feasibility/validate` in `../../backend/api/feasibility.py`. Live OpenAPI returned HTTP 200 and listed these routes. The frontend uses only the dynamic package and feasibility endpoints.

## USER event data flow

`../../frontend/src/pages/EventWizard.jsx` collects type, future date, times, supported city/state, guests, LKR budget, required services and top-K. `../../frontend/src/App.jsx` submits via `../../frontend/src/services/api.js`. `../../backend/schemas/dynamic_package_request.py` validates. `../../backend/engine/dynamic_package_service.py` loads current synthetic option rows, creates a UUID USER ID, selects candidates, obtains Random Forest rule-risk signals and category compatibility, then calls `../../backend/engine/bounded_package_generator.py`. The bounded generator validates examined combinations before ranking, excludes FAIL, scores, explains and returns top-K. The package's PKG number is response-local rank, not a catalog key.

Recommendations, comparison and feasibility are in `../../frontend/src/pages/PackageViews.jsx`. Selected comparison IDs and the current result live in App state; a new generation clears previous result and selection. Dynamic feasibility sends the current USER event and package options; the backend resolves submitted option IDs against current source records and rejects conflicting material fields. `../../frontend/src/pages/FeasibilityDashboard.jsx` displays pass/pending/fail counts and evidence.

Research pages live in `../../frontend/src/pages/AdminPages.jsx`, with navigation in `../../frontend/src/data/navigation.js`. They display historical saved research summaries; they are not live USER recommendations. Existing automated tests are in `../../tests/`. Research evaluation is in `../../research_evaluation/`; Task 2, 3 and 4 prototypes are in sibling `research_data_v2` directories.
The observed port-8000 process command line invoked D:\Vendor-Intelligence-System\venv\Scripts\python.exe -m uvicorn backend.main:app --reload; the port-5173 process was Node running the local Vite CLI. Windows reported the Python host executable underneath the virtual environment as a WindowsApps python3.13.exe; the invocation path was the project virtual environment.

