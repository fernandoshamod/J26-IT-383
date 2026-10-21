# PP1 live demo verification — 18 October 2026

**Decision:** PASS for a qualified local proof-of-concept demonstration. Operation on 22 October remains NOT_VERIFIED. No production code, model, or dataset was changed.

## Exact live request

Backend started with `& .\venv\Scripts\python.exe -m uvicorn backend.main:app --host 127.0.0.1 --port 8000`; `/health` returned HTTP 200, healthy. Frontend started with `npm run dev` from `frontend`; port 5173 returned HTTP 200. The exact `request` from [saved input](../pp1_final_submission/pp1_demo_inputs_and_outputs.json) was posted: Wedding, 2026-11-16, 10:00–18:00, Philadelphia PA, 50 guests, LKR 1,000,000, Photography and Decoration, top K 3.

POST `/api/packages/generate-dynamic`: **HTTP 200, 10,795.85 ms**, event `USER-3E864697E372`, three packages. The response said `search_limit_reached`, candidate limit reached, 156 nodes visited and 138 combinations evaluated. The first package is highest ranked only among examined combinations. The exact request, full response, response time and feasibility rerun are in [api_response_evidence.json](./api_response_evidence.json).

| Package | Cost LKR | Vendors and model classes | Feasibility |
|---|---:|---|---|
| PKG-0001 | 305,535.41 | Minibooths (`FQ_QUyrwtnaEdxUxruZkXg`) Low; Petit Jardin En Ville (`_t_UwNkwAinJSljDDYvnoQ`) Low | VERIFICATION_REQUIRED |
| PKG-0002 | 328,001.78 | Minibooths Low; Carl Alan Floral Designs LTD (`P7MHW-EtCdp3eVF2P_nX0A`) Low | VERIFICATION_REQUIRED |
| PKG-0003 | 244,874.21 | Minibooths Low; Riehs Florist (`zwl7iLwHBTdkb5-0gNgGFg`) Medium | VERIFICATION_REQUIRED |

Each package warns `vendor_availability_unverified` and has 10 simulation checks passed, 8 pending, 0 failed. Pending checks cover each vendor's capacity, availability and schedule, plus vendor collaboration and venue suitability. Top-package dedicated feasibility POST returned **HTTP 200 in 664.35 ms** and `VERIFICATION_REQUIRED`; the response says `is_real_world_feasible: false`.

## Saved-model integration

**PASS.** [packages.py](../../backend/api/packages.py) calls [generate_dynamic_packages](../../backend/engine/dynamic_package_service.py), which calls [load_risk_signals](../../backend/engine/risk_signals.py). This verifies the saved artifact hash and metadata, loads it with `joblib.load`, and calls `model.predict` for complete candidate profiles. The live response reported 134 available profiles, named vendor predictions and SHA-256 `4eed156cfdf677b992b8c36350c21c968d7cb4d532a8afd302ca1b697aea3e6a`; the artifact file hash independently matched. These are predictions of rule-generated review labels, not independently validated operational risk. No retraining or artifact overwrite occurred.

The measured generation response **FAILS** the proposal's five-second target for this run. See [frontend verification](./frontend_verification.md), [vendor check](./selected_vendor_check.md) and [blockers](./blockers_and_fixes.md).
