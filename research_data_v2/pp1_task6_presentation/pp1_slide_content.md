# PP1 slide content — 12 slides

All results below are local research evidence. Synthetic option data, unverified availability/collaboration, and bounded search must remain visible in the spoken presentation. Suggested screenshots are genuine files in this package; do not portray them as fresh Task 6 API requests.

## 1. PlanoVision: Vendor Intelligence and Smart Package Recommendation Engine

- Scope: vendor options, request-time package recommendations, ranking, explainability and simulated feasibility.
- PP1 prototype; Venue Suitability/Digital Twin is another team member's component.
- Visual: title plus active-flow diagram from [architecture diagrams](./architecture_diagrams.md).
- Speaker notes: identify the scope boundary immediately; do not claim an integrated venue assessment.
- Sources: [Task 1 gap analysis](../audit_2026-10-17_01/proposal_gap_analysis.md), [implementation](./implementation_summary.md).

## 2. Research problem and motivation

- Event requirements combine services, budget, capacity, location and timing.
- A package may fit recorded constraints while availability or collaboration is still unknown.
- Visual: event brief to several vendor options.
- Speaker notes: motivate transparent decisions; avoid unsupported claims about market prevalence or user preferences.
- Sources: [Task 1 audit](../audit_2026-10-17_01/audit_summary.md), [dynamic feasibility](../../backend/engine/dynamic_feasibility.py).

## 3. Research gap

- Current source options lack verified event-specific availability, vendor-pair history and operational resources.
- Historical cost-only package reranking does not implement individual-vendor selection.
- Official proposal PDF and exact FR1–FR13 wording remain unavailable; this gap statement is provisional.
- Visual: evidence table (known / simulated / unknown).
- Speaker notes: distinguish an observed dataset limitation from an externally validated literature gap.
- Sources: [Task 1 gaps](../audit_2026-10-17_01/proposal_gap_analysis.md), [Task 3 limits](../pp1_task3_shadow_integration/limitations.md), [historical methodology](../../research_evaluation/evaluation_methodology.md).

## 4. Implemented solution and candidate contribution

- Each accepted request receives a new USER ID and assembles combinations from current option rows.
- Eligibility, bounded search, simulated feasibility, weighted ranking and explanations operate in one flow.
- Novelty claim at PP1: integrated, evidence-explicit prototype; broader scientific novelty is not established.
- Visual: [active-flow diagram](./architecture_diagrams.md).
- Speaker notes: identical input can yield the same selected options despite a new USER ID.
- Sources: [dynamic service](../../backend/engine/dynamic_package_service.py), [bounded generator](../../backend/engine/bounded_package_generator.py), [Task 5 observed results](../pp1_task5_demo_readiness/demo_readiness_report.md).

## 5. System architecture

- React/Vite wizard → FastAPI validation → current option rows → candidate selection → bounded combination search.
- Risk and category compatibility feed ranking; feasibility screens examined packages before top-K.
- Separate Task 2–4 boxes represent prototypes, not deployed modules.
- Visual: [three Mermaid diagrams](./architecture_diagrams.md).
- Speaker notes: USER and PKG labels are response-local; research report pages are historical.
- Sources: [Task 5 discovery](../pp1_task5_demo_readiness/system_discovery.md), [architecture](./architecture_explanation.md).

## 6. Dataset and preprocessing

- 18,430 vendor profiles, 57,549 synthetic service options, 30 synthetic event templates and 15 category matrix pairs.
- Vendor profiles contain review-derived fields; their exact public-source provenance still needs verification. Option prices, capacity and operational fields are synthetic simulations.
- Provenance classes: REAL_PUBLIC, DERIVED, SYNTHETIC_TEST and UNKNOWN.
- Visual: dataset count/provenance table, with synthetic fields highlighted.
- Speaker notes: do not call simulated LKR prices quotations.
- Sources: [Task 1 audit](../audit_2026-10-17_01/audit_summary.md), [dataset inventory](../audit_2026-10-17_01/dataset_inventory.csv), [historical manifest](../../research_evaluation/evaluation_summary.json).

## 7. Random Forest risk model

