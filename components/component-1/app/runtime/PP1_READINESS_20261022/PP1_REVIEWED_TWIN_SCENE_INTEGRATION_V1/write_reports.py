"""Write delivery reports from executed evidence, never manufacture runtime results."""
from pathlib import Path
import json
H=Path(__file__).resolve().parent
def load(name):return json.loads((H/name).read_text(encoding='utf-8'))
def write(name,text):
 with (H/name).open('x',encoding='utf-8') as f:f.write(text)
a=load('FUNCTIONAL_ACCEPTANCE.json');p=load('PATH_A/ANALYSIS.json');life=load('CONTROLLED_003/LIFECYCLE_RESULT.json')
write('README.md','''# Reviewed HTTP Twin → Event Scene → NSGA-II / EAG integration V1

**PASS for the declared controlled registered-HTTP-Twin scope.** This delivery closes the previously disconnected controlled HTTP-Twin-to-Scene inlet. It does not admit genuine external venues to the frozen controlled-only Scene/EAG engines.

The positive test registered an existing all-fixed controlled Scene fixture through the unchanged HTTP review gate, read it back, converted its metric geometry and reviewed identities through the new adapter, then ran the existing compiler, actual local NSGA-II and seven-branch EAG lifecycle. The original worker's synthetic Scene constructor was replaced at its inlet; its optimizer/compiler/verification algorithms were not replaced.

- Actual new drawing/model path: 65 structural + 7 opening candidates; **EXPECTED_PENDING**, no scale/stock fabrication and zero optimizer evaluations.
- Controlled registered-Twin path: seven expected branches, three actual searches, **4080 evaluations**, actual candidate polygons, independent checks, XAI and SQLite readback.
- Unchanged existing regression: **49/49 PASS**. New admission checks: **13** passing or correctly refusing invalid inputs. These are different coverage levels, not 69 independent experiments.
- Genuine reviewed venue: **NOT_EXECUTED**. No genuine measured/reviewed evidence was supplied; original external Scene/EAG execution restrictions remain.
- No frontend, frozen source, model, dataset or prior evidence edits; no retraining or downloads.

Start with [RUNBOOK.md](RUNBOOK.md), [FUNCTIONAL_ACCEPTANCE.md](FUNCTIONAL_ACCEPTANCE.md), [INTERFACE_MAPPING.md](INTERFACE_MAPPING.md) and [LIMITATIONS_AND_NEXT_STEP.md](LIMITATIONS_AND_NEXT_STEP.md). Machine authority: [FUNCTIONAL_ACCEPTANCE.json](FUNCTIONAL_ACCEPTANCE.json). Original architecture, historical S-GCN, weather, safety and feedback objectives remain unchanged and unfinished where previously documented.
''')
rows='\n'.join(f"- {b['branch']}: {b['verdict']}; {b['operation']}; {b['optimizer_evaluations']} evaluations; {b['candidate_count']} candidates / {b['material_menu_count']} material choices." for b in life['branches'])
write('FUNCTIONAL_ACCEPTANCE.md',f'''# Functional acceptance — actual executed evidence

**{a['status']}**

## Path A: drawing → actual models → pending review

Analysis ID `{p['analysis_id']}`. Original drawing is the same previously tested CubiCasa native raster 1848/F1_scaled.png. Original upload bytes/hash, decoded page/hash and checkpoint loads are preserved in `PATH_A/UPLOAD.json`, `PATH_A/ANALYSIS.json` and its model-report original_document. Source metadata and model outputs refer explicitly to the decoded page coordinate frame, not metres or an independently verified physical venue.

Actual V3 U-Net and opening YOLO calls returned **65 + 7** candidates. The U-Net input/logits are [1,3,512,512] / [1,4,512,512]. V4 chair is default off; controlled V2 event12 model is not inferred on this source. Model SHA256 values remain those in the previous delivery and are included in the actual model report.

POST /twins with the pending template returned HTTP422. An attempted unregistered optimization returned HTTP200 logical non-success, no candidates and zero evaluations; the exact denial and numerical explanation were retrieved from SQLite using GET /runs. `PATH_A/RESULT.json` records the requests/results and zero optimizer/Scene calls. Model candidates have null metric_geometry, null scale and no planner confirmation. Correct pending/refusal is not failed detection or a successfully reviewed venue.

## Path B: actual registered HTTP Twin → new adapter → existing Scene/EAG

HTTP registration used the existing Scene fixture generator, not synthetic replacement model predictions: 32×24m, 80 wedding guests, one fixed/protected stage and two fixed/protected buffet counters. Its generator controls are explicitly simulated 0.1m/px. All three existing objects remain individually identified and locked. Only stage and first buffet satisfy active demand; second buffet is retained as an obstacle, not double-counted supply. Compiler demand is ten tables, eighty chairs, one stage and one buffet. Ninety seating objects are new event equipment. No stock was inferred from the plan.

Registration/readback: `HTTP/REGISTER_REQUEST.json`, `TWIN_RECEIPT.json`, `TWIN_READBACK.json`, `research.sqlite3`. `CONTROLLED_003/HTTP_ADAPTER/MAPPING.json`, `LIVE_BINDING.json` and `SCENE_REQUEST.json` show the deterministic conversion and full original provenance. The API gate and evidence checks were rerun at admission, each EAG branch and evidence-fingerprint boundaries. Independent scalar mapping replays controls/origin, boundary and every fixed object; tolerance 1e-8m only handles floating-point arithmetic.

{rows}

Total **4080 evaluations / three real searches**, lifecycle wall time **{life['elapsed_seconds']:.3f}s**, including verification/plots. Reuse branches return the same checked pool and are not independent searches. Eight candidates were returned for each successful branch; the existing material-diversity policy offered three. Global Pareto optimality, certified accessibility/egress and transport-path feasibility are not claimed.

The original worker code is executed with one adapter-install insertion and output binding; its SQLite audit permits explicitly read-only URI connections to the registered input DB. `WORKER_BINDING.json` documents this integration. Original optimizer, compiler, authority and independent checker files are unchanged. This positive run cannot silently fall back to the original Scene constructor: scenarios.initial is replaced by the new adapter's registered-Twin inlet. Fixed HTTP stock is intentionally stricter than the old fixture's movable surplus item.

Every branch has raw INPUT/SPEC/GRAPH/IMPACT/RESULT, original EAG database, adapter admission replay and original independent verification. Full searches additionally save actual frozen engine input/output and scene.sqlite3. Final independent replay reopens all seven databases, recomputes envelope/numerical XAI and each returned geometry/function/lock result, then writes seven exact-readback records to `ADAPTER_RESULTS.sqlite3`. See `INDEPENDENT_FINAL_REPLAY.json`.

## Negative, compatibility and preservation checks

`ADMISSION_TESTS_002/RESULTS.json`: 13 cases including independent poisoned-geometry oracle, stock allocation, fresh receipt, metric/lock/provenance tampering, stale registration, tampered evidence, revoked adapter authority, unauthorized extra stock, uncertain objects, missing measurement, and an actual EAG singleton permission denial with zero evaluations and saved refusal. The stale-record probe uses an isolated DB containing only the newer version; the old requested row is missing, so the exact observed rejection is REVIEWED_TWIN_NOT_REGISTERED. Existing regression also covers stale current-version and revoked HTTP layout approvals.

`outputs/REGRESSION_49_001/TEST_RESULTS.json`: **49/49 PASS**, original source byte-for-byte unchanged. These cover original permissions, poisoned geometry/XAI, guest handling, versions, revoked approvals and persisted results; additional evaluations in that suite are separate from the lifecycle's 4080.

`TCP_PROOF/RESULT.json`: actual localhost TCP POST /twins and GET version readback of the same registered Twin plus exact OpenAPI match; test server stopped. Actual inference was through FastAPI TestClient/ASGI in this task; TCP inference compatibility was previously tested in Step1. Frozen frontend AnalysisReceipt validation passed using its installed AJV and OpenAPI schema; browser/React journey NOT_EXECUTED. No Scene/EAG route was invented.

`PRESERVATION_AFTER.json`: previous integration delivery 458/458, frozen backend 292/292, frozen frontend 51/51 and task-start snapshot 784/784 match. Sets overlap. This is not a new bytewise dataset audit. Prior model and dataset hash evidence remains preserved in the previous frozen delivery.

## Failures retained and corrected

`logs/LIFECYCLE_001.*`: exact polygon equality rejected harmless binary scale-rounding differences. Corrected to a declared 1e-8m Hausdorff plus area tolerance; no gate disabled. `CONTROLLED_001` retained.

`logs/LIFECYCLE_002.*`: adapter installation preceded original output-root relocation; existing writer rejected the path. Corrected output binding before conversion. `CONTROLLED_002` retained.

`logs/ADMISSION_001.*`: independent mapping check allowed one duplicated closing vertex to conceal a changed vertex. Poisoned input exposed this false PASS. Corrected to bijective vertex matching; final ADMISSION_002 passed. Failed `ADMISSION_TESTS/FAILURE.json` is retained.

## Verdict

The missing controlled registered-HTTP-Twin → Scene/EAG bridge now works. Genuine external venue field validation remains **NOT_EXECUTED**, and real-source Scene/EAG execution remains **unsupported by frozen contracts**. No originality, accuracy improvement, real consent or full research completion is claimed.
''')
write('INTERFACE_MAPPING.md','''# Exact interfaces and mapping policy

## Original interfaces connected

- Updated API factory: read-only `PP1_FINAL_MODEL_INTEGRATION_V1/integrated_api.py:create_app`; base `PP1_EXECUTABLE_V1/api.py:create_app`, POST /twins → Register/TwinReview → review_gate.reviewed_metric_twin → Store.register. GET /twins/{venue_id}/versions/{version} reuses original receipt schema.
- New `adapter.py:current` reads the actual registered DB read-only and replays the unchanged review_gate, hashes/evidence and current-version checks. A detached JSON receipt is insufficient.
- New `adapter.py:convert` emits existing `PP1_EVENT_SCENE_INTELLIGENCE_V1/models.py:Request`. Separate previously approved client/planner briefs, actions, policy and source-bound evidence are mandatory. Original client/planner evidence is checked before controlled conversion evidence is generated.
- Existing compiler.compile_scene and oracle.validate_spec consume the converted request. Existing EAG runtime.seal_packet supplies explicit simulated fixture context authority. It is separate from HTTP layout-approval IDs and is not authenticated human approval.
- `adapter.install` installs only the fixture inlet and admission checks around original repair.run/facts. Existing EAG chooses reuse, singleton, full fallback or refusal; optimizer_adapter.full/singleton and frozen initial/adaptive pymoo engines run unchanged.
- Existing independent.verify_candidate/verify_envelope and Scene oracle verify actual outputs. `independent_mapping.py` separately computes pixel-to-metre transforms without calling the adapter.

## Field preservation and refusals

- Source path/SHA/dimensions/domain come from the registered Twin, never from an invented event brief. The complete original candidate bundle, its hash, reviewed record/hash, source metadata and model provenance are retained in MAPPING/LIVE_BINDING.
- Calibration method, distinct measured controls, their evidence refs and origin remain intact in binding. Scene controls rename fields only. Metric boundary and footprints come from the HTTP metric Twin and are checked against scalar transforms. No axis flip, re-scaling or room-boundary inference is added.
- HTTP boundary is the single usable envelope. Fixed restricted_zone objects remain obstacles; no additional usable-region/subzone contract is inferred. Topological connectivity/egress is not certified. Unsupported geometry or semantics remain refusals of original gates.
- HTTP currently allows only fixed reviewed stage/buffet_counter/fixed_column/wall/restricted_zone objects, exactly one stage. All are mapped bijectively with identity/class/geometry, review approval and protection. Movable/uncertain HTTP records are rejected; they are never silently upgraded. Detected and experimental chair symbols are never stock. An explicit brief with extra observed inventory is rejected.
- Candidate references and per-object decision evidence are preserved in binding; Scene candidate_ref is a digest reference to the full HTTP review decision. No detection confidence becomes approval.
- Existing inventory quantities are one per registered object identity. Original Scene policy decides compatible explicit reuse versus retained obstacles, derives new supply separately and preserves action scopes. Loose seating regrouping and observed-stock relocation remain unsupported. Client/planner roles and original evidence/actions remain separate.
- HTTP source/venue/review versions and hashes are bound in MAPPING; Scene/EAG context version and simulated layout-authority/ref hash remain in every packet/certificate. A changed source, evidence, venue geometry, fixed protection or latest registered version requires re-admission. Pending review can pass only to the original refusal gate, never successful optimization.
- Detailed safety/physical truth/planner authentication/topological certification flags remain false. Original clearance hard limits and supported requirements are enforced by compiler/search/oracle. S-GCN, weather and feedback learning are not added.

## API and execution boundary

The HTTP API retains version1.1.0 and the Step1 optional AnalyzeUpdated fields. The new bridge is a versioned Python/CLI integration, not an invented HTTP endpoint. Existing frontend can still call the updated model API using the original response schema. Scene/EAG results retain their distinct research contract and SQLite history; they are not mislabeled as frozen /optimize response rows or HTTP /runs entries. No browser flow was changed.

External `real_source` conversion/execution is explicitly refused by this adapter until genuine compatible Scene authority/evidence and downstream admission contracts exist. The unchanged compiler, bridge and EAG authority have controlled-only guards; this delivery does not remove them. The tested positive is an external HTTP-interface Twin with controlled synthetic domain, not a genuine externally reviewed venue.

Admission is rechecked before/after each run and during the existing EAG freshness fingerprint checks. This local synchronous prototype does not provide a single atomic transaction spanning HTTP registration, filesystem evidence, adapter authority and EAG result databases. Raw computations must not be treated as a successful current admission after a freshness exception. Cross-process concurrent revocation is not newly claimed; the original HTTP regression retains its transactional approval tests.
''')
write('RUNBOOK.md','''# Commands and actual evidence

Run from `C:\\My Research Component` using the installed .venv. Preserve populated evidence directories; use a fresh output name. No installation, training or downloads are needed.

## Start the updated API, without editing original sources

```powershell
.venv\\Scripts\\python.exe -B PP1_READINESS_20261022/PP1_REVIEWED_TWIN_SCENE_INTEGRATION_V1/serve.py --db "C:\\My Research Component\\PP1_READINESS_20261022\\PP1_REVIEWED_TWIN_SCENE_INTEGRATION_V1\\outputs\\MY_API_001\\research.sqlite3" --port 8765
```

Open http://127.0.0.1:8765/docs. Stop an older local backend first; do not run the frozen frontend's old backend launcher simultaneously. A fresh DB has no registered Twin or approval: register supplied review data anew. No approval IDs can be transferred between databases. The new adapter needs the registered DB and its exact receipt, not an arbitrary JSON file.

## Repeat the actual controlled registered-Twin lifecycle

```powershell
.venv\\Scripts\\python.exe -B PP1_READINESS_20261022/PP1_REVIEWED_TWIN_SCENE_INTEGRATION_V1/run_stage.py lifecycle MY_LIFECYCLE_001 CONTROLLED_MY_001
```

This reuses the preserved `HTTP/TWIN_RECEIPT.json`, `HTTP/research.sqlite3` and `SCENE_BRIEF.json`, rereads current source/evidence, executes the NEW adapter, and runs seven original branches. It does not invoke the original synthetic Scene constructor. New authority evidence is explicitly simulated and written only to the fresh run directory. If these registered inputs change, admission must fail; do not edit hashes to force a pass.

Expected: three searches / 4080 evaluations. Open `CONTROLLED_MY_001/LIFECYCLE_RESULT.json`, `HTTP_ADAPTER/MAPPING.json`, all seven INPUT/RESULT/ADAPTER_ADMISSION_REPLAY/POST_READBACK_VERIFICATION files and `figures/SINGLETON_BEFORE_AFTER.png`, `DANCE_FULL_RECOMPUTATION.png`. The actual successful execution used `CONTROLLED_003` and `logs/LIFECYCLE_003.*`.

## Convert a controlled registered Twin without search

```powershell
.venv\\Scripts\\python.exe -B PP1_READINESS_20261022/PP1_REVIEWED_TWIN_SCENE_INTEGRATION_V1/scene_handoff.py --receipt PP1_READINESS_20261022/PP1_REVIEWED_TWIN_SCENE_INTEGRATION_V1/HTTP/TWIN_RECEIPT.json --db PP1_READINESS_20261022/PP1_REVIEWED_TWIN_SCENE_INTEGRATION_V1/HTTP/research.sqlite3 --brief PP1_READINESS_20261022/PP1_REVIEWED_TWIN_SCENE_INTEGRATION_V1/SCENE_BRIEF.json --out PP1_READINESS_20261022/PP1_REVIEWED_TWIN_SCENE_INTEGRATION_V1/HANDOFF_MY_001
```

Actually tested as HANDOFF_CLI_001, exit0. Inspect MAPPING.json and SCENE_REQUEST.json. This command creates no layout or approval and performs zero evaluations.

## Executed acceptance commands

```powershell
.venv\\Scripts\\python.exe -B PP1_READINESS_20261022/PP1_REVIEWED_TWIN_SCENE_INTEGRATION_V1/setup_delivery.py
.venv\\Scripts\\python.exe -B PP1_READINESS_20261022/PP1_REVIEWED_TWIN_SCENE_INTEGRATION_V1/prepare_scene_fixture.py
.venv\\Scripts\\python.exe -B PP1_READINESS_20261022/PP1_REVIEWED_TWIN_SCENE_INTEGRATION_V1/run_stage.py http_stage HTTP_001
.venv\\Scripts\\python.exe -B PP1_READINESS_20261022/PP1_REVIEWED_TWIN_SCENE_INTEGRATION_V1/run_stage.py lifecycle LIFECYCLE_003 CONTROLLED_003
.venv\\Scripts\\python.exe -B PP1_READINESS_20261022/PP1_REVIEWED_TWIN_SCENE_INTEGRATION_V1/run_stage.py regression REGRESSION_001
.venv\\Scripts\\python.exe -B PP1_READINESS_20261022/PP1_REVIEWED_TWIN_SCENE_INTEGRATION_V1/run_stage.py negative_checks ADMISSION_002 ADMISSION_TESTS_002
.venv\\Scripts\\python.exe -B PP1_READINESS_20261022/PP1_REVIEWED_TWIN_SCENE_INTEGRATION_V1/run_stage.py tcp_proof TCP_001
.venv\\Scripts\\python.exe -B PP1_READINESS_20261022/PP1_REVIEWED_TWIN_SCENE_INTEGRATION_V1/run_stage.py finalize FINALIZE_001
```

These populated stages deliberately do not overwrite outputs; do not replay setup/fixture/finalize or tests into their existing directories. Fresh lifecycle and handoff commands above are reproducible. Logs preserve exact child argv/cwd/exit/time; the original tests are unchanged. HTTP-stage logs include actual model inference. Setup and fixture were direct successful invocations, not retrospectively logged child processes.

Frontend compatibility was separately checked with existing Node/AJV:

```powershell
PP1_READINESS_20261022\\PP1_FRONTEND_V1\\tooling\\node-v22.23.3-win-x64\\node.exe PP1_READINESS_20261022/PP1_FINAL_MODEL_INTEGRATION_V1/check_frontend_contract.mjs PP1_READINESS_20261022/PP1_REVIEWED_TWIN_SCENE_INTEGRATION_V1/PATH_A/ANALYSIS.json
```

Exit0. The reused validator prints a generic "Fresh TCP /analyses" label; this input was the fresh ASGI response. Actual TCP registration/readback is separately evidenced in TCP_PROOF. This is response-schema compatibility, not a browser test.
''')
write('LIMITATIONS_AND_NEXT_STEP.md','''# Exact remaining gap and PP1 implication

The PP1 controlled demonstration now starts from an actual registered/replayed HTTP Metric Twin and reaches the existing Scene/EAG research workflow through a tested adapter. It no longer requires constructing a disconnected Scene venue behind the HTTP contract.

It remains a controlled 80-guest Wedding representative slice. Genuine reviewed field operation is NOT_EXECUTED and not enabled: no source-bound physical measurement/review package or genuine event/stock authority is supplied; frozen Scene preflight, bridge and EAG authority explicitly restrict external-source execution. The adapter reports this unsupported condition rather than changing domains or forging test authority.

Required for a real venue: original source/candidate identity; two distinct consistent measured controls and origin; reviewed usable boundary and supported fixed objects including exactly one stage; source-bound measurement/review/object-decision artifacts; separate approved client/planner Scene briefs bound to the actual event policy; explicit stock actions/new-supply and layout permissions; appropriate topology/safety qualification. Current HTTP contracts cannot represent general movable/uncertain stock, and genuine authority is not authenticated. These are contract/data/research gaps, not errors hidden by a synthetic substitute.

No general HTTP Scene/EAG execution endpoint or frozen frontend user journey has been added. API schema compatibility and local execution do not certify a finished frontend workflow. Guest addition, multi-group selective adaptation, full multi-event search, real-venue safety, weather, historical S-GCN and feedback learning remain later original research objectives.

**Single next PP1 action:** rehearse this frozen two-branch demonstration with the actual pending drawing and registered-controlled-Twin lifecycle, displaying provenance, real polygons, independent checks and refusal evidence. Decide separately whether genuinely supplied field review data and a new externally scoped authority contract justify a later real-venue implementation; do not broaden current claims to fit the deadline.

No algorithmic novelty or full research completion is claimed; originality remains UNRESOLVED. Stop after this integration delivery. No frontend, cleanup, retraining or architecture restructuring follows automatically.
''')
write('FRONTEND_SCHEMA_CHECK.json',json.dumps(dict(status='PASS',exit_code=0,validator='Frozen frontend AJV2020/OpenAPI1.1.0 AnalysisReceipt',input='PATH_A/ANALYSIS.json',transport_of_input='FastAPI TestClient ASGI',browser='NOT_EXECUTED',frontend_modified=False),indent=2))
print('Reports written from actual saved evidence')
