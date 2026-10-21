# Remaining PP1 risks and mitigations

- **Local process availability:** Existing servers answered today; fresh startup was not exercised. Rehearse one clean startup before PP1, check ports 8000/5173 and `/health`, and keep terminal output visible.
- **Demo latency:** Live Wedding request took 5.346 s in this run; Task 4 did not establish a stable five-second target. Begin request early, explain the loading state and keep a backup evidence snapshot.
- **Search truncation:** Both positive scenarios reached the candidate cap. Say results rank the examined pool, not the full vendor universe.
- **Synthetic evidence:** Prices, capacities and service areas are simulation assumptions. Verify vendor quotations and availability outside the prototype.
- **Model validity:** Rule-generated risk labels and 100% rule-label classification do not validate real-world failure prediction. Higher rule-risk score means more favorable under the rule.
- **Compatibility/conflict:** Category scores are not collaboration history. Task 2 conflict engine and Task 3 adapter are not production-integrated and have no real-world conflict ground truth.
- **Venue:** External team integration contract is proposed, not live. Venue suitability remains pending.
- **Baseline/proposal:** Official proposal PDF was not found; exact FR1–FR13 remain unverified. Cost-only package reranking is not individual-vendor selection.
- **Usability/security:** No participant SUS evidence or complete accessibility audit. Research/admin pages lack production-grade authentication; use only as a local academic demo.
- **Verification gaps:** Frontend build, full risk/compatibility test file, cold-start setup, console/server logs and all mobile routes were not tested under this write-restricted task. Do not imply they passed.