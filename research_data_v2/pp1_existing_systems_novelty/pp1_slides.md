# PP1 presentation slides — paste-ready content

These are text slide drafts. Source links are embedded; access date for web sources is 2026-10-19. Speaker notes and the full evidence trail are in [the system review](./existing_systems_comparison.md), [literature review](./academic_literature_review.md), and [claim matrix](./claim_evidence_matrix.md).

## Slide 1 — Existing systems

**Title:** Vendor discovery exists; algorithmic evidence is less visible publicly

| Platform | Publicly documented strengths |
|---|---|
| The Knot | Multi-category vendor search, reviews, pricing, availability details, personalized matching and planning tools. |
| WeddingWire | Vendor search by location/preferences, review comparison, pricing and availability information. |
| Zola | Vendor marketplace, personalized style/budget matches, filters and inquiries. |
| Eventective | Venue/vendor discovery, event inquiries, pricing requests, contracts and payments. |

**Takeaway:** PlanoVision does not claim to invent vendor recommendation. Public provider material does not specify comparable auditable package-search and evidence handling; internal capability remains unknown. Sources: [The Knot](https://helpcenter.theknot.com/hc/en-us/articles/46635549990548-How-do-I-find-local-wedding-vendors), [WeddingWire](https://www.weddingwire.com/vendor-reviews), [Zola](https://www.zola.com/wedding-vendors), [Eventective](https://support.eventective.com/hc/en-us/articles/30674595955220-How-do-I-use-Eventective-for-my-event).

## Slide 2 — Research gap

**Title:** From vendor lists to defensible event-specific packages

- Supplier-selection research already covers multiple criteria and multiple sources; package-recommendation research covers combinations; explainable recommendation and constrained scheduling are established fields.
- Open integration problem for this project: enforce event requirements across **multiple distinct vendors**, expose cost/risk/category tradeoffs and bounded-search limits, and keep unverified operational facts **UNKNOWN**.
- Data gap: current event-service options and prices are synthetic; no independently verified booking outcomes, live availability or complete Sri Lankan market records.

**Literature anchors:** [Ho et al., 2010](https://doi.org/10.1016/j.ejor.2009.05.009), [Ghodsypour & O’Brien, 2001](https://doi.org/10.1016/S0925-5273(01)00093-7), [van Schaik et al., 2019](https://doi.org/10.3233/IDT-190140), [Zhang & Chen, 2020](https://doi.org/10.1561/1500000066), [Hartmann & Briskorn, 2010](https://doi.org/10.1016/j.ejor.2009.11.005).

## Slide 3 — Novelty contribution

**Title:** An auditable event-vendor package workflow

1. Saved Random Forest classifies **review-rule labels** using five review features; it does not predict observed booking failure.
2. Filter synthetic options by service, location, event type and recorded Catering capacity; search distinct-vendor budget-feasible combinations with bounded DFS.
3. Rank examined packages by declared cost efficiency, review-rule favorability and category compatibility; expose reasons, unknowns and no-match diagnostics.
4. Show operational conflict logic in a **separate synthetic fixture demo**, with category score kept distinct from pair-level status.

**Scope label:** Implemented research prototype; vendor quotations, availability and collaboration remain unverified. Source evidence: [Novelty 1 audit](../pp1_novelty1_verification/novelty1_verification_report.md), [conflict demo report](../pp1_vendor_conflict_demo/implementation_verification_report.md).

## Slide 4 — Scientific evaluation

**Title:** What is measured, and what still needs validation

| Already measured | Interpretation | Needed next |
|---|---|---|
| Saved model reconstructed holdout accuracy and macro F1 = 1.0 against rule-derived labels. | Rule agreement only. | Independently labeled vendor outcomes, temporal/geographic external validation and calibration. |
| Saved 35-scenario synthetic package study: 202 returned packages; 26/35 events yielded packages; 202/202 were VERIFICATION_REQUIRED; 57.14% search truncation. | Constraint/system behavior on synthetic scenarios, not user satisfaction or booking feasibility. | Tractable exhaustive-search quality baseline, untruncated/greedy/cost-only ablations and robust runtime distributions. |
| Separate conflict fixture tests. | Logic consistency for supplied simulated cases. | Expert-labeled event-specific operational cases and unknown-handling review. |

**No claim:** real-world vendor reliability, global optimum, booking feasibility or superiority to commercial services. Source: [evaluation methodology](../../research_evaluation/evaluation_methodology.md) and [Novelty 1 audit](../pp1_novelty1_verification/novelty1_verification_report.md).
