from io_context import *
import copy,sqlite3,csv,traceback
from recovery import check_request,request_hash,enumerate_grouped,screen,solve_state,functional_loss,nondominated
from conventional_reference import enumerate_reference
from independent_validator import validate,prove_screen

SEEDS=[20261019,20261020]
BUDGET=120

def make_requests(venue,seed):
    folder=PP1/'PP1_ORIGINAL_LAYOUT_RESEARCH_V1';base=read(folder/f'data_v3/{venue}/CASE.json')
    prior=read(folder/f'raw_final/{venue}_{seed}_initial_B1/RESULT.json')
    reference=min(prior['candidates'],key=lambda x:(x['objectives'][1],x['objectives'][0]))
    def req(name):
        c=copy.deepcopy(base)
        return {'schema':'CONTROLLED_RECOVERY_V1','case_id':name,'core':c,'reference':None,
                'requested':{'dance_area_m2':16.,'minimum_buffets':1,'service_front_m':2.5,'stage_target':None},
                'domains':{'dance_area_m2':[16.],'minimum_buffets':[1],'service_front_m':[2.5],'stage_target':[None]},
                'operations':[],'mandatory':[],'protected_stage':None,'recovery_authority':{}}
    def op(i,old,new,cost,function):return {'id':i,'from':old,'to':new,'cost':cost,'function':function,'reason':'PREDECLARED_SIMULATED_NEGOTIATION_POLICY_NOT_LEARNED_PREFERENCE'}
    def dance(r):
        r['requested']['dance_area_m2']=900.;r['domains']['dance_area_m2']=[900.,25.,16.]
        r['operations']=[op('dance_to_25',{'dance_area_m2':900.},{'dance_area_m2':25.},1.,'dancing'),op('dance_to_16',{'dance_area_m2':900.},{'dance_area_m2':16.},2.,'dancing')]
    cases=[]
    r=req('ordinary_feasible');cases.append(r)
    r=req('spatial_negotiable');dance(r);cases.append(r)
    r=req('coupled_service_stock');r['core']['available_buffet_ids']=r['core']['buffet_pool_ids'][:1]
    r['requested'].update(minimum_buffets=2,service_front_m=5.);r['domains'].update(minimum_buffets=[2,1],service_front_m=[5.,2.5])
    r['operations']=[op('service_one_counter',{'minimum_buffets':2,'service_front_m':5.},{'minimum_buffets':1,'service_front_m':2.5},3.,'buffet')];cases.append(r)
    r=req('protected_conflict');r['protected_stage']=reference['decision_vector'][8:11];r['requested']['stage_target']=[19.5,11.,0.];r['domains']['stage_target']=[[19.5,11.,0.]];cases.append(r)
    r=req('missing_permission');dance(r);cases.append(r)
    r=req('mandatory_nonrelaxable');dance(r);r['mandatory']=['dance_area_m2'];cases.append(r)
    r=req('nonnegotiable_stock_shortfall');r['core']['available_buffet_ids']=r['core']['buffet_pool_ids'][:1];r['requested'].update(minimum_buffets=2,service_front_m=5.);r['domains'].update(minimum_buffets=[2],service_front_m=[5.]);cases.append(r)
    r=req('same_event_revision');dance(r);c=r['core'];r['reference']=reference;c.update(version=2,locked_group_0=reference['group_centers_m']['seating_group_0001'])
    c['authority'].update(allow_revision=True,reference_sha256=digest(reference),reference_case_sha256=digest(base),revoked=False,permitted_move_ids=c['table_ids'][1:]+c['chair_ids'][8:]+[c['stage_id']]+c['available_buffet_ids'],permitted_zone_ids=['dance'],allow_function_change=True,allow_allocation_change=True,protected_group='seating_group_0001');cases.append(r)
    r=req('stage_position_preference');r['requested']['stage_target']=[0.,0.,0.];r['domains']['stage_target']=[[0.,0.,0.],None]
    r['operations']=[op('release_stage_preference',{'stage_target':[0.,0.,0.]},{'stage_target':None},1.,'presentation')];cases.append(r)
    for r in cases:
        r['recovery_authority']={'scope':'SIMULATED_CONTROLLED_RESEARCH_NOT_HUMAN_CONSENT','revoked':False,'permitted_operations':[] if r['case_id']=='missing_permission' else [o['id'] for o in r['operations']],'request_sha256':request_hash(r)}
        check_request(r)
    return cases

