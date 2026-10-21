# Research and evaluation validity

## Four distinct outcomes

| Claim | Available evidence | Correct conclusion |
|---|---|---|
| Random Forest classification accuracy | [Reconstructed holdout](../pp1_final_model_verification/holdout_details.json), [metrics](../pp1_final_model_verification/evaluation_metrics.csv), [classification report](../pp1_final_model_verification/classification_report.csv) and [confusion matrix](../pp1_final_model_verification/confusion_matrix.png): 3,686 rows, 100% against review-derived rule labels. | Reproducible for the documented reconstructed split. It measures rule-label replication, not vendor failure. Original immutable held-out IDs were not saved separately. |
| Package recommendation accuracy | Proposal p. 38 demands at least 80% against predetermined correct results. | **NOT_VERIFIED**. Neither RF classification accuracy nor simulated package feasibility supplies a package gold standard. |
| Synthetic simulation results | [Synthetic conflict evaluation](../pp1_task2_conflict_engine/evaluation_report.md): 12/12 hand-authored cases; [shadow evaluation](../pp1_task3_shadow_integration/evaluation_report.md): 6/6 packages pending; [demo package feasibility](../pp1_final_submission/pp1_demo_inputs_and_outputs.json): simulated passes and pending checks. | Tests confirm expected behavior against designed fixtures and current records; not real-world conflict/booking outcomes. |
| Real-world validation | [Yelp lineage/compatibility evidence](../yelp_lineage_gap_audit/compatibility_evidence_audit.md) lacks quotes, event-date availability, verified capacity, vendor-pair collaboration and operational failures. | **NOT_VERIFIED**. No real vendor reliability or booking success claim is supported. |

[Model status](../pp1_final_model_verification/model_status.md) traces the deterministic label rule: Low if mean review rating ≥4, rating standard deviation <1 and collected reviews ≥20; otherwise Medium if mean rating ≥3; else High. The five RF features overlap the rule inputs. Perfect held-out classification therefore can mean faithful reproduction of those rules. It does not validate a causal or predictive relationship to operational failure.

## Proposal evaluation plan versus evidence

The [proposal, pp. 24–26](../../docs/IT23292390%20Proposal%20Report.pdf) specifies a **criteria-based individual vendor selection baseline** using service requirements, price, rating and availability. No evidenced evaluation implements that independently defined baseline on the same held-out event set; reranking existing generated packages by cost would be a different baseline. Freeze an independent baseline algorithm and event scenarios before comparing.

The proposal calls for prelabelled scenarios across event types, budgets, guest counts, service categories, compatible/incompatible vendor combinations and suitable/unsuitable venues. Measured package recommendation accuracy, vendor compatibility correctness, venue suitability correctness, conflict identification accuracy, explanation usefulness and System Usability Scale responses remain **NOT_VERIFIED**. [Standalone synthetic conflict fixtures](../pp1_task2_conflict_engine/fixtures.json) support algorithm tests only. [Performance comparison](../pp1_task4_performance/performance_report.md) is a small local in-process experiment; production end-to-end 5-second compliance is not established.

A fair subsequent evaluation should freeze V1/V2 candidate coverage, independent event labels, acceptable package criteria, provenance classes, baselines and split before tuning. Report coverage/abstention and unknowns alongside accuracy; never score missing real evidence as a verified pass. Venue evaluation requires the teammate's independently documented interface and labels.
