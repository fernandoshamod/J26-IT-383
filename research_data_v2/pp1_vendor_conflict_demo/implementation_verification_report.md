# PP1 vendor conflict research demo — implementation and verification

Date: 2026-10-19. Route: `http://127.0.0.1:5173/#admin-conflicts` (Research Demo → Vendor Conflict Demo).

## Implementation

The page is an isolated **static research snapshot**, not part of package generation. [build_demo_data.py](./build_demo_data.py) executes the existing [standalone engine](../pp1_task2_conflict_engine/conflict_engine.py) on three existing [fixtures](../pp1_task2_conflict_engine/fixtures.json), reads the recorded category score from [the matrix](../../vendor_compatibility_matrix.csv), and writes [vendor_conflict_research.json](../../frontend/src/data/vendor_conflict_research.json). [The page](../../frontend/src/pages/VendorConflictResearch.jsx) reads only that snapshot; it makes no API calls. The route is registered in [App.jsx](../../frontend/src/App.jsx) and [navigation.js](../../frontend/src/data/navigation.js). Styling is scoped in [App.css](../../frontend/src/App.css). [The focused test](./test_vendor_conflict_demo.py) checks parity with the engine/fixtures/matrix and real-world caveats.

| Fixture | Category score | Engine operational result | Explanation |
|---|---:|---|---|
| `compatible_pair` | 85/100 | `COMPATIBLE_WITH_EVIDENCE` | No conflict within supplied synthetic checks. |
| `equipment_insufficient` | 85/100 | `CONFLICT_WITH_EVIDENCE` | Simulated shared-camera peak demand 2 exceeds simulated limit 1, even though simulated pair evidence says compatible. |
| `unknown_pair` | 85/100 | `VERIFICATION_REQUIRED` | No usable event-specific pair evidence. |

All three display named source IDs and service categories, **SYNTHETIC TEST DATA**, real-world availability **NOT VERIFIED**, real-world collaboration history **UNKNOWN**, and venue suitability **VERIFICATION REQUIRED**. Identifiers refer to source records only; fixture services, outcomes, times and capacities are simulated. The 85/100 value is a category heuristic, not a vendor-specific percentage.

## Verification performed

- Snapshot check (`python -B -m research_data_v2.pp1_vendor_conflict_demo.build_demo_data --check`): PASS; generated data matches current engine, fixtures and matrix.
- Focused demo unit tests: **4 passed**.
- Existing standalone conflict-engine unit tests: **19 passed**. The initial combined root-level `unittest` command could not import its local `conflict_engine` module; rerunning from its own folder passed all 19. This was a test invocation path issue, not a code failure.
- Existing frontend Node tests: **7 passed**.
- Frontend lint (`npm run lint`): PASS.
- Frontend build (`npm --prefix frontend run build`, existing VS Code task): PASS, 33 modules transformed.
- Existing backend package/model/feasibility/final-validation regression files (`pytest -p no:cacheprovider -q`): **36 passed, 18 subtests passed**; one Starlette/httpx deprecation warning from the environment.
- Browser route: PASS. The three examples and all provenance labels rendered on `#admin-conflicts`. [Full-page screenshot](./demo_page.png) was captured. A full browser reload was needed after Vite HMR because the preexisting tab retained an old route allowlist; direct navigation then worked.
- Saved Philadelphia Wedding request from [pp1_demo_inputs_and_outputs.json](../pp1_final_submission/pp1_demo_inputs_and_outputs.json) sent unchanged to the live `POST /api/packages/generate-dynamic`: **HTTP 200**, **3 packages**, event `USER-797D6994ECC5`, measured total HTTP time **4691.61 ms**. Search status `search_limit_reached`, consistent with the existing bounded search.
- SHA-256 comparisons against [the verified PP1 backup](../../../PlanoVision-PP1-Backups/PlanoVision_PP1_20261018_134533): active `dynamic_package_service.py`, `bounded_package_generator.py`, `dynamic_feasibility.py`, `vendor_compatibility_matrix.csv`, `models/vendor_risk_random_forest.pkl`, and `synthetic_service_options.csv` all matched their backup copies. No backend, model, dataset or backup file was edited.

## Files created or changed

Created: `frontend/src/pages/VendorConflictResearch.jsx`, `frontend/src/data/vendor_conflict_research.json`, this report, `build_demo_data.py`, `test_vendor_conflict_demo.py`, and `demo_page.png`.
Changed frontend presentation/routing only: `frontend/src/App.jsx`, `frontend/src/data/navigation.js`, `frontend/src/App.css`.

## Limitations

The browser page shows a **generated snapshot**, not live recomputation; regenerate and run `--check` if fixtures, engine or matrix change. Engine fixture statuses test software logic, not real vendor behavior. A simulated compatible result covers only supplied checks; venue, actual availability, and actual collaboration remain unverified. Search remains bounded in the unchanged production demo. No new score, API contract, package constraint, ranking rule, model prediction, or recommendation behavior was introduced.
