# Final recommendation for PP1

**Retain the working demo and document the latency limitation.** Do not change production code before PP1 solely to chase the five-second target. The exact saved event succeeded in all new live HTTP runs (first 3.44 s; warm 1.21–1.33 s), while the earlier valid observation was 10.80 s and prior runs were near 5–6 s. This variability means a reliable under-five-second claim is not established.

The measured persistent costs are CSV parsing, candidate filtering and profile processing. A request-local shared filter is a plausible low-risk change, with limited prior equivalence tests and a small measured gain, but it has not demonstrated robust five-second performance. Caching has more lifecycle and data-freshness risk. Package search, feasibility, ranking and serialization are not the present dominant costs, so changing candidate limits would trade result coverage for little dependable end-to-end gain.

For the 22 October presentation, use the exact saved event, allow visible generation time, and state that timing varies and the five-second target is unverified. Show the bounded-search warning and synthetic-data qualification. Pursue the shared-filter change only after separate approval and the [regression plan](./regression_test_plan.md). No production code, model or dataset was modified.