- Existing model uses five review-related features and predicts deterministic rule-derived Low/Medium/High labels.
- Reconstructed 3,686-row holdout: 100% accuracy and F1 against those rule labels.
- Higher package risk-favorability score means more favorable review-rule label; it is not a failure probability.
- Visual: model evaluation table with a conspicuous “rule-label agreement only” caption.
- Speaker notes: original held-out IDs were not saved; no independent real-world outcome validation.
- Sources: [model evaluation](../../research_evaluation/model_evaluation.md), [risk implementation](../../backend/engine/risk_signals.py).

## 8. Dynamic packages and ranking

- Filter by requested services, event type, synthetic location, capacity and budget.
- Select at most 12 candidates/service; explore at most 5,000 nodes; reject FAIL packages.
- Default weights: cost 0.4, risk favorability 0.4, category compatibility 0.2; show top-K and truncation.
- Visual: genuine [recommendations screenshot](./screenshots/recommendations.png).
- Speaker notes: score is a ranking index over the examined pool, not reliability or global optimality.
- Sources: [candidate selector](../../backend/engine/candidate_selection.py), [bounded generator](../../backend/engine/bounded_package_generator.py), [historical configuration](../../research_evaluation/evaluation_summary.json).

## 9. Compatibility and conflict research prototype

- Production 15-pair matrix scores service categories; it cannot establish collaboration between named vendors.
- Standalone Task 2 engine checks pair evidence, overlaps and resources, returning conflict, compatible-with-evidence or pending.
- Twelve synthetic fixture cases had 12/12 exact statuses; Task 3 shadowed six fresh packages, all pending for missing evidence.
- Visual: genuine [compatibility screen](./screenshots/compatibility_rules.png) alongside a “standalone” Task 2 box.
- Speaker notes: zero shadow conflicts means no supporting evidence, not proof of no conflicts.
- Sources: [matrix](../../vendor_compatibility_matrix.csv), [Task 2](../pp1_task2_conflict_engine/evaluation_report.md), [Task 3](../pp1_task3_shadow_integration/evaluation_report.md).

## 10. Working UI demonstration

- Wizard creates current USER request; recommendations show rank, LKR cost, score, pending checks and explanations.
- Comparison identifies real differences; feasibility groups 10 simulation passes and 8 pending checks for the captured package.
- Visual: genuine [wizard](./screenshots/create_event.png), [comparison](./screenshots/comparison.png), [feasibility](./screenshots/feasibility.png).
- Speaker notes: these captures are from a previously generated shared-browser USER request; they are not evidence of a new Task 6 API run.
- Sources: [screenshot guide](./screenshot_evidence.md), [Task 5 browser checks](../pp1_task5_demo_readiness/demo_readiness_report.md).

## 11. Evaluation results and boundaries

- Historical 35 synthetic scenarios: 34/35 successful, 202 recommendations, 20/35 searches truncated; all 202 returned packages required verification.
- Shared-pool cost-only baseline: proposed mean top-K cost LKR 77,258.317 higher across 26 comparable events.
- Task 4 isolated prototype improved two-service local medians but one single-service median regressed; five-second target unproven.
- Visual: three-row evaluation table; avoid an unsupported “better” arrow.
- Speaker notes: local runs and cost-only reranking do not measure real-world recommendation quality.
- Sources: [historical summary](../../research_evaluation/evaluation_summary.json), [Task 4](../pp1_task4_performance/performance_report.md), [evaluation summary](./evaluation_summary.md).

## 12. Progress and next work

- Production prototype and bounded dynamic flow are demonstrable; Task 2–4 remain standalone.
- Obtain verified vendor evidence, independent outcome/choice ground truth, true individual-vendor baseline and original proposal.
- Integrate venue-team evidence only through an agreed contract; then run controlled user and end-to-end performance studies.
- Visual: three columns “active / standalone / planned”.
- Speaker notes: PP1 readiness is for controlled academic rehearsal, not deployment.
- Sources: [Task 5 readiness](../pp1_task5_demo_readiness/demo_readiness_report.md), [limitations](./limitations_and_future_work.md), [venue contract](../audit_2026-10-17_01/venue_integration_contract.md).