# PP1 Task 4: isolated performance study

All files here are research outputs. Production FastAPI, React, models, datasets, configuration and Task 2/3 files were not edited. The prototype still invokes the production dynamic generator for each fresh USER request; it changes only the candidate filtering function for that call. No generated package is cached or loaded from a catalog.

## Run from the project root (Windows PowerShell)

```powershell
& .\venv\Scripts\python.exe -B research_data_v2\pp1_task4_performance\baseline_profile.py
& .\venv\Scripts\python.exe -B research_data_v2\pp1_task4_performance\regression_tests.py -v
& .\venv\Scripts\python.exe -B research_data_v2\pp1_task4_performance\benchmark.py
& .\venv\Scripts\python.exe -B research_data_v2\pp1_task4_performance\verify.py
```

Scripts create results with exclusive file mode and will refuse to overwrite existing evidence. For a rerun, copy the scripts into a new subdirectory inside this Task 4 directory and adjust their output path. The fixed October 2026 event dates require rerunning before those dates; a later replication must declare shifted dates.

## Files

- `baseline_profile.py`, `profile_results.json`: two runs per scenario, stage wall times, cProfile top calls.
- `optimized_prototype.py`: request-local shared candidate mask; no cross-request cache.
- `regression_tests.py`: exact candidate DataFrame and full response comparisons.
- `benchmark.py`, `benchmark_comparison.csv`: alternating-order unprofiled full-path timing.
- `verify.py`, `validation_results.json`: search metadata and Task 1 inventory hash checks.
- `bottleneck_analysis.md`, `performance_report.md`, `research_evaluation_report.md`, `pp1_evidence_pack.md`, `limitations.md`: interpretation and presentation material.

Interpreter: `D:\Vendor-Intelligence-System\venv\Scripts\python.exe` (Python 3.13.8). No packages were installed. All timing is local synthetic-data evaluation, not deployed API or browser latency.