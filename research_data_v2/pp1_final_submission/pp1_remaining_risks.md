# PP1 remaining risks and disclosure wording

| Risk | Evidence | PP1 action |
|---|---|---|
| Rule-derived target can be mistaken for observed failures | [Model status](../pp1_final_model_verification/model_status.md) and [metrics](../pp1_final_model_verification/evaluation_metrics.csv) | State “100% on reconstructed review-rule labels”; mark real failure accuracy **NOT_VERIFIED**. |
| Historical held-out membership is not independently preserved | [Holdout details](../pp1_final_model_verification/holdout_details.json) | Call the split reconstructed from notebook recipe, not an independently sealed test set. |
| Vendor-service category mismatches are visible | [Vendor capture](../pp1_final_model_verification/live_vendor_predictions.png) and [integration trace](../pp1_final_model_verification/model_integration_trace.md) | Do not endorse questionable rows; manually verify selected demo vendors before the talk. |
| Pricing, option capacities, service areas and event support are simulated | [Yelp lineage audit](../yelp_lineage_gap_audit/audit_summary.md) | Label all LKR prices as estimated simulation, not quotations. |
| Availability, scheduling, collaboration, venue and non-Catering capacity are unverified | [Focused feasibility response](./pp1_demo_inputs_and_outputs.json) and [compatibility audit](../yelp_lineage_gap_audit/compatibility_evidence_audit.md) | Present `VERIFICATION_REQUIRED` and 8 pending checks as an honest result. |
| Search is bounded and candidate-limited | [Focused response](./pp1_demo_inputs_and_outputs.json) | Say highest ranked *examined* packages; do not assert global optimality. |
| Current check used in-process FastAPI, not the presentation browser/server | [Focused response](./pp1_demo_inputs_and_outputs.json) and [earlier UI screenshots](../pp1_task6_presentation/screenshot_evidence.md) | Run a presentation-day server, UI, submission, comparison and feasibility smoke check. |
| Existing live-model screenshot is narrow and tiled | [Existing capture](../pp1_final_model_verification/live_vendor_predictions.png) | Use the live table or clear JSON/sample evidence; do not enlarge the capture as the primary model visual. |
| Yelp academic-use and public-presentation terms may apply | [Source integrity report](../yelp_lineage_gap_audit/source_integrity_report.md) | Check actual agreement and institutional guidance before showing public vendor names; legal status **NOT_VERIFIED**. |
| Model dashboard uses saved metrics | [Integration trace](../pp1_final_model_verification/model_integration_trace.md) | Label it an evaluation snapshot, not live inference. |

**No verified technical blocker** prevents a controlled PP1 model demo. Presentation-day startup, exact vendor selection, readable display, and appropriate use of source names remain open operational checks. No real-world booking readiness or vendor failure validity is claimed.
