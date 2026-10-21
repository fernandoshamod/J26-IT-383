from lab import *
import re,csv,collections
events=guard()
def md(name,text):
 with (H/name).open('x',encoding='utf8') as f:f.write(text)
v=read(H/'INDEPENDENT_VERIFICATION.json');e=read(H/'EXECUTION.json');p=read(H/'POLICY_EXECUTION.json');s=read(H/'MEASURED_SUMMARY.json');rows=read(H/'RAW_REVIEW_RESULTS.json');negative=read(H/'NEGATIVE_CHECKS.json')
summaries={f"{r['method']}_{r['budget']}":r for r in s}
with (H/'MEASURED_SUMMARY.csv').open('x',encoding='utf8',newline='') as f:
 w=csv.DictWriter(f,fieldnames=list(s[0]));w.writeheader();w.writerows(s)
parts=[]
for r in s:
 parts.append(f"- {r['method']}, budget {r['budget']}: mean reviews {r['review_cost_mean']:.4f}; mean loss {r['loss_mean']:.8f}; conditional coverage {r['conditional_coverage']:.4f}; source-qualified availability {r['qualified_coverage']:.4f}; false conditional acceptance {r['false_conditional_accept_rate']:.4f}; valid-choice stage regret {r['stage_regret_m_conditional_mean']}. Denominator: {r['finite_world_weight']:.0f} weighted worlds; raw rows {r['raw_rows']}.")
