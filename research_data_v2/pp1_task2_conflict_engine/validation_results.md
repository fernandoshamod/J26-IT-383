# Standalone validation results

- Interpreter: `D:\Vendor-Intelligence-System\venv\Scripts\python.exe`, Python 3.13.8.
- Executed `-B -m unittest -v test_conflict_engine.py`: **19 tests, 0 failures, 0 errors**, completed in 4.172 s. The first run exposed a UTF-8 BOM in the existing option CSV; the isolated test was changed to read `utf-8-sig`, then the full suite passed.
- Editor diagnostics for the four new Python files: no errors reported.
- Executed [evaluate.py](./evaluate.py): 12/12 expected three-way statuses; [full results](./evaluation_results.json). Recomputed fixture/engine SHA-256 and case/conflict counts from the saved JSON: PASS.
- Executed [demo.py](./demo.py): output saved to [demo_output.txt](./demo_output.txt). It shows compatible, resource conflict and unknown-pair cases with explicit synthetic labels.
- Executed [verify_source_hashes.ps1](./verify_source_hashes.ps1): **22 Task 1 inventoried existing files checked, 0 hash mismatches**; see [source_hash_verification.json](./source_hash_verification.json). This inventory covers datasets, models and research outputs, not every production source file.
- Existing backend regression tests, frontend build and production API smoke tests were not run for this isolated Task 2 because the implementation does not touch production and the allowed output scope is this directory. No production behavior is claimed freshly retested.
