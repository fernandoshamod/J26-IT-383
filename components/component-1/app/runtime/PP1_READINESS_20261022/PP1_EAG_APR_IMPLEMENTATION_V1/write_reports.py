"""Reports derived from actually executed raw evidence, not planned metrics."""
import collections
from runtime import *
from scenarios import EXPECTED

def write(name,text):
    with (HERE/name).open('x',encoding='utf-8') as f:f.write(text.strip()+'\n')
def table(headers,rows):return '\n'.join(['| '+' | '.join(headers)+' |','|'+'|'.join('---' for _ in headers)+'|']+['| '+' | '.join(str(x).replace('|','/') for x in row)+' |' for row in rows])
final=read(HERE/'outputs/CLOSEOUT_FINAL/FINAL_ACCEPTANCE.json');ag=read(HERE/'outputs/CLOSEOUT_FINAL/AGGREGATES.json');raw=read(HERE/'outputs/EXPERIMENT_FINAL/RAW_COMPARISON.json');weak=read(HERE/'outputs/CLOSEOUT_FINAL/WEAK_CONTEXT_OMISSION_DIAGNOSTIC.json');stale=sum(not r['old_certificate_current'] for r in weak);badold=sum(not r['old_candidate_current_checks']['valid'] for r in weak)
aggtable=table(['Method','Outcomes','False accept / refusal','Candidate records','Search evaluations','Fallback attempts / successes','Protected / unauthorized changes','Dirty metadata nodes'],[(a['method'],a['scenario_outcomes'],str(a['false_accepts'])+' / '+str(a['false_refusals']),a['candidate_records'],a['actual_search_evaluations'],str(a['fallback_attempts'])+' / '+str(a['fallback_successes']),str(a['protected_changes'])+' / '+str(a['unauthorized_changes']),a['dirty_graph_nodes_total']) for a in ag])
casetable=table(['Scenario','Expected status','Observed operation (one unit)','Candidates / menu'],[(case,status,next(r['operation'] for r in raw if r['case']==case),str(next(r['candidate_count'] for r in raw if r['case']==case))+' / '+str(next(r['material_menu_count'] for r in raw if r['case']==case))) for case,status in EXPECTED.items()])
write('README.md',f'''# EAG-APR V1 — implemented assurance and repair prototype

**Scientific verdict: controlled functional correctness demonstrated; strong-baseline equivalence; no algorithmic originality established.** This isolated subsystem uses the existing Event Scene compiler, actual frozen initial/adaptive NSGA-II and independent function/geometry oracle. It does not replace the full A–F research or define it as Wedding planning.

Final experiment: **52 controlled scenario instances × three methods = 156 outcomes**, with zero false acceptance/refusal under pre-authored synthetic labels. **All 52 three-method outcome/candidate comparisons and all 52 EAG/incremental closures match.** The scenario outputs contain **684 correlated candidate records**. Twelve initial searches plus sixty scenario searches consumed **92,160 actual evaluations** (14,400 initial + 77,760 scenario), excluding separately labelled probes/tests/CLI repetitions. All admitted candidates pass independent full checks; zero protected/unauthorized changes were accepted.

Executed checks: **381 main assertions; 17 adversarial tests; 7 schema/CLI tests; 316 closeout replay checks**. Coverage overlaps; none is a research completion percentage. Recorded preservation covers **3,920 prior files**, with byte hashes for files ≤1 MB and size/mtime for larger dependencies. No new whole-dataset/checkpoint bytewise audit was performed.

Read [implementation](IMPLEMENTATION_REPORT.md), [actual comparison](EXPERIMENT_COMPARISON.md), [scientific verdict](SCIENTIFIC_NOVELTY_EVALUATION.md), [limits](KNOWN_LIMITATIONS.md), [PP1 evidence](PP1_EVIDENCE_SUMMARY.md), [next action](NEXT_IMPLEMENTATION_STEP.md), and [primary-source comparison/hypotheses](SCIENTIFIC_COMPARISON.md).

## Run instructions

From `C:\\My Research Component`, choose **new** output directories; use the installed environment. No installation, server, model training, frontend or cloud service is required.

```powershell
.venv\\Scripts\\python.exe -B PP1_READINESS_20261022/PP1_EAG_APR_IMPLEMENTATION_V1/experiment.py --out outputs/MY_EXPERIMENT_001
```

This executes both venue templates, seeds 20261017/20261018, explicit simulated initial/layout approvals, thirteen changes, all three methods and real supported searches. Raw failure/no-candidate/unsupported outcomes are saved. A nonzero exit denotes failed expectations/checks; no broad feasibility claim follows from a PASS.

The already executed fresh CLI singleton example can be repeated:

```powershell
.venv\\Scripts\\python.exe -B PP1_READINESS_20261022/PP1_EAG_APR_IMPLEMENTATION_V1/research.py --input PP1_READINESS_20261022/PP1_EAG_APR_IMPLEMENTATION_V1/outputs/EXPERIMENT_FINAL/VENUE_32_24_SEED_20261017/authorized_singleton_repair/INPUT.json --reference PP1_READINESS_20261022/PP1_EAG_APR_IMPLEMENTATION_V1/outputs/CLOSEOUT_FINAL/REFERENCE_EAG_V32_S20261017.json --method EAG --seed 20261017 --out outputs/MY_SINGLETON_001
```

These inputs are explicitly simulated records, not genuine approval. Reference/input bytes and original fixture evidence must stay in place. CLI exits 0 only for eligible verified output; pending/refused/unsupported/no-candidate exit 2. Invalid strict-schema input raises validation errors. The local schema is [INPUT_SCHEMA.json](outputs/CLOSEOUT_FINAL/INPUT_SCHEMA.json); no frozen HTTP routes were added.

Repeat adversarial probes with `tests_execution.py --out outputs/MY_TESTS_001`. They use preserved final experiment inputs but write fresh local corruptions/results. `closeout.py` defaults to replaying the preserved final experiment and attempts an exclusive fresh CLI output named CLI_INITIAL_FINAL; its default executed evidence is preserved and a naive rerun will intentionally fail on existing output. For reruns, use the experiment/test CLI with new names; do not overwrite final evidence. `contract_checks.py` and `render_actual.py` similarly preserve their fixed final directories.

## Inspect actual artifacts

- [Final acceptance JSON](outputs/CLOSEOUT_FINAL/FINAL_ACCEPTANCE.json), [raw comparison](outputs/EXPERIMENT_FINAL/RAW_COMPARISON.json), [per-method aggregates](outputs/CLOSEOUT_FINAL/AGGREGATES.json), [constraint/disruption records](outputs/CLOSEOUT_FINAL/CONSTRAINT_WORK_AND_DISRUPTION.json).
- [Actual singleton result/certificate/XAI](outputs/EXPERIMENT_FINAL/VENUE_32_24_SEED_20261017/authorized_singleton_repair/EAG/RESULT.json), [its native unchanged-engine request](outputs/EXPERIMENT_FINAL/VENUE_32_24_SEED_20261017/authorized_singleton_repair/EAG/ACTUAL_SEARCH/FROZEN_ADAPTIVE_REQUEST.json), [native response](outputs/EXPERIMENT_FINAL/VENUE_32_24_SEED_20261017/authorized_singleton_repair/EAG/ACTUAL_SEARCH/FROZEN_ADAPTIVE_RESPONSE.json).
- [Evidence-linked graph](outputs/EXPERIMENT_FINAL/VENUE_32_24_SEED_20261017/mandatory_dance_added/EAG/GRAPH.json), [impact report](outputs/EXPERIMENT_FINAL/VENUE_32_24_SEED_20261017/mandatory_dance_added/EAG/IMPACT.json), each run's `assurance.sqlite3`.
- [Actual repair figure](outputs/FIGURES_FINAL/ACTUAL_SINGLETON_REPAIR.png), [measured baseline figure](outputs/FIGURES_FINAL/MEASURED_BASELINE_COMPARISON.png). Figures use actual polygons/metrics, not generated concepts. Older closeout plot retained; final figures correct its footer spacing.
- [Adversarial results](outputs/TESTS_FINAL/TEST_RESULTS.json), [strict schema/real CLI checks](outputs/CONTRACT_CHECKS_FINAL/TEST_RESULTS.json), preserved `PILOT_001.log` and `ADAPTIVE_PROBE_001.log`.

Stop point: implementation and evaluation complete. Frozen backend/frontend, old experiments, datasets and weights were not modified. No weather integration, S-GCN training, broad cleanup or restructuring was performed.
''')
write('IMPLEMENTATION_REPORT.md','''# Implementation report

## Reused active interfaces

`runtime.py` imports existing `compiler.compile_scene`, `baseline.baseline_scene`, strict Scene `Request`, `fixtures.fixture/seal`, `bridge.execute/menu`, and independent `oracle.validate_spec/validate_layout`. The source versions are recorded. It redirects only the existing shared writer and bridge output-containment variable **in memory** to this new folder; installed/frozen files remain unchanged. `load_engine` loads the unchanged `engine_adaptive.execute`; its existing permission gate is imported from the older research-core dependency.

Scene input remains `EVENT_SCENE_INPUT_V1`: source-bound controlled reviewed metric geometry, actors, policy hash, actions/design controls. Scene output remains a derived specification with counts/allocations/zones/hard bounds. The new packet adds versioned local simulated context, object/group locks/permissions, scenario scope and a source-bound hashed authority artifact. It is a new isolated contract, not an invented API 1.1.0 route. Public CLI schemas are in `eag_contracts.py` and exported JSON. Real-source/other-event optimization remains unsupported.

## Modules A–E

- **A, evidence-linked constraints — `constraint_graph.py`:** thirteen typed hard/soft obligation nodes carry ID/version, evidence path/hash IDs, venue source version, qualified/pending status, client/planner responsibility, object/function incidence and declared scenario. Fact changes propagate through graph closure. `INCREMENTAL` uses ordinary reverse incidence/worklist; `FULL` marks all nodes; `EAG` uses fixed-point closure. Object scope is coarse/global, not a proven minimum movable set. Dirty-node count is bookkeeping, not the number of geometry predicates skipped.
- **B, contextual validity certificates — `certificates.py`:** context/venue versions, actual file hashes, approved protected IDs, active hard bounds, mandatory functions, full independent validation, eligibility status, reasons and result hash. `is_current` detects supplied source/context/permission snapshot mismatch. Every revalidation issues a fresh certificate; an old geometric candidate can survive without an old certificate being reused as current. Records are unsigned local machine-checkable assertions, not cryptographic identity/regulatory certification.
- **C, impact — `constraint_graph.py` plus `repair.py`:** exact fact-token delta, propagated constraint/object incidence, old-certificate staleness, actual previous-candidate invalidation reasons. Full validation always remains mandatory, including after graph-based reasoning. Fault injection deliberately omits all propagation; the full checker catches missing dance/function/geometry obligations and triggers a real full search. No selective validation/optimal dependency theorem is claimed.
- **D, governed repair — `repair.py`, `authority.py`, `optimizer_adapter.py`:** explicit local authority/evidence binding; protected-object denial; current source qualification; actual verified-pool reuse; frozen singleton repair when the scene is unchanged and one group is explicitly permitted; otherwise supported full initial recomputation with all changed seating groups permitted. Newly approved quantities/functions/usable boundaries propagate through actual compilation/search. Observed-stock relocation is explicitly unsupported, even with a simulated permission: the inherited stock compiler does not implement that design transition.
- **E, verification/XAI — `independent.py`:** existing independent geometry/function/numerical oracle plus separate permission/reference/protected-ID checks, stable-ID group/individual displacement, raw result replay, Pareto nondominance/menu diversity, current certificate/result binding and descriptive claims tied to evidence and constraint IDs. Each saved result has an isolated SQLite record. Evidence is re-read before issuance and after issuance before write; an injected last-moment change prevents successful persistence.

## Real algorithms and decision spaces

Initial optimization uses the original engine/population/operators: 48 population × 25 generations, actual 1200 fitness/G-vector evaluations in dispatched successful runs. Authorized singleton uses the original two-coordinate engine: 48 × 35, actual 1680 evaluations. ID normalization translates engine group/table/chair names back to the Scene identity contract; computational reservation polygons are separated from physical equipment. Independent checking verifies the normalized individual geometry.

Initial objectives remain mean stage-centroid distance and Hungarian assignment displacement from the generated initializer. Singleton search objectives remain target stage distance and target stable relocation; reported mean-stage/initializer metrics are separately reconstructed and verified. Actual stable-reference group/individual relocation is also recorded. Full-recomputation fallback is not a general minimum-disruption algorithm and does not claim collision-free physical movement routes.

## Execution/failures

`PILOT_001` found six false refusals in singleton cases because reissuing unchanged scene-evidence file paths made the strict eligibility check see a scene change. `scenarios.py` now preserves scene bytes for a permission-only request; the targeted adaptive probe executed actual 1680-evaluation search with eight valid outputs. The failed pilot and probe are retained, not added to final independent coverage. Final two-seed experiment, adversarial suite, contract checks and raw closeout all executed successfully. All new work remains isolated.
''')
write('EXPERIMENT_COMPARISON.md',f'''# Executed fair comparison

Two synthetic venue templates × two seeds × thirteen scenarios = **52 case/seed instances**. All three receive the same reviewed fixture bytes, actors, permissions, required functions, context versions, reference, feasible variables and optimizer seeds/budgets. Methods differ in demand compiler/graph representation; the strong ordinary incremental baseline retains every authority/geometry rule. Every final candidate is fully revalidated. Common dispatch/validators are explicit, not independent solver implementations.

{aggtable}

All 52 three-way semantic/geometry/search-decision comparisons match. EAG and standard incremental propagation match in 52/52. Each method has 32 expected eligible and 20 expected noneligible outcomes; zero false acceptance/refusal. Noneligible breakdown is four pending, eight refused, four unsupported and four no-candidate outcomes. No global infeasibility proof is claimed for failed finite/grid initialization.

## Scenario coverage

{casetable}

Table uses the 32×24 m / seed 20261017 record for concrete operation/menu counts; all units' exact outcomes are in RAW_COMPARISON.json. Menus offer three on 28 eligible records per method and one on the four lock-added records; no padding. Twenty fallback attempts per method include sixteen successful full searches and four failed initializations; denominator is all 52 scenario outcomes (38.46%). These are not 20 successful repairs.

## Optimization, work and quality

Scenario searches: 60 actual minimize calls total, 77,760 actual fitness/G-vector evaluations; base initial searches: twelve calls, 14,400 evaluations. Total authoritative main experiment is 72 actual minimize calls and 92,160 evaluations. Separate probes, test fallback and CLI repeats are excluded. Each matched full call uses 1200 and each singleton 1680; failed initialization can consume zero optimizer evaluations and is recorded.

Per method, scenario G scalar values reconstructed from the saved native request's actual constraint dimension × pymoo n_eval total 2,476,800. This is an explicitly derived work count, not direct instrumentation of individual comparisons and excludes extra candidate selection/replay evaluations. `graph_qualification_nodes` is a dirty-node metadata count, **not** measured predicate evaluations. Full candidate replay still happens for all returned layouts; its raw-record lower bound is 416 per method and omits duplicated issuance/envelope replay calls. No exclusive revalidation speedup is established.

Actual end-to-end median scenario times: FULL {ag[0]['median_elapsed_seconds']:.6f} s, INCREMENTAL {ag[1]['median_elapsed_seconds']:.6f} s, EAG {ag[2]['median_elapsed_seconds']:.6f} s. These include compilation, verification and I/O; execution order/cache effects and small samples preclude significance/superiority claims. Objective vectors, each candidate's moved-object count and stable-ID group/individual distance, menus and runtime remain in CONSTRAINT_WORK_AND_DISRUPTION.json. Matching coordinate pools imply identical declared numerical trade-offs within each case; unrelated scenarios/reference initializers are not pooled as one objective-quality score.

## Diagnostic ablation — explicitly not a fair comparator

The context-blind replay diagnostic returns the actual prior layout/certificate without using updated context. It reuses a stale certificate in **{stale}/{len(weak)}** cases under the declared exact-snapshot rule; independent current candidate checks fail in **{badold}/{len(weak)}** cases. These are different denominators/properties: stale provenance can coexist with valid geometry. Removing context/authority information creates contract failures, not evidence that EAG outperforms an equal-information algorithm. No simplified optimizer replaces the real engine in the main comparison.

## Independence and coverage limits

Expected statuses are pre-authored synthetic labels, not external planner annotations. The existing oracle has separate equations/geometry implementation but shares catalog policies and Shapely/SciPy kernels. Three wrappers share dispatch and some gates; this deliberately competent comparison can demonstrate equivalence, not superiority over all dynamic-CSP solvers. Candidate records/seed repeats are correlated. All 684 scenario candidate records were replayed in closeout; schemas, poisoned geometry/XAI, permission changes, evidence races and graph omission have additional executed tests.
''')
write('SCIENTIFIC_NOVELTY_EVALUATION.md',f'''# Scientific novelty evaluation — null differentiation result

1. **Functionally correct?** Within the declared controlled scope, final tests support evidence/authority qualification, protected geometry, required functions, actual initial/singleton optimization, supported full-recomputation fallback and faithful descriptive records. All 156 labelled outcomes match and all admitted candidates pass full checks. This is not a universal proof, real-venue validation or every requested capability: authorized observed-stock relocation remains unsupported.
2. **Better than an information-omitting weak system?** The executed blind-cache diagnostic would serve stale certificates in {stale}/52 cases and fails current candidate checks in {badold}/52. This shows why the declared information/gates matter. It is not a fair like-for-like algorithm comparison or new empirical discovery about provenance.
3. **Different from competent conventional methods with the same inputs?** No demonstrated outcome difference. FULL, INCREMENTAL and EAG match all 52 candidate/decision comparisons; standard incremental and EAG dirty closures match all 52. No unique affected-set or repair decision advantage is established.
4. **Algorithmic performance improvement?** None supported. Search objectives, actual budgets, candidate pools and protected/function outcomes match. Metadata bookkeeping improves on all-node marking only in unchanged cases and is reproduced by ordinary dependency tracking. Full validation is mandatory and runtime differences are not inferential evidence.
5. **Useful assurance protocol or benchmark?** Yes as an implemented application artifact: explicit evidence/role/context links, testable current-validity records, governed dispatch, actual search/fallback, full independent replay, unsigned result/certificate binding, faults/refusals and reusable controlled fixtures. Distinct application packaging/usefulness does not establish first-in-literature scientific novelty or exclusive benefit.
6. **Defensible novelty claim?** A candidate event-domain formulation and reproducible assurance benchmark/prototype can be presented, with originality explicitly unresolved and the null hypothesis of conventional equivalence retained on tested cases. It is indefensible to claim a new NSGA-II, invented provenance/dependency/repair algorithm, superiority, minimum repair, general multi-event adaptation or validated real safety.

The scientific object remains **evidence- and authority-qualified context-sensitive event-layout recommendations and permitted adaptation** within the complete A–F plan. Standard prior art already solves substantial constituent and combined mechanisms; see SCIENTIFIC_COMPARISON.md and preserved earlier paper comparisons. An invented acronym cannot close the panel warning. The new evidence strengthens implementation correctness and falsifiability; it does not rescue a failed originality hypothesis by renaming it.

Earlier 12/12 reduced/selective, 39/39 scene-specification and 10/10 temporal-pool null findings remain untouched. The EAG baseline agreement is a new scoped null, not a reinterpretation of those experiments as success. The panel must decide whether a rigorously evaluated applied protocol/benchmark meets the required research contribution category.
''')
write('KNOWN_LIMITATIONS.md','''# Known limitations and unsupported claims

- Controlled synthetic source/calibration/role/approval/evidence records only. No genuine measurement, authenticated planner, consent/preference label, weather observation or safety consequence is fabricated. Content hashes and self-checking unsigned certificates do not establish authenticity/truth. Supplied current context remains an operator input; no global latest-version authority service exists.
- Existing observed stock relocation is deliberately UNSUPPORTED, even with an approved simulated request. The compiler cannot model relocation; no new observation or physical move is silently invented. Actual movable repair is of previously placed event seating groups through the existing singleton engine.
- Guest increase, new dance function and multiple dependent changes are supported only as new qualified **initial recomputation**, with explicit new-supply/all-affected-group permissions. This is not incremental guest addition or multi-group adaptive search. Full fallback may move many permitted groups and does not minimize stable-reference disruption.
- Planner-pinned stage/buffets/design zones remain fixed controls. Only Wedding/eight-seat controlled seating optimization executes; other event profiles remain compiler-only. Full indoor/outdoor/hybrid understanding, historical S-GCN, weather/environment consequence modeling, detailed safety, feedback learning and general event adaptation remain original objectives and unfinished.
- Manual controlled usable-boundary revision is the tested operational scenario; it is not weather integration or a safety forecast. Infeasible status means no candidate found by the supported finite initialization/search path, with global_infeasibility_proven=false.
- All final candidates receive complete independent replay. Graph nodes are coarse/global; no minimum affected variables, minimal conflict proof, incremental constraint solver, graph-maintenance speedup or optimal revalidation certificate is established. The standard incremental comparator is incidence/worklist tracking with full verification, not a reproduced state-of-the-art DCSP engine.
- All strategies share conservative dispatch/validators and some representation/gates. Separate demand loops and independent geometry equations do not create independent human labels or numerical kernels. Objective/candidate equality on two related templates and two seeds is not general equivalence proof or external validity.
- Initializer Hungarian displacement, stable-ID reference relocation and target adaptive relocation are distinct measurements. Arrows connect verified endpoint layouts; no collision-free relocation route, crowd/egress/accessibility/occupancy/structural safety or physical furniture accuracy is certified.
- Three alternatives are conditional on actual spatial/objective diversity. Lock-added cases offer one; some contexts legitimately refuse/pending/unsupported/no-candidate. Rejected outputs have no drawing candidates.
- Descriptive numerical/rule XAI is checked; learned attribution, counterfactual causality and human usefulness are not. Evidence/constraint ID lists are audit traces, not minimal causal explanations.
- Public CLI enforces a strict local packet schema; internal experimental Python functions assume structured records supplied by the fixture/runner. This is not a production service, authenticated approval store or browser integration. Certificate content includes original compiler/engine/checker versions; this release's own code provenance is in its artifact manifest, not a digital signature.
- Failed PILOT_001 and the corrected adaptive probe are preserved. The final authoritative experiment excludes them from coverage. The first plot footer overlapped its x label; FIGURES_FINAL rerenders from unchanged actual data and preserves the earlier plot.
- Preservation checks cover 3,920 targeted prior files: byte hashes for ≤1 MB, metadata for larger assets; not fresh bytewise proof of all datasets/weights. No original source, frontend/backend, datasets or checkpoint was edited; no full project cleanup occurred.
''')
write('PP1_EVIDENCE_SUMMARY.md',f'''# PP1 evidence for Proposal Panel Warning 3

**Show a working assurance/repair mechanism, then show the null comparison.** Do not promise a newly invented adaptive optimizer.

- New source modules implement typed evidence-linked constraints, contextual validity records, dependency change propagation, permitted singleton/full dispatch, full geometry/function/authority checks, numerical XAI and persistence.
- Actual controlled case sequence: initial 1200-evaluation layout → explicit simulated layout approval → current context/certificate → permitted 1680-evaluation singleton with all other individual objects locked; guest/function/usable-area changes requalify and use actual full fallback. New source/locks/evidence and pending/conflicting/unsupported cases have explicit decisions.
- Two venue templates × two seeds × thirteen scenarios; 52 matched three-method comparisons. All outcomes/candidates match; no algorithmic originality established. Zero false decisions under finite labels, zero accepted protected/unauthorized changes; 684 correlated scenario candidates independently replayed.
- Executed 381 main assertions, 17 adversarial tests, 7 strict-schema/CLI checks and 316 closeout checks; overlap is disclosed. Fresh public CLI initial/singleton and pending exit-code behavior were executed. Graph fault omission forces actual fallback; self-hashed poisoned geometry/XAI and late evidence change cannot produce accepted saved output.
- Figures: `outputs/FIGURES_FINAL/ACTUAL_SINGLETON_REPAIR.png` and `MEASURED_BASELINE_COMPARISON.png`. Raw evidence: EXPERIMENT_FINAL/RAW_COMPARISON.json, per-run GRAPH/IMPACT/SPEC/RESULT, native search JSON and SQLite; CLOSEOUT_FINAL/FINAL_ACCEPTANCE.json.

Suggested examiner wording: “We investigate how source evidence and actor authority qualify a changing event-layout problem and its accepted recommendations. Our restricted prototype executes real optimization and independent assurance checks. A conventional compiler and dependency approach reproduce our tested outcomes, so we do not claim a novel NSGA-II or proven superiority. The implemented protocol and reusable faults/benchmark are current progress; full scientific differentiation, real-venue generalization and future learning/weather/safety work remain open.”

Full A–F, multi-event, indoor/outdoor/hybrid, reviewed Twin, historical S-GCN, weather, detailed safety, optimizer recommendations, review/feedback and cross-cutting XAI remain preserved. Current examples are explicit controlled demonstrations only. This package does not claim that the warning letter is withdrawn or that PP1 acceptance is guaranteed.
''')
write('NEXT_IMPLEMENTATION_STEP.md','''# Single highest-priority next PP1 action

**Freeze and rehearse the supported EAG-APR CLI demonstration and its null-result explanation in one fresh isolated PP1 run.** Use actual initial → explicit simulated approval → current certificate → permitted singleton, then one function/area-change full fallback and one refusal. Inspect saved polygons/IDs, context/source hashes, numerical XAI and SQLite rather than adding another mechanism.

Acceptance: exact commands/exit codes and measured outputs; no weakened gates; observed-stock relocation remains unsupported; one lock case returns fewer than three options; existing 12/12, 39/39, 10/10 and new 52/52 conventional-equivalence findings are plainly acknowledged. Review the contribution category/API interpretation with the supervisor using the actual results, not a promised new algorithm. This is more PP1-critical than frontend work, weather, S-GCN or cleanup.

The next integration boundary, only after explicit approval, would be a separately versioned orchestration/approval-context interface for this local assurance workflow. It is currently a CLI research subsystem, not part of frozen API 1.1.0 or the frontend. Do not edit those frozen files to claim seamless integration. Genuine identity/venue measurements remain evidence-dependent and cannot be manufactured for rehearsal.

Stop here: implementation, tests and fair comparisons have executed. No frozen backend/frontend modification or cleanup is authorized or performed.
''')
