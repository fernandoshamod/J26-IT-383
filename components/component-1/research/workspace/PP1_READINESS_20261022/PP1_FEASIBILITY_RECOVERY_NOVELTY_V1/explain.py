"""Evidence-bound numerical explanation sidecars; never creates approvals/layouts."""
from io_context import *

def build(run,outname):
    root=H/run;out=H/outname;out.mkdir(exist_ok=False);index=[]
    for entry in read(root/'SUMMARY.json')['outcomes']:
        rid=entry['run_id'];d=root/rid;r=read(d/'REQUEST.json');resp=read(d/'RESPONSE.json')
        states={digest(s):s for s in [read(p/'STATE.json') for p in d.glob('state_*')]}
        definitions={o['id']:o for o in r['operations']};alts=[]
        for item in resp['pareto_recovery_alternatives']:
            s=states[item['state_sha256']];alts.append({'layout_sha256':item['layout_sha256'],'state_sha256':item['state_sha256'],'requirements_before':r['requested'],'requirements_after':s['values'],'operations':[definitions[i] for i in s['operations']],'declared_concession_cost':item['recovery_objectives'][1],'declared_functional_loss_proxy':item['recovery_objectives'][0],'total_center_disruption_m':item['recovery_objectives'][2],'service_distance_proxy_m':item['recovery_objectives'][3],'required_functions_preserved':['dining','presentation','buffet','dancing'],'stock_ids':[o['object_id'] for o in item['layout']['objects'] if o['class']=='buffet_counter'],'geometry_validation':'INDEPENDENT_PASS_LOCAL_FOOTPRINTS_AND_FUNCTION_PORTS_NOT_ROUTE_CERTIFICATION'})
        e={'run_id':rid,'request_sha256':digest(r),'response_sha256':digest(resp),'source_sha256':r['core']['source_sha256'],'context_version':r['core']['version'],'status':resp['status'],'planner_approval':'NOT_GRANTED_RECOMMENDATION_ONLY','alternatives':alts,'refusal_or_impossibility_witnesses':[x for x in resp['states'] if x['proof']],'excluded_operations':read(d/'ENUMERATION.json')['rejected'],'limits':['No global infeasibility inference from NSGA-II failure','Synthetic cost and function-loss policies, not actual planner valuation','No real-venue/safety approval','No proof of globally optimal concession/layout front']}
        save(out/(rid+'.json'),e);index.append({'run_id':rid,'path':str(out/(rid+'.json')),'sha256':digest(e)})
    save(out/'INDEX.json',index);print('EXPLAINED',len(index),'responses')
if __name__=='__main__':build(*sys.argv[1:])
