# Major presentation claims audit

This is a source-to-claim audit, not a fresh production test. PASS means existing implementation and/or executed evidence supports the stated narrow claim; QUALIFIED means caveats must accompany it; UNSUPPORTED means it must not be asserted.

| Claim permitted in slides/demo | Evidence | Status and required wording |
|---|---|---|
| New USER requests use request-time option-based generation | [Dynamic service](../../backend/engine/dynamic_package_service.py), [Task 5 repeat smoke](../pp1_task5_demo_readiness/demo_readiness_report.md) | PASS: source path reads current rows; repeated identical input can select same option sequence |
| No pre-generated package catalog supplies dynamic recommendations | [Dynamic path](../../backend/engine/dynamic_package_service.py), [Task 5 discovery](../pp1_task5_demo_readiness/system_discovery.md) | PASS for inspected active path; historical report files still exist |
| Required services, unique vendors, budget and FAIL exclusion are checked | [Generator](../../backend/engine/bounded_package_generator.py), [Task 5 tests](../pp1_task5_demo_readiness/demo_readiness_report.md) | PASS within tested implementation |
| Candidate/search limits bound enumeration | [Generator](../../backend/engine/bounded_package_generator.py), [historical configuration](../../research_evaluation/evaluation_summary.json) | PASS; top rank is not global optimum |
| Risk 100/100 indicates good review-rule favorability | [Risk implementation](../../backend/engine/risk_signals.py), [Task 5 UI](../pp1_task5_demo_readiness/demo_readiness_report.md) | QUALIFIED; not failure probability or real-world reliability |
| Random Forest 100% accuracy proves real-world failure prediction | [Model evaluation](../../research_evaluation/model_evaluation.md) | UNSUPPORTED; only reconstructed rule-label agreement |
| Category matrix proves vendor collaboration | [Compatibility source](../../vendor_compatibility_matrix.csv), [Task 2 report](../pp1_task2_conflict_engine/README.md) | UNSUPPORTED; categories only |
| Task 2 conflict engine detected 12/12 fixture statuses | [Task 2 evaluation](../pp1_task2_conflict_engine/evaluation_report.md) | QUALIFIED; controlled SYNTHETIC_TEST fixture agreement only |
| Task 3 conflict engine active in production | [Task 3 README](../pp1_task3_shadow_integration/README.md) | UNSUPPORTED; read-only shadow prototype |
| Task 4 optimization reduced median time for two multi-service cases | [Task 4 benchmark](../pp1_task4_performance/benchmark_comparison.csv) | QUALIFIED; two local runs/scenario, isolated not deployed; Birthday regressed |
| Five-second full-system target met | [Task 4 report](../pp1_task4_performance/performance_report.md) | UNSUPPORTED |
| Historical 35 scenarios, 34 success, 202 recommendations, 20 truncations | [Summary JSON](../../research_evaluation/evaluation_summary.json) | PASS for historical synthetic local experiment, not live field performance |
| Cost-only baseline is an individual-vendor baseline | [Historical methodology](../../research_evaluation/evaluation_methodology.md) | UNSUPPORTED; same-package-pool cost-only reranking |
| Captured feasibility is a real-world pass | [Genuine feasibility capture](./screenshots/feasibility.png), [Task 5 results](../pp1_task5_demo_readiness/demo_readiness_report.md) | UNSUPPORTED; 10 simulation passes, 8 pending, VERIFICATION_REQUIRED |
| Live Task 5 Wedding/Corporate requests returned HTTP 200 | [Task 5 execution JSON](../pp1_task5_demo_readiness/demo_execution_results.json) | PASS for those past local requests; no new Task 6 HTTP request claimed |
| Browser screenshots show working existing UI | [Screenshot evidence](./screenshot_evidence.md) | PASS for captured routes/current USER state; no full browser/accessibility audit |
| Official FR1–FR13 proposal requirements are exactly covered | [Task 1 gap analysis](../audit_2026-10-17_01/proposal_gap_analysis.md) | UNSUPPORTED; official PDF unavailable, comparisons provisional |
| Venue Suitability is integrated | [Venue contract](../audit_2026-10-17_01/venue_integration_contract.md) | UNSUPPORTED; external team boundary only |

No claim of real availability, booking, validated vendor collaboration, real-world conflict accuracy, user satisfaction, deployment readiness or independent recommendation superiority is supported by the supplied evidence.