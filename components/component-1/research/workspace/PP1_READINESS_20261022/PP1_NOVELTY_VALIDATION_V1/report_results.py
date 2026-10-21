"""Summaries and scientific verdict derived from completed raw/replayed evidence."""
from lab import *
import collections,statistics,csv,math,ast
events=guard();raw=read(H/'RAW_EXPERIMENT_RESULTS.json');ver=read(H/'INDEPENDENT_VERIFICATION.json');run=read(H/'EXECUTION_RESULTS.json');config=read(H/'EXPERIMENT_CONFIGURATION.json')
assert ver['status']=='PASS';pairs=ver['pair_checks'];units=sorted({r['unit'] for r in raw});methods=config['methods']
def doc(name,s):
 with (H/name).open('x',encoding='utf-8') as f:f.write(s.strip()+'\n')
def fmt(v):return f'{v:.6f}'
aggregate={}
for m in methods:
 rows=[r for r in raw if r['method']==m];eligible=[r for r in rows if r['status']=='eligible']
 aggregate[m]=dict(outcomes=len(rows),statuses=dict(collections.Counter(r['status'] for r in rows)),comparable=sum(r['comparable'] for r in rows),evaluations=sum(r['evaluations'] for r in rows),candidate_records=sum(r['candidates'] for r in rows),search_calls=sum(r['optimizer_calls'] for r in rows),false_accept_labels=sum(r['false_accept'] for r in rows),false_refusal_labels=sum(r['false_refusal'] for r in rows),protected_changes=sum(r['protected_changes'] for r in rows),geometry_failures=sum(r['geometry_failures'] for r in rows),function_omissions=sum(r['function_omissions'] for r in rows),median_wall_seconds=statistics.median(r['wall_seconds'] for r in rows),median_material_alternatives=statistics.median(r['material_alternatives'] for r in eligible) if eligible else None)
lookup={(r['unit'],r['case'],r['method']):r for r in raw};equal=sum(all(p[k] for k in ['status_equal','pool_equal','evaluations_equal']) for p in pairs);paired=[]
for p in pairs:
 a,b=[lookup[(p['unit'],p['case'],m)] for m in ['EAG','B4']]
 eligible=a['status']==b['status']=='eligible'
 paired.append(dict(unit=p['unit'],case=p['case'],evaluations_difference=a['evaluations']-b['evaluations'],wall_seconds_difference=a['wall_seconds']-b['wall_seconds'],both_eligible=eligible,best_stage_difference=min(x['stage'] for x in a['metrics'])-min(x['stage'] for x in b['metrics']) if eligible else None,min_individual_relocation_difference=min(x['individual_relocation_m'] for x in a['metrics'])-min(x['individual_relocation_m'] for x in b['metrics']) if eligible else None))
save('AGGREGATES.json',aggregate);save('PAIRED_DIFFERENCES.json',paired)
with (H/'METHOD_AGGREGATES.csv').open('x',newline='',encoding='utf-8-sig') as f:
 keys=list(next(iter(aggregate.values())));w=csv.writer(f);w.writerow(['method']+keys)
 for m,r in aggregate.items():w.writerow([m]+[json.dumps(r[k]) if isinstance(r[k],dict) else r[k] for k in keys])
