# PlanoVision — Component 4 portable VS Code project

Spatial-Financial Intelligence and Budget Optimization. Research prototype,
packaged 16 October 2026. Current serving model: `expense_risk_v3_1_20261016`.

## Component 2 bridge update — 18 October

What-If → Import Component 2 quotations accepts a proposed strict JSON contract.
Share `api/contracts/component2_quotation_bundle.schema.json` and the TypeScript
contract with the Component 2 student. An explicitly mock test example is supplied
under fixtures; never describe it as a real vendor quotation. Import affects only
the preview. Existing tax/escalation/validity and confirmation rules apply.

Reports → Historical price forecasts replays existing saved price/index results
with exact units, source dates and range gates. It is not current-event forecasting
or fresh Prophet inference: October 2026 is outside the archived coverage and blocks.
No historical ingredient price is automatically added to catering or multiplied
across a hotel package. Current vendor lookup belongs to Component 2.

See reports/COMPONENT2_FORECAST_BRIDGE_20261018.md for limits and next evidence.

## Functional gap update — 18 October 2026

- Financial planner: Save main plan stores validated inputs in this browser;
  refresh restores them and recalculates. Confirming a client preview also saves
  the updated main plan. Unconfirmed previews and old predictions are not saved.
- Export/import main-plan JSON moves inputs between browsers/devices. Import
  replaces the editor and preview; review results and explicitly Save afterward.
- What-If: the simple allowance form remains. Expand Supplier quotation terms
  only for declared rates, units, charge scope, validity and price terms. Core
  rate replacement is supported within existing rules; Corporate bundled core
  changes remain blocked pending package requotation.
- Reports: a line-by-line pricing-scope table distinguishes reference assumptions,
  planner allowances and supplied terms. Explicit quote escalation is a total
  declared uplift, not an annual inflation forecast. Unknown terms block results.
- No calibrated future-price forecast or independent quotation verification has
  been added. Existing numerical rules, model weights and datasets are unchanged.
- Local browser storage is origin-specific and not encrypted. It is not a shared
  database or production access-control system; export a backup on a private device.

## Visible Model Evidence update

Open **Reports & explainability → Model Evidence Lab**. Its five buttons separate
live inference, training evaluation, learning curves, error analysis and robustness.
The latter three read checksum-pinned archived reports through local read-only
API endpoints; they do not retrain anything. Charts can be opened full-size.
Adverse-shock margin-risk recall is only 37.29%: this limitation is intentionally
visible. Health/costs remain accounting rules, not learned predictions.
The original three workspace pages and preview/confirm behavior are preserved.
If upgrading an older extraction, use a new folder and stop its old server first;
restart this copy's launcher and refresh Chrome. The previous ZIP is unchanged.

## Fastest Windows setup

**One entry point:** after extracting, double-click `START_PLANOVISION.cmd`.
It runs first-time setup when needed, then launches the existing dashboard in your
browser. Python 3.12 64-bit must be installed; initial dependency installation
requires internet. Keep the server window open. The steps below are the manual
alternative, not extra required steps.

1. Extract the ZIP completely. Do not run files from inside the ZIP viewer.
2. Open the extracted `PlanoVision_Component4` folder in VS Code (File > Open Folder).
3. Install Python 3.12 **64-bit** if needed. Enable the Windows Python launcher.
4. Double-click `Setup_Windows.cmd`. It creates this folder's `.venv`, installs
   pinned dependencies and verifies the package. Internet is needed initially.
5. Double-click `Run_Financial_Dashboard.cmd`. It starts the Python backend and
   opens Chrome/default browser at http://127.0.0.1:8765.
6. Keep the server terminal open. Closing it causes connection refused. Ctrl+C
   stops the server. This is a local app, not a public hosted service.

No Node.js is needed to run the included built frontend. No GPU, API key, login,
cloud service, live vendor lookup or model retraining is required.

## VS Code terminal alternative

Open PowerShell in the extracted project root:

```powershell
py -3.12 -m venv .venv
& '.\.venv\Scripts\python.exe' -m pip install -r requirements.txt
& '.\.venv\Scripts\python.exe' scripts/research_pipeline/verify_portable_package.py --http
& '.\.venv\Scripts\python.exe' scripts/research_pipeline/launch_financial_dashboard.py
```

Activation or an execution-policy change is not required. Select
`.venv\Scripts\python.exe` as the VS Code Python interpreter. Python and Python
Debugger extensions are recommended. F5 provides the backend debug configuration.
The `.vscode` tasks also provide Run dashboard and Verify portable package.

If port 8765 is occupied, close the earlier PlanoVision server or use:

