# Research gap and actual PlanoVision contribution

## Research gap, stated with evidence limits

The reviewed [commercial documentation](./existing_systems_comparison.md) establishes discovery, reviews, budget information, personalization and booking workflows. The reviewed [papers](./academic_literature_review.md) establish multi-criterion supplier selection, multiple sourcing, package recommendation, explanation and operational scheduling as prior art. **Open question for this project:** how to produce an inspectable, event-specific multi-vendor shortlist that enforces stated constraints, exposes tradeoffs and search limits, and distinguishes simulated evidence from unverified operational facts. Public commercial pages do not provide enough algorithmic detail to compare internal package generation or conflict checks; “not publicly documented” is not “absent.”

This is a **system-integration and evaluation gap**, not a claim that no one has ever proposed these component methods. A further evidence gap is the absence of independently verified event-vendor outcomes, current availability and Sri Lankan market coverage in the prototype. That gap remains **unresolved** by the current implementation.

## Implemented now

| Component | Evidence in current source | Claim boundary |
|---|---|---|
| Review-derived Random Forest classification | [risk_signals.py](../../backend/engine/risk_signals.py) verifies artifact SHA-256, checks five feature names and classes, and calls model.predict for complete profiles. [Novelty 1 audit](../pp1_novelty1_verification/novelty1_verification_report.md) records evaluation against rule labels. | The target is rule-generated risk level. Perfect agreement with that rule does not establish actual vendor reliability. The ranking uses the separate rule-derived numeric favorability after checking model-rule agreement, not a calibrated failure probability. |
| Event-dependent filtering | [candidate_selection.py](../../backend/engine/candidate_selection.py) matches category, simulated city/state, supported event type and Catering guest capacity. [Dynamic service](../../backend/engine/dynamic_package_service.py) joins request and option records. | Service areas, prices, capacity and offerings are synthetic; live calendars are not filtered. |
| Bounded multi-vendor packages | [bounded_package_generator.py](../../backend/engine/bounded_package_generator.py) checks priceability, distinct vendor IDs, budget and feasibility in a bounded DFS; defaults are 12 candidates/service and 5,000 nodes. | Top K ranks examined combinations, not an exhaustive global optimum. |
| Multi-criterion ranking | Same [generator](../../backend/engine/bounded_package_generator.py) combines cost efficiency, review-rule risk favorability, and [category matrix](../../backend/engine/service_compatibility.py), default weights 0.4/0.4/0.2; missing components are omitted and weights renormalized. | Fixed research weights have no demonstrated user-preference calibration. Category scores are not vendor-pair collaboration. |
| Package-level explanation | [package_explanations.py](../../backend/engine/package_explanations.py) reports coverage, cost, effective weights, risk/category provenance, unknown factors and verification steps. | Deterministic summary of recorded factors; no human-subject assessment of comprehension or trust. |
| No-match diagnostics | [coverage_diagnostics.py](../../backend/engine/coverage_diagnostics.py) reports observed location, category, event-type, capacity, pricing, budget and search-limit causes, with suggested locations derived from source rows. | Explanations are tied to synthetic options and cannot establish real-world absence of vendors. |
| Operational conflict research demo | [isolated report](../pp1_vendor_conflict_demo/implementation_verification_report.md), [standalone engine](../pp1_task2_conflict_engine/conflict_engine.py), and [frontend page](../../frontend/src/pages/VendorConflictResearch.jsx) show three synthetic fixtures. | Separate static research snapshot. It is not integrated into live recommendation ranking and does not verify actual availability, equipment, collaboration or venue suitability. |

## Data and validation limits

- Yelp-derived profiles contain historical listing/review evidence, while the event service options and most operating assumptions are **synthetic**. See [Novelty 1 verification](../pp1_novelty1_verification/novelty1_verification_report.md).
- Reported 100% model holdout accuracy is against **rule-derived labels** on a reconstructed split, not independently labeled vendor failures. Saved [evaluation methodology](../../research_evaluation/evaluation_methodology.md) explains the synthetic package study and its cost-only comparison on an already selected candidate pool.
- The [final readiness response](../pp1_final_readiness/api_response_raw.json) showed three Philadelphia packages but candidate truncation and VERIFICATION_REQUIRED on all three. This is existing evidence, not a new demo test.
- The Sri Lankan OSM pilot is isolated and lacks review, price and availability fields needed for equivalent operation. Do not imply the US-derived Philadelphia prototype is a verified Sri Lankan market system.

## Proposed future work, not PP1 implementation

Collect consented/current Sri Lankan vendor offerings, prices, capacities, service areas, calendars and operational constraints; obtain independent outcome or expert labels; validate pair/venue evidence; perform geographic and temporal external validation; compare against pre-registered baselines and ablations; conduct user studies of explanation utility. None of these are delivered by the current live package API.
