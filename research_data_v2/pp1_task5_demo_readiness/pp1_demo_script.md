# Three-minute live PP1 demonstration

## Before the audience arrives

Use the existing virtual environment. Confirm `http://127.0.0.1:8000/health` returns HTTP 200 and `http://127.0.0.1:5173/#create-event` loads. Do not launch duplicate servers. If neither is running, from separate terminals in the project root run `& .\venv\Scripts\python.exe -m uvicorn backend.main:app --host 127.0.0.1 --port 8000`, then from `frontend` run `npm run dev`. These fresh-start commands were discovered but not executed during this audit.

## Script

**0:00–0:25 — Research problem and architecture.** “PlanoVision builds vendor packages for a new event from current service-option records. FastAPI validates the request and searches bounded combinations. React shows the results. All prices and service areas in this prototype are synthetic estimates.”

**0:25–1:05 — Submit the event.** On Create Event choose Wedding, Philadelphia PA, a date after the current day, 10:00–18:00, 50 guests, Photography + Decoration, LKR 1,000,000 and top-K 3. Point out the simulation disclosure. Submit once, wait for the loading state, and show the fresh USER ID. Explain that response-local PKG labels can repeat across requests.

**1:05–1:40 — Explain packages.** Show three cards, LKR cost, remaining budget, ranking score, rule-risk favorability, category compatibility and the search-limit warning. Expand Research Details to show actual option/vendor IDs, scoring components, explanations and verification needs. “Rank only orders the examined pool.”

**1:40–2:05 — Compare alternatives.** Select two packages from this USER event. Show the cost difference and identical risk/compatibility wording if the values match. “Category compatibility does not prove vendor collaboration; review-derived risk is not a verified failure probability.”

**2:05–2:30 — Check feasibility.** Return to recommendations, choose Check feasibility, then Rerun feasibility. Show passed, pending and failed counts. “Pending checks include availability, collaboration, scheduling and venue; this is not a confirmed booking.”

**2:30–3:00 — Research boundaries and next steps.** Briefly open Compatibility Rules and Research Reports. Identify the historical saved evaluation as separate from live USER results. “Task 2 conflict detection, Task 3 shadow assessment and Task 4 optimization remain isolated research prototypes. Next we need event-specific evidence, a true individual-vendor baseline and a venue-team contract.”

## Backup plan

If the live request is slow or unavailable, show the unaltered `demo_execution_results.json` from this directory and state its execution date and synthetic status. Show the documented browser observation and screenshot checklist; do not pretend an old USER ID is a live event. If the frontend fails, call `/health`, `/api/locations` and `/api/packages/generate-dynamic` from a prepared API client with the current future date. If the backend fails too, present the recorded Task 5 report, the 32 passing tests and Task 4's benchmark CSV, clearly labeling them historical local evidence.