# Safe test and build results — 18 October 2026 local audit

All commands used existing source files. Python used the project [venv](../../venv/) with `-B` to avoid bytecode writes. The Vite build output was directed to [frontend_build/](./frontend_build/) inside this audit folder; [frontend/dist/](../../frontend/dist/) was not used as an output target.

| Check | Command / method | Result |
|---|---|---|
| Backend suite | `venv/Scripts/python.exe -B -m unittest discover -s tests -p test_*.py -q` | **PASS: 51 tests**, 49.884 s. One Starlette warning about deprecated httpx/TestClient integration. |
| Standalone conflict engine | `venv/Scripts/python.exe -B -m unittest discover -s research_data_v2/pp1_task2_conflict_engine -p test_conflict_engine.py -q` | **PASS: 19 tests**, 3.238 s. These cover synthetic fixtures only. |
| Shadow adapter | `venv/Scripts/python.exe -B -m unittest discover -s research_data_v2/pp1_task3_shadow_integration -p test_shadow_adapter.py -q` | **PASS: 7 tests**, 13.745 s. This is separate from production. |
| Frontend lint | `npm --prefix frontend run lint` | **PASS**, oxlint exit 0. |
| Frontend build | From [frontend/](../../frontend/): `node_modules/.bin/vite.cmd build --outDir D:/Vendor-Intelligence-System/research_data_v2/pp1_final_technical_audit/frontend_build` | **PASS**, Vite 8.3.4, 31 modules transformed, built in 1.04 s. Vite warned that the external output directory would not be emptied; this was a new audit folder. |
| Focused API | [focused_api_probe.py](./focused_api_probe.py) using FastAPI TestClient | **PASS:** all three requests HTTP 200 with expected package/no-match statuses; exact [results JSON](./focused_api_results.json). |
| Model agreement for ranking trace | Inference-only pass over all current complete profiles | **PASS:** 18,430 complete profiles, 0 model/stored-rule disagreements. No model training. |
| Source integrity | Rehashed 15 inventoried files from [source_hashes.csv](../pp1_final_model_verification/source_hashes.csv) after tests/build | **PASS:** 0 changed among the 15. This is not a whole-repository snapshot. |

An initial `npm --prefix frontend run build -- --outDir ...` invocation failed because npm stripped the Vite flag and treated the path as an entry module. The corrected direct Vite command above succeeded. This was **test invocation error**, not a source/build failure. No production file was edited or overwritten.

## Focused API observations

[focused_api_results.json](./focused_api_results.json) uses Corporate, 26 Nov 2026, 10:00–18:00, Catering + Entertainment, LKR 1m, top 3. Bensalem PA / 50 guests returned 3 simulated packages and a candidate-limit warning. Bensalem PA / 500 guests returned 0 with `BUDGET_INSUFFICIENT`. Belle Chasse LA / 50 guests returned 0 with `NO_SERVICE_COVERAGE`. These results confirm graceful no-match behavior, not actual vendor affordability or availability.

## Limits

The suite and local TestClient do not certify deployed-server reliability, browser accessibility, response-time targets, real vendor service correctness, operational conflict accuracy, or user-study outcomes. The [FR13 browser evidence](../pp1_fr13_no_match_recovery/fr13_verification.md) is a separate prior controlled interaction and was not replayed in this audit.
