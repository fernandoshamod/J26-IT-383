"""Governed dispatch shared by fair strategies; no invented optimizer.
All methods receive the same candidate reuse policy, scope, locks and budgets.
"""
import copy,time,sqlite3,json
from runtime import *
from constraint_graph import build,impact
from authority import qualify
from certificates import issue,is_current
from independent import verify_candidate,verify_envelope
from optimizer_adapter import full,singleton

def run(packet,out,method,seed,reference=None):
    out=Path(out).resolve();out.mkdir(parents=True,exist_ok=False);start=time.perf_counter();save(out/'INPUT.json',packet)
    strategy=compiler.compile_scene if method=='EAG' else baseline.baseline_scene
    spec=strategy(packet['scene'],POLICY);graph=build(packet,spec);oldgraph=reference['graph'] if reference else dict(nodes=[],tokens={});change=impact(oldgraph,graph,method)
    save(out/'GRAPH.json',graph);save(out/'IMPACT.json',change);save(out/'SPEC.json',spec)
    status,reasons=qualify(packet,spec,reference);layouts=[];validations={};initial={};operation='REFUSE';evaluations=0;calls=0;seconds=0.;invalid_old=[];fallback=False;target=None
    stale=bool(reference and not is_current(packet,reference['certificate']))
    if status=='qualified':
        target=packet['context']['requested_group']
        if target and (digest(packet['scene'])!=digest(reference['request']) or spec['hard']!=reference['spec']['hard']):
            status='unsupported';reasons=['SINGLETON_CONTEXT_CHANGE_REQUIRES_UNSUPPORTED_REPAIR']
        elif reference and not target:
            operation='REVALIDATE_EXISTING_POOL';initial=reference['initial']
            for l in reference['pool']:
                v=verify_candidate(packet,spec,l,initial,reference)
                if v['valid']:layouts.append(copy.deepcopy(l));validations[l['layout_id']]=v
                else:invalid_old.append(dict(layout_id=l['layout_id'],errors=v['errors']))
        if status=='qualified' and (not layouts or target):
            operation='SELECTIVE_SINGLETON' if target else 'FULL_RECOMPUTATION';fallback=bool(reference and not target)
            result=singleton(packet['scene'],spec,out/'ACTUAL_SEARCH',seed,reference,target) if target else full(packet['scene'],spec,out/'ACTUAL_SEARCH',seed)
            evaluations=result['evaluations'];calls=result['optimizer_calls'];seconds=result['seconds'];initial=result['initial']
            if result['status']!='success':
                status='infeasible' if result['status']=='failed_search' else 'refused';reasons=[result['reason']]
            else:
                for l in result['layouts']:
                    v=verify_candidate(packet,spec,l,initial,reference,target)
                    if v['valid']:layouts.append(l);validations[l['layout_id']]=v
                    else:invalid_old.append(dict(layout_id=l['layout_id'],errors=v['errors']))
        if status=='qualified':
            if layouts:status='eligible';reasons=['CURRENT_CONTEXT_AND_ALL_RETURNED_RECOMMENDATIONS_VERIFIED']
            else:status='refused';reasons=['NO_RETURNED_CANDIDATE_PASSES_FULL_AUTHORITY_AND_GEOMETRY_VALIDATION']
    if status!='eligible':layouts=[];validations={}
    menu=bridge.menu(layouts)
    # Canonical pairwise nondominance check on declared optimizer objectives.
    values=[list(l.get('search_objectives',l['objective_metrics']).values()) for l in layouts]
    if any(all(x<=y+1e-9 for x,y in zip(a,b)) and any(x<y-1e-9 for x,y in zip(a,b)) for i,a in enumerate(values) for j,b in enumerate(values) if i!=j):raise RuntimeError('POST_VALIDATION_PARETO_DOMINANCE')
    # Re-read all evidence immediately before issuing/persisting. No stale success.
    fresh=strategy(packet['scene'],POLICY)
    if status=='eligible' and (fresh['spec_sha256']!=spec['spec_sha256'] or qualify(packet,fresh,reference)[0]!='qualified'):raise RuntimeError('INPUT_CHANGED_BEFORE_PERSISTENCE')
    evidence_fingerprint=facts(packet)
    reason_records=[dict(code=reason,constraint_id='EVIDENCE' if any(s in reason for s in ['EVIDENCE','SOURCE','METRIC','REVIEW']) else 'PERMISSIONS' if any(s in reason for s in ['PERMISSION','PROTECTED','REFERENCE','MOVE']) else 'FUNCTION_DEMAND' if any(s in reason for s in ['CONFLICT','SUPPLY']) else 'GEOMETRY') for reason in reasons]
    body=dict(schema='EAG_APR_RESULT_V1',method=method,status=status,spec=spec,candidate_layouts=layouts,selected_ids=menu['selected_ids'],menu=menu,validation=validations,graph_constraint_ids=[n['constraint_id'] for n in graph['nodes']],impact=change,operation=operation,fallback=fallback,previous_certificate_stale=stale,optimizer_evaluations=evaluations,optimizer_calls=calls,optimizer_seconds=seconds,elapsed_seconds=time.perf_counter()-start,invalidated_previous_candidates=invalid_old,reasons=reason_records,initialization_centers_m=initial,reference_sha256=packet['context']['reference_sha256'],qualification_fingerprint=evidence_fingerprint,seed=seed,global_infeasibility_proven=False)
    response=issue(packet,body)
    if facts(packet)!=evidence_fingerprint:raise RuntimeError('EVIDENCE_CHANGED_DURING_CERTIFICATE_ISSUANCE')
    independent=verify_envelope(packet,response,reference);save(out/'INDEPENDENT_ENVELOPE.json',independent)
    if not independent['valid']:raise RuntimeError('CERTIFICATE_OR_XAI_INVALID:'+str(independent))
    save(out/'RESULT.json',response)
    with sqlite3.connect(out/'assurance.sqlite3') as db:
        db.execute('CREATE TABLE records(input_json TEXT,response_json TEXT,sha256 TEXT)');db.execute('INSERT INTO records VALUES(?,?,?)',(json.dumps(packet),json.dumps(response),digest(response)))
    return response,graph

def make_reference(request,response,graph,path):
    layout=min(response['candidate_layouts'],key=lambda l:l['objective_metrics']['initializer_assignment_movement_m'])
    return dict(request=request,layout=layout,pool=response['candidate_layouts'],initial=response['initialization_centers_m'],spec=response['spec'],certificate=response['certificate'],graph=graph,engine_request=read(Path(path)/'ACTUAL_SEARCH/FROZEN_ENGINE_REQUEST.json'))
