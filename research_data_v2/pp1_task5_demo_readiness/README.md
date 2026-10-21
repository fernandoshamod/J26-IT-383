# PP1 Task 5 — demo readiness evidence

This directory contains a verification snapshot for 17 October 2026. It does not modify PlanoVision production code or research outputs. The live HTTP scenarios were sent to an already-running server at `http://127.0.0.1:8000`; a shared browser was used at `http://127.0.0.1:5173`.

## Reproduce safely

From the project root, while the backend is already running:

```powershell
& .\venv\Scripts\python.exe -B research_data_v2\pp1_task5_demo_readiness\verify_demo.py
```

The script creates `demo_scenarios.json` and `demo_execution_results.json` with exclusive mode. It refuses to overwrite this snapshot. For a new audit, copy the script into a new subdirectory under this Task 5 directory and point its output there. Dates are computed as 5–7 days after execution.

The four existing unittest files executed safely with `-B`: `test_dynamic_packages.py` (8), `test_dynamic_feasibility.py` (8), `test_final_validation.py` (9), `test_research_evaluation.py` (7): **32 passed, 0 failed**. `npm run lint` passed. The risk/compatibility test file was skipped because one test writes a temporary CSV outside this task's permitted directory. Frontend build was skipped because its outputs/caches may write outside this directory. Do not represent skipped steps as passing.

Start with `demo_readiness_report.md`, then `pp1_demo_script.md` and `screenshot_checklist.md`. `requirements_traceability.csv` is **PROVISIONAL** because the official proposal PDF was not found.
Final integrity check: run .\venv\Scripts\python.exe -B research_data_v2\pp1_task5_demo_readiness\verify_final_integrity.py. It writes final_integrity.json exclusively in this directory; the completed run found 22/22 inventoried files and 7/7 watched code files unchanged.

