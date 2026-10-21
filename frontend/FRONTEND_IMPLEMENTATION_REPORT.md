# PlanoVision frontend implementation report

> **Current-state update (Task 8):** The Legacy Demo frontend page, navigation route, and legacy API calls are absent from the active application. Historical Task 7 observations below are retained as a dated record. See [dynamic-only validation](./DYNAMIC_ONLY_VALIDATION.md) for current verification.

**Task:** 7 — professional frontend development. **Date:** 2026-10-17 (Asia/Colombo). This is a research prototype using synthetic simulation data and existing FastAPI endpoints. The frontend does not implement accounts, booking, confirmed vendor availability or independent vendor-outcome validation.

## Architecture

The application is a React/Vite single-page site with hash navigation, three visible navigation groups and a responsive sidebar. [App.jsx](./src/App.jsx) owns the current unsaved event, latest API response, comparison selection and feasibility result. [AppShell.jsx](./src/components/AppShell.jsx) provides the sidebar, topbar, breadcrumbs and footer. [UI.jsx](./src/components/UI.jsx) provides icon, badge, status, notice, KPI, loading, empty-state and progress components. [api.js](./src/services/api.js) contains the live FastAPI calls and actionable error parsing. Pages are separated under [pages/](./src/pages/). Visual tokens and responsive rules are in [App.css](./src/App.css).

No React ranking implementation or mock package list was added. The latest recommendation list comes only from POST /api/packages/generate-dynamic. A new request clears prior results and comparison state; the backend creates a fresh USER event and searches current option records. Browser state is ephemeral and disappears on reload.

## Areas and pages

| Area | Page | Implemented scope |
|---|---|---|
| Public website | Home | Research-focused hero, dynamic process, capabilities, transparency, CTA and footer. |
| Public website | Methodology | Actual candidate/search caps, scoring defaults, validation sequence and model limitation. |
| User workspace | Overview | Actions and current-session API-derived summary; explicitly no saved history. |
| User workspace | Create Event | Four-step wizard: event context, guests/services, budget/top-K and review. Supported locations come from the live API with search. |
| User workspace | Recommendations | Live returned packages, selected vendors/options, LKR estimates, ranking components, risk and compatibility evidence, feasibility, explanations, filters and search metadata. |
| User workspace | Compare Packages | Side-by-side comparison of two or three packages from the current USER response only. |
| User workspace | Feasibility | Dedicated USER-event check on a returned package, with passed/pending/failed checks and verification requirements. |
| Research demo admin | Overview | Read-only saved dataset and Task 5 experiment totals; not live activity. |
| Research demo admin | Vendor Intelligence | Searchable vendors from the current response only; full catalog unavailable without an API. |
| Research demo admin | Service Options | Filterable option rows from the current response only; full catalog unavailable without an API. |
| Research demo admin | AI Model | Reconstructed holdout metrics, features, support, confusion matrix and prominent rule-label warning. |
| Research demo admin | Recommendation Analytics | Saved Task 5 success, coverage, feasibility, baseline, sensitivity and local timing metrics. |
| Research demo admin | Compatibility Rules | Exact read-only 15-pair category matrix snapshot with interpretation. |
| Research demo admin | Research Reports | Links to actual read-only copies of seven Task 5/6 Markdown or CSV files. |

The admin group is an **unprotected research/demo analytics workspace**. No auth or admin CRUD API exists. It performs no source-data edits.

## API integrations and data provenance

| Endpoint | Frontend use |
|---|---|
| GET /api/locations | Supported synthetic city/state choices. |
| POST /api/packages/generate-dynamic | Creates a new USER request; all recommendation cards and metadata come from its response. |
| POST /api/feasibility/validate-dynamic | Rechecks the selected returned USER package using its event and current option IDs. |

[Evaluation summary snapshot](./src/data/evaluation_summary.json) is an exact copy of the unchanged Task 5 JSON. [Compatibility rule snapshot](./src/data/compatibility_rules.json) was converted from the unchanged category CSV. [Research document copies](./public/research/) are exact copies of existing reports and comparisons. Their public routes returned HTTP 200. These static data are labeled saved research evidence and are **never used as recommendation packages**. Static copies will need manual refresh if the original research is updated; the originals were not modified.

