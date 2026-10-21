# PP1 Task 3: read-only shadow integration

This folder is an isolated research prototype. It does not change FastAPI, React, Task 2, model artifacts, source datasets, ranking, or feasibility decisions.

## Run on Windows

From the project root:

```powershell
& .\venv\Scripts\python.exe -B -m unittest discover -s research_data_v2\pp1_task3_shadow_integration -p test_shadow_adapter.py -v
& .\venv\Scripts\python.exe -B research_data_v2\pp1_task3_shadow_integration\evaluate.py
```

The evaluation script uses exclusive file creation and refuses to overwrite existing results. Move or rename this entire Task 3 output folder before a new run, or adapt the output location within this folder.

## Actual schema and boundary

The request model is `backend/schemas/dynamic_package_request.py`. The dynamic service creates a UUID `USER-*` event with date, start/end time, city/state, guests, LKR budget and semicolon-separated required services. The generator returns `generation.packages`; each package has response-local `PKG-*` ID, `option_ids`, `vendor_ids`, `service_breakdown`, `package_options`, estimated cost, remaining budget, ranking score and `feasibility.final_status`. `PKG-*` is assigned by rank on every request and is not evidence of saved-package retrieval.

The adapter resolves IDs from the current `hybrid_simulation_v1/synthetic_service_options.csv` source, cross-checks embedded IDs, service, event type and simulated location, then invokes Task 2's `lookup_pair` for each distinct vendor pair. It deliberately supplies an empty event-specific evidence list. No Task 2 fixtures or historical SIMEVT availability/collaboration data enter ordinary USER assessments. The adapter returns a new assessment object; it does not mutate packages.

## Outputs

- `shadow_adapter.py`: source mapping and separate pending/conflict assessment.
- `test_shadow_adapter.py`: focused standalone unit tests.
- `evaluate.py`: two controlled fresh dynamic USER requests.
- `evaluation_results.json`: execution metadata, package measurements, source inventory hash comparison.
- `shadow_comparison.csv`: per-package comparison; identifiers and scores only, no reusable package catalog.
- `example_output.txt`: short presentation example.
- `evaluation_report.md`: measured findings.
- `limitations.md`: evidence limitations.
- `integration_proposal.md`: future production handoff, not activated.

The source records are synthetic service-option simulations. No result validates actual vendor collaboration, availability, equipment capacity, or booking feasibility.