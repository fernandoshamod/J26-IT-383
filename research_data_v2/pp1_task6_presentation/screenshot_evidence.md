# Genuine browser captures and manual follow-up

Captured 17 October 2026 from the shared, already-running Vite browser at 127.0.0.1:5173 using Playwright page.screenshot. Files were saved directly inside this Task 6 directory. The captures do not show a fresh server start or a newly submitted Task 6 event. Their visible current request was USER-5D45E28BC362, Wedding, Philadelphia PA, 2026-11-16; option records and prices are synthetic.

| File | Route | Visible evidence | Presentation use |
|---|---|---|---|
| [create_event.png](./screenshots/create_event.png) | /#/create-event | Wizard step 1, event/date/location inputs | Show entry flow; later steps are not pictured |
| [recommendations.png](./screenshots/recommendations.png) | /#/recommendations | Three current USER package cards, score/cost/status/truncation | Main demo UI |
| [recommendations.png](./screenshots/recommendations.png) | /#/recommendations | Same cards at narrow viewport | Responsive example only, not accessibility certification |
| [comparison.png](./screenshots/comparison.png) | /#/comparison | Two selected same-request packages, cost/vendor differences, equal compatibility | Compare view |
| [feasibility.png](./screenshots/feasibility.png) | /#/feasibility | PKG-0001, 10 passed in simulation, 8 pending, 0 failed | Pending verification |
| [compatibility_rules.png](./screenshots/compatibility_rules.png) | /#/admin-compatibility | Category pair explorer; collaboration disclaimer | Category-vs-pair distinction |
| [research_reports.png](./screenshots/research_reports.png) | /#/admin-reports | Historical report links and summaries | Research evidence navigation |

The screenshot files are genuine rendered pixels, not mocked graphics. The report contains no fabricated screenshot. Capture SHA-256 and byte sizes in [screenshot_manifest.csv](./screenshot_manifest.csv) during final verification.

## Manual captures still useful

1. On presentation day, capture the four wizard steps and new submission before a fresh USER ID is known.
2. Capture the live response with the date, selected services, search metadata and all three cards readable.
3. Expand one “View Research Details” section and capture full score/explanation provenance.
4. Rerun feasibility and capture the resulting status plus expanded raw checks.
5. Capture browser console/network panel only if needed to substantiate a claim about error-free operation; none was captured in this task.
6. Capture desktop and mobile at planned projector/browser dimensions; current captures do not constitute a full accessibility or responsive audit.

See [Task 5 screenshot checklist](../pp1_task5_demo_readiness/screenshot_checklist.md).