md('ACTUAL_RESULTS.md',f'''# Actual executed review-policy sensitivity results

**Verdict: NOVELTY_NOT_ESTABLISHED.** Independently coded task-aware B5 and NEW matched in {v['strong_matches']}/{v['strong_pairs']} case/budget/hidden-world pairs, including decision, reviewed facts, answer trace, loss and readiness. These are correlated finite-grid pairs, not independent venues or a statistical equivalence theorem.

Actual searches: {e['searches']}; total original optimizer evaluations {e['actual_evaluations']}; returned candidate occurrences {v['actual_candidate_occurrences']}; separate counterfactual candidate checks {v['cross_world_candidate_checks']}. Each accepted source-world candidate has independent geometry/function/EAG/XAI replay and one of {v['sqlite_rows']} directly read SQLite rows. Counterfactual seating checks include invalid attempts; error occurrences remain in INDEPENDENT_VERIFICATION.json, not hidden or converted into PASS candidates. Independent replay: {v['assertions']} assertions within one verification, not that many experiments.

Four development case contexts over one controlled metric venue, not independent real venues. Four real saved prediction anchors across three collections; no real metric transfer, no calibrated uncertainty, no human review or untouched evaluation split. {p['rows']} raw review-policy rows include six equally weighted random permutations and ablations; they do not multiply search count.

World-build elapsed {e['seconds']:.3f}s; traced Python peak {e['python_tracemalloc_peak_bytes']} bytes. Policy/table stage {p['seconds']:.3f}s, traced Python peak {p['python_tracemalloc_peak_bytes']} bytes. Tracing/instrumentation overhead is included; this excludes complete native/CUDA/process memory and is not a throughput benchmark. Methods share the complete counterfactual optimization table. Policy fresh evaluations are zero; that does NOT mean free planning. All actual {e['actual_evaluations']} lookahead evaluations are charged once to the experiment. No method-specific end-to-end compute saving or policy speed superiority is established.

## Measured results

'''+ '\n'.join(parts)+'''

B6 always reviews all three facts; its apparent coverage/quality at budget0/1/2 exceeds those budgets and is intentionally NOT a matched-budget superiority comparison. Conditional coverage measures research seating decisions; source-qualified availability references the actual target-world optimizer envelope. They are different endpoints. A policy can stop once seating choice stabilizes while still failing the source-evidence gate. This is a limitation of optimizing conditional decision loss alone, not evidence that mandatory review can be removed.

Conditional-refusal-with-full-information-feasible is a diagnostic information-limited abstention rate, not an erroneous real safety refusal. Regret uses a shared finite candidate pool, not a global optimum. Initializer displacement is not furniture transport; no cross-world initializer-based Pareto quality assertion is made. Genuine source-to-approved-real-venue success remains untested.

## Negative and ablation outcomes

Four actual EAG negative cases (pending metric, tampered authority, protected stage move, conflicting briefs) all rejected/pending with zero optimizer evaluations; numerical denial envelopes independently pass. No acceptance count is inflated with these nested checks.

NO_EVENT replaces decision-aware selection with geometry-only ranking; NO_FEEDBACK with uncalibrated opening ranking. These are mechanism-removal diagnostics, not perfectly isolated learned-model causal ablations. NO_AUTHORITY removes authority only from the diagnostic loss table; false conditional acceptance in true authority-disqualified worlds is retained, and approved readiness is always disabled. Without calibration: NOT_COMPARABLE_NO_CALIBRATED_UNCERTAINTY. No fake calibrated baseline was manufactured.

Read MEASURED_SUMMARY.json/.csv, RAW_REVIEW_RESULTS.json/.csv, STRONG_BASELINE_PAIRS.json and per-case policy_inputs/OUTCOME_TABLE.json. All world INPUT/SPEC/GRAPH/RESULT/ACTUAL_SEARCH/SQLite records and failure checks remain.

The first independent verifier attempt (VERIFY_001) stopped at an exact floating comparison: source and independently recomputed mean-stage losses differed by up to 1.11e-16 in the inspected first table. VERIFIER_AT_FAILURE.py and the nonzero log are retained. The corrected verifier applies the predeclared 1e-10 numerical tolerance and is rerun as VERIFY_002. No raw loss, optimizer geometry, policy decision or metric was edited to obtain a pass. Numerical equivalence is not bitwise equality.
''')
md('NOVELTY_VERDICT.md',f'''# Final scientific verdict: NOVELTY_NOT_ESTABLISHED

The new candidate adds an executable source-linked review-selection sensitivity harness upstream of the existing Scene/EAG optimizer. It compares uncertainty, area, sensitivity, myopic VOI and independently implemented optimal task-aware acquisition. That is useful implementation/evaluation work; it is not a demonstrated new decision-making algorithm.

B5 matched NEW {v['strong_matches']}/{v['strong_pairs']} across every tested finite case/budget/realized-answer state. Standard Bayesian decision theory already accounts for the implemented Bellman operations. Closest recent work also targets decision stability and safe acquisition. No exclusive operational advantage or new mathematical property survives this comparison. Do not claim DOMAIN_SPECIFIC_RESEARCH_EXTENSION_SUPPORTED merely because event labels and evidence hashes were added. Application-methodology academic originality remains UNRESOLVED; the exact new-algorithm claim is unsupported by this pilot.

Prior EAG/B4 72/72 and reduced-singleton12/12 nulls remain intact. This pilot is a different upstream question, not a rerun or reinterpretation of those studies. No world-first, new NSGA-II, calibrated uncertainty, optimal review of real venues, risk guarantee, real-review savings or safety certification is allowed.

Precise missing evidence: source-disjoint reviewed metric scenes; verified uncertainty alternatives/calibration on held-out source families; genuine review action time/errors/authority; a concrete hypothesis that differs from conventional task-aware robust acquisition; and a preregistered matched test of that difference. Potential future hypothesis: whether planner-specific review cost/error and adversarial drawing-style shift materially change qualification burden at fixed invalid-recommendation risk. That is already close to robust decision-aware design, so distinguish it before coding, not by renaming.

PP1 recommendation: freeze this null and rehearse the existing working local perception-pending and controlled qualified optimization/lifecycle demonstrations. Seek explicit supervisor/panel agreement on bounded applied research scope and the next independent human/source evaluation, instead of another rushed novelty acronym. Do not claim the novelty warning is cleared.
''')
failure_examples=[]
for manifest in read(H/'POLICY_INPUT_MANIFEST.json'):
 table=read(manifest['path']);bad=next((x for x in table['checks'] if not x['verification']['valid']),None)
 if bad:failure_examples.append(dict(case=table['case'],bits=bad['bits'],decision=bad['decision'],errors=bad['verification']['errors'],table_path=manifest['path']))
