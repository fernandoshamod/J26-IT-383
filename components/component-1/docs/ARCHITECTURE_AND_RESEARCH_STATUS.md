# Component 1 GitHub readiness audit — 2026-10-21

## Decision

SOURCE PREPARATION COMPLETE; GROUP INTEGRATION PARTIAL; PUBLIC PUBLICATION NOT APPROVED BY THIS AUDIT. The staging copy preserves maintained runtime and additional original research sources. It is not a declaration that every proposed research feature works or that the target laptop has passed.

The original workspace and verified laptop package are read-only sources. The public group repository is https://github.com/fernandoshamod/J26-IT-383. No git add, commit, push, merge, branch mutation or PR was executed. Repository compatibility is assessed against a read-only GitHub API snapshot, not a local merged checkout.

## Source of truth and version differences

The current desktop frontend is PP1_READINESS_20261022/PP1_FRONTEND_V1. Its launcher uses PP1_EXECUTABLE_V1/research.py, companion, Scene compiler and Vite KNOX configuration on ports 5174/8765/8768/8770. The frozen backend factory reuses this research engine through integrated_api. Historical CUDA/four-model verification must not be mistaken for a portable CPU startup requirement.

The selected application is the existing CPU portable copy: 403 manifest entries, of which 388 match corresponding original files, seven are deliberate portability differences, three are portable-only additions and five are root runtime/verifier/requirements files. Differences: frontend/vite.config.ts; scene_compiler_service.py; frozen runtime_check.py; integrated_api.py; model_registry.py; perception.py; upload_inference.py. Additions: portable Playwright config/spec and EAG portable_demo.py. These patches enable package-relative configuration, lazy model loading and CPU startup. No new algorithm changes were made during staging.

The portable package is NOT the entirety of Component 1. Original model training/evaluation, strong baseline, review-selection, function-usability, recovery and diagnosis sources are separately included under research/workspace. Older Stage-E kernels remain in app/runtime because current adapters import them; their original prototype scope is retained. Curated presentation reports and notebook source snapshots are evidence references, not the newest runtime authority. The newly attempted five-class U-Net was not promoted over retained four-class V3.

Each copied file has an exact source SHA-256 in SOURCE_OF_TRUTH_MANIFEST.json; public provenance uses workspace-relative origins. Eight notebooks have explicitly recorded output/metadata stripping. The staged application manifest is regenerated after removal of unused third-party dataset utilities and obsolete desktop frontend launch/test artifacts. Neither original manifest is edited.

## A–F architecture and eight research logics

A / L1 — AI venue understanding: IMPLEMENTED BUT PARTIALLY VERIFIED. U-Net V3 predicts room_region/wall/door/window; Opening YOLO V3 predicts door/window. Genuine training/evaluation and inference code exists. Real-image predictions are candidates in pixel space, not approved metre geometry. Event-object twelve-class YOLO is EXPERIMENTAL PROOF OF CONCEPT using synthetic diagrams; chair pilot is experimental and disabled by default. Remote Colab execution and staged fresh inference are NOT VERIFIED.

B / L2 — Spatial Digital Twin: IMPLEMENTED BUT PARTIALLY VERIFIED. Source hashes, candidate decisions, source-image editor, scale controls, reviewed polygons, calibrated transform and backend admission gates exist. Calibration needs a known real length and consistent controls; model output alone does not establish metres. Current reviewed-object contract admits supported fixed classes; movable/uncertain registration is not a complete stock-state engine. Absence of detected candidates does not establish an empty real hall. Source-review UI confirmation is separate from metric Twin registration. Real-source positive registration-to-layout remains incomplete.

C / L3 — Requirement-to-scene intelligence: IMPLEMENTED AND VERIFIED FOR CONTROLLED SUBSET. Compiler profiles include four event families, demand/allocation oracle, evidence/geometry checks and bridge. Only Wedding is coupled to the retained optimizer: multiples of eight, 8–240 guests. Date/time are stored context; comprehensive activity, stock, indoor/outdoor/hybrid and environmental semantics are only partially compiled. Client/planner declaration strings do not prove authenticated authority.

