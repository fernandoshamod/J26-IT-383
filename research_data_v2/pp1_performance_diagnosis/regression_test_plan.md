# Regression test plan for any approved optimization

1. Capture a baseline from the unchanged API for the exact saved event and additional Wedding, Birthday, Corporate, one-service, Catering, low-budget/no-match and unsupported-location cases. Retain request JSON and raw response.
2. For a candidate-filter change, compare candidate DataFrames in original order, including IDs and every field. Check city/state case and whitespace handling, event-type parsing, Catering guest capacity and service order.
3. Compare normalized full JSON responses, replacing only nondeterministic USER event IDs. Require identical candidate counts, selected option/vendor IDs and order, costs, model classes, ranking scores/factors, explanations, feasibility checks, warnings, search flags and response fields. Verify saved model SHA-256 stays unchanged.
4. Exercise `/api/packages/generate-dynamic` and `/api/feasibility/validate-dynamic` over live HTTP and the browser creation, comparison, regeneration and no-match paths. Preserve 422/503 handling.
5. Benchmark cold and warm requests in alternating baseline/optimized order with enough repeats to report median and slowest observed run. Include host, Python version, process model, file-cache state, request timing method and response size. Do not infer a five-second guarantee from a small sample.
6. Check simultaneous requests and source-file changes before adopting any cache. Verify there is no cross-request mutation and that a changed file invalidates cached data. Check memory use if caching large DataFrames.

The diagnostic cap probes in this folder are **not** proposed production settings; they only establish the cap's work and ranking-pool effects. No production fix was implemented in this diagnosis.
