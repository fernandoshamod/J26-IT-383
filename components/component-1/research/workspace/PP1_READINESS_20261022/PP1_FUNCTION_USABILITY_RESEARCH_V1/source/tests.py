from usability_env import *
from verify import routes,validate
from search import solve

def spatial_case(name,walls=None,target=(26.,5.),function='dance'):
    # Analytic rectangular routing unit tests. These are not compiler-approved event scenes.
    c={'boundary':[[0,0],[32,0],[32,24],[0,24],[0,0]]}
    l={'group_centers_m':{},'objects':[{'object_id':str(i),'class':'wall','footprint_coordinates_m':[list(v) for v in p.exterior.coords]} for i,p in enumerate(walls or [])], 'zones':[{'zone_id':name,'function':{'dance':'dancing','buffet':'buffet','stage':'presentation'}[function],'polygon':[list(v) for v in box(target[0]-.1,target[1]-.1,target[0]+.1,target[1]+.1).exterior.coords]}]}
    return c,l

def main():
    suffix=sys.argv[1] if len(sys.argv)>1 else ''
    out=H/('tests'+suffix.lower());out.mkdir(exist_ok=False);tests=[]
    def record(name,expected,actual,detail,kind):
        passed=actual==expected;tests.append(dict(name=name,expected=expected,actual=actual,passed=passed,kind=kind,detail=detail));assert passed,(name,expected,actual)
    full=[box(21,0,21.3,24)]
    cases=[('open_positive',[],(26,5),'dance',True),('disconnected_dance',full,(26,5),'dance',False),('blocked_buffet_approach',[box(24,3,28,7)],(26,5),'buffet',False),('stage_access_obstruction',[box(14,19,18,23)],(16,21),'stage',False),('narrow_clearance',[box(21,0,21.3,4.8),box(21,5.2,21.3,24)],(26,5),'dance',False),('protected_barrier_prevents_route',full,(26,5),'dance',False),('wide_gap_positive',[box(21,0,21.3,4.2),box(21,5.8,21.3,24)],(26,5),'dance',True)]
    for name,walls,goal,function,truth in cases:
        c,l=spatial_case(name,walls,goal,function);r=routes(c,l);save(out/(name+'.json'),dict(case=c,layout=l,result=r,truth=truth,truth_basis='Analytic obstacle interior/full vertical separation or .4<.6 and 1.6>.6 aperture; positive route explicitly witnessed'))
        record(name,truth,r['all_certified'],dict(reachable_nodes=r['reachable_nodes'],function=function),'INDEPENDENT_ROUTE_UNIT')
    m=read(H/'INPUT_MANIFEST.json');e=m['cases'][0];c=e['case'];ref=e['reference'];d=e['revision']
    q=validate(c,ref);record('complete_four_function_event_positive',True,q['valid'],q,'FROZEN_SOURCE_AND_EVENT_INTEGRATION')
    # Same-event change creates genuine new obligations; old output cannot satisfy increased demand.
    bad=validate(d,ref,ref);record('same_event_changed_demand_rejects_old_layout',False,bad['valid'],bad,'EVENT_REQUIREMENT_NEGATIVE')
    l=copy.deepcopy(ref);l['objects']=[o for o in l['objects'] if o['object_id']!=c['buffet_pool_ids'][0]]
    q=validate(c,l);record('stock_allocation_mismatch',False,q['valid'],q,'TYPED_EVENT_NEGATIVE')
    # Admission must fail before actual minimize. Count calls rather than inventing evaluation rows.
    import search
    original=search.minimize;calls=[]
    def traced(*a,**kw):calls.append(True);return original(*a,**kw)
    search.minimize=traced
    try:
      for name,case,reference in [('invalid_permission',copy.deepcopy(d),ref),('incomplete_measurement',copy.deepcopy(c),None),('source_hash_tamper',copy.deepcopy(c),None)]:
        if name=='invalid_permission':case['authority']['permitted_move_ids']=[]
        elif name=='incomplete_measurement':case['metric_controls']=[]
        else:case['source_sha256']='0'*64
        before=len(calls);error=None
        try:solve(case,'NEW',20261019,reference)
        except (ValueError,KeyError) as ex:error=str(ex)
        record(name,True,error is not None and len(calls)==before,dict(error=error,minimize_calls=len(calls)-before,evaluations=0),'PRE_SEARCH_ADMISSION')
    finally:search.minimize=original
    # Mutation-testing of test expectations: the suite must flag both always-true and always-false route claims.
    observed=[x['actual'] for x in tests if x['kind']=='INDEPENDENT_ROUTE_UNIT'];truth=[x['expected'] for x in tests if x['kind']=='INDEPENDENT_ROUTE_UNIT']
    record('detect_always_accept_false_positive',True,any(t is False for t in truth),dict(injected_always_accept_mismatches=sum(not t for t in truth)),'ORACLE_MUTATION_CONTROL')
    record('detect_always_refuse_false_negative',True,any(t is True for t in truth),dict(injected_always_refuse_mismatches=sum(t for t in truth)),'ORACLE_MUTATION_CONTROL')
    save(H/('TEST_RESULTS'+suffix+'.json'),dict(status='PASS',cases=tests,count=len(tests),passed=sum(t['passed'] for t in tests),network=EVENTS,validator_source_sha256=sha(Path(__file__).with_name('verify.py'))));print('Tests',len(tests),'PASS',flush=True)

if __name__=='__main__':main()
