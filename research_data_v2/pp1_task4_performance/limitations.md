# Limitations and safety decisions

- No production integration or feature flag was added. The isolated prototype preserves current generation and ranking semantics only in the three tested scenarios; broad equivalence needs more cases before any production patch.
- Benchmark has two paired, local in-process runs per scenario. OS caches, model warmup, background load and cProfile overhead affect timing. No peak-memory measurement or deployed HTTP/browser latency was collected.
- The first profiled Wedding run includes cold sklearn/model import. Risk loading, CSV parsing and inference were measured together in later runs; separate inference-only timing is unavailable.
- All scenarios reached the candidate cap; the node cap did not trigger. Measurements say nothing about uncapped global optimum or large-service tail latency.
- Source/profile CSV caching was not prototyped. A future cache would need a path plus content-hash or equivalent strong freshness key, bounded memory, immutable cached data and request-local copies. Never cache final generated packages.
- No real vendor availability, collaborations, equipment, prices, failure outcomes or user study evidence was created. Venue suitability belongs to the external component.
- The official proposal PDF is still needed to verify formal FR1–FR13 wording, a true individual-vendor baseline, and any five-second requirement.
- The fixed October 2026 event dates are valid for the PP1 deadline; later reruns must declare a date shift to pass production request validation.