# Evaluation evidence for PP1

| Source and scope | Executed result | Correct interpretation |
|---|---:|---|
| Historical Task 5 research evaluation | 35 synthetic scenarios; 34/35 successful requests; 202 recommendations | Local TestClient experiment on simulation records, not real bookings |
| Historical recommendation pool | 202/202 returned packages covered services and fit synthetic budgets; all 202 VERIFICATION_REQUIRED | No real-world feasibility confirmation |
| Historical bounded search | 20/35 scenarios truncated (57.14%) | Top-K can omit better unexamined packages |
| Historical latency | Mean 1,986.383 ms; median 1,964.343 ms; p95 3,181.122 ms | Local historical TestClient timing, not browser/deployed latency |
| Historical shared-pool cost-only baseline | 26 comparable events; proposed mean top-K cost higher by LKR 77,258.317; mean top-K overlap 0.711538 | Isolates ranking on the same examined pool; not individual-vendor baseline or superiority test |
| Reconstructed model holdout | 3,686 rows; accuracy/macro and weighted F1 = 1.0; High 576, Low 408, Medium 2,702 | Agreement with deterministic review-feature labels, not independent real-world failure prediction; original held-out IDs not persisted |
| Task 2 standalone fixtures | 12/12 exact statuses; known binary cases TP 6, TN 2, FN 0, FP 0; 4 pending | Hand-authored SYNTHETIC_TEST cases, not external accuracy |
| Task 3 shadow | 2 fresh USER requests, 6 packages; 0 evidence-supported conflicts, 6 pending; 0 mapping failures | Missing evidence prevents conflict conclusion |
| Task 4 isolated optimization | Wedding median 5,822.090 → 4,862.088 ms; Corporate 5,482.624 → 4,627.236 ms; Birthday 4,251.556 → 4,616.353 ms | Two local unprofiled runs/scenario; not deployed; five-second target unproven |
| Task 5 live smoke | Wedding and Corporate HTTP 200, three packages each; low-budget HTTP 200, zero packages; invalid inputs HTTP 422 | Already-running localhost servers; not fresh Task 6 execution |

Sources: [historical summary](../../research_evaluation/evaluation_summary.json), [research report](../../research_evaluation/research_results_report.md), [model evaluation](../../research_evaluation/model_evaluation.md), [Task 2](../pp1_task2_conflict_engine/evaluation_report.md), [Task 3](../pp1_task3_shadow_integration/evaluation_report.md), [Task 4](../pp1_task4_performance/performance_report.md), [Task 5](../pp1_task5_demo_readiness/demo_readiness_report.md). Historical evaluation and Task 5 live smoke used different dates and execution paths; do not combine their latency distributions.