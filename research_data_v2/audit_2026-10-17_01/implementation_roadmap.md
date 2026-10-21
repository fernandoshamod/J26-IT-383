# Small-stage roadmap toward PP1 (no implementation in this task)

| Order | Stage | Dependency and deliverable | Acceptance evidence |
|---|---|---|---|
| 0 | Obtain official proposal and dataset rights | Confirm FR1–FR13, research questions, non-functional targets, Yelp/Google usage terms | Signed requirement matrix and source permissions |
| 1 | Freeze provenance and quality rules | Reconcile existing profile/option IDs; review local public-source lineage; keep original data untouched | Hash manifest, FK and missingness report; no unverified REAL_PUBLIC assertions |
| 2 | Define vendor pair/conflict evidence | Agree schema, evidence levels and adjudicated conflict fixtures; never reuse sample-event collaboration as USER evidence | Symmetric pair tests, unknown handling, traceable positive/negative cases |
| 3 | Add event-specific scheduling/resource reasoning (future task) | Requires option resources, venue-team contract and event-time records | Unit tests for time overlap, capacity, power/space, missing evidence |
| 4 | Specify fair baseline and preference study | Proposal's individual-vendor baseline may differ from existing cost-only package rerank | Same scenarios, eligible universe, search budget, independent metrics |
| 5 | Validate risk and usability claims | Requires independent outcomes or restrict claim to rule replication; SUS requires participant protocol | External validity report and actual participant scores, with limitations |

**Task 2 recommendation:** Implement a provenance-aware vendor-pair evidence and conflict-test-case layer in isolation, with explicit REAL_PUBLIC/DERIVED/SYNTHETIC_TEST/UNKNOWN labels, symmetric pair lookup, unknown-as-pending semantics, and deterministic resource-conflict fixtures. Keep production category compatibility and ranking unchanged until evidence and tests are reviewed. Venue suitability remains owned by the other team member.
