from io_context import *
import copy
from experiment import make_requests,SEEDS
from recovery import *
from conventional_reference import enumerate_reference
from independent_validator import validate

def main(name):
    out=H/name;out.mkdir(exist_ok=False);tests=[];searches=0;evals=0
    def record(n,ok,detail=None):
        tests.append({'name':n,'passed':bool(ok),'detail':detail});assert ok,(n,detail)
    def reject(n,fn):
        try:fn()
        except (ValueError,KeyError) as e:record(n,True,str(e));return
        record(n,False,'accepted unexpectedly')
    cases=make_requests('venue_1',SEEDS[0]);by={r['case_id']:r for r in cases}
    for venue in ['venue_1','venue_2']:
      for seed in SEEDS:
        for r in make_requests(venue,seed):
            a,_=enumerate_grouped(r);b=enumerate_reference(r)
            record(f'enumeration_{venue}_{seed}_{r["case_id"]}',{digest(x) for x in a}=={digest(x) for x in b},len(a))
    r=by['coupled_service_stock'];states,_=enumerate_grouped(r)
    _,partials=enumerate_grouped(r,split_bundles=True)
    record('coupled_single_field_edits_rejected',sum('BROKEN_SERVICE_FUNCTION_DEPENDENCY' in x['errors'] for x in partials)==2)
    for scenario in ['missing_permission','mandatory_nonrelaxable']:
        st,_=enumerate_grouped(by[scenario]);record(scenario+'_no_changed_states',all(not x['operations'] for x in st))
    stale=copy.deepcopy(r);stale['requested']['dance_area_m2']=25;reject('stale_recovery_binding',lambda:check_request(stale))
    revoked=copy.deepcopy(r);revoked['recovery_authority']['revoked']=True;reject('revoked_recovery_authority',lambda:check_request(revoked))
    invalid=copy.deepcopy(r);invalid['requested']['boundary']='replace';reject('unsupported_structural_edit',lambda:check_request(invalid))
    # Real frozen admission failures, not a stand-in permission function.
    jc=engine()
    missing=copy.deepcopy(by['ordinary_feasible']['core']);missing['metric_controls']=[];reject('frozen_gate_missing_measurement',lambda:jc.admit(missing))
    changed=copy.deepcopy(by['ordinary_feasible']['core']);changed['source_sha256']='0'*64;reject('frozen_gate_source_mismatch',lambda:jc.admit(changed))
    noauth=copy.deepcopy(by['ordinary_feasible']['core']);noauth['authority']['allow_design']=False;reject('frozen_gate_missing_design_authority',lambda:jc.admit(noauth))
    r=by['coupled_service_stock'];state=next(s for s in states if s['operations']);c,result=solve_state(r,state,SEEDS[0],120);searches+=1;evals+=result['evaluations']
    record('actual_joint_nsga_smoke',bool(result['candidates']) and result['evaluations']==120,{'candidates':len(result['candidates']),'evaluations':result['evaluations']})
    save(out/'COUPLED_SMOKE.json',{'request':r,'state':state,'case':c,'result':result})
    l=result['candidates'][0];record('positive_independent_smoke',validate(r,state,c,l)['valid'])
    changed=copy.deepcopy(l);changed['objects'][0]['footprint_coordinates_m'][0][0]+=.25;record('mutated_protected_polygon_rejected',not validate(r,state,c,changed)['valid'])
    changed=copy.deepcopy(state);changed['concession_cost']+=1;record('wrong_concession_cost_rejected',not validate(r,changed,c,l)['valid'])
    changed=copy.deepcopy(r);changed['recovery_authority']['permitted_operations']=[];record('missing_permission_independent_rejection',not validate(changed,state,c,l)['valid'])
    changed=copy.deepcopy(state);changed['values']['service_front_m']=5.;record('partial_service_change_rejected',not validate(r,changed,c,l)['valid'])
    changed=copy.deepcopy(l);changed['xai']['metrics']['service_distance_proxy_m']+=1.;record('poisoned_numerical_xai_rejected',not validate(r,state,c,changed)['valid'])
    revision=by['same_event_revision'];state=next(s for s in enumerate_grouped(revision)[0] if s['values']['dance_area_m2']==25)
    cc,rr=solve_state(revision,state,SEEDS[0],120);searches+=1;evals+=rr['evaluations'];save(out/'REVISION_SMOKE.json',{'request':revision,'state':state,'case':cc,'result':rr})
    record('actual_revision_locked_individuals',bool(rr['candidates']) and all(validate(revision,state,cc,q)['valid'] for q in rr['candidates']))
    bad=copy.deepcopy(revision['core']);bad['authority']['permitted_move_ids']=[];reject('frozen_revision_missing_object_permission',lambda:jc.admit(bad,revision['reference']))
    bad=copy.deepcopy(revision['core']);bad['authority']['revoked']=True;reject('frozen_revision_revocation',lambda:jc.admit(bad,revision['reference']))
    bad=copy.deepcopy(revision);bad['core']['authority']['revoked']=True;record('independent_revision_revocation',not validate(bad,state,cc,rr['candidates'][0])['valid'])
    save(out/'TEST_RESULTS.json',{'status':'PASS','tests':tests,'total':len(tests),'passed':sum(x['passed'] for x in tests),'actual_smoke_searches':searches,'smoke_evaluations':evals,'audit':AUDIT})
    print('PASS',len(tests),'cases/checks;',searches,'actual smoke searches',evals,'evaluations; not independent venue samples')
if __name__=='__main__':main(sys.argv[1])
