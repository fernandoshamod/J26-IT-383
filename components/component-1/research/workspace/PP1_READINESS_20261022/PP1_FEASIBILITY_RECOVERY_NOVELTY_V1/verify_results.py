"""Reopen all raw evidence/SQLite and independently replay qualification and Pareto claims."""
from io_context import *
import sqlite3,copy
from independent_validator import validate,prove_screen
from conventional_reference import enumerate_reference

def main(run,name):
    root=H/run;out=H/name;out.mkdir(exist_ok=False);summary=read(root/'SUMMARY.json');db=sqlite3.connect(f'file:{(root/"results.sqlite3").as_posix()}?mode=ro',uri=True)
    checks=[];total=0;searches=0;evals=0;violations=0;unknown=0
    for rec in summary['outcomes']:
        d=root/rec['run_id'];r=read(d/'REQUEST.json');response=read(d/'RESPONSE.json');enum=read(d/'ENUMERATION.json')
        baseline=enumerate_reference(r);assert {digest(x) for x in baseline}=={digest(x) for x in enum['grouped']}
        row=db.execute('select request_json,result_json,response_sha256 from outcomes where run_id=?',(rec['run_id'],)).fetchone();assert json.loads(row[0])==r and json.loads(row[1])==response and row[2]==digest(response)
        witnesses=[];states={};proofs=0
        for p in sorted(d.glob('state_*')):
            state=read(p/'STATE.json');states[digest(state)]=state;res=read(p/'RESULT.json')
            if res['proof']:
                assert prove_screen(r,state,res['proof']);proofs+=1;assert res['evaluations']==0;continue
            c=read(p/'CORE_CASE.json');sr=read(p/'SEARCH_RESULT.json');searches+=1;evals+=sr['evaluations'];assert sr['evaluations']==len(sr['trace'])==120
            if not sr['candidates']:unknown+=1
            for l in sr['candidates']:
                check=validate(r,state,c,l);assert check['valid'],(rec['run_id'],check);total+=1;witnesses.append((state,l,check))
        # Recompute recovery front by independent pairwise arithmetic.
        front=[]
        for state,l,check in witnesses:
            vec=check['recovery_objectives']
            dominated=False
            for _,_,other in witnesses:
                ov=other['recovery_objectives']
                if all(x<=y+1e-10 for x,y in zip(ov,vec)) and any(x<y-1e-10 for x,y in zip(ov,vec)):dominated=True;break
            if not dominated:front.append((digest(l),digest(state),vec))
        reported=[(x['layout_sha256'],x['state_sha256'],x['recovery_objectives']) for x in response['pareto_recovery_alternatives']]
        assert sorted(front)==sorted(reported)
        assert response['all_verified_witnesses']==len(witnesses) and response['optimizer_evaluations']==sum(s['evaluations'] for s in response['states'])
        assert response['planner_approval']=='NOT_GRANTED_RECOMMENDATION_ONLY' and response['xai']['hard_constraints_relaxed']==[]
        assert response['xai']['operations_in_menu']==sorted({o for x in response['pareto_recovery_alternatives'] for o in x['operations']})
        for s in response['states']:
            if s['status'].startswith('PROVEN'):assert s['proof']
            if s['status'].startswith('NO_WITNESS'):assert not s['proof']
        checks.append({'run_id':rec['run_id'],'status':response['status'],'valid_witnesses':len(witnesses),'front_size':len(front),'sound_proofs':proofs,'baseline_states_matched':True,'sqlite_exact':True})
    db.close();assert searches==summary['actual_unique_searches'] and evals==summary['actual_total_evaluations']
    save(out/'INDEPENDENT_VALIDATION.json',{'status':'PASS','queries':len(checks),'matched_baseline_pairs':len(checks),'valid_layout_witnesses':total,'actual_unique_comparative_searches':searches,'comparative_evaluations':evals,'states_without_witness_not_proven_unsat':unknown,'hard_protected_unauthorized_accepted_violations':violations,'checks':checks,'audit':AUDIT,'scope':'Raw-readback geometry/function/governance/metric/Pareto replay; no inference/search rerun; not a new independent venue trial'})
    print('PASS',len(checks),'queries',total,'raw layout witnesses',searches,'searches',evals,'evaluations')
if __name__=='__main__':main(*sys.argv[1:])
