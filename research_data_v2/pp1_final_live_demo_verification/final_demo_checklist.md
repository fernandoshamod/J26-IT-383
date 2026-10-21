# Final PP1 demo checklist

| Check | Status | Evidence |
|---|---|---|
| Start backend and frontend | PASS | Both commands ran; health and frontend returned HTTP 200. |
| Exact saved request over live HTTP | PASS | HTTP 200, 10,795.85 ms, `USER-3E864697E372`, three packages. [API evidence](./api_response_evidence.json). |
| React event and result flow | PASS | [Frontend verification](./frontend_verification.md). |
| Comparison, explanations and feasibility | PASS | [Frontend verification](./frontend_verification.md). |
| Edit, regenerate and no-match recovery | PASS | [Frontend verification](./frontend_verification.md). |
| Selected vendor source categories | PASS | Four category matches; offerings remain NOT_VERIFIED. [Vendor check](./selected_vendor_check.md). |
| Saved Random Forest active inference | PASS | Active call path, matching artifact hash, live predictions. [Results](./live_demo_results.md). |
| Five-second response target | FAIL | One exact-request run took 10,795.85 ms. |
| Complete search or global optimum | FAIL | `search_limit_reached`; candidate limit reached. |
| Real offerings, availability, capacity, collaboration, venue fit | NOT_VERIFIED | Eight pending checks per package; synthetic options. |
| Actual 22 October presentation environment | NOT_VERIFIED | Current run took place 18 October. |

Presentation sequence: create the saved event; show three bounded packages and the search warning; compare PKG-0001/0002; show Vendor Intelligence model classes; run PKG-0001 feasibility; edit budget and regenerate; use LKR 1 only as an explicitly separate no-match example. Say source categories are tags and option details are simulated.