```powershell
& '.\.venv\Scripts\python.exe' scripts/research_pipeline/launch_financial_dashboard.py --port 8766
```

That command opens the matching browser URL. The Vite development proxy below
expects the default backend port 8765.

## Editing the React frontend

Node.js 22.12+ (or another runtime compatible with the included Vite version) and
npm are needed only for frontend development. In a VS Code terminal:

```powershell
npm.cmd ci --prefix frontend
npm.cmd test --prefix frontend
npm.cmd run build --prefix frontend
```

Refresh the browser after rebuilding. Refresh resets unsaved main/draft plans;
download their reports/JSON first. For hot reload, run the Python backend on 8765
and, in a second terminal, `npm.cmd run dev --prefix frontend`; open the printed
Vite URL (normally port 5173). The backend still must be running.

## Clear three-page demonstration

- Financial planner: Wedding, 150 guests, 5 hours, venue 20×25 m, spending cap
  LKR 2,000,000, client payment LKR 2,500,000, minimum margin 15%.
- Click Use original plan for client changes.
- What-If: enter Fireworks and LKR 500,000, then Preview addition. Main plan stays
  unchanged. Estimated cost increases from LKR 1,570,450.20 to LKR 2,070,450.20.
- Reports: current native budget-risk score is approximately 0.00239→0.69339;
  native margin-risk score approximately 0.00307→0.35898. Inspect native TreeSHAP,
  model hashes and the separate model-evaluation panel.
- Discard preview before trying a different expense, so changes do not accumulate.
- No extra expense gives rule health 100/green; one LKR 500,000 expense gives
  87.8/yellow; one LKR 800,000 expense gives 34.5/red. Health is not an ML output.
- Confirm changes to main plan is an explicit browser-session update, not a
  supplier booking/payment or persistent database save.
- Generate explainable report exports computed narrative/native SHAP. No LLM is
  connected. Stage stays 4×6 m in the background; venue inputs are width/length.

`Run_Trained_Expense_Model_Check.cmd` prints actual native before/after predictions
without the browser. Optional argument: `--amount 800000`.

## What this ZIP contains

- React/TypeScript source, package lock, tests and production `frontend/dist`.
- Python financial engine, loopback backend, native XGBoost + TreeSHAP inference.
- Current v3.1 models, supporting v3.0/v2 artifacts and required numerical/evidence
  source files with their original integrity checks preserved.
- The current 3,600-row LKR synthetic training table with ledger/provenance and
  family split records, plus required historical v2 artifact dependencies.
- Existing model metrics, error audit, learning curves and frozen robustness
  reports, including limitations and source hashes.
- A selected portable Python test suite. It is not the entire historical workspace
  or every one of its 434 tests.

Large original v1 hybrid release archives, all raw downloads and legacy
Prophet/GAT experiment environments are not included. This archive runs the
current financial dashboard; it does not claim those older models are connected.
No `.venv`, `node_modules`, credentials, caches or machine-specific Python binary
is shipped. Setup installs dependencies locally.

Some historical protocols reference hashes of archival files not shipped here.
Their protocols remain unchanged as records. Use `Verify_Package.cmd` for this
portable subset, not historical full-release audit scripts expecting those archives.
Training sources retained for provenance are not instructions to refit existing runs.

## Verification

Run `Verify_Package.cmd` or:

```powershell
& '.\.venv\Scripts\python.exe' scripts/research_pipeline/verify_portable_package.py --http
& '.\.venv\Scripts\python.exe' -m unittest discover -s tests -v
```

The verifier checks package hashes, actual model loading, expense add/remove,
spatial blocking and optionally local backend/static frontend HTTP responses.
No fitting occurs. After intentionally editing source, the original package
manifest can correctly report a content change. Frozen numerical-source/model
gates remain in force; do not bypass them to change scientific assumptions.

## Scientific boundaries — retain these for viva

The trained targets are synthetic Budget Overrun and Profit Margin Risk, not
validated real-event probabilities. Costs/profit/capacity/health/recommendations
remain financial rules. Existing test accuracy is 95.56% budget / 93.19% margin
on a previously inspected synthetic holdout, not real-world accuracy. Simpler
financial rules are competitive. Health is an experimental planning indicator.

The frozen robustness audit found weak margin-risk detection when costs rise and
receipts fall together (37.29% risk recall on its targeted hypothetical grid),
and withheld 45/180 out-of-support planning cases. These results are included,
not hidden. Public prices plus assumed rates/taxes/shocks are not confirmed vendor
quotations. No guaranteed profitability or institutional/domain approval is claimed.

Read `reports/robustness/v3_1_frozen_robustness_20261016/README.md` and
`reports/diagnostics/v3_1_steps1_2_20261016/README.md` for the complete evidence.
