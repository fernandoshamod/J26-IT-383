"""Raw replay, paired aggregation, diagnostics and measured scientific figures."""
import argparse,copy,sqlite3,statistics,collections,subprocess
from runtime import *
from repair import make_reference
from independent import verify_envelope,verify_candidate
from certificates import is_current
from eag_contracts import Packet

def reference_at(root,method):
    p=root/'INITIAL'/method;r=read(p/'INPUT.json')['scene'];response=read(p/'RESULT.json');ref=make_reference(r,response,read(p/'GRAPH.json'),p)
    p=root/('APPROVAL' if method=='FULL' else 'COMMON_APPROVAL')/method;approved=read(p/'RESULT.json');ref.update(certificate=approved['certificate'],graph=read(p/'GRAPH.json'),pool=approved['candidate_layouts']);return ref

def main(out):
    out.mkdir(parents=True,exist_ok=False);base=HERE/'outputs/EXPERIMENT_FINAL';records=read(base/'RAW_COMPARISON.json');experiment=read(base/'EXPERIMENT_RESULTS.json');tests=read(HERE/'outputs/TESTS_FINAL/TEST_RESULTS.json');checks=[];metrics=[];weak=[]
    def check(name,ok,details=None):checks.append(dict(name=name,passed=bool(ok),details=details))
    check('MAIN_EXPERIMENT_PASS',experiment['passed']);check('ADVERSARIAL_TEST_PASS',tests['passed'] and tests['skipped']==0)
    for r in records:
        root=base/r['unit'];folder=root/r['case']/r['method'];packet=read(folder/'INPUT.json');response=read(folder/'RESULT.json');ref=reference_at(root,r['method']);v=verify_envelope(packet,response,ref)
        check('RAW_CERTIFICATE_LAYOUT_REPLAY_'+r['unit']+'_'+r['case']+'_'+r['method'],v['valid'],v['errors'])
        with sqlite3.connect(folder/'assurance.sqlite3') as db:row=db.execute('SELECT input_json,response_json,sha256 FROM records').fetchone()
        check('SQLITE_'+r['unit']+'_'+r['case']+'_'+r['method'],digest(__import__('json').loads(row[0]))==digest(packet) and digest(__import__('json').loads(row[1]))==row[2]==digest(response))
        native=folder/'ACTUAL_SEARCH/FROZEN_ENGINE_REQUEST.json';adaptive=folder/'ACTUAL_SEARCH/FROZEN_ADAPTIVE_REQUEST.json';n_constraint=0
        if native.exists() or adaptive.exists():
            req=read(native if native.exists() else adaptive);n=req['event_requirements']['guest_count']//8;fixed=len(req['venue_twin']['fixed_obstacles']);bounds=sum(x is not None for x in req['hard_limits'].values())
            n_constraint=n+n*fixed+n*(n-1)//2+bounds if native.exists() else fixed+(n-1)+1+bounds
        metrics.append(dict(r,search_G_vector_evaluations=r['optimizer_evaluations'],search_G_scalar_values_reconstructed=n_constraint*r['optimizer_evaluations'],search_G_dimension=n_constraint,scalar_count_scope='G dimension from saved actual request and unchanged engine formula × actual pymoo n_eval; excludes extra selection/replay calls, not directly instrumented scalar operations'))
        if r['method']=='EAG':
            # Deliberate information-omission diagnostic; never a fair competitor.
            old=ref['layout'];geometry=verify_candidate(packet,response['spec'],old,ref['initial'],ref)
            weak.append(dict(unit=r['unit'],case=r['case'],diagnostic='context-blind replay of an actual prior layout/certificate',fair_comparator=False,old_certificate_current=is_current(packet,ref['certificate']),old_candidate_current_checks=geometry))
    aggregates=[]
    for method in ['FULL','INCREMENTAL','EAG']:
        rows=[r for r in metrics if r['method']==method];statuses=dict(collections.Counter(r['status'] for r in rows));eligible=[r for r in rows if r['status']=='eligible']
        aggregates.append(dict(method=method,scenario_outcomes=len(rows),expected_eligible=sum(r['expected']=='eligible' for r in rows),expected_noneligible=sum(r['expected']!='eligible' for r in rows),statuses=statuses,false_accepts=sum(r['false_accept'] for r in rows),false_refusals=sum(r['false_refusal'] for r in rows),candidate_records=sum(r['candidate_count'] for r in rows),minimize_calls=sum(r['optimizer_calls'] for r in rows),actual_search_evaluations=sum(r['optimizer_evaluations'] for r in rows),search_G_scalar_values_reconstructed=sum(r['search_G_scalar_values_reconstructed'] for r in rows),fallback_attempts=sum(r['fallback'] for r in rows),fallback_frequency=sum(r['fallback'] for r in rows)/len(rows),fallback_successes=sum(r['fallback'] and r['status']=='eligible' for r in rows),protected_changes=sum(r['protected_changes'] for r in rows),unauthorized_changes=sum(r['unauthorized_changes'] for r in rows),function_complete_records=sum(r['function_complete'] is True for r in rows),dirty_graph_nodes_total=sum(r['graph_qualification_nodes'] for r in rows),median_elapsed_seconds=statistics.median(r['elapsed_seconds'] for r in rows),optimizer_seconds_total=sum(r['optimizer_seconds'] for r in rows),candidate_replays_lower_bound=sum(r['full_candidate_replays'] for r in rows),menu_counts=dict(collections.Counter(r['material_menu_count'] for r in eligible)),all_certificates_current=all(r['certificate_current'] for r in rows)))
    save(out/'AGGREGATES.json',aggregates);save(out/'CONSTRAINT_WORK_AND_DISRUPTION.json',metrics);save(out/'WEAK_CONTEXT_OMISSION_DIAGNOSTIC.json',weak)
    unit='VENUE_32_24_SEED_20261017';ref=reference_at(base/unit,'EAG');save(out/'REFERENCE_EAG_V32_S20261017.json',ref);save(out/'INPUT_SCHEMA.json',Packet.model_json_schema())
    # Fresh public CLI execution, not saved-output replay.
    dest=HERE/'outputs/CLI_INITIAL_FINAL';cmd=[sys.executable,'-B',str(HERE/'research.py'),'--input',str(base/unit/'INITIAL/FULL/INPUT.json'),'--out',str(dest.relative_to(HERE))]
    p=subprocess.run(cmd,cwd=ROOT,capture_output=True,text=True);save(out/'CLI_COMMAND_RESULT.json',dict(args=cmd,exit_code=p.returncode,stdout=p.stdout,stderr=p.stderr));check('PUBLIC_CLI_ACTUAL_INITIAL',p.returncode==0,dict(stdout=p.stdout,stderr=p.stderr))
    before=read(base/'PRESERVATION_BEFORE.json');after=snapshot();check('PRESERVATION',before==after,dict(files=len(before)));save(out/'PRESERVATION_AFTER.json',after)
    paired=sum(c['passed'] for c in experiment['checks'] if c['name'].endswith('MATCHED_CANDIDATES'));closures=sum(c['passed'] for c in experiment['checks'] if c['name'].endswith('INCREMENTAL_CLOSURE_MATCH'))
    initial=list(base.glob('*/INITIAL/*/RESULT.json'));initial_evals=sum(read(p)['optimizer_evaluations'] for p in initial)
    final=dict(status='VERIFIED_CONTROLLED_ASSURANCE_PROTOTYPE_STRONG_BASELINE_EQUIVALENCE' if all(c['passed'] for c in checks) else 'FAIL',scenario_instances=experiment['scenario_instances'],method_outcomes=len(records),paired_three_method_matches=paired,incremental_eag_closure_matches=closures,scenario_candidate_records=sum(r['candidate_count'] for r in records),scenario_actual_minimize_calls=sum(r['optimizer_calls'] for r in records),initial_runs=len(initial),initial_evaluations=initial_evals,scenario_evaluations=sum(r['optimizer_evaluations'] for r in records),false_accepts=sum(a['false_accepts'] for a in aggregates),false_refusals=sum(a['false_refusals'] for a in aggregates),adversarial_tests=len(tests['checks']),main_assertions=len(experiment['checks']),closeout_checks=len(checks),preserved_files=len(before),algorithmic_originality_established=False,all_scopes_synthetic=True,checks=checks)
    save(out/'FINAL_ACCEPTANCE.json',final)
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    from matplotlib.patches import Polygon as Patch
    fig,axes=plt.subplots(1,3,figsize=(13,4));names=[a['method'] for a in aggregates]
    for ax,key,label in zip(axes,['actual_search_evaluations','dirty_graph_nodes_total','protected_changes'],['Actual search evaluations (scenario runs)','Dirty graph nodes (metadata only)','Protected changes in returned layouts']):
        vals=[a[key] for a in aggregates];ax.bar(names,vals,color=['#5a6872','#527f89','#536b59']);ax.set_title(label,fontsize=10);ax.set_ylabel('Count');ax.tick_params(axis='x',labelsize=9)
        for i,v in enumerate(vals):ax.text(i,v if v else .01,str(v),ha='center',va='bottom',fontsize=9)
        ax.margins(y=.2)
    fig.suptitle('Matched outcomes: no EAG-exclusive correctness or optimizer advantage');fig.text(.5,.01,'Source: EXPERIMENT_FINAL/RAW_COMPARISON.json; 2 synthetic venues × 2 seeds × 13 scenarios. Dirty nodes are not full validation work.',ha='center',fontsize=8);fig.tight_layout(rect=(0,.04,1,.92));fig.savefig(out/'MEASURED_BASELINE_COMPARISON.png',dpi=160);plt.close(fig)
    actual=read(base/unit/'authorized_singleton_repair/EAG/RESULT.json');new=max(actual['candidate_layouts'],key=lambda l:actual['validation'][l['layout_id']]['stable_group_relocation_m']);target=read(base/unit/'authorized_singleton_repair/INPUT.json')['context']['requested_group'];fig,axes=plt.subplots(1,2,figsize=(11,5))
    for ax,layout,title in zip(axes,[ref['layout'],new],['Actual approved controlled reference','Actual returned singleton alternative']):
        boundary=ref['request']['venue']['boundary_m'];x,y=zip(*boundary);ax.plot(x,y,color='black')
        for ob in layout['objects']:ax.add_patch(Patch(ob['footprint_coordinates_m'],facecolor='#2e8390' if ob['group_id']==target else '#a7afb5',edgecolor='white',linewidth=.3))
        for z in layout['zones']:
            if z['exclusive']:ax.add_patch(Patch(z['footprint_m'],fill=False,hatch='///',edgecolor='#745e76'))
        ax.set_aspect('equal');ax.autoscale_view();ax.set_title(title);ax.set_xlabel('x (m)');ax.set_ylabel('y (m)')
    x,y=ref['layout']['group_centers_m'][target];nx,ny=new['group_centers_m'][target];axes[1].annotate('',xy=(nx,ny),xytext=(x,y),arrowprops=dict(arrowstyle='->',color='black'));fig.suptitle('Actual authorized movement; all other individual object records locked');fig.text(.5,.01,'Largest-relocation returned alternative shown for inspection, not a preference recommendation. Synthetic scope; 1680 real evaluations.',ha='center',fontsize=8);fig.tight_layout(rect=(0,.04,1,.92));fig.savefig(out/'ACTUAL_SINGLETON_REPAIR.png',dpi=160);plt.close(fig)
    print(__import__('json').dumps({k:v for k,v in final.items() if k!='checks'},indent=2))
    if final['status']=='FAIL':raise SystemExit(1)

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--out',default='outputs/CLOSEOUT_FINAL');a=p.parse_args();out=(HERE/a.out).resolve()
    if not out.is_relative_to(HERE):raise ValueError('ISOLATION')
    main(out)