C/F / L4 — Historical S-GCN preference learning: PROPOSED/FUTURE WORK. No qualified genuine preference dataset, trained S-GCN or validated learned policy. UI alternative preference is selection among candidates, not learned S-GCN weights.

C/F / L5 — Weather/safety: IMPLEMENTED BUT PARTIALLY VERIFIED FOR GEOMETRIC CONSTRAINTS; WEATHER PROPOSED. Containment, selected obstacle/clearance and boundary checks run. No validated weather consequence model, live weather-aware repair, complete evacuation/accessibility or legal safety certification. Outdoor/hybrid recognition scope is not an equivalent optimized event workflow.

D / L6 — NSGA-II: IMPLEMENTED AND VERIFIED FOR CONTROLLED SUBSET. Actual local pymoo search with multi-objective scores, hard feasibility tests, Pareto candidates, separate compiler allocation oracle and controlled fixtures. Retain original objectives and constraints; do not replace search with mock alternatives. Input scene/dimensions and event support remain bounded.

E / L7 — EAG-APR: IMPLEMENTED AND VERIFIED FOR CONTROLLED SUBSET. Full source preserves evidence-linked dependency graph, certificate hashes, change classification, authority/locks, selective permission-aware repair, relocation objective, recheck/refusal, fallback and history artifacts. Simulated approval, singleton repair and negative/admission tests exist. General multi-group repair, guest additions and movable stock transitions remain partial/unsupported. Basic frontend revision is not the complete standalone EAG experiment lifecycle. Scene sidecar outputs are not canonical frozen-backend approval/adaptation history.

F / L8 — XAI/history: IMPLEMENTED BUT PARTIALLY VERIFIED. Numerical objective trade-offs, feasibility/refusal reasons, relocation/change records and experiment certificates exist. Counterfactual utility and user-comprehension/real-world utility are future work, not established results. SQLite CRUD is local event-draft persistence, not group-wide approval storage.

Historical/superseded: old broad CUDA/hash verifier for portable startup, Python 2 third-party dataset scripts, machine-specific launcher variants, obsolete frontend prepare_lab path assumptions and failed five-class attempt. Retained historical research code is labelled reference, not freshly reproduced.

## Scientific evidence and boundaries

Original EAG controlled study: 52 scenario instances, 156 method records; zero false acceptances/refusals under those controlled labels. Strong conventional baseline B4 matched 72/72 cases; B5 review-selection baseline matched 128/128. Function usability recorded 12/12; recovery recorded 36/36 with 274 witnesses. These are existing experiment evidence, not new staging experiments. The null/equality findings are retained: no algorithmic superiority or originality has been established by these comparisons. A proposed contribution slide may state the research design, but cannot change that evidence.

## Concrete blockers identified in source

1. Controlled Layout workspace fixture registration JSONs contain original desktop source paths outside the package; source admission can reject them. The previously verified three browser flows did not cover this positive registration route. Obsolete prepare_lab.py does not rebuild valid portable fixtures.
2. KNOX scene source/analysis defaults are private-assets paths, while compiler common.ROOT is rebound to run state. The source gate does not admit those defaults. The image URL /knox-demo/KNOX_HALL.jpg also has no committed public asset. Merely transferring weights/images does not establish this route. Ravenswood has no equivalent verified positive plan-to-workspace adapter.
3. Fresh inference writes an analysis under runtime-state then evaluates out.relative_to(H), where H is the integration source directory. This can raise ValueError. Fresh inference was not exercised in the CPU package; no successful end-to-end real-image claim is made.
4. No verified app-to-Colab service bridge, shared group IDs/auth/gateway, C1-to-C3 converter or cross-component approval transaction exists.
5. Target i3/8 GB laptop installation, memory and presentation paths remain NOT VERIFIED. Repository/public license and third-party obligations need team review.

## Next engineering work, not silently performed

Create new package-local controlled registration receipts under allowed state, verify their hashes/admission and add the missing positive Layout workspace browser flow. Correct KNOX source allowlist/image serving and analysis output-root logic in a separately reviewed change, then test with privately installed assets. Implement versioned common-ID/time/resource/geometry adapters only after group contract agreement. Reproduce independent research benchmarks with their required raw experiment inputs before calling the full research directory standalone reproducible.
