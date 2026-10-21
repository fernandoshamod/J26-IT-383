# Rehearsable three-minute live demo

## Before speaking

Reuse the already-running servers if available. If absent, follow [Task 5 startup commands](../pp1_task5_demo_readiness/system_discovery.md): project venv Python launches backend.main:app on 127.0.0.1:8000; npm run dev in frontend launches Vite on 127.0.0.1:5173. A fresh startup was not executed for Task 6. Check /health before the presentation. Use a date that is future **on demo day**; 2026-11-16 is a suitable prepared example as of 2026-10-17. If time or availability changes, choose a later date. Do not show historical SIMEVT pages as live recommendations.

## 0:00–0:35 — Event brief

Open Create Event. Enter Wedding, Philadelphia, PA, 2026-11-16, 10:00–18:00, 50 guests, Photography + Decoration, LKR 1,000,000, top 3. Say: “These are a new USER event's requirements; option prices and service areas are synthetic simulations.” [Wizard capture](./screenshots/create_event.png).

## 0:35–1:25 — Generate and inspect

Submit. Read the returned USER ID aloud; confirm it is new for this request. Point to service coverage, actual option/vendor IDs in research details, package cost and remaining budget, weighted score, and visible search truncation. Say: “The source code forms combinations from current service options; a fresh ID does not promise different combinations for identical inputs.” Do not assert this live run succeeded until it has actually completed. Prepared prior browser evidence: USER-5D45E28BC362, PKG-0001, LKR 305,535.41 cost, LKR 694,464.59 remaining, 84.8/100 displayed ranking score, 8 pending. [Recommendations capture](./screenshots/recommendations.png); [Task 5 executed request](../pp1_task5_demo_readiness/demo_execution_results.json).

## 1:25–2:05 — Explain and compare

Open “View Research Details”; point to cost, rule-risk favorability and category compatibility. Select two current-request packages and open comparison. Say: “The same categories can yield the same compatibility score, while selected vendors and costs differ. Review-rule risk is not a measured failure probability.” [Comparison capture](./screenshots/comparison.png).

## 2:05–2:40 — Feasibility

Choose “Check feasibility” and rerun if needed. Point to PASS in simulation count, pending count and exact research details. Say: “The captured package had 10 recorded simulation passes, 8 checks needing confirmation, 0 failures. No booking, availability, pair collaboration or venue suitability has been verified.” [Feasibility capture](./screenshots/feasibility.png).

## 2:40–3:00 — Close

Show Compatibility Rules or the evidence slide. Say: “The category matrix is active; pair-specific operational conflict detection is a separate Task 2/3 research prototype. Our next step is verified vendor evidence, a true individual-vendor baseline and venue-team integration.” [Compatibility capture](./screenshots/compatibility_rules.png).

## Backup path

If live submission stalls, show only the genuine captured screenshots and label them as prior browser evidence. Then cite [Task 5 live API results](../pp1_task5_demo_readiness/demo_readiness_report.md). If backend is down, do not claim a new live response or silently switch to saved packages.