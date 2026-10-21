# Architecture explanation

The active system is a React/Vite client, FastAPI backend, CSV records and existing Random Forest artifacts. Each user submits one event brief. Validation precedes source-option filtering. Bounded search avoids enumerating the full Cartesian product. Each examined complete package is costed and feasibility-checked; failed packages cannot be recommended. Surviving packages are scored, sorted, explained and reduced to top-K. The frontend holds that response in current-session state for recommendations, comparison and dynamic feasibility rerun. USER IDs are generated per request; PKG IDs label the response rather than a catalog entry.

The model's risk signal reflects review-based rule labels; service-category compatibility reflects matrix rules. Neither establishes a booking or a real vendor relationship. Synthetic price, capacity, location and service-area fields support simulation only. The VERIFICATION_REQUIRED outcome records missing evidence.

Task 2's fixture-based conflict engine, Task 3's read-only shadow adapter and Task 4's isolated optimization are separate from the production flow. No production feature flag is enabled. The future venue-team interface can supply venue suitability evidence when integrated, but no Digital Twin is implemented here.

See [Mermaid diagrams](./architecture_diagrams.md), [implementation](./implementation_summary.md) and [Task 5 discovery](../pp1_task5_demo_readiness/system_discovery.md).