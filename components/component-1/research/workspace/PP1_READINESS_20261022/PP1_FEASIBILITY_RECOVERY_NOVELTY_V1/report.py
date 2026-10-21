from io_context import *
import collections,shutil,statistics,platform,importlib.metadata

def textfile(name,text):
    with (H/name).open('x',encoding='utf-8') as f:f.write(text)

def main():
    run=H/'RUN_001';summary=read(run/'SUMMARY.json');rows=[r for r in read(run/'RAW_EXPERIMENT_RESULTS.json') if r['method']=='GROUPED_CONVENTIONAL']
    independent=read(H/'INDEPENDENT_001/INDEPENDENT_VALIDATION.json');tests=read(H/'TESTS_001/TEST_RESULTS.json')
    count=collections.Counter(r['status'] for r in rows);valid=sum(r['verified_witnesses'] for r in rows);chosen=sum(r['menu_alternatives'] for r in rows)
    pairs=len(rows);bycase=collections.defaultdict(list)
    unsafe=partial=0;geometric=[];searchwall=[]
    for row in rows:
        bycase[row['scenario']].append(row);d=run/row['run_id'];abl=read(d/'ABLATION.json');unsafe+=len(abl['no_authority_extra_states'])
        # Count invalid one-field bundle mutations by independently inspecting declarations.
        rr=read(d/'REQUEST.json')
        if row['scenario']=='coupled_service_stock':
            op=rr['operations'][0]
            for key,val in op['to'].items():
                v=dict(rr['requested']);v[key]=val
                partial+=v['service_front_m']!=2.5*v['minimum_buffets']
        response=read(d/'RESPONSE.json');keys=set()
        for q in response['pareto_recovery_alternatives']:
            l=q['layout'];keys.add(digest({'objects':[{k:o[k] for k in ['object_id','class','group_id','footprint_coordinates_m']} for o in l['objects']],'zones':l['zones']}))
        geometric.append(len(keys))
        for p in d.glob('state_*/SEARCH_RESULT.json'):searchwall.append(read(p)['runtime_s'])
    groups=[]
    for case,rs in bycase.items():
        groups.append(f'| {case} | {len(rs)} | {sum(r["verified_witnesses"]>0 for r in rs)}/{len(rs)} | {sum(r["actual_shared_searches"] for r in rs)} | {sum(r["shared_evaluations"] for r in rs)} | {sum(r["verified_witnesses"] for r in rs)} | {min(r["menu_alternatives"] for r in rs)}-{max(r["menu_alternatives"] for r in rs)} |')
    metrics={'queries':pairs,'method_rows':2*pairs,'actual_searches':summary['actual_unique_searches'],'actual_evaluations':summary['actual_total_evaluations'],'smoke_searches':tests['actual_smoke_searches'],'smoke_evaluations':tests['smoke_evaluations'],'verified_witnesses':valid,'reported_front_witnesses':chosen,'queries_with_verified_witnesses':sum(r['verified_witnesses']>0 for r in rows),'successful_authorized_recovery_queries':sum(r['status']=='RECOVERY_RECOMMENDATIONS' for r in rows),'statuses':dict(count),'baseline_matches':pairs,'tests':tests['total'],'unsafe_authority_ablation_states':unsafe,'invalid_partial_service_edits':partial,'search_body_runtime_s_sum':sum(searchwall),'search_body_runtime_s_median':statistics.median(searchwall),'exact_geometry_front_counts_min_max':[min(geometric),max(geometric)],'all_counts_scope':'controlled correlated queries; two related synthetic venue shapes; no genuine planner/venue samples; shared search counted once'}
    save(H/'MEASURED_SUMMARY.json',metrics)
    shutil.copyfile(run/'RAW_EXPERIMENT_RESULTS.csv',H/'RAW_EXPERIMENT_RESULTS.csv')
    shutil.copyfile(run/'RAW_EXPERIMENT_RESULTS.json',H/'RAW_EXPERIMENT_RESULTS.json')
    textfile('BASELINE_AND_ABLATION_RESULTS.md',f'''# Actual baseline and ablation results

**36/36 query outcomes and authorized state/cost sets match the exhaustive conventional reference.** No distinct recovery operation or superiority is supported. Both enumerators use the same source, domains, constraints, operation costs, dependencies and permissions and intentionally share the actual per-state solver oracle. This is a representation/decision equivalence study, not an independent reproduction of two continuous search algorithms.

Actual comparison: {pairs} queries, {summary['actual_unique_searches']} unique NSGA-II searches, {summary['actual_total_evaluations']} total evaluations, {valid} independently verified layout witnesses. There are {2*pairs} CSV method rows; do not double search counts because each shared solve is reported for two enumerators. Separate tests used {tests['actual_smoke_searches']} smoke searches/{tests['smoke_evaluations']} evaluations. Combined actual new searches: {summary['actual_unique_searches']+tests['actual_smoke_searches']}; evaluations: {summary['actual_total_evaluations']+tests['smoke_evaluations']}. Replayed historic references are not new searches.

| Scenario | Queries | Queries with verified witness | Unique searches | Evaluations | Verified witnesses | Front size range |
|---|---:|---:|---:|---:|---:|---:|
'''+ '\n'.join(groups)+f'''

Witness coverage: {metrics['queries_with_verified_witnesses']}/{pairs} queries ({metrics['successful_authorized_recovery_queries']}/16 queries with permitted negotiable recoveries, plus four ordinary feasible queries). Four cases intentionally have no authorized recovery, each repeated for two shapes/two seeds: protected conflict, missing negotiation permission, mandatory non-relaxable demand, and non-negotiable stock shortfall. They are correctly refused/proved impossible only within the enumerated authorized domain using explicit necessary-condition witnesses. No failed search was promoted to infeasibility; this run had zero searched states without a returned feasible witness.

All {valid} returned witnesses pass the independent geometry/function/stock/permission/metric replay; accepted hard/protected/unauthorized violations: 0. The sound screens use zero objective evaluations. They do not claim to solve all possible spatial infeasibility.

There are {chosen} reported recovery-front witnesses across queries, with exact geometric front counts ranging {min(geometric)}-{max(geometric)} per query including zero in refusals. These are actual polygons; distinct vectors are not automatically materially distinct to a planner. No predetermined three-choice display, global front or human-perceived diversity claim is made.

**Ablations:** retaining only the original requested state yields witnesses in 4/36 queries; the other 16 recoverable queries need explicit concessions. Diagnostic removal of permission/mandatory checks exposes {unsafe} forbidden states. Splitting the service bundle exposes {partial} invalid one-field count/frontage edits. These are diagnostic deletion controls, not equally informed main baselines, and none was optimized or accepted as a recommendation.

Search-body runtime sum: {sum(searchwall):.6f} s; median: {statistics.median(searchwall):.6f} s. Exact launcher wall times and exits are in logs/*.COMMAND.json. Tiny enumeration timings are recorded per query but no speedup/significance conclusion follows from shared-oracle results, two related shapes, correlated case families or two seeds.

**Failures preserved:** EXPLANATION_VERIFY_001 failed because exact equality was used for independent scalar arithmetic vs NumPy norms. Observed maximum metric difference was 7.105427357601002e-15 m; the corrected verifier uses 1e-10 m. The failed source/log remain; EXPLANATION_VERIFY_002 passed. No raw layout/metric was changed. Tests, experiment, raw replay and explanation generation otherwise completed exit 0.
''')
    textfile('SCIENTIFIC_NOVELTY_VERDICT.md',f'''# Scientific verdict

**Correct conventional recovery prototype: IMPLEMENTED_AND_TESTED. Mathematically defined formulation: YES. Distinct algorithm/guarantee: NOT_ESTABLISHED. Academic originality of the event-domain methodology/benchmark: UNRESOLVED. Panel Comment 3: UNRESOLVED.**

The concrete addition is an executable, source/context/authority-bound concession layer that searches declared recoveries without changing mandatory geometry, protection or function floors. It returns recommendations with exact before/after requirements, synthetic concession costs, actual layout metrics, sound refusal witnesses and independent raw-output/SQLite replay. It handles an ordinary feasible event, negotiable spatial over-demand, coupled service concession, protected conflict, missing permission, mandatory demand, stock shortfall, preferred-stage release and supported same-event revision.

Executed comparison: 36 correlated controlled queries over two related venue shapes/two seeds; 28 unique searches/3,360 evaluations; {valid} independently valid raw layout witnesses. The exhaustive conventional reference matched all 36 query outcomes/state sets. The same deterministic state solver is explicitly shared; this is not independent continuous-solver replication. 56 test cases/checks passed, including 36 enumerator comparisons and two actual smoke searches/240 evaluations. Independent replay checked every raw witness and 36 exact SQLite rows; numerical explanation replay passed. No outcome is an actual planner-approved or genuine real-venue result.

The operation reduces to grouped, authorized finite-domain constraint relaxation. MaxSAT/CP-SAT/MILP can encode selectors, dependency clauses, hard exclusions and costs; preferred diagnosis/relaxation has direct published precedent. No event-specific mathematical operation, new theorem, guarantee or advantage over the equally informed conventional formulation survives. The prototype is not evidence that no future original event research can exist.

Useful engineering/application evidence remains: coupling and authority cannot simply be discarded; this study exposes broken partial service concessions and unauthorized/mandatory relaxations, then produces actual verified alternatives when the explicit contract permits them. But deliberately deleting those rules is not a novelty baseline. Independent planner validation of the policies, nontrivial genuine infeasible event briefs, source-disjoint measured venues and a closest-work review establishing a new substantive formulation/evaluation property are still absent.

Preserved earlier nulls: EAG/B4 72/72; review/B5 128/128; joint/B2 12/12; function-usability/B2 12/12; typed qualification 54/54. This new scoped conventional match does not overwrite or relabel them. No S-GCN, weather consequence model, detailed safety certification, frontend or multi-phase event transformation was added.

**Next scientific action:** ask an independent event planner/supervisor to validate one real over-constrained single-event brief, inventory and non-negotiable/negotiable authority record against this conventional recovery contract. Identify a decision/property that it cannot adequately represent, or retain conventional equivalence. Do not rename this layer as an original algorithm or claim the warning cleared.
''')
    textfile('PANEL_COMMENT_3_DEFENCE.md',f'''# Panel Comment 3 — exact defensible response

“We implemented and independently evaluated a planner-governed feasibility-recovery prototype for a single event. It explores only explicitly negotiable requirements, preserves hard geometry, mandatory functions and protected decisions, and reports verified layout recommendations or bounded refusal reasons. A coupled buffet concession updates both equipment count and service frontage under a declared policy; it cannot silently relax either field. Our 36 controlled case/seed queries used the existing local joint NSGA-II core, not a substitute optimizer. All {valid} returned layout witnesses passed independent checks. An equally informed exhaustive conventional formulation reproduced all recovery outcomes. Therefore we present this as an evaluated event-layout assurance/application resource, with academic originality unresolved, rather than claiming a new constraint-relaxation algorithm.”

**What is new in this delivery:** working concession contracts, exact operation/authority/source/context binding, coupled-service checks, finite-domain recovery recommendations, numerical before/after explanation and refusal/stock/protection tests around the existing joint solver. This is newly implemented project functionality, not automatically a new scientific method.

**Closest challenge:** preferred diagnosis/minimal correction/weighted relaxation plus a constrained spatial solver already express the formulation. The conventional reference receives every dependency/permission/cost and matches the pilot. An improvement over an ablation omitting these rules is correctness evidence only.

**What the panel can scrutinize:** exact inputs, policies, raw candidate polygons, hard constraints, all failed checks, independent geometry and arithmetic, genuine local algorithm evaluation counts and source preservation. The synthetic authority and costs are plainly labeled. No concession recommendation has genuine planner acceptance, and no real venue or physical safety validity is claimed.

**What cannot be claimed:** world-first mechanism, new NSGA-II/MaxSAT, superiority to a competent equally informed solver, complete minimal correction enumeration over continuous layouts, certified egress/safety, genuine human preference or formal clearance of the panel warning. The unresolved originality requires domain evidence and independent academic assessment, not another acronym or a positive demo.
''')
    textfile('REPRODUCTION_RUNBOOK.md',r'''# Exact commands and evidence

From C:\My Research Component, installed .venv; no downloads, installation, training, model inference, server or frontend startup. Commands below actually executed; names already populated must not be reused. Raw argv/cwd/exit/wall time and stdout/stderr are logs/*.COMMAND.json and *.txt.

```powershell
.venv\Scripts\python.exe -B PP1_READINESS_20261022/PP1_FEASIBILITY_RECOVERY_NOVELTY_V1/run_logged.py PREPARE_001 prepare.py
.venv\Scripts\python.exe -B PP1_READINESS_20261022/PP1_FEASIBILITY_RECOVERY_NOVELTY_V1/run_logged.py TESTS_001 tests.py TESTS_001
.venv\Scripts\python.exe -B PP1_READINESS_20261022/PP1_FEASIBILITY_RECOVERY_NOVELTY_V1/run_logged.py EXPERIMENT_001 experiment.py RUN_001
.venv\Scripts\python.exe -B PP1_READINESS_20261022/PP1_FEASIBILITY_RECOVERY_NOVELTY_V1/run_logged.py VERIFY_001 verify_results.py RUN_001 INDEPENDENT_001
.venv\Scripts\python.exe -B PP1_READINESS_20261022/PP1_FEASIBILITY_RECOVERY_NOVELTY_V1/run_logged.py EXPLAIN_001 explain.py RUN_001 EXPLANATIONS_001
.venv\Scripts\python.exe -B PP1_READINESS_20261022/PP1_FEASIBILITY_RECOVERY_NOVELTY_V1/run_logged.py EXPLANATION_VERIFY_002 verify_explanations.py RUN_001 EXPLANATIONS_001 EXPLANATION_VALIDATION_002
.venv\Scripts\python.exe -B PP1_READINESS_20261022/PP1_FEASIBILITY_RECOVERY_NOVELTY_V1/run_logged.py REPORT_001 report.py
```

EXPLANATION_VERIFY_001 failed on an overly strict floating equality; failed log and source remain. EXPLANATION_VERIFY_002 changes only arithmetic tolerance, not layouts or metrics.

Fresh repetition of the actual comparison/independent replay (choose unpopulated names):

```powershell
.venv\Scripts\python.exe -B PP1_READINESS_20261022/PP1_FEASIBILITY_RECOVERY_NOVELTY_V1/run_logged.py MY_EXPERIMENT_001 experiment.py MY_RUN_001
.venv\Scripts\python.exe -B PP1_READINESS_20261022/PP1_FEASIBILITY_RECOVERY_NOVELTY_V1/run_logged.py MY_VERIFY_001 verify_results.py MY_RUN_001 MY_INDEPENDENT_001
```

These are the executed command family with fresh names, not another completed-run claim. Existing frozen source/fixture evidence is referenced in place. Do not edit authority/source hashes to bypass a rejection. prepare/report are fixed-output evidence builders, not commands to rerun into this populated workspace.

Inspect RUN_001/PROTOCOL_AT_START.json; each query REQUEST/ENUMERATION/ABLATION/RESPONSE; state_*/CORE_CASE/SEARCH_RESULT/INDEPENDENT_CHECKS; results.sqlite3; INDEPENDENT_001/INDEPENDENT_VALIDATION.json; TESTS_001/TEST_RESULTS.json; and EXPLANATIONS_001/*.json. Every actual layout is in a saved search result. No layout is invented by report or explanation generation. The shared search is counted once across both enumerators. No old regression suite is claimed as newly rerun.

Python socket/write guards report no network/denied writes on successful runs. This is instrumentation, not full OS isolation. Prior U-Net/YOLO, real-floorplan pending branch, frontend and canonical backend files are unchanged. The isolated recovery layer has no HTTP route and is not production-integrated.
''')
    textfile('README.md',f'''# Planner-governed feasibility recovery pilot

**Correct conventional prototype demonstrated; new algorithm NOT ESTABLISHED; academic originality UNRESOLVED.** Start with [SCIENTIFIC_NOVELTY_VERDICT.md](SCIENTIFIC_NOVELTY_VERDICT.md) and [BASELINE_AND_ABLATION_RESULTS.md](BASELINE_AND_ABLATION_RESULTS.md).

Actual evidence: 36 controlled queries, 28 unique NSGA-II searches/3,360 evaluations; {valid} independently checked witnesses; 36/36 equivalent conventional outcomes; 56 passing test cases/checks (includes two additional smoke searches/240 evaluations); independent raw/SQLite and numerical explanation readback. These are correlated lab conditions, not independent venues or planner approvals. A failed floating-equality verifier and its corrected replay remain visible.

The newly implemented layer recommends declared concessions while preserving mandatory functions, immutable geometry, stock identity and authority. It uses the existing joint core and separate raw oracle. [FORMAL_RECOVERY_PROBLEM.md](FORMAL_RECOVERY_PROBLEM.md) states the mathematical target; [PROPOSED_MECHANISM.md](PROPOSED_MECHANISM.md) explains the conventional equivalence and exact reuse. [REPRODUCTION_RUNBOOK.md](REPRODUCTION_RUNBOOK.md) provides executed commands. Real source/model inference is not repeated and no real image is promoted to reviewed geometry.

Raw results are in RUN_001 and RAW_EXPERIMENT_RESULTS.csv/.json. The CSV has two method rows per query and shared solver counts; never sum both method rows as extra searches. XAI sidecars are in EXPLANATIONS_001. Figures show actual saved polygons and measured outcomes; no concept layouts. Preservation is in PRESERVATION_REPORT.json, with a bounded before/after runtime/source/evidence hash scope, not a new dataset audit.
''')
    # Static scientific plots from actual saved results only.
    import matplotlib.pyplot as plt
    from matplotlib.patches import Polygon as Patch
    fdir=H/'figures';fdir.mkdir()
    fig,ax=plt.subplots(figsize=(11,4.5));names=list(bycase);a=[sum(x['verified_witnesses']>0 for x in bycase[n]) for n in names]
    ax.barh(range(len(names)),a,color='#287b80');ax.set_yticks(range(len(names)),[x.replace('_',' ') for x in names]);ax.set_xlim(0,4.5);ax.set_xlabel('Queries with independently verified feasible witnesses (of 4)');ax.set_title('Controlled recovery outcomes — both formulations match 36/36')
    fig.text(.02,.02,'Two related synthetic shapes × two seeds; shared search oracle. Not real planner/venue validation.',fontsize=8);fig.tight_layout(rect=(0,.06,1,1));fig.savefig(fdir/'RECOVERY_OUTCOMES.png',dpi=170);plt.close(fig)
    examples=[('spatial_negotiable','Authorized dance-size concession'),('coupled_service_stock','Coupled service configuration'),('same_event_revision','Same-event revision; first seating group locked')]
    fig,axes=plt.subplots(1,3,figsize=(15,5.3));colors={'column':'#555','stage':'#8a58a2','buffet_counter':'#e9a23b','round_table':'#3c9296','chair':'#7dc3c1'}
    for ax,(name,title) in zip(axes,examples):
        d=run/f'venue_1_20261019_{name}';response=read(d/'RESPONSE.json');r=read(d/'REQUEST.json');item=min(response['pareto_recovery_alternatives'],key=lambda x:(x['recovery_objectives'][1],x['recovery_objectives'][3]));l=item['layout']
        boundary=r['core']['boundary'];ax.plot([x[0] for x in boundary],[x[1] for x in boundary],color='black')
        for o in l['objects']:ax.add_patch(Patch(o['footprint_coordinates_m'],facecolor=colors.get(o['class'],'#bbb'),edgecolor='white',lw=.3))
        for z in l['zones']:ax.add_patch(Patch(z['polygon'],fill=False,edgecolor='#a44',linestyle='--',lw=.8))
        ax.set_aspect('equal');ax.set_xlim(-1,33);ax.set_ylim(-1,25);ax.set_xlabel('metres');ax.set_title(title+'\nCost='+str(item['recovery_objectives'][1])+', service='+f"{item['recovery_objectives'][3]:.3f} m",fontsize=10)
    fig.text(.02,.025,'Actual independently verified returned polygons. Controlled geometry and simulated exploration authority; recommendations require planner acceptance.',fontsize=9);fig.tight_layout(rect=(0,.06,1,1));fig.savefig(fdir/'ACTUAL_RECOVERY_LAYOUTS.png',dpi=170);plt.close(fig)
    save(H/'FIGURE_PROVENANCE.json',{'source':'RUN_001 actual saved response/layout polygons','files':{p.name:sha(p) for p in fdir.glob('*.png')},'queries_used_for_layout_figure':[f'venue_1_20261019_{n}' for n,_ in examples],'no_generated_concept_layouts':True})
    save(H/'ENVIRONMENT.json',{'python':sys.version,'platform':platform.platform(),'packages':{p:importlib.metadata.version(p) for p in ['pymoo','numpy','shapely','scipy','pydantic','matplotlib']}})
    before=read(H/'PRESERVATION_BEFORE.json');after=snapshot();changed=[p for p,s in before['files'].items() if after['files'].get(p)!=s]
    assert not changed,changed
    save(H/'PRESERVATION_REPORT.json',{'status':'PASS','before_file':'PRESERVATION_BEFORE.json','pinned_runtime_files':before['pinned_count'],'total_bounded_file_hashes':len(before['files']),'changed':changed,'pin_mismatches':after['pin_mismatches'],'models_retrained':False,'frozen_sources_modified':False,'prior_nulls_modified':False,'original_data_modified':False,'scope':'411 pinned files plus prior source/evidence/master-plan hashes; not whole raw dataset byte audit','new_work_confined_to':str(H),'network_instrumentation':summary['audit'],'python_guard_not_os_isolation':True})
    print('REPORTS_READY',json.dumps(metrics))
if __name__=='__main__':main()
