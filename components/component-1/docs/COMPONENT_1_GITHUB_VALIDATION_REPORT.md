# Component 1 GitHub validation report — 2026-10-21

## Verdict and test environment

SOURCE REVIEW SNAPSHOT ASSEMBLED. CONTROLLED APP SUBSET PASSES. FULL REAL-VENUE AND GROUP INTEGRATION NOT COMPLETE. Target i3/8 GB laptop NOT TESTED. No commit, push, merge or PR performed.

Validation ran on this development Windows PC in a disposable copy under validation-state/app, outside C:\My Research Component. Frontend npm ci was a fresh install into that disposable copy, using a separate npm cache. Python checks and services reused the existing portable Python 3.12 CPU interpreter/dependencies read-only; this is NOT a fresh Python install of the staged source. External Node 22 executable was reused. All runtime source and outputs used by services were in the external validation copy; no original source imports were needed for those tested flows. No model weights were loaded. A future clean environment/laptop setup is still required.

## Source, dependency and static checks

- Source-to-staging copied/transformed files: 463; SHA-256 checks PASS with zero source or staged mismatches. Exact copies retain bytes; notebook transforms have separate source/output hashes.
- Original portable source snapshot: 417 files unchanged; original 403-entry manifest still matches. Prior transfer ZIP SHA-256 remains 5b59b6b82aa0d5c3ec81e622bb586fdc93e7f88ce4ae6eb9100c4a0cd99a4855.
- Original-versus-portable comparison: 388 identical, seven portability patches, three portable-only files, five portable-root entries. Individual relationships/hashes in outer provenance manifest.
- Python AST: 402 staged files PASS. Active service imports exercised by startup PASS. Training/evaluation/reference scripts were syntax-checked only; not imported/run to avoid training or historical side effects.
- PowerShell parser: setup/start/stop, 3/3 PASS. Actual setup.ps1 clean Python environment creation NOT VERIFIED.
- CPU dependency pins: all 16 checked distributions match the reused CPU environment, accepting +cpu local wheel suffix. This is not a fresh resolver test. Model/dataset dependencies remain external.
- package.json and package-lock.json root dependencies agree. Fresh npm ci PASS; tsc --noEmit and Vite production build PASS. Existing build warning remains: JS chunk roughly 515.6 kB (>500 kB); no build failure.
- Staged application source manifest regenerates for allowed exclusions; verify_portable.py PASS against that snapshot. Root setup regenerates a local manifest, so retain provenance/source control as the immutable origin record rather than treating a freshly regenerated manifest as independent authenticity proof.
- Proposed JSON schemas: two positive examples and four invalid-status/unknown-field negative examples PASS using AJV 2020. These are schema-shape checks, not geometry/time/auth semantic enforcement or implemented adapters.

## Fresh controlled runtime checks

- portable-integrity-imports: PASS, 1.476 s (exit 0).
- launcher-start: PASS, 5.173 s (exit 0).
- browser-three-flows: PASS, 7.929 s (exit 0).
- launcher-stop: PASS, 0.199 s (exit 0).
- eag-controlled-lifecycle: PASS, 5.158 s (exit 0).
- launcher-restart: PASS, 4.287 s (exit 0).
- launcher-stop-restart: PASS, 0.173 s (exit 0).

Four-service health returned HTTP 200 (backend, SQLite companion, scene and frontend). UI test 1 creates, lists, updates and permanently deletes a real local SQLite draft. UI test 2 runs controlled partially-furnished Wedding compiler and renders actual alternatives, with independent demand/allocation oracle true; emitted RESULT.json records 1200 optimizer evaluations. UI test 3 confirms an empty Twin Editor remains pending without inventing registration. Three tests passed; this is not a positive image-analysis/metric-Twin/Layout-workspace test.

Standalone EAG controlled lifecycle: initial search 1200 evaluations, simulated approval 0, eligible SELECTIVE_SINGLETON repair 1680, eight candidates, fallback false. It does not authenticate a planner or qualify a real venue. Additional fresh governance checks: missing_metric_verification -> pending with 0 search evaluations; unauthorized_stage_relocation -> refused with 0; multiple_dependent_changes -> eligible FULL_RECOMPUTATION fallback with 1200. No search/repair mechanism was simplified for this test.

Audit ports were 15183/18785/18788/18789. Initial stop and restarted stop both used launcher-owned identity checks and completed; no existing desktop listener was terminated. Generated service state/logs/DBs and browser artifacts remain outside the repository overlay.

## Repository and privacy checks

The read-only GitHub recursive tree at C3 revision b4676b7a16664ab4dd4d584157a279d5fc620832 is not truncated: 565 existing C3 paths checked. Proposed components/component-1 prefix has no exact file-path collision with that tree or audited main README. API-prefix conflicts and schema/ownership differences still require an adapter/gateway. Path isolation is not successful runtime integration or an actual Git merge test. No C3 code is copied into the candidate prefix.

Actual candidate-byte privacy policy scan PASS; no excluded assets or token-pattern findings. Actual git check-ignore, git index privacy scan, merge conflict simulation and branch creation NOT VERIFIED (Git unavailable; no mutation authorized). Main/branch state may change after snapshot; re-fetch before any later operation.

## NOT VERIFIED / remaining blockers

- Clean Python dependency installation and setup.ps1 on this staging tree; target i3/8 GB laptop install, RAM/performance and full rehearsal.
- Positive controlled lab registration/Layout workspace route: existing registration fixture paths still point at original desktop runtime files. Do not use source-only hashes as a positive receipt.
- KNOX scene image/source-root admission and missing /knox-demo serving; Ravenswood positive real-source layout adapter; fresh image-analysis MANIFEST output relocation defect. These are documented source defects, not passed tests.
- Fresh inference with privately installed weights; remote Colab execution or application bridge; independent real-venue measurements, reviewed metric geometry and actual planner approval.
- Historical full research reproduction/large experiment inputs; scientific superiority or algorithmic originality; learned S-GCN, validated weather consequences and general multi-group/stock transitions.
- C3 runtime integration, shared IDs/units/time conversion, authenticated group authority, cross-service stale-version/rollback handling, and Components 2/4 contracts.
- Actual git-stage checks and team/public licensing approval.

## Reproduction evidence

Private audit tools: tools/assemble.py, write_docs.py, write_contracts.py, build_validation.py, validate_runtime.py, validate_governance.py, validate_static.py and validate_compatibility.py. Read raw logs/JSON under validation-state (not proposed for commit). Frontend acceptance test and proposed contract validator are included in the candidate source. No evidence from these new tests upgrades historical experiments to newly reproduced results.
