# Shadow evaluation: measured local run

Evaluated UTC: 2026-10-17 09:27:45.426715. Data class: **SYNTHETIC_TEST**.

| Measure | Executed result |
|---|---:|
| Fresh USER requests | 2 |
| Returned packages shadow assessed | 6 (3 per request) |
| Packages with supported conflicts | 0 |
| Packages requiring verification | 6 |
| Source mapping failures | 0 |
| Existing/shadow status differences | 0 |
| Adapter total time, excluding generation and CSV load | 2.926 ms |
| Adapter mean per package | 0.488 ms |
| Full evaluation loop wall time | 21.089 s |

Each of six packages lacked availability, option schedule, teardown, resource requirements, resource capacity and event-specific vendor-pair evidence (6/6 packages for each category). Existing and shadow statuses were `VERIFICATION_REQUIRED` in all six cases. Zero supported conflicts means no relevant evidence was supplied; it is not a measured absence of real conflicts.

Scenario 1: Wedding, Philadelphia PA, 50 guests, Photography + Decoration, LKR 1,000,000, 21 October 2026. Scenario 2: Corporate, Philadelphia PA, 40 guests, Photography + Audio Visual, LKR 1,000,000, 22 October 2026. Both returned `search_limit_reached` because the candidate cap was reached; the node cap was not reached. Production generation took 15,951.93 ms and 5,133.67 ms respectively on this local run. Search was bounded to 12 candidates per service and 5,000 nodes. Results do not cover the full vendor universe.

All 22 files in the Task 1 dataset inventory matched their recorded SHA-256 hashes after the run. Four monitored production/Task 2 code files had identical SHA-256 hashes before and after execution. See `evaluation_results.json` and `shadow_comparison.csv` for machine-readable values and IDs.