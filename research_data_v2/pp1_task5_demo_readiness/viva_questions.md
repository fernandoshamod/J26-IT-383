# Ten likely examiner questions — concise evidence-based answers

1. **Are recommendations pre-generated packages?** No. The dynamic route reads current option records and searches new combinations for each USER request. A repeated request may legitimately return the same option set under deterministic ranking.
2. **Why did the same PKG number appear for another event?** PKG numbers are response-local rank labels. The USER event ID identifies the request.
3. **Are vendor prices and availability real?** Option prices and service areas are synthetic assumptions; availability is unverified. We make no booking or quotation claim.
4. **What does the risk score mean?** Higher is more favorable under a review-feature rule. The Random Forest predicts rule-derived classes, not independently observed vendor failure.
5. **What does compatibility measure?** A static service-category pair heuristic. It does not establish that two named vendors have collaborated.
6. **Why is feasibility pending after a package passes budget checks?** Budget and some option constraints pass in the simulation; event-specific availability, scheduling, collaboration and venue evidence are missing.
7. **What did the live tests verify?** Two positive event requests returned three packages each; low budget returned zero; invalid inputs returned 422; dynamic feasibility accepted canonical options and rejected a changed price.
8. **Is the five-second response target achieved?** Not established. This audit measured 5.346 s for one live Wedding request, and Task 4 had mixed local timings across only two pairs per scenario.
9. **What baseline did the research evaluation use?** Cost-only reranking of the same examined package pool. That is not the proposed Criteria-Based Individual Vendor Selection baseline.
10. **Is the conflict engine already recommending safer vendor teams?** No. Task 2 is a synthetic standalone proof of concept, Task 3 is a read-only shadow adapter, and neither is active in production ranking. Real pair/resource evidence is still needed.