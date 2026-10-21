# Current compatibility and ranking

Audit date: 2026-10-19. Source inspection only; no production edits.

[The matrix](../../vendor_compatibility_matrix.csv) contains 15 predefined rows: ten cross-category pairs among Catering, Photography, Decoration, Entertainment, Audio Visual, and five same-category pairs. It has no vendor IDs, observations, dates or citations. [The loader](../../backend/engine/service_compatibility.py) identifies it as a `static_service_category_heuristic` and sets `is_vendor_collaboration_evidence=False`. The exact derivation of its scores is **UNKNOWN** from inspected source; the values are DERIVED heuristics, not measured pair evidence. Event Planning and Equipment Rental are absent from the matrix. Same-category rows do not contribute to ordinary requests selecting each service once.

[Dynamic generation](../../backend/engine/dynamic_package_service.py) computes one score from requested service names before search. [Ranking](../../backend/engine/bounded_package_generator.py) weights cost 0.4, rule-risk favorability 0.4, category compatibility 0.2. If any requested category pair is missing, the total category score is null; the component is omitted and available weights renormalized. Compatibility is not a candidate or feasibility filter and removes no candidates.

Every package for the same requested services gets the same category score. This constant cannot distinguish or reorder vendor pairs within that request, although cost and risk can differ. It can affect the displayed absolute score. The [standalone engine](../pp1_task2_conflict_engine/conflict_engine.py) is not called by the live API. [USER feasibility](../../backend/engine/dynamic_feasibility.py) leaves availability, scheduling, collaboration and venue pending; `is_real_world_feasible=False`.

**Answer:** The current live system cannot distinguish two vendor pairs in the same service-category pair on operational compatibility. The isolated engine could distinguish them if separate valid event-specific evidence were supplied; current USER-event data does not supply it.