eligible_pairs=[p for p in paired if p['both_eligible']];wd=[p['wall_seconds_difference'] for p in paired]
lines='\n'.join(f"- {m}: statuses {a['statuses']}; {a['evaluations']:,} evaluations; {a['candidate_records']} candidate records; {a['search_calls']} searches." for m,a in aggregate.items())
doc('EXPERIMENT_STATISTICAL_SUMMARY.md',f'''# Actual experimental results and denominators
{len(units)} balanced reference units: two controlled demand instances (80/96 guests), two seeds (20261017/20261018), **one registered venue geometry**. Eighteen case types yield {len(pairs)} correlated scenario instances and {len(raw)} method outcomes. The four initial setup searches consumed 4,800 evaluations; approval revalidation consumed 0. These are shared setup, not independent six-method trials. The aborted first wrapper attempt consumed an additional 1,200 evaluations and is excluded from final comparative totals, retained in PROTOCOL_AMENDMENT_1.json and logs.

{lines}

Final scenario evaluations: **{sum(r['evaluations'] for r in raw):,}**; plus 4,800 setup and 1,200 retained failed-attempt evaluations. Initialization failures can consume 0; this is not a proof of mathematical infeasibility. Actual calls and budgets are preserved in ACTUAL_SEARCH engine requests/responses and the local function trace.

Primary B4/EAG comparison: **{equal}/{len(pairs)}** matched status, complete returned candidate pool and actual evaluation count. This includes {sum(p['shared_adapter_gate'] for p in pairs)} shared adapter-revocation probes; {sum(not p['shared_adapter_gate'] for p in pairs)} pairs independently exercised the conventional versus EAG qualification/dispatch. There were {len(eligible_pairs)} mutually eligible pairs; best-stage and minimum stable-ID individual-relocation differences are {sorted(set(p['best_stage_difference'] for p in eligible_pairs))}m and {sorted(set(p['min_individual_relocation_difference'] for p in eligible_pairs))}m respectively. Equal pools also imply equal returned Pareto quality/diversity under the shared metrics; global optimality is not established. EAG/B3 graph closure equality: {sum(bool(p['closure_equal']) for p in pairs)}/{sum(p['closure_comparable'] for p in pairs)} computed closures. Shared pre-admission refusals without graphs are excluded from that denominator.

Replayed {ver['returned_candidate_records']} correlated candidate records ({ver['unique_returned_geometry_hashes']} distinct complete object/zone/center hashes); {ver['validated_sql_rows']} certificate-bearing SQLite response rows; zero accepted protected-geometry, literal seating count, function-completeness or geometry violations under the declared checker. Additionally {len(ver['rejected_raw_proposals'])} rejected raw search proposals were replayed, including unsupported reference removals and changed protected geometry. These are technical records, not that many independent events. Expected-label false acceptance/refusal counts are in AGGREGATES.json with each method's applicable denominator. They measure conformance to pre-authored controlled labels; they are not population false-acceptance/false-refusal estimates. B1 NO_VALID_REUSE and NOT_COMPARABLE cases are excluded from those comparisons, rather than treated as equivalent repairs.

Paired EAG-minus-B4 wall-time difference: median {statistics.median(wd):.6f}s, observed range [{min(wd):.6f}, {max(wd):.6f}]s. Method order was rotated, but this was one sequential run per case/method, with instrumentation, warm caches, shared hardware and repeated related inputs. No speed superiority, p-value, confidence interval or statistical significance is claimed. Verification replay timing is separately saved per certificate-bearing row in INDEPENDENT_VERIFICATION.json; conventional primary candidate-check timing is separate in REVALIDATION_TIMING.json. EAG's internal candidate-check component was not separately timed, so those component times are not an apples-to-apples runtime claim.

H1/H2/H4 are finite controlled correctness tests. H3 shows standard reuse avoids unnecessary searches relative to forced full B0 where comparable; B1/B4 have that same reuse opportunity. H5 finds no beneficial operational distinction from the conventional equivalent wrapper. No empirical advantage over an actual published Cassowary/DCSP solver or commercial event product was measured.

Demand reduction and protected-obstacle changes demonstrate current Scene/EAG reference-preservation refusals, not successful removal/relocation. The project's separate HTTP guest-reduction feature is not reclassified unsupported by this result. Multiple dependent requirement changes use full fallback; multi-group selective repair remains unimplemented. Source/context-version changes are simulated Scene successors, not physical venue reviews.
''')
verdict='NOVELTY_NOT_ESTABLISHED' if equal==len(pairs) and not ver['paired_equivalence_failures'] else 'NOVELTY_NOT_ESTABLISHED_PENDING_DISCREPANCY_ANALYSIS'
doc('NOVELTY_VERDICT.md',f'''# Scientific verdict: {verdict}
Choose **C—NOVELTY_NOT_ESTABLISHED** for a distinct EAG-APR algorithm/mechanism. No tested operational distinction survives the strongest conventional wrapper comparison: {equal}/{len(pairs)} B4/EAG pairs have identical status, candidate pools and evaluation counts. Existing papers already cover dynamic reuse, minimal perturbation, dependency propagation, layout locks, ongoing authorization, provenance and runtime enforcement. Passing correctness tests alone is not originality.

Option A is not supported. Option B describes a useful **bounded application-level assurance implementation and evaluation resource**, but the academic originality of that application methodology is still unresolved. Do not upgrade B to an experimentally established novel algorithm. Combining conventional components can be useful; ordinary integration alone is insufficient scientific novelty.

The baseline intentionally implements the same information/policy contract and shares the optimizer and validation kernels. Equivalence is therefore partly expected. It establishes operational reproducibility by ordinary independently coded qualification/dispatch, not a theorem that no future event-specific mechanism can be novel. The study did not implement every cited solver or test every proprietary product. No world-first or superiority claim is supported.

The new independently coded B4 removes part of the earlier shared-wrapper confound, but compiler/oracle/engine/library sharing and controlled labels remain. One venue, two demand levels and two seeds do not establish real-domain generalization. Broader safety, genuine planner identity/truth, new supply removal semantics, automatic minimal affected sets and multi-group repair remain unproven. No null result was renamed into a new optimizer.

The proposal panel warning is not formally cleared by this package. The panel may assess implementation quality, bounded event-domain contracts, critical comparison and reproducibility, while requiring a stronger original-research hypothesis and independent application evidence for later research acceptance.
''')
doc('PP1_RESEARCH_CONTRIBUTION.md',f'''# Recommended bounded PP1 contribution statement
“Component1 implements and evaluates a source- and authority-qualified event-layout assurance workflow: a reviewed metric Spatial Twin and separately supplied client/planner briefs determine functional scene obligations; current evidence and scoped permissions govern verified reuse, authorized singleton NSGA-II repair, full recomputation fallback or refusal; accepted candidates carry independently checked geometry/function/identity metrics, response-bound explanations and persisted records.”

Implementation and controlled correctness are demonstrated. **Algorithmic novelty is not established; application-methodology originality remains unresolved.** The new benchmark contains {len(pairs)} correlated controlled scenario instances and {len(raw)} method outcomes, with a conventional equivalent assurance wrapper matching EAG in {equal}/{len(pairs)} primary pairs. This is not a new NSGA-II, a proven minimum repair set, authenticated planner approval, field safety certification or a genuine floorplan-to-approved-venue result.

The investigated decision policy is which recommendations remain eligible under changed evidence, event functions and protected spatial decisions. Its present operations are reproducible by competent conventional components. A defensible application research contribution would require a justified domain contract, independent real-use failures/benefits and a benchmark resource beyond engineering conformance—not simply more architecture diagrams.

All eight original research logics and A–F scope remain intact. Future historical S-GCN learning, weather/environmental adaptation, detailed safety, genuine planner feedback and real-domain evaluation remain hypotheses/milestones, not implementation claims. Do not rewrite the research as only Wedding planning; Wedding is the supported local optimizer slice used for this controlled study.
''')
doc('PANEL_COMMENT_DEFENCE.md',f'''# Three panel comments: evidence-backed response
## 1. Existing systems and research gap
Cvent documents scaled diagramming, automated seating/diagram assistance, collaboration and reuse; Prismm documents spatial digital twins and stakeholder feedback. Existing layout research already demonstrates fixed furniture and interactive suggestions. We do not claim no alternatives exist or infer proprietary internal absence. The scoped question is whether an explicit, testable event-domain evidence/function/permission contract improves decision assurance in real practice. That practical research gap needs independent field evidence; algorithmic distinction is not established by this benchmark.

Official sources checked18October2026: [Cvent](https://www.cvent.com/en/event-marketing-management/cvent-event-design-software), [Prismm](https://www.prismm.com/the-platform/collaboration-tool). Academic claim-level evidence is in PRIOR_ART_EVIDENCE_MATRIX.csv. No vendor benchmark or market superiority claim was executed.

## 2. Develop without using external APIs
The current experiment directly executes local Python, existing pymoo NSGA-II, compiler and checkers; guarded execution logs record network attempts. This experiment does not rerun AI inference. Existing PP1_FINAL_API_DEFENCE_V1 independently records actual local checkpoint inference and offline optimizer execution. Local library APIs and internal FastAPI/HTTP interfaces still exist; package installation/data acquisition and this literature review are separate network activities. Python audit hooks are not OS-level network isolation. Literal “no APIs of any kind” remains unresolved pending panel clarification.

## 3. Insufficient novelty
We tested the strongest conventional composition, rather than removing safety or permissions from a weak comparator. B4 matched EAG on {equal}/{len(pairs)} paired outcomes/pools/budgets. The result supports a bounded assurance workflow and reproducible controlled benchmark, with no demonstrated new optimization algorithm. Ordinary provenance, authorization and revalidation are acknowledged prior art. Further academic contribution requires a precise differentiating property or independently demonstrated event-domain decision benefit. No formal clearance of the panel warning is claimed.

Two-minute oral answer: “Our contribution claim is now deliberately bounded. The system links reviewed metric venue geometry and event-function demand to current evidence and planner permissions, then decides whether to reuse a verified pool, run an authorized singleton repair, perform full fallback or refuse. It uses existing U-Net/YOLO and NSGA-II; it does not invent those algorithms. We checked relevant primary work and executed matched conventional baselines. The strongest independently coded wrapper reproduced our decisions and pools. Therefore we report a null algorithmic-novelty result. What PP1 demonstrates is a working, auditable event-domain assurance prototype with negative tests, explanations and persistent evidence. Genuine venue reviews, human benefit evaluation and unfinished research objectives remain later work. We want the panel to assess this demonstrated scope and help resolve whether a narrower application-methodology contribution meets the research requirement.”
''')
doc('VIVA_QUESTIONS_AND_ANSWERS.md','''# Five difficult viva questions
1. **What makes EAG-APR more than integration?** Current evidence does not establish a new algorithmic operation. It operationalizes an event-domain assurance contract and controlled evaluation. Independent practical benefit or a precise new property is still needed for an originality claim.
2. **Did you weaken the baselines?** No mandatory evidence/permission/function/geometry checks were removed. B0 is NOT_COMPARABLE for locks/objectives its frozen full engine cannot enforce. B4 independently implements ordinary qualification/dispatch while sharing the same compiler/search/checker as deliberate controls. That sharing limits independence and makes equality partly expected.
3. **Does zero evaluations mean your algorithm is faster?** It may mean a valid saved pool was fully rechecked or a bad input refused. B1/B4 have the same opportunity. It does not establish a new optimizer, less revalidation work or speed superiority.
4. **How do you know a layout is safe and approved?** Controlled geometric/function/identity checks and file hashes verify the declared model and supplied simulated authority. They do not authenticate a human, establish physical measurement truth, verify egress/fire codes or certify safety. Genuine external evidence remains pending.
5. **Are72cases statistically independent and are all changes supported?** No: eighteen case types × two demand levels × two seeds share one controlled venue/reference family. Layout candidates are correlated. Multi-dependent changes use full fallback, not multi-group selective repair. Guest decrease/protected-obstacle changes expose current reference-preservation refusals. No significance or universal feasibility claim follows.
''')
doc('PRESENTATION_EVIDENCE_GUIDE.md','''# Evidence guide and recommended presentation sequence
No slides or presentation files were created. This is an evidence/figure selection guide; slides are not proof of originality.

1. Research question and full eight-logics/A–F alignment: preserve the original architecture and explicitly mark this evaluated assurance slice.
2. Existing work: show the claim-level matrix, with fixed furniture/dynamic repair/authorization/provenance precedents. Vendor internals are unknown, not absent.
3. Method: use the contribution diagram below and the identical-input/constraint/budget baseline table in BASELINE_EQUIVALENCE_REPORT.md.
4. Actual results: use figures_v2/MEASURED_EVALUATIONS.png and figures_v2/PAIRED_STAGE_DIFFERENCES.png, derived only from RAW_EXPERIMENT_RESULTS.json. Include denominators, NOT_COMPARABLE/NO_VALID_REUSE and null outcomes.
5. Working controlled example: figures_v2/ACTUAL_SINGLETON_REPAIR.png uses actual returned polygons and reference IDs; inspect its corresponding raw engine request/response, independent checks and SQLite. Authority is explicitly simulated.
6. Scientific verdict and remaining work: NOVELTY_VERDICT.md, PP1_RESEARCH_CONTRIBUTION.md and the five viva answers. Never claim a new NSGA-II, automatic minimal affected set or real-venue success.

```mermaid
flowchart LR
 A[Registered controlled metric Twin] --> C[Existing event scene compiler]
 B[Separate client and planner briefs] --> C
 C --> Q[Current evidence and permission qualification]
 Q --> R[Revalidate saved pool]
 Q --> S[Supported singleton NSGA-II]
 Q --> F[Full NSGA-II fallback]
 Q --> N[Pending or refusal]
 R --> V[Independent geometry/functions/identity checks]
 S --> V
 F --> V
 V --> X[Bound explanation and SQLite]
 N --> X
```
This is an implemented domain workflow, not a diagram of an established novel algorithm. B4 reproduces the same operational choices with conventional qualification/dispatch.
''')
# Static source separation check: no calls to frozen EAG dispatch/qualifier/issuer.
tree=ast.parse((H/'conventional.py').read_text(encoding='utf-8'));imports=[ast.unparse(n) for n in ast.walk(tree) if isinstance(n,(ast.Import,ast.ImportFrom))]
save('BASELINE_IMPLEMENTATION_BOUNDARY.json',dict(imports=imports,shared=['runtime.baseline.baseline_scene','optimizer_adapter.full/singleton','independent.verify_candidate/verify_envelope','runtime.bridge.menu','runtime.facts','graph schema supplied by benchmark'],not_called=['repair.run','authority.qualify','constraint_graph.impact','certificates.issue'],limits='Certificate freshness comparison uses existing certificates.is_current; same model/schema/facts and validators by design. B2/B3/B4 share this conventional runner.'))
doc('RUNBOOK.md',r'''# Executed commands and evidence
Run from C:\My Research Component using installed .venv; no training, installation, model inference, server or frontend startup needed.

```powershell
.venv\Scripts\python.exe -B PP1_READINESS_20261022/PP1_NOVELTY_VALIDATION_V1/run_logged.py BENCHMARK_001 benchmark.py
.venv\Scripts\python.exe -B PP1_READINESS_20261022/PP1_NOVELTY_VALIDATION_V1/run_logged.py BENCHMARK_002 resume.py
.venv\Scripts\python.exe -B PP1_READINESS_20261022/PP1_NOVELTY_VALIDATION_V1/literature.py
.venv\Scripts\python.exe -B PP1_READINESS_20261022/PP1_NOVELTY_VALIDATION_V1/run_logged.py VERIFY_001 verify_results.py
.venv\Scripts\python.exe -B PP1_READINESS_20261022/PP1_NOVELTY_VALIDATION_V1/run_logged.py REPORT_001 report_results.py
.venv\Scripts\python.exe -B PP1_READINESS_20261022/PP1_NOVELTY_VALIDATION_V1/run_logged.py FIGURES_001 figures.py
```
BENCHMARK_001 failed on a missing baseline envelope field after setup and one extra full search. BENCHMARK_002 fixes that field and restarts comparisons in raw_final using the unchanged frozen input manifest/reference setup. Failed raw/ and logs remain. Exact child argv/cwd/exit/time are logs/*.COMMAND.json. Never rerun these populated stages or edit hashes to overwrite evidence.

RAW_EXPERIMENT_RESULTS.csv/.json contains one row per method outcome and links exact result files. FROZEN_BENCHMARK_MANIFEST.json pins every input and reference before comparative search. Each raw result folder retains input, specification, graph/impact, actual search requests/responses where run, result/certificate/XAI and a SQLite row where the method returns an assurance envelope. NOT_COMPARABLE/NO_VALID_REUSE and adapter refusals have explicit results; do not invent SQLite rows for these.

To repeat, create a new peer workspace with the provided reproduce.py helper and a fresh explicit name. It copies only the harness Python files, never old outputs or models; original frozen dependencies stay in place. It runs the corrected benchmark from scratch and independent replay. Inspect the new raw CSV/JSON and verification pairs directly; original scientific reports retain this delivery's original failure/command history and are not regenerated by the helper. This optional helper is not used to inflate the current completed run count and was not itself tested end to end.

```powershell
.venv\Scripts\python.exe -B PP1_READINESS_20261022/PP1_NOVELTY_VALIDATION_V1/reproduce.py PP1_NOVELTY_VALIDATION_REPEAT_001
```
The experiment uses one registered base Twin; synthetic changed Scene versions are not newly registered HTTP Twins. The real-floorplan branch remains pending genuine venue evidence. Python socket/write guards are instrumentation, not complete OS isolation. Old49/13regression results are reused, not rerun; the new experiment and independent replay validate this isolated harness. No frozen runtime source or weight was altered.
''')
doc('README.md',f'''# EAG-APR novelty validation V1
**Scientific verdict: {verdict}.** B4 independently coded conventional qualification/dispatch matched EAG's status, candidate pools and evaluation counts in {equal}/{len(pairs)} paired scenario instances. Correctness is useful; no new NSGA-II or distinguishing optimizer mechanism is established.

Four controlled reference units (80/96 guests × two seeds), one registered metric venue, eighteen case types, {len(raw)} method outcomes. NOT_COMPARABLE and reuse-only limits are visible. {ver['returned_candidate_records']} correlated candidate records and {ver['validated_sql_rows']} SQLite rows independently replayed. No genuine planner approval, real venue validation, autonomous multi-group repair, S-GCN or weather implementation claim.

Start with NOVELTY_VERDICT.md, EXPERIMENT_STATISTICAL_SUMMARY.md, BASELINE_EQUIVALENCE_REPORT.md and PP1_RESEARCH_CONTRIBUTION.md. PRIOR_ART_EVIDENCE_MATRIX.csv/RELATED_WORK_REVIEW.md distinguish eleven academic works and one standard by verification depth. PANEL_COMMENT_DEFENCE.md and VIVA_QUESTIONS_AND_ANSWERS.md provide bounded examiner answers; no warning is declared formally cleared.

Actual code: benchmark.py, conventional.py, lab.py, verify_results.py. Reports/plots read raw artifacts. Failed first-wrapper logs/source and protocol amendment remain. RUNBOOK.md lists commands; existing populated evidence is exclusive-write. All new work stays here; frozen original research modules are read-only dependencies. Current integrity/guard/preservation results are EXECUTION_RESULTS.json and INDEPENDENT_VERIFICATION.json. The original49/13regression evidence was not rerun.
''')
print('Verdict',verdict,'B4/EAG equivalent',equal,'/',len(pairs));print(json.dumps(aggregate,indent=2))
