# Measured execution path and bottlenecks

`DynamicPackageRequest` validation → `generate_dynamic_packages` → `load_service_options` → `select_candidates_for_event` → `load_risk_signals` (verified Random Forest and profile CSV) → `load_compatibility_rules` / `service_compatibility` → `generate_bounded_packages` → per-combination `validate_dynamic_package`, `_ranking`, `explain_package` → JSON serialization.

Stage timings are instrumented wall time within the full request. `bounded_generation` includes its nested feasibility, ranking and explanation calls; those nested values must not be added to the parent time. The pure DFS loop was not separately exposed.

Warm, unprofiled second baseline runs from `profile_results.json` (ms):

| Scenario | Full path | Source CSV | Candidate selection | Risk stage | Bounded generation | Feasibility calls | Ranking calls | Explanation calls |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| Wedding | 5347.365 | 1346.316 | 1317.924 | 1828.991 | 225.811 | 43.183 | 26.897 | 3.625 |
| Corporate | 5302.597 | 1718.380 | 1531.753 | 1252.996 | 45.153 | 5.846 | 1.196 | 0.872 |
| Small | 4517.584 | 1285.710 | 897.823 | 1675.326 | 35.458 | 8.422 | 0.714 | 0.342 |

The risk stage includes model hash verification, cached model access, profile CSV read, ID matching and inference. Its subparts were not independently timed. The first Wedding cProfile run took 30.419 s; `load_risk_signals` accounted for 20.041 s, including 18.024 s in `_load_verified_model`, largely first-time sklearn import. cProfile and cold imports inflate that first run; do not use it as an ordinary latency estimate. Matrix loading and compatibility calculation were small in this sample.

Confirmed opportunities: the production candidate filter repeats city/state normalization and event-type parsing for every requested service. This is amplified for multi-service requests on 57,549 option rows. The prototype computes a request-local shared mask once, then applies the same service and Catering rules. It does not copy the source DataFrame beyond the original per-service `.copy()`. Repeated source/profile CSV reads remain larger costs; no cache was introduced because freshness, memory and process lifecycle need review.

Rejected for this task: caching final package results, changing candidate or DFS caps, changing weights, skipping feasibility checks, or using Task 2 fixtures as live evidence.