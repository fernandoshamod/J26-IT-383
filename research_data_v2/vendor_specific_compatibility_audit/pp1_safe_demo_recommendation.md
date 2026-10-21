# PP1-safe demo recommendation

Show two separate concepts:

| Display | Meaning | Safe wording |
|---|---|---|
| Category compatibility score | Static mean of predefined service-category rules; one value for requested categories. | “Category-level heuristic used in ranking.” |
| Operational conflict status | Named vendor-pair and time/resource check with explicit evidence scope. | “Conflict in synthetic fixture”, “No conflict within supplied synthetic checks”, or “Verification required.” |

Keep the working live [Recommendations/Feasibility UI](../../frontend/src/pages/PackageViews.jsx) and verified event unchanged. Explain that two vendor pairs serving Photography + Decoration receive the **same category score**. Separate vendor-specific synthetic evidence could yield different scoped operational statuses. The current USER request has no such evidence, so its operational pair status is `VERIFICATION_REQUIRED`.

If time permits, demonstrate the already isolated [Task 2 fixtures](../pp1_task2_conflict_engine/README.md) beside the live app, clearly labeled **synthetic research demonstration**. Show one conflict and one pending case, with category score as separate context. Describe the 19 passing tests and 12/12 fixture result as checks of prototype logic only. Do not call these live availability, actual vendor cooperation, verified inventory, or real-world predictive accuracy.

**PP1 boundary:** Current data is insufficient to integrate vendor-specific conflict outcomes into the working demo. Real-world claims require event-matched attributable availability, schedules, resource and pair evidence plus independent review. Present the distinction clearly now; consider production changes only after approval and real evidence.
