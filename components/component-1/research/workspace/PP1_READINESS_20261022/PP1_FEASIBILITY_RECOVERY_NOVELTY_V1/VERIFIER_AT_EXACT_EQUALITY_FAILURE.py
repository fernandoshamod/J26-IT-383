from io_context import *
def main(run,explanations,name):
    checks=[]
    for p in (H/explanations).glob('*.json'):
        if p.name=='INDEX.json':continue
        e=read(p);d=H/run/e['run_id'];r=read(d/'REQUEST.json');response=read(d/'RESPONSE.json')
        assert e['request_sha256']==digest(r) and e['response_sha256']==digest(response)
        assert e['source_sha256']==r['core']['source_sha256'] and e['context_version']==r['core']['version']
        raw={q['layout_sha256']:q for q in response['pareto_recovery_alternatives']}
        assert len(e['alternatives'])==len(raw)
        states={digest(read(q/'STATE.json')):read(q/'STATE.json') for q in d.glob('state_*')}
        for alt in e['alternatives']:
            v=raw[alt['layout_sha256']];s=states[alt['state_sha256']]
            assert alt['requirements_before']==r['requested'] and alt['requirements_after']==s['values']
            assert alt['operations']==[q for oid in s['operations'] for q in r['operations'] if q['id']==oid]
            assert alt['declared_concession_cost']==sum(q['cost'] for q in alt['operations'])==v['recovery_objectives'][1]
            assert alt['service_distance_proxy_m']==v['layout']['objectives'][0] and alt['total_center_disruption_m']==v['layout']['objectives'][1]
            old=r['requested'];new=s['values'];loss=max(0,old['dance_area_m2']-new['dance_area_m2'])/old['dance_area_m2']+max(0,old['minimum_buffets']-new['minimum_buffets'])/old['minimum_buffets']
            assert abs(alt['declared_functional_loss_proxy']-loss)<1e-12
        assert e['planner_approval']=='NOT_GRANTED_RECOMMENDATION_ONLY';checks.append(e['run_id'])
    save(H/(name+'.json'),{'status':'PASS','responses':len(checks),'checks':checks,'scope':'Independent arithmetic/raw-response/hash replay, not human explanation evaluation'})
    print('PASS',len(checks),'numerical response explanations')
if __name__=='__main__':main(*sys.argv[1:])
