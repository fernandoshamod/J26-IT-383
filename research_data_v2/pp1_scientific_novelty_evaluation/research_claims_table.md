# Research claims: supported and not supported

All measured cases here use synthetic service options. “Supported” means supported **within the stated experiment**, not demonstrated in the real event market. Source rows: [ranking](./baseline_comparison.csv), [search](./search_quality_comparison.csv), [risk](./risk_model_baseline.json), [conflicts](./conflict_comparison.csv).

| Claim | Status | Evidence | Boundary |
|---|---|---|---|
| Both ranking methods used identical requirements, constraints and examined package pools. | SUPPORTED | One generator capture per event; both sort that same validated pool; proposed rerank was asserted to reproduce production Top-K. | Pool itself was selected with production risk-aware candidate rule. |
| Proposed top result improves review-derived risk favorability over cheapest. | PARTIALLY SUPPORTED | One of eight events gained 20 rule-score points; mean paired gain 2.5, median 0. | Not a reliability or user-utility gain; 7/8 top choices identical. |
| Proposed ranking is cheaper or more cost effective than cheapest. | NOT SUPPORTED | Mean paired cost difference +LKR 522.63; Belleville +LKR 4,181.03; all other top choices identical. | Cheapest baseline minimizes estimated cost in common pool by design. |
| Proposed ranking improves category compatibility for these events. | NOT SUPPORTED | Both methods scored 85/100 on every event. | Category-only score is constant for fixed Photography+Decoration services. |
| Top packages satisfy required coverage and estimated budget. | SUPPORTED BY CONSTRUCTION | 8/8 events for both methods. | Constraints enforced by the common generator; not independent efficacy. |
| Bounded DFS found a globally best package in all cases. | SUPPORTED ONLY FOR THESE EIGHT REFERENCES | Exhaustive reference top option IDs matched bounded in 8/8; measured regret 0. | Five cases hit candidate cap; three feasible combinations missed. No general optimality claim. |
| Candidate truncation can omit feasible packages. | SUPPORTED | 3 of 173 exhaustive feasible combinations omitted, all in West Chester PA. | Small two-service scenario set. |
| Random Forest is more accurate than the source rule for current target. | NOT SUPPORTED | Model and rules-only both accuracy/macro-F1 1.000 on 3,686 reconstructed holdout rows. | Rule-generated target; no independent outcomes. |
| Category compatibility alone establishes vendor-pair operational status. | NOT SUPPORTED | Same category-score groups contained multiple fixture statuses. | Synthetic cases, not real collaboration history. |
| Standalone conflict engine preserves compatible/conflict/unknown on supplied fixtures. | SUPPORTED IN SYNTHETIC TESTS | 12/12 authored fixture statuses matched; 2 compatible, 6 conflict, 4 verification required. | This is fixture consistency, not external validity. |
| PlanoVision predicts real vendor reliability or booking feasibility. | NOT SUPPORTED | No observed failure labels, live calendars, verified prices, capacity or collaboration in this evaluation. | Requires independent field evidence and validation. |
| Proposed method statistically outperforms baseline. | NOT SUPPORTED | Eight purposive events; one changed top choice; descriptive bootstrap only. | No valid population inference or user-outcome test. |
