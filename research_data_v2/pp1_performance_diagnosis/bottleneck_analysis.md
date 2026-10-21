# Bottleneck analysis — exact saved PP1 request

## What was measured

The unchanged Wedding / Philadelphia request from [saved input](../pp1_final_submission/pp1_demo_inputs_and_outputs.json) was sent to a freshly started Uvicorn server four times, then run four times in a separate timed Python process. [performance_measurements.csv](./performance_measurements.csv) contains every stage and run. The timed wrappers are in [profile_exact_request.py](./profile_exact_request.py); [cProfile output](./cprofile_exact_warm.txt) is a separate profiled warm run. Instrumentation stayed outside production modules.

| Measurement | Times, ms | Interpretation |
|---|---|---|
| Earlier PP1 live HTTP | 10,795.85 | Actual prior observation; no stage profile was captured then. |
| New HTTP: first / warm 2–4 | 3,442.24 / 1,330.92, 1,278.00, 1,205.85 | First request slower; warm median 1,278.00. All HTTP 200, three packages. |
| New in-process: first / warm 2–4 | 1,435.77 / 1,237.85, 1,345.22, 2,342.85 | Separate process and measurement overhead; warm median 1,345.22. Its first run pre-imported sklearn, so it is not a true cold-model measure. |

Warm in-process stage medians (runs 2–4): option CSV/load 550.71/552.52 ms; profile CSV 248.72 ms; candidate filtering 265.37 ms; model verification 1.87 ms; Random Forest inference 68.90 ms; entire risk stage 359.87 ms; bounded generation 58.46 ms; feasibility 13.55 ms; ranking 2.87 ms; JSON-safe conversion 3.32 ms. Nested values are **not additive**: profile CSV and inference are inside risk stage; feasibility and ranking are inside bounded generation. The risk-stage remainder includes profile ID joins and signal assembly. Bounded-generation remainder includes candidate price validation, cap selection, DFS, sorting and package assembly, so it is not a pure DFS measurement.

[cProfile output](./cprofile_exact_warm.txt) confirms the structural hot spots in a profiled warm run: candidate selection 1.653 s, three `pandas.read_csv` calls 1.525 s cumulative, risk stage 1.195 s, bounded generation 0.175 s. cProfile increased the run to 3.998 s and must not be used as unprofiled latency. The 115,098 event-type lambda calls show the filter repeats parsing over 57,549 option rows for each of two services. [Production candidate filter](../../backend/engine/candidate_selection.py) confirms that call pattern.

**Actual repeatable bottleneck:** repeated CSV parsing and full-table candidate filtering, plus profile loading/joins. Feasibility, ranking, combination search and serialization are small in this exact default-cap request. Cold server/request cost is visible in HTTP but cannot be split into model import versus OS file cache from these measurements. The original 10.80-second outlier cannot be assigned to one stage retrospectively; current readings do not reproduce it. The [earlier performance report](../pp1_task4_performance/performance_report.md) also found warm original-path Wedding runs near 5.8 s, demonstrating environment variability.

## Candidate limit

Default cap 12 selected 12 Photography and 12 Decoration candidates from 165 and 237 eligible, then evaluated 138 combinations; the candidate cap was reached, the 5,000-node cap was not. Controlled diagnostic caps 6, 12, 24 evaluated 36, 138, 558 combinations. Bounded-generation time in the second cap-stage series was roughly 40–42, 50–61, 162–231 ms respectively; whole-request times varied enough that cap changes are not a reliable 5-second fix. [Cap probes](./cap_and_serialization_probe.py) and [stage probes](./cap_stage_probe.py) used process-local environment overrides only. All six cap runs returned the same top-three option IDs and scores for **this event**. The cap still affects result quality scope: excluded options are never ranked, so a better combination may be missed for this or another event. Candidate limit therefore affects **both** latency and the completeness of results; current evidence does not quantify missed quality.

## Serialization boundary

The in-process `to_json_safe` conversion took 0.63–4.68 ms in the three warm stage runs. A separate encode of the saved full response with FastAPI `jsonable_encoder` took 1.48–5.76 ms across four runs, and `JSONResponse` rendering took 0.45–0.75 ms (see the `serialization` rows in [performance_measurements.csv](./performance_measurements.csv)). These are offline serialization measurements, not a timer inside the live Uvicorn response path. Total HTTP time was measured directly; subtracting times from separate processes would not reliably isolate network, scheduling or FastAPI overhead.
