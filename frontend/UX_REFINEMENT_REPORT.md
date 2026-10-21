# PlanoVision frontend UX refinement report

**Date:** 2026-10-17. **Scope:** Compatibility Rules and Research Reports pages only.

## Changes

- Added a shared Simple View / Research View preference for the two research pages. Research View opens the full matrix; Simple View keeps it in a disclosure.
- Added a plain-English compatibility introduction, an interactive unordered service-pair explorer, a score bar for recorded pairs, an explicit unknown state for unlisted pairs, and clear limits on category-level rules. The complete 15-row matrix remains visible in Advanced Research Details.
- Replaced the seven technical report card titles with plain-English headings. Each card retains its original report name and filename, a source-grounded summary, an expandable Read Summary action, and a View Original Report link.
- Added responsive layouts, labeled form controls, live score updates, native disclosure and keyboard-focus styling. The navy, violet and white palette remains.
- Report results are identified as historical Task 5 / Task 6 outputs. They do not update with live USER requests.

## Source and link verification

- [The source matrix](../vendor_compatibility_matrix.csv) and [bundled matrix copy](./src/data/compatibility_rules.json) match in row order and all 15 scores. The source matrix SHA-256 remains `de72d8483871813f1c18113b66a8882465e98f4ba51b31388fb7751edf741aba`.
- Browser interaction displayed Catering + Photography **95/100**, Catering + Decoration **90/100**, and Catering + Equipment Rental **Unknown**, without a fabricated bar or value.
- Research View displayed all 15 source rows. All seven View Original Report URLs returned HTTP **200** with the expected Markdown or CSV content type and file heading. Every bundled file's SHA-256 matched its source in [research_evaluation](../research_evaluation/) or [final_validation](../final_validation/).
- At a 375 px browser viewport, both pages had no document-level horizontal overflow; the report grid and pair selectors used one column.

## Verification results

| Check | Result |
|---|---|
| Frontend `npm run lint` | Passed |
| Frontend `npm run build` | Passed; Vite built 28 modules |
| Compatibility and research backend regressions | 18 tests passed, 0 failures |
| Browser report link checks | 7 of 7 HTTP 200 |
| Source matrix and report copies | Matched originals |

## Files changed

- [App.jsx](./src/App.jsx): shared view preference.
- [AdminPages.jsx](./src/pages/AdminPages.jsx): page content, explorer and report cards.
- [App.css](./src/App.css): scoped page styling.
- This report.

## Limitations

Compatibility scores are category heuristics, not evidence of vendor collaboration. Unknown pairs stay unknown. Historical research reports and synthetic experiment results do not establish current vendor availability, quotations, real-world outcomes or production performance. The browser checks covered the specified interactions and a narrow mobile viewport; they were not a full assistive-technology audit.


## Recommendation and comparison redesign — 2026-10-17

### Before and after

- Recommendations previously placed a long vendor table, technical evidence and repeated explanation text in each open card. The redesigned page initially shows three compact, source-backed cards with rank, actual package ID, covered services, LKR cost, remaining budget, utilization, score, review-derived risk favorability, category compatibility, feasibility status and pending-check count. The full original explanation, scoring factors, vendor options, trade-offs and checks remain under **View Research Details**. A Show More Packages control reveals the rest of the current response.
- Comparison previously repeated explanation lists in each column and relied on selections made elsewhere. It now permits choosing two or three current-response packages directly, compares their actual values and vendors, and gives a deterministic **What’s Different?** summary. The complete technical evidence remains expandable in each column.
- Both pages explain that rank describes a bounded search, review-derived risk is not a real-world failure prediction, compatibility is a category rule rather than vendor collaboration, and synthetic prices are estimates.

### Comparison behavior and accessibility

- Selection is shared between both pages and cleared when a new USER event is submitted. Unselected checkboxes are disabled at three selections. Fewer than two selected or available packages show an explanatory empty state.
- Equal known risk or compatibility values are reported as identical. Missing scores stay unknown. Cost differences, vendor-ID differences, pending-check counts and feasibility observations are derived from the compared response records.
- Metric help uses keyboard-focusable native disclosures. Research details use native disclosure controls. Buttons and checkboxes have labels and visible focus styles. At a 375 px viewport, both pages used a single card column with no document-level horizontal overflow; at 1440 px, three comparison columns had CSS sticky headings.

### Tests and browser evidence

| Check | Result |
|---|---|
| Frontend lint | Passed |
| Frontend production build | Passed; Vite built 29 modules |
| Comparison-summary unit tests | 4 passed, 0 failed |
| Relevant backend dynamic generation, feasibility and risk/compatibility tests | 27 passed, 0 failed |
| Fresh browser USER event | Wedding, Philadelphia, PA, Photography + Decoration; 10 packages returned, 3 initially visible |
| API cross-check | Separate HTTP 200 dynamic request produced a distinct USER ID and the same first-three costs, remaining budgets, ranking scores, risk values, compatibility scores and pending counts |
| Browser interactions | Selected 2 then 3 packages, enforced the three-package cap, preserved selections on return navigation, expanded research details with mouse and Enter key, and showed all 10 via Show More Packages |