## Research correctness in the UI

- Cost and remaining budget use backend LKR estimates. The UI does not edit option pricing or eligibility.
- Rule-derived low-risk favorability is correctly oriented: Low=100, Medium=60, High=20; higher is more favorable, not a failure probability.
- Compatibility is a service-category heuristic, not proof of vendor-to-vendor collaboration. Unknown values remain unknown.
- PASS_IN_SIMULATION, VERIFICATION_REQUIRED and FAIL retain backend meanings. Simulated pass does not confirm live availability.
- Candidate cap, node cap, examined combinations, rejected FAIL count, per-service candidate counts and truncation warning are displayed.
- A first-ranked package is not called globally optimal under bounded search.
- The saved model's 100% reconstructed holdout agreement is labeled rule imitation and not real-world outcome validation.
- No package recommendations, personal statistics, login, live bookings or quotations are fabricated.

## Responsive and accessible behavior

The CSS covers desktop, tablet and mobile layouts. The sidebar collapses on desktop and becomes a scrollable drawer on narrow screens. Tables and comparisons can scroll within their containers. Form controls have labels, buttons have focus indicators, status/error messaging uses live roles, loading and empty states are explicit, and reduced-motion preferences are respected. Icons are local inline SVGs; no external icon package or font download is required.

## Executed verification

- Backend: project venv Python ran the complete unittest suite: **43 tests passed, 0 failures**, 75.416 seconds. A Starlette/httpx deprecation warning appeared without failing tests.
- Frontend: Vite 8.3.4 production build passed: 29 transformed modules, 7.71 seconds, 292.94 kB JavaScript and 22.37 kB CSS output before gzip. oxlint passed with no warnings after cleanup.
- Browser: the already running local backend and Vite server were used. A Philadelphia, PA Wedding with 50 guests, Photography + Decoration and LKR 1,000,000 created a new USER ID and 10 returned packages. The top package showed LKR 305,535.41, LKR 694,464.59 remaining, risk favorability 100/100, category compatibility 85/100 and VERIFICATION_REQUIRED. Package details, explanations, two-package comparison and a dedicated USER feasibility check were exercised. The dedicated check showed the same cost and no API error.
- Historical Task 7 browser record: the former legacy page and its sample-event flow were exercised then. That page is now removed. Task 8 independently checked all **14 current** navigation destinations; see the dynamic-only validation report. The earlier 375 px menu and sidebar check remains a Task 7 observation.
- Research document routes: all seven static report links returned HTTP 200 locally.
- Integrity: all eight source/model artifact hashes and all seven original Task 5 output hashes still match their pre-task values. The seven bundled document copies match their originals byte for byte. No original dataset, model, research output, backend endpoint or production ranking weight was changed.

These are local development-server observations, not deployed performance or an external accessibility audit. No screenshots are included.

## Known limitations and next work

The backend offers no safe read-only full vendor or option catalog endpoint, so the two admin explorer tables can inspect only vendors/options returned by the current request. Admin is unprotected and should remain a research/demo area until real authentication and authorization are designed. Static research snapshots require an explicit update process if results change. Current plans are not saved. Synthetic pricing, simulated service areas, unverified vendor availability/collaboration and rule-derived model labels continue to limit claims. Independent user testing and assistive-technology review were not performed.

## Start on Windows

From the project root in PowerShell:

~~~powershell
Set-Location 'D:\Vendor-Intelligence-System'
& '.\venv\Scripts\python.exe' -m uvicorn backend.main:app --host 127.0.0.1 --port 8000
~~~

In a second PowerShell terminal:

~~~powershell
Set-Location 'D:\Vendor-Intelligence-System\frontend'
npm run dev
~~~

Open http://127.0.0.1:5173. For checks, use the project Python with `-m unittest discover -s tests -v`, and run `npm run lint` and `npm run build` from [frontend/](./). The production build emits [dist/](./dist/).


