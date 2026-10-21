# PlanoVision — Component 04

Spatial-Financial Intelligence and Budget Optimization.

This repository contains the frontend, Python backend, financial/model source code, experiment scripts, configuration and tests. It is a source-only distribution.

## Layout

- `frontend/`: React, TypeScript and Vite UI.
- `backend/`: Python API entry point and dependency entry file.
- `component4/`: calculations, saved-model inference, explanations, forecasting and SQLite persistence.
- `api/contracts/`: integration schemas and types.
- `config/`: versioned algorithm, simulation and runtime configuration.
- `scripts/dev/`: development launchers.
- `scripts/model_experiments/`: model training and evaluation source.
- `scripts/research_pipeline/`: data preparation, verification and packaging source.
- `tests/` and `fixtures/`: test source and small test-only mock payloads.
- `packaging/`: portable-release launcher and configuration templates.

## What is excluded

Datasets, raw downloads, trained model weights, generated reports, executed notebooks, build output, local LLM runtime/weights, personal SQLite databases, virtual environments and node_modules are excluded from Git and the code-only ZIP.

The backend depends on frozen artifacts under `data/`, `outputs/` and selected `reports/` paths. To run the complete research application, restore those folders from the matching full application release, retaining their original relative paths. Git ignores these local artifacts. The source ZIP alone cannot perform trained-model inference.

No real client records or private database is included.

## Development setup

Use Python 3.12 x64 and Node.js 20.19+ (20.x), or Node.js 22.12+.

```powershell
npm install
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r backend/requirements.txt
```

After restoring matching research artifacts:

```powershell
npm run dev
```

Frontend: http://127.0.0.1:5173
Backend: http://127.0.0.1:8765

For separate terminals:

```powershell
npm run dev:backend
npm run dev:frontend
```

Run each command in its own terminal. Details: [VS Code setup](README_VSCODE_DEV.md).

## Checks

Frontend tests/build work after installing the locked frontend dependencies:

```powershell
npm test
npm run build
```

The complete backend/research suite additionally requires its frozen datasets, model files and evidence artifacts. Research and notebook builders can need extra tools stated in their scripts or matching release. Do not represent a source-only checkout as a fully provisioned research runtime.

## Research scope

The main risk classifiers train on synthetic LKR scenarios. Their recorded test results describe that simulator. Health scoring and accounting use rules. Real-event validity and live team-feed integration require further evaluation.

## Push this source to GitHub

Create an empty repository in your own GitHub account, then use its URL:

```powershell
git remote add origin <YOUR_GITHUB_REPOSITORY_URL>
git push -u origin master
```

Use the branch name reported by `git branch --show-current`. If an origin already exists, inspect `git remote -v` before changing it.

The code-only ZIP omits Git history. After extracting it into a new folder, use `git init`, `git add .` and `git commit -m "Initial PlanoVision source"` before adding your own remote.
