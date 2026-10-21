# Known limitations and unsupported claims

## Data and external validity

- Current [service options](../hybrid_simulation_v1/synthetic_service_options.csv), locations, prices, capacity and event support are **synthetic simulation data**. Estimated LKR prices use a fixed synthetic USD-to-LKR conversion of 330.777 in the saved evaluation. They are not current vendor quotes.
- No new USER event has confirmed availability, venue suitability, scheduling or vendor collaboration evidence. VERIFICATION_REQUIRED is the common status. PASS_IN_SIMULATION is only a simulation status, never real-world confirmation.
- [Service compatibility rules](../backend/engine/service_compatibility.py) describe category pairs, not observed cooperation among named vendors. For packages with the same required service categories, compatibility may be constant and offer no ranking discrimination. Missing pairs are unknown.
- The [risk model path](../backend/engine/risk_signals.py) uses an existing Random Forest trained on rule-derived labels. The notebook maps Low to 100, Medium to 60 and High to 20. Its reconstructed holdout accuracy of 100% reflects agreement with those rules, not prediction of independently verified real-world failures. Rule leakage and circular evaluation limit external validity. Original held-out row identities were not separately persisted.
- Underlying risk/profile joins have missing matches documented by prior research. Missing risk must remain unknown; it is not a safety signal.

## Recommendation and evaluation limits

- [Candidate selection](../backend/engine/candidate_selection.py) and [bounded search](../backend/engine/bounded_package_generator.py) use finite limits (default 12 options per service and 5,000 search nodes). A better feasible combination may not be examined. The saved experiment truncated **20 of 35** scenarios; quality claims must include search metadata.
- The cost-only baseline and proposed system rerank a shared examined pool, isolating ranking differences within that pool. This cannot establish superiority over unexamined combinations. Measuring the proposed system solely by its own weighted score would be circular.
- All **202** returned packages in saved Task 5 scenarios were VERIFICATION_REQUIRED. Priority for PASS_IN_SIMULATION is covered by controlled tests, not observed for a new real event.
- The 35 scenarios and timings are a synthetic local evaluation, not a representative sample of future users or deployed performance. No field outcome validation, fairness study, concurrency/load run or real vendor study was performed.
- Returned-package budget/coverage rates use returned packages as denominator. They do not measure all possible combinations; zero-result scenarios must remain distinct from successes.

## Security, interface and operations

- The [USER feasibility API](../backend/api/feasibility.py) resolves submitted option IDs against current source rows and rejects changed material fields, preventing invented cheap options from changing estimates. It is stateless: a caller can submit a valid but different USER event payload with a plausible ID. It does not cryptographically bind that payload to an earlier generated event. It is analytical validation, not attestation of original request identity.
- The local TestClient suite is not a penetration test. Authentication, authorization, rate limiting, persistence and concurrency were not assessed for deployment readiness.
- The [React UI](../frontend/src/App.jsx) source and API integration were inspected and its production build passed, but a real browser walkthrough was **not verified**. Follow the [manual demo checklist](./demo_walkthrough.md) and record actual observations before presenting them as tested.
- The legacy SIMEVT route uses sample-event evidence and is separate from dynamic USER generation. Its evidence must never be transferred to a new USER event.

**Readiness boundary:** Suitable for a supervised academic demonstration of a synthetic, request-time recommendation method. It is not production-ready, and no validated real-world vendor-outcome claim is supported.
