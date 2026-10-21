# PlanoVision academic demonstration walkthrough

This is a **manual checklist**, not a completed browser walkthrough. The FastAPI routes were exercised through TestClient and the React production build passed. Vendor information, prices, capacity and service areas here are synthetic simulation records; availability and collaboration require verification.

## Start on Windows

In the first PowerShell terminal:

~~~powershell
Set-Location 'D:\Vendor-Intelligence-System'
& '.\venv\Scripts\python.exe' -m uvicorn backend.main:app --host 127.0.0.1 --port 8000
~~~

Keep it open. In another terminal:

~~~powershell
Set-Location 'D:\Vendor-Intelligence-System\frontend'
npm run dev
~~~

Open http://127.0.0.1:5173. The [Vite configuration](../frontend/vite.config.js) proxies /api and /health to port 8000. Confirm http://127.0.0.1:8000/health responds. The Python path above is the project virtual environment used for backend tests.

## Suggested live demonstration

1. Open **Event Planning** in the [React application](../frontend/src/App.jsx).
2. Choose **Wedding**, date **2099-06-20**, time **10:00–16:00**, **Philadelphia, PA**, **50 guests**, **LKR 10,000,000**, **Photography** and **Decoration**, and **2** ranked packages. This future date is a repeatable demonstration input, not a vendor availability claim.
3. Select **Generate My Packages**. Show the new USER event ID, result message, candidate counts, limits and truncation notice. Repeat the request to show a different USER ID; deterministic option order can remain the same.
4. Read each selected service, vendor and source option ID, estimated LKR cost and remaining budget. The prices are synthetic estimates, not quotes.
5. Explain the rule-derived low-risk favorability: higher is more favorable (Low=100, Medium=60, High=20). It is not a verified failure probability. Compatibility is a service-category rule, not proven vendor collaboration. Unknown evidence stays unknown.
6. Show VERIFICATION_REQUIRED feasibility, passed and pending checks, ranking explanation, trade-offs and verification steps.
7. Select **Check Feasibility** on a returned package. The [USER feasibility route](../backend/api/feasibility.py) validates the in-memory event and resolves submitted option IDs against current source rows; altered prices are rejected. Confirm the cost and checks match the package.
8. Visit legacy event and package views. Sample-event evidence on the legacy route does not transfer to a new USER event.

## Manual observation checklist

| Observation | Record during demo |
|---|---|
| Supported event input produces a new USER ID | [ ] |
| Required services appear exactly once and vendors are unique | [ ] |
| Costs, remaining budget and ranking factors display | [ ] |
| Risk direction, category compatibility and unknown values are clear | [ ] |
| Feasibility status, pending checks and explanation display | [ ] |
| Check Feasibility works on a returned package | [ ] |
| Loading, no-results and API errors display clearly | [ ] |
| Legacy navigation still works | [ ] |

## Troubleshooting

| Symptom | Check |
|---|---|
| Python/import error | Use the exact project venv Python above, not WindowsApps Python or global packages. |
| Port 8000 in use | Stop the conflicting process or align the backend port and [Vite proxy](../frontend/vite.config.js) for the demo session. |
| UI API error | Check /health, backend terminal output and the Vite proxy. |
| Frontend dependencies missing | Run npm ci from [frontend/](../frontend/) using its [lockfile](../frontend/package-lock.json), then npm run dev. |
| Unsupported location/service or no results | Pick a location from /api/locations; check the event type and services, increase the budget or reduce guests. |
| HTTP 422 on USER feasibility | Submit unchanged option IDs from a generated package; invented IDs and altered fields are rejected. |
| Model loading/hash error | Confirm the original artifact is present and unchanged; see [research integrity](./research_integrity_check.md). Do not retrain for the demo. |
| Slow request | Local TestClient smoke took about 2.7–5.3 seconds for three representative calls; this is not deployed latency. |

See [test evidence](./test_results.md) and [limitations](./known_limitations.md).
