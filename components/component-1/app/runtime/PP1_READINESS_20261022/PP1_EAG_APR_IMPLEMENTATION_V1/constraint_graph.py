"""Evidence-linked graph and conventional reverse-index propagation.
Graph closure/dirty tracking are standard techniques, not novelty claims.
"""
from runtime import *

def tokens(packet):
    r=packet['scene'];v=r['venue'];c=packet['context']
    return dict(source=digest(v['source']),metric=digest({k:v[k] for k in ['boundary_m','boundary_px','controls','origin_px','version','review']}),stock=digest(v['existing']),client=digest(r['client']),planner=digest(r['planner']),functions=digest([r['client']['optional_functions'],r['planner']['optional_functions'],r['dance_zone_m'],r['placements']]),capacity=digest([r['client']['guest_count'],r['planner']['guest_count']]),locks=digest(c['protected_object_ids']),permissions=digest([c['allowed_groups'],c['new_supply_permitted'],c['object_moves'],c['requested_group']]),scenario=digest([c['scenario'],c['version']]),bytes=digest(facts(packet)['artifacts']))

DEPS={
 'EVIDENCE':(['source','metric','bytes'],[]),
 'ACTOR_APPROVAL':(['client','planner','bytes'],['EVIDENCE']),
 'FUNCTION_DEMAND':(['capacity','functions'],['ACTOR_APPROVAL']),
 'STOCK_ALLOCATION':(['stock','functions','capacity'],['FUNCTION_DEMAND']),
 'GEOMETRY':(['metric','stock','functions'],['EVIDENCE','STOCK_ALLOCATION']),
 'PROTECTED':(['locks','stock'],['GEOMETRY']),
 'PERMISSIONS':(['permissions'],['ACTOR_APPROVAL','PROTECTED']),
 'HARD_CLEARANCE':(['client','planner'],['GEOMETRY']),
 'HARD_STAGE':(['client','planner'],['GEOMETRY']),
 'HARD_MOVEMENT':(['client','planner'],['PERMISSIONS']),
 'SCENARIO_SCOPE':(['scenario'],['EVIDENCE']),
 'PARETO_STAGE':(['functions'],['GEOMETRY']),
 'PARETO_DISRUPTION':(['permissions'],['PERMISSIONS'])}

def build(packet,spec):
    r=packet['scene'];c=packet['context'];evidence=[r['venue']['review']['evidence'],r['client']['evidence'],r['planner']['evidence'],packet['authority']];objects=[o['instance_id'] for o in spec['retained_existing']+spec['new_equipment']]
    return dict(schema='EAG_CONSTRAINT_GRAPH_V1',nodes=[dict(constraint_id=k,constraint_version=1,evidence_ids=[dict(evidence_id='sha256:'+e['sha256'],path=e['path']) for e in evidence],source_version=r['venue']['version'],verification_status='qualified' if spec['status']=='accepted' else 'not_qualified',responsible_authorities=[dict(role=p,actor_id=r[p]['actor_id'],scope=r[p]['scope']) for p in ['client','planner']],dependent_objects=objects,dependent_functions=spec['functions'],scenario=c['scenario'],classification='soft' if k.startswith('PARETO') else 'hard',qualification_status=spec['status'],fact_dependencies=a,constraint_dependencies=b) for k,(a,b) in DEPS.items()],tokens=tokens(packet))

def impact(old,new,mode):
    changed=sorted(k for k,v in new['tokens'].items() if old['tokens'].get(k)!=v)
    if mode=='FULL':dirty={n['constraint_id'] for n in new['nodes']}
    elif mode=='EAG':
        dirty={n['constraint_id'] for n in new['nodes'] if set(n['fact_dependencies'])&set(changed)}
        while True:
            expanded=dirty|{n['constraint_id'] for n in new['nodes'] if set(n['constraint_dependencies'])&dirty}
            if expanded==dirty:break
            dirty=expanded
    else:
        # Ordinary reverse incidence worklist, no graph-specific certificate logic.
        reverse={}
        for n in new['nodes']:
            for key in n['fact_dependencies']+n['constraint_dependencies']:reverse.setdefault(key,[]).append(n['constraint_id'])
        queue=list(changed);dirty=set()
        while queue:
            key=queue.pop()
            for cid in reverse.get(key,[]):
                if cid not in dirty:dirty.add(cid);queue.append(cid)
    affected=sorted({o for n in new['nodes'] if n['constraint_id'] in dirty for o in n['dependent_objects']})
    return dict(directly_changed_dependencies=changed,affected_constraints=sorted(dirty),affected_object_variables=affected,qualification_nodes_evaluated=len(dirty),not_a_minimum_repair_set=True)