For the checked event, the first three displayed estimated costs were LKR 305,535.41, LKR 328,001.78 and LKR 244,874.21. The corresponding unrounded API ranking scores were 84.7786, 83.8799 and 79.205; the cards display one decimal. All three had category compatibility 85/100 and eight pending external checks. These are synthetic estimates for one local test request, not a representative study result.

### Changed files for this stage

- [App.jsx](./src/App.jsx): passes the shared comparison action to the comparison page.
- [PackageViews.jsx](./src/pages/PackageViews.jsx): redesigned recommendation and comparison views.
- [App.css](./src/App.css): responsive cards, comparison layout, sticky headings and focus styling.
- [comparisonInsights.js](./src/data/comparisonInsights.js): pure deterministic comparison observations.
- [comparisonInsights.test.js](./src/data/comparisonInsights.test.js): focused comparison tests.
- This report.

### Remaining limitations

No actual vendor availability, collaboration, prices or outcome labels were verified. Rankings are bounded and can be truncated. The view state is held in the current browser session and does not survive a full reload. Browser checks covered representative interactions and responsive width, not a full assistive-technology audit or deployed performance test.


## Feasibility verification dashboard — 2026-10-17

### Implementation and hierarchy

The Feasibility page now leads with the current USER event, package ID, required services, estimated LKR cost, remaining budget, backend feasibility status and a rerun action. A plain-English outcome follows, then exact passed/pending/failed counts and a segmented bar whose lengths represent **recorded check counts only**. No real-world readiness percentage is calculated.

"What Still Needs Confirmation?" groups only present pending checks by backend `code` prefix: `availability:`, `capacity:`, `scheduling:`, `vendor_collaboration:`, and `venue_suitability`. Any other pending code appears under "Other recorded checks." "Checks Already Satisfied" groups only actual passed records for service coverage, unique vendors, duration, event type, simulated location, option pricing, simulated capacity and budget. A category absent from the response is not shown. The primary cards use service names from check codes and current package breakdown; raw vendor IDs remain in Research Details.

Research Details includes every original passed, pending and failed check with its exact code, status, message and evidence origin. Missing lists display Unknown instead of zero. Zero recorded checks show no chart. The existing dynamic `/api/feasibility/validate-dynamic` request, USER-event selection, canonical price checks and production feasibility decisions were unchanged.

### Browser verification

A current Wedding USER event in Philadelphia, PA with Photography and Decoration was checked through the dedicated API. The rerun returned **VERIFICATION_REQUIRED** with **10 passed, 8 pending, 0 failed** checks, estimated cost **LKR 305,535.41**, event budget **LKR 1,000,000.00**, and remaining budget **LKR 694,464.59**. The five pending cards represented 2 availability, 2 capacity, 2 scheduling, 1 collaboration and 1 venue check. Research Details exposed all **18** original messages and statuses: 10 passed, 8 pending, 0 failed. No check was duplicated or promoted from pending to passed in the view.

At 1440 px, the pending cards used two columns; at a 375 px viewport they used one column with no document-level horizontal overflow, including with raw evidence open. Research Details closed with the Enter key when focused. No screenshot was saved; these are direct browser interaction observations.

### Verification results

| Check | Result |
|---|---|
| Frontend lint | Passed |
| Frontend production build | Passed; Vite built 31 modules |
| Feasibility view-model tests | 3 passed, 0 failed |
| Relevant backend feasibility, dynamic generation and final-validation tests | 25 passed, 0 failed |
| Browser USER feasibility rerun | Succeeded; status and values above displayed |
| Raw evidence completeness | 18 displayed messages for 18 recorded checks |

### Files changed in this stage

- [PackageViews.jsx](./src/pages/PackageViews.jsx): current USER package header and dashboard integration.
- [FeasibilityDashboard.jsx](./src/pages/FeasibilityDashboard.jsx): outcome, count bar, grouped cards and original evidence disclosures.
- [feasibilityViewModel.js](./src/data/feasibilityViewModel.js): code-based grouping without changing statuses or records.
- [feasibilityViewModel.test.js](./src/data/feasibilityViewModel.test.js): count, grouping, failure, missing and unknown-code cases.
- [App.css](./src/App.css): dashboard layout, colors, focus styling and responsive behavior.
- This report.

### Remaining limitations

The dashboard presents simulation evidence. Vendor availability, capacity, collaboration, venue suitability, travel and schedules were pending for the checked event and remain externally unverified. A FAIL response is covered by backend tests and frontend view-model tests, but no FAIL package was available through the recommendation UI because the engine excludes failed packages. A full assistive-technology audit and deployed browser-performance test were not performed.

