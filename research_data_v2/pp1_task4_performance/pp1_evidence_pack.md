# PP1 evidence pack — PlanoVision

## Three-minute presentation outline

**0:00–0:30 — Architecture.** React/Vite submits event requirements to FastAPI. The backend reads current synthetic service options, selects location/event/category candidates, joins vendor profile risk signals, applies category compatibility, searches bounded combinations, validates feasibility, ranks and explains. Each submission gets a fresh USER ID. No stored package catalog supplies recommendations.

**0:30–1:20 — Technical demo.** Start the existing backend and frontend using the project instructions. In Event Planning, enter Wedding, Philadelphia PA, 21 October 2026, 10:00–18:00, 50 guests, LKR 1,000,000, Photography and Decoration. Generate packages; point out new USER ID, selected option/vendor IDs, LKR costs, remaining budget, risk favorability, category compatibility and pending feasibility checks. Submit again and show a different USER ID. Explain that response-local PKG numbers are rank labels, not saved package IDs.

**1:20–2:05 — Research evidence.** Explain the 12-candidate/service and 5,000-node caps and visible truncation. Show the isolated Task 2 controlled conflict fixtures and Task 3 shadow assessment: six packages all pending due missing event-specific evidence. Show the Task 4 profile: source and profile CSV reads plus repeated candidate filtering dominate warm local time; feasibility/ranking are smaller.

**2:05–2:40 — Before/after.** The isolated shared-mask prototype preserved the full tested responses. Two-run local medians: Wedding 5.822→4.862 s, Corporate 5.483→4.627 s, small Birthday 4.252→4.616 s. This is not yet a robust five-second guarantee or a deployed API measurement.

**2:40–3:00 — Boundaries and next steps.** Synthetic option prices and capacity are estimates. Rule-derived risk labels do not validate real-world failures; category compatibility does not establish vendor collaboration. Obtain the official proposal, event-scoped evidence and a true individual-vendor baseline, then expand performance and correctness testing before any production integration.

## Implementation status

| Component | Status |
|---|---|
| Dynamic USER-event generation, cost/budget checks, bounded search, ranking and explanations | Existing production implementation |
| Random Forest inference of rule-generated labels | Existing production implementation; real-world predictive validity unverified |
| Service-category compatibility | Existing production heuristic; named-vendor collaboration unverified |
| Operational conflict detection | Task 2 standalone SYNTHETIC_TEST proof of concept |
| Current-package conflict adapter | Task 3 read-only shadow prototype |
| Shared-mask candidate optimization | Task 4 isolated prototype; not deployed |
| Venue suitability / Digital Twin | Separate group member's component; pending interface |
| Individual-vendor baseline and SUS study | Planned, not measured |

## Next milestones before October 19

1. Obtain the official proposal and confirm the exact baseline, FR1–FR13 and response-time criterion.
2. Demonstrate fresh USER submissions and search-limit disclosure using the current application.
3. Show Task 4 measured CSV/JSON and three passing regression tests; describe the mixed small-case result.
4. Agree on event-scoped pair/schedule/resource evidence requirements with the venue team; do not activate Task 2/3 against real users yet.

## Ten likely examiner questions

1. **Are packages loaded from a saved catalog?** No. The tested dynamic path reads current option records and searches new combinations for each USER request.
2. **Why can PKG-0001 appear twice?** It is a response-local rank label; the USER event ID distinguishes requests.
3. **Are listed prices actual quotations?** No. They are synthetic USD option assumptions converted to estimated LKR.
4. **What does the risk score mean?** A higher rule-derived score is more favorable. The model predicts rule-generated labels, not verified failure events.
5. **Does compatibility prove collaboration?** No. The matrix describes service-category pairs, not named-vendor working history.
6. **What does VERIFICATION_REQUIRED mean?** Essential availability, collaboration, scheduling or venue evidence is missing; it is not a pass.
7. **What did Task 2's perfect fixture score prove?** Agreement with 12 controlled synthetic cases only; not real-world accuracy.
8. **Did the optimization change recommendations?** The three tested scenarios produced identical complete responses after normalizing only USER IDs. Broader proof is still needed.
9. **Is the five-second target met?** Not established. Some prototype runs exceeded five seconds, and the sample contains only two local pairs per scenario.
10. **Is cost-only ranking the proposal's individual-vendor baseline?** No. It reranks the same package pool. A distinct criteria-based vendor-selection baseline remains to be defined and tested.