"""Executed three-strategy experiment, no frontend/weather/learning changes."""
import argparse,copy,platform,time,sqlite3
from runtime import *
from repair import run,make_reference
from scenarios import initial,change,EXPECTED
from independent import verify_candidate,verify_envelope
from certificates import is_current

def main(out,seeds):
    out.mkdir(parents=True,exist_ok=False);before=snapshot();save(out/'PRESERVATION_BEFORE.json',before)
    save(out/'PREREGISTERED_EXPECTATIONS.json',dict(statuses=EXPECTED,units='two controlled partial venues × declared seeds; layouts/seeds correlated repeats',methods=['FULL','INCREMENTAL','EAG'],initial_budget=1200,singleton_budget=1680,same_reuse_and_fallback_policy=True,labels='pre-authored synthetic expected statuses; not independent human labels',no_originality_assumed=True,seeds=seeds))
    checks=[];records=[]
    def check(name,ok,detail=None):checks.append(dict(name=name,passed=bool(ok),detail=detail));print(name,bool(ok),flush=True)
    for width,height in [(32,24),(36,28)]:
      for seed in seeds:
        unit=f'VENUE_{width}_{height}_SEED_{seed}';root=out/unit;base=initial(root/'BASE_INPUT',width,height);refs={};bases={}
        for method in ['FULL','INCREMENTAL','EAG']:
            response,graph=run(base,root/'INITIAL'/method,method,seed)
            check(unit+'_'+method+'_ACTUAL_INITIAL',response['status']=='eligible' and response['optimizer_evaluations']==1200)
            ref=make_reference(base['scene'],response,graph,root/'INITIAL'/method)
            # An explicit, newly supplied simulated layout approval is required.
            ctx=copy.deepcopy(base['context']);ctx.update(version=2,reference_sha256=digest(ref['layout']),allowed_groups=sorted(ref['layout']['group_centers_m']))
            approved=seal_packet(base['scene'],ctx,root/('SIMULATED_LAYOUT_APPROVAL_'+method));review,graph=run(approved,root/'APPROVAL'/method,method,seed,ref)
            check(unit+'_'+method+'_EXPLICIT_APPROVAL',review['status']=='eligible' and review['optimizer_evaluations']==0)
            ref.update(certificate=review['certificate'],graph=graph,pool=review['candidate_layouts']);refs[method]=ref;bases[method]=approved
        # Use the exact same actor/evidence packet for all strategies. Bind all
        # cached certificates to the same approval packet, not per-method file paths.
        base=bases['FULL']
        for method in ['INCREMENTAL','EAG']:
            review,graph=run(base,root/'COMMON_APPROVAL'/method,method,seed,refs[method]);refs[method].update(certificate=review['certificate'],graph=graph,pool=review['candidate_layouts'])
        for name,expected in EXPECTED.items():
            packet=change(name,base,refs['FULL'],root/name/'CONTROLLED_INPUT');save(root/name/'INPUT.json',packet);responses={}
            for method in ['FULL','INCREMENTAL','EAG']:
                response,graph=run(packet,root/name/method,method,seed,refs[method]);responses[method]=response
                check(unit+'_'+name+'_'+method,response['status']==expected,dict(expected=expected,status=response['status'],reasons=response['reasons']))
                rec=dict(unit=unit,seed=seed,case=name,method=method,status=response['status'],expected=expected,false_accept=response['status']=='eligible' and expected!='eligible',false_refusal=response['status']!='eligible' and expected=='eligible',operation=response['operation'],fallback=response['fallback'],optimizer_evaluations=response['optimizer_evaluations'],optimizer_calls=response['optimizer_calls'],optimizer_seconds=response['optimizer_seconds'],elapsed_seconds=response['elapsed_seconds'],graph_qualification_nodes=response['impact']['qualification_nodes_evaluated'],full_candidate_replays=len(response['validation'])+len(response['invalidated_previous_candidates']),candidate_count=len(response['candidate_layouts']),material_menu_count=len(response['selected_ids']),certificate_current=is_current(packet,response['certificate']),old_certificate_stale=response['previous_certificate_stale'],function_complete=all(v['geometry']['allocated_counts']==response['spec']['required_quantities'] for v in response['validation'].values()) if response['candidate_layouts'] else None,protected_changes=sum(len(v['protected_changes']) for v in response['validation'].values()),unauthorized_changes=sum('UNAUTHORIZED_OBJECT_CHANGE' in v['errors'] for v in response['validation'].values()),layout_disruption=[dict(layout_id=k,moved_objects=v['moved_object_count'],stable_group_relocation_m=v['stable_group_relocation_m'],stable_individual_relocation_m=v['stable_individual_relocation_m']) for k,v in response['validation'].items()],objective_vectors=[dict(layout_id=l['layout_id'],reported=l['objective_metrics'],actual_search_objectives=l.get('search_objectives',l['objective_metrics'])) for l in response['candidate_layouts']],validation_coverage=[v['checked_obligations'] for v in response['validation'].values()])
                records.append(rec)
                if response['candidate_layouts']:check(unit+'_'+name+'_'+method+'_FULL_VERIFIED',all(v['valid'] and len(v['checked_obligations'])==13 for v in response['validation'].values()))
            def semantics(r):return dict(status=r['status'],layouts=r['candidate_layouts'],selected=r['selected_ids'],operation=r['operation'],evaluations=r['optimizer_evaluations'])
            check(unit+'_'+name+'_MATCHED_CANDIDATES',digest(semantics(responses['FULL']))==digest(semantics(responses['INCREMENTAL']))==digest(semantics(responses['EAG'])))
            check(unit+'_'+name+'_INCREMENTAL_CLOSURE_MATCH',responses['EAG']['impact']['affected_constraints']==responses['INCREMENTAL']['impact']['affected_constraints'])
    save(out/'RAW_COMPARISON.json',records);after=snapshot();check('PRESERVATION',before==after,dict(files=len(before)));save(out/'PRESERVATION_AFTER.json',after)
    save(out/'ENVIRONMENT.json',dict(python=sys.version,platform=platform.platform(),source_versions=source_versions(),seeds=seeds,weather=False,sgcn=False,all_scopes='SIMULATED_FIXTURE'))
    result=dict(passed=all(c['passed'] for c in checks),scenario_method_records=len(records),scenario_instances=len(records)//3,false_accepts=sum(r['false_accept'] for r in records),false_refusals=sum(r['false_refusal'] for r in records),preserved_files=len(before),novel_algorithm_established=False,checks=checks)
    save(out/'EXPERIMENT_RESULTS.json',result);print(__import__('json').dumps({k:v for k,v in result.items() if k!='checks'},indent=2))
    if not result['passed']:raise SystemExit(1)

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--out',default='outputs/EXPERIMENT_001');p.add_argument('--seeds',type=int,nargs='+',default=[20261017,20261018]);a=p.parse_args();out=(HERE/a.out).resolve()
    if not out.is_relative_to(HERE):raise ValueError('ISOLATION')
    main(out,a.seeds)
