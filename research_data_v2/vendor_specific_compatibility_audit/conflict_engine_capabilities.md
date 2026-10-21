# Standalone conflict engine capabilities

[The isolated engine](../pp1_task2_conflict_engine/conflict_engine.py) accepts supplied event, assignment and evidence records. It is not integrated into FastAPI or React. It returns `COMPATIBLE_WITH_EVIDENCE`, `CONFLICT_WITH_EVIDENCE`, or `VERIFICATION_REQUIRED`; conflict dominates pending. Results concern only supplied evidence, never a confirmed booking.

| Check | Engine behavior | Existing USER-event evidence |
|---|---|---|
| Event/service time | Requires timezone offsets, service interval inside event; checks overlap. | Submitted event times exist; option-specific interval/timezone absent. |
| Availability | Requires matching event ID, source, observation timestamp and covering interval. | [Availability rows](../../hybrid_simulation_v1/synthetic_availability.csv) are SIMEVT-only and unconfirmed. |
| Vendor pair | Symmetric ID lookup; category rule, out-of-event, contradictory or unverified pair evidence stays pending. | [Pair rows](../../hybrid_simulation_v1/synthetic_collaboration_scenarios.csv) are random SIMEVT simulations; all `is_actual_collaboration=False`. |
| Same-vendor schedule | Checks overlapping service and setup/teardown windows with multitask/exclusive-crew flags. | No confirmed calendar, teardown or crew flags; live packages require distinct vendors. |
| Equipment/crew | Compares peak timed demand with documented capacity for named `equipment:`/`crew:` resources. | No inventory, timed allocations or capacities. |
| Venue | Always pending and external. | [Legacy table](../../venue_constraints.csv) is header-only. |

The engine checks the *shape* of `REAL_PUBLIC` records but cannot authenticate their source or meaning. It always returns `is_real_world_collaboration_confirmed=False` and `is_real_world_feasible=False`. Its `evidence_scope` text is fixed to synthetic-fixture wording, so a future adapter must review it before any different source is used.

Executed on 2026-10-19: `venv/Scripts/python.exe -B -m unittest -v test_conflict_engine.py` in the engine folder: **19 tests passed**. They cover 12 hand-authored synthetic cases, symmetric lookup, event mismatch, unknowns, contradictions, time/resource conflicts, determinism and source option IDs. The [prior evaluation](../pp1_task2_conflict_engine/evaluation_report.md) reports 12/12 expected fixture statuses (6 conflicts, 2 compatible, 4 pending). These measure software agreement with synthetic fixtures, not real-world accuracy. [The shadow adapter](../pp1_task3_shadow_integration/shadow_adapter.py) previously mapped six fresh USER packages with all six pending; the full operational engine was not run because inputs were missing ([report](../pp1_task3_shadow_integration/evaluation_report.md)).
