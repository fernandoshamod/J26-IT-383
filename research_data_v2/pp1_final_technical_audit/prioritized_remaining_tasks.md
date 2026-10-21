# Prioritized remaining work before PP1

Priority means **impact on the individual vendor intelligence/package recommendation component's PP1 demonstration**, not a commitment to edit production in this audit.

## P0 — Blocks an honest live PP1 demonstration if left undone

1. **Obtain and read the official proposal before asserting FR1–FR13 compliance.** Its exact text was absent from the project and prior audits. [requirements_FR1_FR13.csv](./requirements_FR1_FR13.csv) is a **provisional topic matrix**, not formal compliance. If the presentation demands signed FR-by-FR signoff, this is a documentation blocker. The demo can still show verified behavior without that claim.
2. **Run presentation-day backend/UI smoke and record a fresh request.** Start the current system, enter a future dated [chosen event](../pp1_final_submission/pp1_demo_checklist.md), confirm package generation, model classes, compare and feasibility. Earlier [in-process evidence](../pp1_final_submission/pp1_demo_inputs_and_outputs.json) does not guarantee the presentation machine works.
3. **Keep the claim boundary visible on model and feasibility slides.** State that 100% is reconstructed **review-rule label** accuracy, not real vendor failure prediction; that 10 passed checks are simulation passes; and that 8 pending checks remain. [Model limitations](../pp1_final_model_verification/limitations.md), [feasibility result](../pp1_final_submission/pp1_demo_inputs_and_outputs.json). No code change is required to make the claim accurate.

## P1 — Important correctness and research-integrity issues

4. **Review selected vendor-service rows before showing named examples.** [vendor_category_issues.md](./vendor_category_issues.md) found broad category mappings, including Trader Joe's→Decoration and matt-hair→Photography. The source tags exist, but event services are not verified. Use clearer examples or disclose uncertainty; do not silently present simulated options as genuine offers.
5. **Describe model influence precisely.** [model_to_ranking_trace.md](./model_to_ranking_trace.md): model class gates a stored numeric rule score, but all 18,430 profiles agree with stored labels, so no distinct present-day rank effect was observed. Do not call the rank a directly learned failure-risk score.
6. **Treat capacity and location as simulation boundaries.** Catering has randomized tier limits; other service capacity is unknown; location is exact simulated city/state. The 500-guest Bensalem no-package case is a synthetic budget result, while Belle Chasse lacks Entertainment. [package_generation_status.md](./package_generation_status.md).
7. **Resolve operational compatibility requirements before promising conflict prevention.** The standalone engine is not active, and USER events lack verified pair, crew, availability and schedule evidence. [compatibility_integration_status.md](./compatibility_integration_status.md). If the official proposal requires live conflict detection at PP1, reassess this as P0.
8. **Check public-source presentation terms and institutional guidance** before showing Yelp-derived names or screenshots externally. [Agreement summary](../yelp_lineage_gap_audit/source_integrity_report.md). This audit gives no legal conclusion.

## P2 — After PP1 unless the official proposal changes priority

9. Gather independent quotations, capacities, availability, vendor-pair outcomes and real service confirmations with provenance; then validate category assignments. Do not infer them from synthetic options. [V2 proposal](../yelp_lineage_gap_audit/dataset_v2_schema_proposal.md).
10. Specify and test an event-scoped contract before integrating the standalone conflict engine. Keep unknowns pending and venue-team evidence separate. [Shadow integration proposal](../pp1_task3_shadow_integration/integration_proposal.md).
11. Add persistent event editing/history if required beyond the current browser session. Current FR13 flow regenerates a new USER request and loses state on reload. [FR13 verification](../pp1_fr13_no_match_recovery/fr13_verification.md).
12. Establish independent user-choice/recommendation labels, a true individual-vendor baseline, and repeated end-to-end performance/usability studies. Existing historical cost-only reranking is not that baseline. [Prior proposal gap](../audit_2026-10-17_01/proposal_gap_analysis.md).

**Implementation order after approval:** first confirm proposal scope, then review demo vendors and claim wording, then choose a separate data/evidence workstream for real service capability; only after a tested evidence contract should conflict integration or new evaluation claims proceed. No fixes were implemented here.
