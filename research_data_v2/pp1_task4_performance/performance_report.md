# Local performance comparison

The profiler ran the original path twice each for Wedding, Corporate and a small Birthday scenario. The first run per scenario had cProfile enabled; only the second was unprofiled, so profile medians are not used as before/after estimates. `benchmark_comparison.csv` is a separate unprofiled, alternating-order comparison with two paired runs per scenario. The verified model loader was warmed before both approaches.

| Scenario | Original median (range) ms | Prototype median (range) ms | Change in mean/median time | Search result |
|---|---:|---:|---:|---|
| Wedding: Photography + Decoration | 5822.090 (5747.562–5896.617) | 4862.088 (4605.716–5118.459) | 16.49% faster | Candidate cap reached; 138 combinations examined |
| Corporate: Photography + Audio Visual | 5482.624 (5109.910–5855.337) | 4627.236 (4562.864–4691.608) | 15.60% faster | Candidate cap reached; 36 combinations examined |
| Small Birthday: Photography | 4251.556 (4184.855–4318.257) | 4616.353 (3641.985–5590.721) | 8.58% slower median | Candidate cap reached; 12 combinations examined |

All rows use 12 candidates/service and a 5,000-node maximum. Candidate truncation occurred in all six benchmark pairs; node truncation did not. The observed percentage uses (original median − prototype median) / original median × 100; with two runs, median equals mean. One small-scenario prototype run was slower, so the optimization is not a consistent win for one-service events.

**Correctness:** 3 regression tests passed. Exact candidate DataFrames matched for three scenarios. Complete generated JSON responses matched after replacing only their nondeterministic USER IDs. Thus returned vendor/option IDs, order, LKR costs, risk, compatibility, feasibility, ranking, explanation, candidate counts, examined combinations, and truncation flags matched in those scenarios. The 22 Task 1 source/model inventory files matched recorded SHA-256 hashes. This is controlled regression evidence, not a proof for all possible requests.

**Five-second target:** not established. Wedding prototype had a 5.118 s run; the small case had a 5.591 s run. Two local runs per scenario do not establish a robust tail latency target. Full path here is in-process Python generation, not HTTP/browser latency. Peak memory was not measured. Task 3's shadow adapter timing (0.488 ms/package) is separate and was not included in this comparison.