def run(name):
    out=H/name;out.mkdir(exist_ok=False)
    requests=[(v,s,r) for v in ['venue_1','venue_2'] for s in SEEDS for r in make_requests(v,s)]
    protocol={'schema':'RECOVERY_PROTOCOL_V1','venues':['venue_1','venue_2'],'seeds':SEEDS,'scenarios':[r['case_id'] for r in make_requests('venue_1',SEEDS[0])],'search_budget_per_admissible_state':BUDGET,'solver':'UNCHANGED_JOINT_CORE_B1_LOCAL_PYMOO_NSGA2','strong_reference':'independently enumerated declarative finite-domain assignment with exact operation cover; same shared deterministic solver oracle','hypothesis':'Coupled authorized concessions preserve all required functions; declarative conventional formulation should reproduce states and outcomes. No distinct algorithm presumed.','rejection':'Any accepted unauthorized/hard/protected violation refutes correctness; matched conventional outcomes refute exclusive algorithmic benefit.','scope':'two controlled related shapes, two seeds, one Wedding event; not real venue/planner samples','request_hashes':[{'venue':v,'seed':s,'case':r['case_id'],'sha256':digest(r)} for v,s,r in requests]}
    save(out/'PROTOCOL_AT_START.json',protocol)
    db=sqlite3.connect(out/'results.sqlite3');db.execute('create table outcomes (run_id text primary key, request_json text, result_json text, response_sha256 text)')
    rows=[];summaries=[];actual_searches=0;total_evals=0
    for venue,seed,r in requests:
        rid=f'{venue}_{seed}_{r["case_id"]}';d=out/rid;d.mkdir();save(d/'REQUEST.json',r)
        start=time.perf_counter();t=time.perf_counter();states,rejected=enumerate_grouped(r);grouped_time=time.perf_counter()-t
        t=time.perf_counter();baseline=enumerate_reference(r);baseline_time=time.perf_counter()-t
        norm=lambda seq:sorted([(digest(x['values']),x['concession_cost'],sorted(x['operations'])) for x in seq])
        assert norm(states)==norm(baseline),('BASELINE_DIFFERENCE',rid)
        save(d/'ENUMERATION.json',{'grouped':states,'conventional_reference':baseline,'rejected':rejected,'matched':True,'grouped_runtime_s':grouped_time,'reference_runtime_s':baseline_time})
        # Diagnostic ablations never authorize or execute a forbidden state.
        noauth,_=enumerate_grouped(r,ignore_authority=True);flat,_=enumerate_grouped(r,split_bundles=True)
        ablation={'no_authority_extra_states':[x for x in noauth if digest(x['values']) not in {digest(x['values']) for x in states}], 'flat_atom_accepted':flat, 'no_concession_state_count':sum(not s['operations'] for s in states),'diagnostic_only':True}
        save(d/'ABLATION.json',ablation)
        state_results=[];valid_records=[];evals=0;searches=0;screened=0;unknown=0
        print('START',rid,len(states),'authorized states',flush=True)
        for index,state in enumerate(states):
            p=d/f'state_{index:02d}';p.mkdir();save(p/'STATE.json',state);proof=screen(r,state)
            if proof:
                assert prove_screen(r,state,proof);screened+=1
                sres={'state_sha256':digest(state),'status':'PROVEN_INFEASIBLE_FOR_THIS_STATE','proof':proof,'evaluations':0,'candidates':0};save(p/'RESULT.json',sres);state_results.append(sres);continue
            c,result=solve_state(r,state,seed,BUDGET);save(p/'CORE_CASE.json',c);save(p/'SEARCH_RESULT.json',result)
            checks=[validate(r,state,c,l) for l in result['candidates']];save(p/'INDEPENDENT_CHECKS.json',checks)
            if not all(q['valid'] for q in checks):raise RuntimeError(('INDEPENDENT_VALIDATION_FAILED',rid,index,[q['errors'] for q in checks]))
            actual_searches+=1;total_evals+=result['evaluations'];searches+=1;evals+=result['evaluations']
            if not checks:unknown+=1
            for l,check in zip(result['candidates'],checks):
                valid_records.append({'layout_sha256':digest(l),'state_sha256':digest(state),'operations':state['operations'],'layout':l,'recovery_objectives':check['recovery_objectives'],'independent_check':check,'search_path':str(p/'SEARCH_RESULT.json')})
            sres={'state_sha256':digest(state),'status':'VERIFIED_FEASIBLE' if checks else 'NO_WITNESS_WITHIN_BUDGET_NOT_UNSAT','proof':[],'evaluations':result['evaluations'],'runtime_s':result['runtime_s'],'candidates':len(checks)}
            save(p/'RESULT.json',sres);state_results.append(sres)
        menu=nondominated(valid_records)
        # The shared solve oracle intentionally gives identical outcomes to both enumerators.
        if valid_records:status='FEASIBLE_UNCHANGED' if any(not x['operations'] for x in menu) else 'RECOVERY_RECOMMENDATIONS'
        elif unknown:status='INCONCLUSIVE_SEARCH_NO_WITNESS'
        elif r['case_id']=='missing_permission':status='REFUSED_NO_AUTHORIZED_RECOVERY'
        else:status='NO_AUTHORIZED_RECOVERY_PROVEN_FOR_DECLARED_DOMAIN'
        response={'request_sha256':request_hash(r),'run_id':rid,'status':status,'authority_scope':r['recovery_authority']['scope'],'planner_approval':'NOT_GRANTED_RECOMMENDATION_ONLY','states':state_results,'pareto_recovery_alternatives':menu,'all_verified_witnesses':len(valid_records),'optimizer_evaluations':evals,'searches':searches,'search_failures_unknown':unknown,'conventional_match':True,'shared_search_oracle':True,'xai':{'request_sha256':request_hash(r),'hard_constraints_relaxed':[],'operations_in_menu':sorted({o for x in menu for o in x['operations']}),'required_functions':['dining','presentation','buffet','dancing'],'proofs':[q['proof'] for q in state_results if q['proof']],'cost_units':'declared synthetic concession-cost units; not learned/human valuation','not_claimed':['Global infeasibility from failed search','Global Pareto optimality','Physical safety','Real venue approval','Algorithmic novelty']}}
        save(d/'RESPONSE.json',response)
        payload=json.dumps(response,sort_keys=True,separators=(',',':'),allow_nan=False);db.execute('insert into outcomes values (?,?,?,?)',(rid,json.dumps(r,sort_keys=True),payload,digest(response)));db.commit()
        got=db.execute('select request_json,result_json,response_sha256 from outcomes where run_id=?',(rid,)).fetchone();assert json.loads(got[0])==r and json.loads(got[1])==response and got[2]==digest(response)
        for method in ['GROUPED_CONVENTIONAL','DECLARATIVE_REFERENCE']:
            row={'run_id':rid,'venue':venue,'seed':seed,'scenario':r['case_id'],'method':method,'status':status,'authorized_states':len(states),'screened_proofs':screened,'actual_shared_searches':searches,'shared_evaluations':evals,'verified_witnesses':len(valid_records),'menu_alternatives':len(menu),'distinct_concessions':len({tuple(x['operations']) for x in menu}),'hard_violations':0,'protected_violations':0,'best_concession_cost':min((x['recovery_objectives'][1] for x in menu),default=None),'best_service_m':min((x['recovery_objectives'][3] for x in menu),default=None),'enumeration_runtime_s':grouped_time if method=='GROUPED_CONVENTIONAL' else baseline_time,'shared_total_runtime_s':time.perf_counter()-start,'response_path':str(d/'RESPONSE.json')};rows.append(row)
        summaries.append({'run_id':rid,'status':status,'matched':True,'witnesses':len(valid_records),'alternatives':len(menu),'searches':searches,'evaluations':evals})
        print('DONE',rid,status,evals,len(valid_records),flush=True)
    db.close();save(out/'RAW_EXPERIMENT_RESULTS.json',rows);save(out/'SUMMARY.json',{'outcomes':summaries,'independent_case_seed_queries':len(summaries),'method_rows':len(rows),'actual_unique_searches':actual_searches,'actual_total_evaluations':total_evals,'matched_pairs':len(summaries),'audit':AUDIT})
    with (out/'RAW_EXPERIMENT_RESULTS.csv').open('x',newline='',encoding='utf-8') as f:
        writer=csv.DictWriter(f,fieldnames=list(rows[0]));writer.writeheader();writer.writerows(rows)
    print('COMPLETE',len(summaries),'queries',actual_searches,'searches',total_evals,'evaluations',flush=True)

if __name__=='__main__':run(sys.argv[1])
