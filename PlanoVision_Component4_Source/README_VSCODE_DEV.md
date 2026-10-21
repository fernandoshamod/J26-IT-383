# PlanoVision in VS Code

Extract the ZIP completely, then open the inner **PlanoVision_Component4** folder in VS Code. This is the folder containing the root `package.json`, `frontend/` and `backend/`. Do not run commands from the ZIP viewer.

## Folder layout

```text
PlanoVision_Component4/
  package.json             root development commands
  backend/
    app.py                 Python API entry point
    requirements.txt       backend dependency entry point
  frontend/
    package.json           React/Vite commands
    src/                   editable UI source
  component4/              existing verified financial/model engine
  config/                  frozen and runtime configurations
  data/, outputs/          required model data and saved model artifacts
  runtime/planner.sqlite3  personal database, created at runtime, never shipped
```

The shared engine/model folders deliberately retain their original locations so their checksum-verified relative paths do not break. The backend remains Python; `npm run dev` starts it alongside Vite, it does not convert the models into JavaScript or train them.

## First setup on Windows

Use Python 3.12 x64 and a Node.js version supported by the included Vite 7 package. Internet is required for the first dependency install.

In the VS Code terminal at the project root:

```powershell
npm install
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r backend/requirements.txt
npm run dev
```

`npm install` installs the frontend dependencies through the root setup script. If they already exist, it keeps them. To deliberately reinstall from the frontend lockfile, run `npm ci --prefix frontend`.

The development launcher first looks for `.venv`, then `backend/.venv`, then the existing workspace research environment. No Python activation is needed for `npm run dev`. If this extracted folder already has a working `.venv` from `Setup_Windows.cmd`, do not recreate it. `Setup_Windows.cmd` remains a valid alternative for first Python setup.

If `py -3.12` reports no suitable runtime, the setup stopped before creating `.venv`. Check `py -0p`. Use the full path to an existing Python 3.12 x64 executable (`& 'C:\path\to\python.exe' -m venv .venv`) or install Python 3.12 x64 first; do not continue to pip until `.venv\Scripts\python.exe` exists. A different registered Python version is not proof that 3.12 is absent from the machine.

Open **http://127.0.0.1:5173**. API: **http://127.0.0.1:8765**. Keep the terminal open. Ctrl+C stops this command's child processes. Stop older dashboard/API terminals first; the launcher refuses occupied ports and does not kill unrelated processes.

## Two terminals, if preferred

Terminal 1 at project root:

```powershell
npm run dev:backend
```

Terminal 2 at project root:

```powershell
npm run dev:frontend
```

Alternatively run `npm run dev` inside `frontend/`, while starting Python from the root with `.\.venv\Scripts\python.exe backend/app.py`.

Vite reloads frontend changes. Restart the backend after changing Python files. The proxy forwards `/api` to Python and rewrites the Host header to preserve the backend's loopback restrictions. Backend CRUD and models remain real server requests.

## Data and local AI

- Saved backend events and reservations use `runtime/planner.sqlite3` in this project folder. The dev server and built app share that database when they use this folder. Back it up with the app stopped and keep it when moving to another extraction.
- Browser-only main-plan backups and legacy bookings are origin-specific. Port 5173 has different browser storage from 8765. Export browser backups from the old address before switching. Backend records are separate from browser backups.
- Optional local-AI drafts require the installed local Ollama/Qwen model. Run `Setup_Local_AI.cmd` once if using an extracted release on another machine. The Qwen weights are not bundled. Core calculations and primary models do not require an AI API key.
- No datasets or model weights regenerate when the app starts.

## Connected financial CRUD

Saved backend events now load automatically on Financial planner, including after a browser reload. Event setup still starts blank unless explicitly restored. Select and **Load saved event** before editing it. The selected/loaded identity is retained while visiting What-If and Reports, and cleared by New blank event or browser-file import. Refreshing the list does not silently advance a loaded event's revision: concurrent edits still require explicit reload.

What-If additions/removals are previews. Confirm changes updates the main plan and browser backup only. **Save confirmed plan to backend** returns to Financial planner; use **Update selected backend event** to persist to the same SQLite record, or **Save new event** for a separate record. No preview or report-generation action creates a database write. Calendar reservations are explicit and separate; deleting a financial event does not cancel a booking. Calendar client details/date moves/cancellation/restoration use their own revision-checked backend endpoints.

## Reviewed historical price values (21 October 2026)

Reports → Future ingredient-price estimate now distinguishes original source flags from unresolved model-price values. The separate pinned review matches 1,900 direct measurements from 181 retained PDFs and reconciles the same 563 monthly values. No numeric observations, raw flags or trained weights changed. A named January 2024 week-4 publisher title conflict is retained and resolved using its explicit current-price/comparison columns. Monetary ingredient conversion is permitted only when that series' complete model-value review is resolved; missing/tampered/partial evidence fails closed. The existing three-month horizon, index-versus-LKR rules and no-automatic-event-budget-application policy remain unchanged. See reports/DATA_QUALITY_FIX_20261021.md. Reproducing the source PDF review needs the full research checkout; normal app serving needs no additional packages.

## Verification commands

```powershell
npm run test:dev
npm test
npm run build
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
```

`npm run build` creates `frontend/dist`. The original `START_PLANOVISION.cmd` still runs the built app without a Vite development server. Use `Verify_Package.cmd` in a release extraction before editing source files. Its manifest checks deliberately detect edits.

This is a loopback-only research prototype. SQLite records have no authentication or encryption. Synthetic model scores do not establish real-event accuracy. Do not expose the development ports publicly.