pending_example=next((r for r in rows if r['method']=='NEW' and r['conditional_plan'] and not r['ready'] and r['actual_status']=='EXPECTED_PENDING'),None)
ablation_example=next((r for r in rows if r['method']=='NO_AUTHORITY' and r['false_conditional_accept']),None)
save('FAILURE_EXAMPLES.json',dict(counterfactual_geometry=failure_examples,conditional_but_pending=pending_example,authority_ablated_diagnostic_failure=ablation_example))
md('FAILURE_CASES.md','# Actual retained failure and refusal cases\n\n'+ '\n'.join(f"- {x['case']}, world {x['bits']}, diagnostic seating decision{x['decision']}: {', '.join(x['errors'])}. Raw layout/check: {x['table_path']}. This invalid proposal was not accepted or called an actual returned target-world alternative." for x in failure_examples)+'\n\nSee FAILURE_EXAMPLES.json for an actual conditional plan that remains pending (if one occurred) and an authority-ablated diagnostic acceptance failure (if one occurred); absent examples are null, not manufactured. NEGATIVE_CHECKS.json retains four actual original EAG refusal/pending outcomes and zero evaluations. Failed counterfactual proposals are part of the loss table; they do not invalidate valid source-world engine results.\n\nRETURNED_POOL_STABILITY.json retains actual returned seating-signature overlap across source-world nondominated pools. It is not a distance to the unknown true Pareto front. Source-world initializer references differ; no cross-world initializer-objective dominance claim is made.\n')
md('PANEL_DEFENCE.md',f'''# Two-minute technical defence

Our system investigates how uncertain structural evidence, event-function obligations and planner authority affect spatial design decisions. Existing U-Net/YOLO and NSGA-II are reused methods. We independently challenged EAG-APR and found a strong conventional wrapper matched72/72 outcomes. We preserved that null.

We then tested whether downstream planning consequences could guide which spatial facts to review. The prototype actually consumes saved V3 candidates, uses a reviewed controlled metric venue and the existing event compiler, local optimizer, authority gate and independent checker. It enumerates explicit hypothetical alternatives, computes the loss of actual seating decisions, and selects budgeted review actions by expected posterior decision risk. Real drawings remain unapproved; uncertainty weights and reviewer answers are controlled simulations.

The new run executed {e['searches']} real searches/{e['actual_evaluations']} evaluations and replayed {v['actual_candidate_occurrences']} returned candidate occurrences. But ordinary task-aware Bayesian acquisition matched the proposed policy in {v['strong_matches']}/{v['strong_pairs']} finite-grid pairs. We therefore do not claim a new algorithm or superiority. Our supportable output is an implemented event-domain review/assurance test resource with explicit provenance and negative results. Academic originality of that applied methodology remains unresolved.

The next scientific requirement is genuine source-disjoint metric review and a precisely different, falsifiable decision hypothesis with realistic review costs/errors. S-GCN and weather remain original future objectives. For PP1 we can demonstrate the tested bounded system and explain its limits; we cannot honestly claim the novelty warning has been resolved.

## Difficult questions

- What is new beyond standard VOI? **No exclusive algorithmic operation is established; this is a controlled event-domain instantiation/evaluation.**
- Did predictions create the metric world? No. Actual candidate identities/confidences are source anchors; all metric alternatives are separately declared controlled geometry.
- Are priors calibrated? No. Uniform sensitivity weights, not error probabilities learned from U-Net/YOLO.
- Is B5 weakened? No. Same loss table, event/authority facts, budget and conditional information; independently coded finite-horizon decision policy. This is a conventional reference implementation, not a reproduction of every cited paper.
- Do fewer review actions mean the Twin is approved? No. Unknown mandatory evidence stays pending. Conditional decision stabilization is a different endpoint.
- Are transplanted seating arrangements actual Pareto alternatives? No. They are independently checked counterfactual diagnostic decisions. Qualified receipts refer only to actual target-world engine-returned polygons and original certificates.
- Is the oracle using test truth? The planning table includes all declared hypothetical worlds equally. Hidden realized answers are delivered only after a selected review. No real GT labels choose actions.
- Why no human-benefit claim or statistical significance? Four related controlled cases, one seed/venue and simulated costs cannot support either.
- What safety is proven? Only declared nominal geometry/functions and authority refusals; not exits, evacuation, weather or legal compliance.
''')
md('RUNBOOK.md','''# Actual execution and replay

From C:\\My Research Component, installed .venv; no new dependencies, training, downloads, server or frontend. Populated stages use exclusive output writes. Do not rerun builders into this evidence directory.

Executed commands (actual exit/time/argv/cwd in logs/*.COMMAND.json):

```powershell
.venv\\Scripts\\python.exe -B PP1_READINESS_20261022/PP1_ORIGINAL_RESEARCH_MECHANISM_V1/run_logged.py WORLDS_001 build_worlds.py
.venv\\Scripts\\python.exe -B PP1_READINESS_20261022/PP1_ORIGINAL_RESEARCH_MECHANISM_V1/run_logged.py NEGATIVE_001 negative_checks.py
.venv\\Scripts\\python.exe -B PP1_READINESS_20261022/PP1_ORIGINAL_RESEARCH_MECHANISM_V1/run_logged.py POLICIES_001 evaluate_policies.py
.venv\\Scripts\\python.exe -B PP1_READINESS_20261022/PP1_ORIGINAL_RESEARCH_MECHANISM_V1/run_logged.py VERIFY_001 verify_results.py
.venv\\Scripts\\python.exe -B PP1_READINESS_20261022/PP1_ORIGINAL_RESEARCH_MECHANISM_V1/run_logged.py VERIFY_002 verify_results.py
.venv\\Scripts\\python.exe -B PP1_READINESS_20261022/PP1_ORIGINAL_RESEARCH_MECHANISM_V1/run_logged.py REPORT_001 report.py
.venv\\Scripts\\python.exe -B PP1_READINESS_20261022/PP1_ORIGINAL_RESEARCH_MECHANISM_V1/run_logged.py FIGURES_001 figures.py
.venv\\Scripts\\python.exe -B PP1_READINESS_20261022/PP1_ORIGINAL_RESEARCH_MECHANISM_V1/run_logged.py CLI_001 recommend.py --case ACTIVITY_GUEST_CHANGE --budget 2
.venv\\Scripts\\python.exe -B PP1_READINESS_20261022/PP1_ORIGINAL_RESEARCH_MECHANISM_V1/closeout.py
```

Inspect RAW_REVIEW_RESULTS, common OUTCOME_TABLE files, actual world search requests/responses, original EAG RESULT/SQLite and independent replay. Open figures/REVIEW_TRADEOFFS.png and CONTROLLED_ALTERNATIVES.png. They show measured policy summaries and actual returned polygons, not concept layouts. All generated outputs stay here via output-only in-memory bindings to unchanged existing modules. Source-linked anchors are not metric venue reconstruction.

Read-only CLI (safe to repeat; does not create a layout, approval or output file):

```powershell
.venv\\Scripts\\python.exe -B PP1_READINESS_20261022/PP1_ORIGINAL_RESEARCH_MECHANISM_V1/recommend.py --case ACTIVITY_GUEST_CHANGE --budget 2
```

The direct closeout invocation completed separately; it was not retrospectively assigned a subprocess COMMAND log. It verifies all existing command exit records and source hashes and indexes final artifacts. Its console exit is retained in the tool execution record.

For a fresh complete repetition: create an explicitly new peer folder under PP1_READINESS_20261022, copy only this folder's *.py and PROTOCOL.md to it, then run the same stages with its new folder name. Frozen dependencies remain referenced in place; run build_worlds, negative_checks, evaluate_policies, verify_results, report, figures in that order, stopping on nonzero exit. This manual fresh-peer procedure is a reproduction instruction, not a second executed-run claim. No helper auto-overwrites old evidence. Preserve failed attempts and logs.
''')
md('README.md',f'''# Planning-impact-driven active spatial verification: executed falsification pilot

**NOVELTY_NOT_ESTABLISHED.** NEW equals independently coded optimal task-aware B5 in {v['strong_matches']}/{v['strong_pairs']} finite-grid pairs. This is a working conventional-equivalent research harness, not a new NSGA-II algorithm or proof of original VOI.

Start with NOVELTY_VERDICT.md, ACTUAL_RESULTS.md, PRIOR_ART_AND_NOVELTY_GATE.md and PANEL_DEFENCE.md. Formal operations/pseudocode/complexity: ALGORITHM_AND_HYPOTHESIS.md. Original eight logics: EIGHT_LOGIC_ALIGNMENT.md. Input independence and calibration limits: SOURCE_PROVENANCE_AND_LIMITS.md. Predeclared decisions: PROTOCOL.md and PRE_EXECUTION_FREEZE.json/POLICY_CODE_FREEZE.json.

Executed {e['searches']} actual original initial searches/{e['actual_evaluations']} evaluations, {v['actual_candidate_occurrences']} returned candidate occurrences, four actual zero-evaluation EAG negative cases, source/model anchor hash checks, independent geometry/function/XAI and {v['sqlite_rows']} SQLite result rows. {p['rows']} policy rows are correlated simulated replay, not independent venues. One controlled base venue, four cases, four previously observed source artifact records. Models are reused via saved artifacts; no new inference/calibration/training.

All real-source metric/review paths remain pending. No frozen source/frontend/checkpoint/data/evidence edits. Preservation checks and final artifacts are indexed by PRESERVATION_FINAL.json and ARTIFACT_HASHES.json after closeout. RUNBOOK.md contains commands; logs retain actual outcomes/failures.
''')
prior=(H/'PRIOR_ART_AND_NOVELTY_GATE.md').read_text(encoding='utf8');claims=[]
for line in prior.splitlines():
 if line.startswith('- **'):
  claims.append(dict(claim=line.split('**')[1],evidence=line,urls=re.findall(r'\]\((https?://[^)]+)\)',line),retrieval='PRIMARY_FULL_TEXT_OR_OFFICIAL_ABSTRACT_AS_EXPLICITLY_LABELLED'))
save('CLAIM_LEVEL_PRIOR_ART_MATRIX.json',claims)
with (H/'CLAIM_LEVEL_PRIOR_ART_MATRIX.csv').open('x',encoding='utf8',newline='') as f:
 w=csv.DictWriter(f,fieldnames=['claim','evidence','urls','retrieval']);w.writeheader();w.writerows({**c,'urls':json.dumps(c['urls'])} for c in claims)
save('REPORT_PROVENANCE.json',dict(independent_sha256=sha(H/'INDEPENDENT_VERIFICATION.json'),summary_sha256=sha(H/'MEASURED_SUMMARY.json'),raw_sha256=sha(H/'RAW_REVIEW_RESULTS.json'),guard=events))
