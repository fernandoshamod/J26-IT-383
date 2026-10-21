from usability_env import *
import statistics,collections,itertools
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Polygon as Patch

def write(name,text):
    p=H/name
    with p.open('x',encoding='utf-8') as f:f.write(text.strip()+'\n')

def main():
    s=read(H/'FINAL_SUMMARY.json');rows=read(H/'RAW_EXPERIMENT_RESULTS_FINAL.json');tests=read(H/'TEST_RESULTS_FINAL.json');manifest=read(H/'INPUT_MANIFEST.json')
    db=sqlite3.connect(H/'results.sqlite3');assert db.execute('select count(*) from results').fetchone()[0]==60;assert db.execute('select count(*) from qualified').fetchone()[0]==60
    menus=[];rejected=[];lock_checks=0
    for row in rows:
        result=read(row['result_path']);q=read(H/'independent_final'/(row['id']+'.json'));c=read(Path(row['result_path']).parent/'CASE.json')
        stored=db.execute('select qualification_json,sha256 from qualified where id=?',(row['id'],)).fetchone();assert json.loads(stored[0])==q['qualification'] and stored[1]==digest(q['qualification'])
        chosen=[]
        for i,(layout,check) in enumerate(zip(result['candidates'],q['checks'])):
            if row['phase']=='revision':
                ref=read(Path(row['result_path']).parent/'REFERENCE.json');a=[o for o in layout['objects'] if o['group_id']=='seating_group_0001'];b=[o for o in ref['objects'] if o['group_id']=='seating_group_0001'];assert a==b;lock_checks+=len(a)
            if not check['valid']:rejected.append(dict(run=row['id'],index=i,failed=[t['function'] for t in check['access']['targets'] if not t['certified']]));continue
            if row['method']!='NEW':continue
            def distinct(a,b):
                aa={o['object_id']:o for o in a['objects']};bb={o['object_id']:o for o in b['objects']}
                if set(aa)!=set(bb):return True
                if any(Polygon(o['footprint_coordinates_m']).centroid.distance(Polygon(bb[k]['footprint_coordinates_m']).centroid)>=.5 for k,o in aa.items()):return True
                za={z['zone_id']:Polygon(z['polygon']) for z in a['zones']};zb={z['zone_id']:Polygon(z['polygon']) for z in b['zones']}
                return any(za[k].hausdorff_distance(zb[k])>=.5 for k in za)
            if len(chosen)<3 and all(distinct(layout,result['candidates'][j]) for j in chosen):chosen.append(i)
        if row['method']=='NEW':menus.append(dict(run=row['id'],indices=chosen,layout_sha256=[digest(result['candidates'][i]) for i in chosen],distinct_choices=len(chosen),policy='Greedy actual independently certified menu: different equipment IDs, or >=.5m object-centroid displacement, or >=.5m zone Hausdorff change; not transport feasibility'))
    db.close();save(H/'ACTUAL_MENU_SELECTION.json',menus);save(H/'FAILED_LAYOUT_EXAMPLES.json',rejected)
    summaryrows=[]
    for method,v in s['methods'].items():summaryrows.append(dict(method=method,**{k:v[k] for k in ['runs','runs_with_certified_output','returned','certified','certified_percent','evaluations','median_optimizer_runtime_s','repair_access_queries','repair_pose_trials']}))
    # Flat artifact-tool authoring inputs; raw JSON keeps genuine nulls.
    save(H/'CSV_AUTHORING_INPUT.json',[{k:('' if v is None else v) for k,v in r.items()} for r in rows])
    save(H/'SUMMARY_CSV_AUTHORING_INPUT.json',summaryrows)
    figs=H/'figures';figs.mkdir(exist_ok=False)
    methods=METHODS;colors=['#87929c','#4776ac','#26836b','#e0a528','#a885b4']
    fig,axs=plt.subplots(1,3,figsize=(14,4.6),layout='constrained')
    for ax in axs:ax.spines[['top','right']].set_visible(False);ax.grid(axis='y',alpha=.2);ax.set_axisbelow(True)
    vals=[s['methods'][m]['certified'] for m in methods];bars=axs[0].bar(methods,vals,color=colors)
    for b,m in zip(bars,methods):v=s['methods'][m];axs[0].text(b.get_x()+b.get_width()/2,b.get_height()+1,f"{v['certified']}/{v['returned']}",ha='center',fontsize=9)
    axs[0].set_ylim(0,56);axs[0].set_ylabel('Certified layouts');axs[0].set_title('Independent qualification of actual returns')
    axs[1].bar(methods,[s['methods'][m]['runs_with_certified_output'] for m in methods],color=colors);axs[1].set_ylim(0,13);axs[1].set_title('Runs with at least one certified output');axs[1].set_ylabel('Runs / 12 per method')
    axs[2].bar(methods,[s['methods'][m]['median_optimizer_runtime_s'] for m in methods],color=colors);axs[2].set_title('Measured optimizer wall time');axs[2].set_ylabel('Median seconds; independent replay excluded')
    fig.suptitle('60 actual searches: conventional B2 and NEW match in all 12 pairs',fontsize=14)
    fig.savefig(figs/'MEASURED_COMPARISON.png',dpi=160);plt.close(fig)
    # Actual polygons and independent positive route witnesses: failure vs successful repair vs revision.
    keys=['barrier_20261019_initial_B0','barrier_20261019_initial_NEW','barrier_20261019_revision_NEW']
    fig,axs=plt.subplots(1,3,figsize=(15,5),layout='constrained')
    palette={'column':'#333333','wall':'#333333','stage':'#7c68ab','buffet_counter':'#d78b37','round_table':'#58a7b1','chair':'#a5ced1'}
    provenance=[]
    for ax,key in zip(axs,keys):
        row=next(r for r in rows if r['id']==key);res=read(row['result_path']);lay=res['candidates'][0];check=read(H/'independent_final'/(key+'.json'))['checks'][0]
        for obj in lay['objects']:ax.add_patch(Patch(obj['footprint_coordinates_m'],closed=True,facecolor=palette.get(obj['class'],'gray'),edgecolor='white',linewidth=.3))
        for zone in lay['zones']:ax.add_patch(Patch(zone['polygon'],closed=True,fill=False,edgecolor='#1d754c',linestyle='--',linewidth=1))
        for target in check['access']['targets']:
            if target['certified']:
                a=np.asarray(target['path']);ax.plot(a[:,0],a[:,1],color='#3774ad',alpha=.55,linewidth=.65)
            else:ax.plot(*target['goal'],'rx',ms=10,mew=2)
        ax.plot(*ORIGIN,'k*',ms=10);ax.set(xlim=(0,32),ylim=(0,24),aspect='equal',xlabel='metres',ylabel='metres')
        ax.set_title(key.replace('barrier_20261019_','')+'\n'+('CERTIFIED' if check['valid'] else 'NOT FUNCTION-USABLE'),fontsize=11)
        provenance.append(dict(run=key,result_path=row['result_path'],layout_sha256=digest(lay),validator='independent_final/'+key+'.json'))
    fig.suptitle('Actual returned polygons: protected barrier stays fixed; activity placement changes',fontsize=13)
    fig.savefig(figs/'ACTUAL_FAILURE_REPAIR_REVISION.png',dpi=170);plt.close(fig);save(H/'FIGURE_PROVENANCE.json',provenance)
    matched_quality=[p['new_minus_b1_service'] for p in s['pairs'] if p['new_minus_b1_service'] is not None]
    stats=dict(usable_total=sum(r['usable'] for r in rows),returned_total=sum(r['returned'] for r in rows),runs_with_usable=sum(r['usable']>0 for r in rows),protected_individual_records_checked=lock_checks,material_choices={str(n):sum(m['distinct_choices']==n for m in menus) for n in range(4)},paired_common_feasible_service_n=len(matched_quality),paired_new_minus_b1_service_m=matched_quality,mean_new_minus_b1_service_on_common_feasible=statistics.mean(matched_quality) if matched_quality else None)
    save(H/'ADDITIONAL_MEASURED_STATS.json',stats)
    lines=['| Method | Certified / returned | Runs with certified output / 12 | Median search s | Evaluations |','|---|---:|---:|---:|---:|']
    for m,v in s['methods'].items():lines.append(f"| {m} | {v['certified']}/{v['returned']} | {v['runs_with_certified_output']}/12 | {v['median_optimizer_runtime_s']:.3f} | {v['evaluations']} |")
    write('README.md',f'''# Function-usability research V1 — finished bounded experiment

**Actual search executed. Distinct algorithm NOT ESTABLISHED; NO-GO for an exclusive novelty claim.** Conventional B2 and NEW have identical evaluation traces, repair traces and candidate polygons in 12/12 matched case/seed/phase pairs. This is conventional accessibility-constrained layout engineering and a controlled assurance/benchmark resource, with academic application originality unresolved.

60 search invocations completed, 14,400 actual pymoo evaluations. {stats['runs_with_usable']}/60 runs yielded at least one independently certified layout; {stats['usable_total']}/{stats['returned_total']} reported candidates certified. Search execution success does not imply feasible output success. B1's no-output runs are bounded-search outcomes, not global infeasibility proofs.

15/15 test cases PASS: 13 functional/admission cases and two explicit always-accept/always-refuse mutation controls, not 15 independently sampled venues. See TEST_RESULTS_FINAL.json. Three related synthetic geometries × two seeds × initial/revision × five methods. No genuine human/real-venue usability validation.

Read COMPARISON_RESULTS.md, SCIENTIFIC_NOVELTY_VERDICT.md, MATHEMATICAL_METHOD.md and RUNBOOK.md. Source is in source/, raw search data in raw/, final independent route witnesses/certificates in independent_final/, exact persistence in results.sqlite3. ACTUAL_MENU_SELECTION.json contains only actual materially distinct returned choices; three are never guaranteed. No frozen source was edited.
''')
    write('COMPARISON_RESULTS.md',f'''# Measured comparison

{chr(10).join(lines)}

Every run uses 40 individuals and exactly 240 objective/constraint evaluations (six populations); full traces are saved. The output policy selects the first four distinct decision vectors from actual finite nondominated returns. These are not independent experiments or a global Pareto frontier. No 100% measure uses empty outputs as a denominator: B1/ablation have 16/16 certified returned candidates but only 4/12 productive runs. B0 intentionally omits access constraints, so improvement over B0 alone cannot establish originality.

B2 and NEW agree in all 12 paired evaluation/proposal/candidate traces. B1 and repair-disabled ablation agree in all 12 pairs. No superiority over competent conventional repair is supported. Additional repair work is disclosed: each B2/NEW method totals 4,670 repair access queries and 6,326 pose trials, in addition to 2,880 fitness access queries. B1 has 2,880 fitness access queries and no repair trials. Identical fitness budgets are not identical wall time or primitive-operation budgets. B2 and NEW have exactly matching additional counts and maximum 16 pose attempts per proposed repair. B0 monitors the same access information but does not enforce it. Methods share variables, origins, stock, permissions, initial samples and objective definitions; repair changes sampling and offspring, not information availability.

Mean NEW minus B1 certified-candidate count per run: {s['paired_summary']['new_minus_b1_mean_certified_candidates']:.6f}. Geometry-cluster means: {s['paired_summary']['geometry_cluster_means']}. Exact 27 size-three cluster resamples give descriptive 2.5/97.5 percentiles {s['paired_summary']['exact_27_cluster_resamples_percentile_2_5_97_5']}; only three related synthetic configurations exist. This is not evidence of population significance, independent real-venue replication or human usability. NEW minus B2 is exactly zero. Runtime differences between identical B2/NEW traces are execution noise, not speedup evidence.

Common-feasible NEW/B1 service-quality pairs: {len(matched_quality)}, differences in metres {matched_quality}; no comparison imputes objective values for no-output runs. All individual objective values and menu-vector distances are retained in RAW_EXPERIMENT_RESULTS_FINAL.json. The latter is an unscaled mixed decision-vector distance, not a physical metre metric. Material choices instead use actual object/zone geometry, as recorded in ACTUAL_MENU_SELECTION.json. Count distribution: {stats['material_choices']}.

First independent verification conservatively failed 24 candidates because the single nearest grid node did not attach to an otherwise reachable exact endpoint. VERIFY_AT_FIRST_BENCHMARK.py, raw/*/INDEPENDENT.json and RAW_EXPERIMENT_RESULTS.json remain unchanged. The corrected verifier tries nearby collision-checked connectors and independently replays all returned layouts. It changed no search, objective, permission, layout or evaluation count. FINAL_SUMMARY.json and independent_final/ are final authority. A grid failure still means not certified, not continuous-space impossibility. No failed check was silently turned into a PASS.
''')
    write('MATHEMATICAL_METHOD.md',r'''# Explicit function-usability and search model

Reuse the original 21-variable mixed decoder: four seating XY centres, stage XY/orientation, two counter XY/orientations, counter allocation and dance XY/width (depth = required area/width). Tables/chairs are the original typed rigid groups. Requirements are 32 seats, one stage, at least one counter and 16 m² dance initially; the same-event revision requires two counters and 25 m² dance and protects the first group's nine individual objects. These are declared controlled catalog demands, not real venue capacity statements.

For required function f define U_f = declaration ∧ typed allocated stock ∧ dimensions/geometry ∧ local relations ∧ source/authority qualification ∧ access. Seating has four designated group approach ports (cx,cy−2.12); stage and each allocated buffet use their reserved approach-zone centroids; dance uses its centroid. All named ports must be connected to the declared origin (1,1). No individual chair reach, stage ascent, crowd flow or queue functionality is asserted.

With declared disc radius r=.3m and polygonal boundary V, C_free(x)=(V eroded by D_r) \ union_i (O_i(x) dilated by D_r). Conservative seating-group envelopes have radius 1.72m and remain impassable even between individual chairs. Furniture/columns/walls obstruct travel; stage/buffet approach and dance zones do not themselves obstruct travel. Search uses polygonal buffers and component membership. Access violation A(x)=sum over designated targets of 1[target is not in the origin's free component]. Standard hard-constraint NSGA-II receives CV_local(x)+A(x). The heterogeneous violation score is an algorithmic ordering scalar, not a physical unit or certified risk measure.

Objectives remain unchanged: mean seat-to-stage Euclidean distance plus .25 mean seat-to-nearest-allocated-counter distance; sum stable-control XY change from the common source-qualified seed/reference; allocated counter count. Movement is design-control displacement, not a collision-free equipment-transport plan. Source/control/stock/permission admission runs before minimize. Revision canonicalization and independent individual-object comparison keep group 1 fixed; every fixed obstacle remains unchanged.

B0 = original joint Measures/decoder/objectives and standard SBX/PM, historical local constraints only. B1 = same NSGA-II plus A. NEW proposes: choose one disconnected function witness, map it to a movable variable block, sample at most 16 XY placements, require containment/local clearance and an access witness for that block, keep the first qualifying pose, then ordinary NSGA-II survival. B2 expresses the same operation conventionally as disconnected-block feasibility repair. Both share the geometric kernel; their independently stated witness-to-block selections are algebraically identical. They are equivalent by construction under these assumptions, which is a reason to stop the exclusive novelty claim. Ablation removes repair and is operationally B1. No learned function or original connectivity algorithm is introduced.

The independent verifier does not call access_fitness or its component decomposition. It reconstructs targets/obstacles from exported polygons and identities, uses exact analytic inflated seating disks and unbuffered polygon distance, and constructs a .25m four-neighbor graph. Every accepted path segment, including endpoint connectors, is checked against boundary and obstacle distances. Conservative failure is UNKNOWN/not certified. Local typed/stock/permission/geometry checks reuse the already independent old oracle. Numerical service objectives are independently recomputed. Independent implementation still shares Shapely geometry primitives and declared modelling assumptions; it is not a separate physical measurement study.
''')
    write('CLOSEST_PRIOR_ART.md',r'''# Targeted closest-primary-work challenge

No broad new survey. Full-text sections inspected through the web tool on 19 October 2026; implementations were not reproduced.

1. Merrell, Schkufza, Li, Agrawala, Koltun (2011), *Interactive Furniture Layout Using Interior Design Guidelines*, ACM TOG/SIGGRAPH. [Author PDF](https://paulmerrell.org/furnitureLayout2.pdf), pp.3–5, Sections 2.1 and 3.1–3.2. Explicit clearance dilation, disc configuration space, component-based circulation cost and stochastic layout search already occur together. Our typed event ports/hard constraints/protected revision narrow the application but do not establish an original operation. Earlier Stanford/Berkeley links failed; the author PDF was successfully read. No claim of reproducing its GPU/MCMC implementation.

2. Wang et al. (2026), *Function2Scene: 3D Indoor Scene Layout from Functional Specifications*. [Full-text version](https://arxiv.org/html/2605.30819), Table 1, Sections 3 and 4.2, Appendix C.3. Functional constraints, circulation/path-width tools and targeted local repair directly challenge the proposed concept. Our deterministic governed Wedding contract differs in application and assurance; exclusivity or superiority is not established. Appendix tool descriptions are not independently tested implementations.

3. LaValle (2006), *Planning Algorithms*, [Chapter 4](https://lavalle.pl/planning/ch4.pdf), Section 4.3.1 Formulation 4.1, Section 4.3.2 Eq.4.37. Inflated-obstacle free space and start/goal path feasibility are standard. Our disc radius is an explicit synthetic sensitivity assumption, not a value taken from this source or a legal requirement.

4. Contardo and Costa, *On the optimal layout of a dining room in the era of COVID-19 using mathematical optimization*, [author full text](https://arxiv.org/html/2108.04233), Sections 3.1–3.4. Predeclared table/chair configurations, obstacles and compatibility support competent event/furniture baselines; that model should not be recast as a certified human-route solver. Our B2 is a conventional NSGA-II feasibility-repair implementation, not their published set-packing code.

Search failures and scope: a mistyped arXiv identifier 1105.3720 resolved to unrelated physics and was excluded; MIME's CVF page was inaccessible in this pass and is not treated as a freshly verified method. A targeted search cannot prove worldwide uniqueness. These four sources already suffice to reject the broad claim that usability-coupled layout search or configuration-space repair is newly invented here.

Previous sourced product/system comparison is reused from ../PP1_FINAL_PANEL_RESOLUTION_V1/01_EXISTING_SYSTEMS_AND_RESEARCH_GAP.md and 02_REFERENCED_COMPARISON_MATRIX.csv. Product internals are unknown; no absence claim is inferred from marketing documentation.
''')
    write('SCIENTIFIC_NOVELTY_VERDICT.md',f'''# Scientific verdict

**Distinct algorithm: NOT ESTABLISHED. Exclusive novelty/superiority claim: NO-GO. Academic originality of the applied methodology/benchmark: UNRESOLVED.**

Actual search-level access coupling is implemented and tested. Its benefit over historical incomplete local checks is engineering evidence. Conventional B2 reproduces NEW's complete evaluated/proposed/candidate traces in 12/12 pairs, with identical oracle/repair work; no operative distinction survives. B1 is equally informed but has no repair heuristic; finite-budget differences cannot establish a new problem or algorithm. No comparison with a fully tuned global solver or published Function2Scene implementation was performed.

Supported contribution: a reproducible controlled Wedding function-usability contract/benchmark with source/authority-bound geometry, protected same-event changes, explicit routes and independent checked output qualification, exposing local-to-global failures. This is a concrete evaluated application/assurance resource, not proof of academic novelty, physical safety, real planner benefit or real venue validity. Minimum missing originality evidence is independent event-domain requirements/annotation validation and a closest-work review identifying a substantive new formulation/property; no such operation is supplied by another renamed repair routine.

All 60 searches completed; {stats['runs_with_usable']} yielded certified output. All 15 tests passed; they include two mutation controls and related controlled cases, not independent venue samples. No claim that every search succeeded or that all B0 candidates are usable. Previous 72/72, 128/128 and 12/12 null findings remain unchanged. New B2/NEW equality is another scoped null, not a positive originality result.

STOP new algorithm discovery/implementation for this mission. PP1 should show the working bounded prototype and this null result, while asking the supervisor/panel to assess the applied contribution and agree an explicit next scientific acceptance criterion. The warning is not declared formally cleared.
''')
    write('FAILURE_CASES.md',f'''# Failures and negative evidence

Final independent checks reject {len(rejected)} reported B0 candidates: their local typed geometry passes, but the barrier leaves required functions disconnected. Exact identities and failed functions: FAILED_LAYOUT_EXAMPLES.json. B1/ablation return no candidates in eight cases each at the 240-evaluation budget; that does not prove infeasibility. B2/NEW demonstrate feasible outputs in those matched cases with more repair computation.

TEST_RESULTS_FINAL.json contains seven analytically labelled routing unit cases (two positives and five negatives), one complete four-function source-qualified positive, changed-demand and stock-mismatch negatives, three pre-search admission negatives, and two mutation controls. The protected-barrier unit case fixes the destination across a fixed barrier; it is not an optimizer proof that a freely relocated dance zone is impossible. Blocked approach probes test named ports, not every square metre of approach zones. Invalid permission/measurement/source trials call minimize zero times. No failed dependency was hidden.

Setup attempts SETUP_001 and SETUP_002 failed (local common.py shadowing the compiler module, then exclusive-write preservation evidence). SETUP_003 passed. The colliding local module was renamed usability_env.py; COMMON_AT_SETUP_FAILURE.py remains. Old code was untouched. REPLAY_001 corrects nearest-cell attachment in the new independent verifier; 24 certification decisions changed with checked alternative connectors. VERIFY_AT_FIRST_BENCHMARK.py and all original raw checks remain. First and final tests remain separate; repeating the same tests is not new coverage.
''')
    write('PANEL_COMMENT_RESPONSE_MATRIX.md',r'''# Three panel warnings — bounded response

| Comment | Evidence and supported answer | Status / remaining boundary |
|---|---|---|
| Existing solutions not showcased | Reuse sourced Cvent/Prismm comparison; closest academic mechanisms in CLOSEST_PRIOR_ART.md. Existing systems offer documented design/seating/collaboration features; internal algorithms remain unknown. New measured failure: 32/48 locally valid B0 returns fail declared function access. | Evidence supplied for discussion; do not claim competitors lack these functions or that the warning is formally cleared. |
| Develop without APIs | Reuse successful local U-Net/YOLO and optimization traces in PP1_FINAL_PANEL_RESOLUTION_V1/08_RAW_BENCHMARKS/LOCAL_MODEL_002 and LOCAL_JOINT_001; new ENVIRONMENT.json traces local pymoo and source modules. No new perception run is claimed. | Tested hosted-AI/optimization-service independence supported; local Python/library/internal HTTP APIs still exist. Literal no-API wording requires panel clarification. Python socket guards are not OS isolation. |
| Insufficient novelty | Real search-coupled usability constraints/repair, independent paths, fair B2 equality and preserved nulls. Application assurance/benchmark evidence exists; distinct algorithm and academic originality are not established. | Scientifically UNRESOLVED as a novelty warning; no formal clearance. Agree independent domain evidence and academic acceptance criterion rather than rename another conventional method. |
''')
    write('PP1_STOP_GO.md',r'''# PP1 decision and essential next task

GO: demonstrate the actual local perception branch producing pending-review candidates, separately demonstrate the controlled metric Wedding/Scene/EAG workflow, then display a B0 disconnected function and the actual B2/NEW corrected layout with independent paths, permitted same-event revision, stock/source refusal and saved numerical qualification. Display exact denominators and one retained failure. Use original product comparisons and disclose the B2 equivalence.

NO-GO: claim a new NSGA-II/connectivity algorithm, new best-in-world score, authenticated planner authority, arbitrary real-venue generation, certified accessibility/egress/safety, every-guest accessibility or external-domain perception success. Do not conflate component membership with a real site survey. This isolated research harness has no new frontend/HTTP production endpoint.

Preserve all eight logics: local perception; reviewed metric Twin; requirement/stock Scene; future historical S-GCN; future weather/detailed safety; actual NSGA-II; governed same-event adaptation; evidence-bound XAI/feedback. A–F remains acquisition → perception → Twin/context → qualification → optimization/adaptation → explanation/decision. S-GCN, weather consequences, detailed safety, genuine human evaluation and real-venue qualification remain unfinished. No multi-phase transformation is added.

Single essential pre-deadline task: hold one supervisor-led acceptance rehearsal of the already verified bounded demonstration, explicitly agree what applied contribution the panel will assess and document unresolved originality/API wording. Do not begin another open-ended algorithm search. No further implementation is justified by this null result.
''')
    write('RUNBOOK.md',r'''# Exact execution and fresh reproduction

From C:\My Research Component, installed .venv; no training, downloads, server, frontend or package installation.

Actual commands (all via source/run_logged.py; logs record argv/cwd/exit/time): SETUP_001/002 failed and were preserved; SETUP_003 experiment.py setup passed; SMOKE_001 experiment.py smoke passed; BENCHMARK_001 experiment.py benchmark passed; TESTS_001 tests.py and TESTS_FINAL tests.py _FINAL passed; REPLAY_001 replay.py passed. REPLAY is independent recertification/readback, not 60 additional searches. REPORT_001 runs closeout.py. CSV authoring and final preservation check are separate commands.

```powershell
.venv\Scripts\python.exe -B PP1_READINESS_20261022/PP1_FUNCTION_USABILITY_RESEARCH_V1/source/run_logged.py BENCHMARK_001 experiment.py benchmark
.venv\Scripts\python.exe -B PP1_READINESS_20261022/PP1_FUNCTION_USABILITY_RESEARCH_V1/source/run_logged.py REPLAY_001 replay.py
```

The populated names above are historical evidence: do not overwrite/replay into them. For a fresh output namespace inside this same workspace:

```powershell
$env:USABILITY_RUN_NAME='MY_REPEAT_001'
.venv\Scripts\python.exe -B PP1_READINESS_20261022/PP1_FUNCTION_USABILITY_RESEARCH_V1/source/run_logged.py SETUP experiment.py setup
.venv\Scripts\python.exe -B PP1_READINESS_20261022/PP1_FUNCTION_USABILITY_RESEARCH_V1/source/run_logged.py SMOKE experiment.py smoke
.venv\Scripts\python.exe -B PP1_READINESS_20261022/PP1_FUNCTION_USABILITY_RESEARCH_V1/source/run_logged.py BENCHMARK experiment.py benchmark
.venv\Scripts\python.exe -B PP1_READINESS_20261022/PP1_FUNCTION_USABILITY_RESEARCH_V1/source/run_logged.py TESTS tests.py _FINAL
.venv\Scripts\python.exe -B PP1_READINESS_20261022/PP1_FUNCTION_USABILITY_RESEARCH_V1/source/run_logged.py REPLAY replay.py
Remove-Item Env:USABILITY_RUN_NAME
```

Stop after any nonzero exit and retain logs. Fresh namespace routing was actually tested for setup and smoke as REPRO_SMOKE_001; a complete second 60-run experiment is not claimed. Source-qualified old fixture dependencies remain in place. Namespace IDs accept letters/digits/underscores only. No manual hash editing is permitted. Fresh reports/CSV can be generated after successful replay; final scientific reports here retain original failure history.

Inspect RAW_EXPERIMENT_RESULTS_FINAL.json/.csv and FINAL_SUMMARY.json first; then raw/<id>/CASE/REFERENCE/RESULT and independent_final/<id>.json. The SQLite results table saves exact raw output; qualified table saves bound independently accepted layout hashes and numerical XAI. Raw search returns are not automatically accepted layouts. ACTUAL_MENU_SELECTION.json only offers materially distinct verified candidates, possibly fewer than three. Open figures/ACTUAL_FAILURE_REPAIR_REVISION.png and MEASURED_COMPARISON.png. They show actual polygons and measured data.
''')
    print('Reports and measured figures produced',stats,flush=True)

if __name__=='__main__':main()
