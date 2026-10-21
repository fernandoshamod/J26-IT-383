# PP1 demonstration readiness — 17 October 2026

## Verdict

**PASS WITH LIMITATIONS for a controlled academic demonstration.** The already-running backend and frontend completed the tested USER-event flow. This is not a production-readiness or real-vendor validation claim. The demonstration should disclose synthetic options, unverified availability and bounded search.

## Executed evidence

Live server: GET `/`, `/health`, `/api/locations`, `/openapi.json` and historical GET `/api/events/SIMEVT-0000` all returned HTTP 200. Philadelphia, PA was present in locations. Wedding and Corporate dynamic POSTs each returned HTTP 200 with three packages. A repeat Wedding POST returned a different USER ID and the same option-ID sequence. This demonstrates fresh request handling and deterministic selection; it does **not** mean every request receives different combinations. Source-reading code and Task 3 source-ID mapping support that packages come from current option rows, not saved package catalogs.

| Scenario | Date used | HTTP | Result | Local live request time |
|---|---|---:|---|---:|
| A Wedding, Philadelphia, 50 guests, Photography + Decoration, LKR 1,000,000 | 2026-10-22 | 200 | 3 packages, candidate/search limit disclosed | 5,345.926 ms |
| B Corporate, Philadelphia, 40 guests, Photography + Audio Visual, LKR 1,000,000 | 2026-10-23 | 200 | 3 packages, candidate/search limit disclosed | 4,377.524 ms |
| C Wedding, same services, LKR 1 | 2026-10-24 | 200 | no_budget_feasible_combinations; 0 packages | 4,870.337 ms |
| A repeated | 2026-10-22 | 200 | 3 packages, new USER ID; same option sequence | 4,779.075 ms |

Example A top package from `demo_execution_results.json`: `PKG-0001`, `SIMOPT-000111-B` + `SIMOPT-001022-S`, estimated LKR 305,535.41, remaining LKR 694,464.59, score 84.7786/100, rule-risk favorability 100/100, category compatibility 85/100, `VERIFICATION_REQUIRED` with 8 pending checks. This is a synthetic estimate, not a quotation or booking.

Zero budget, unsupported location and invalid service each returned HTTP 422. Dynamic feasibility returned HTTP 200; changing a submitted option price returned HTTP 422. The shared browser displayed the Wedding event `USER-5D45E28BC362`, three cards, two-package comparison, and feasibility with 10 simulation passes, 8 pending, 0 failed. A rerun action completed. At 390×844 on the feasibility page, its heading and rerun button were visible with no document-level horizontal overflow. Research Reports and Compatibility Rules pages were opened; the latter showed 15 matrix rows and Catering + Photography = 95/100. These are the browser observations made, not a complete accessibility audit.

## Tests, skips and integrity

Existing tests: 8 dynamic-package + 8 dynamic-feasibility + 9 final-validation + 7 research-evaluation = **32 passed, 0 failed**. `npm run lint` passed. Risk/compatibility test file was skipped because its temporary-CSV test writes outside the allowed Task 5 directory. Frontend production build was not run because its output/cache locations might breach the directory restriction. Fresh backend/frontend process startup, full console-log inspection and all browser routes were not verified.

The live-test script checked Task 1's 22 inventoried dataset/model hashes: **22/22 matched**. Seven watched production files had identical SHA-256 hashes before and after the live requests. All deliberate writes in this task were confined to this directory. No Git repository or pre-task code-hash baseline was available, so claims about earlier existing-code changes cannot be made.

## Research interpretation and next action

The historical cost-only reranking baseline is not Criteria-Based Individual Vendor Selection. Random Forest labels derive from review-feature rules; category compatibility does not prove vendor collaboration. Task 2/3/4 are standalone. Task 4's two-run local medians improved for two multi-service cases but did not establish a five-second target. Obtain the official proposal, capture the screenshot checklist, rehearse the existing servers and a backup path, and avoid claims of verified vendor availability, recommendation accuracy, conflict accuracy or SUS.
Final post-test integrity check: final_integrity.json recorded 22/22 Task 1 hashes and 7/7 watched code hashes matching the live-run baseline. Functional table: 15 PASS, 3 PARTIAL, 4 NOT_TESTED; provisional requirement-topic table: 5 PASS, 7 PARTIAL, 2 NOT_TESTED. No FAIL entries were observed in these scoped checks.

