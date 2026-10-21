"""Conventional rule/assignment baseline; does not call the compiler.
Same schema, evidence/geometry gates and output assembler are shared deliberately.
The independently implemented decision loops derive demand and assign compatible
stock. Identical semantics are a legitimate null, not claimed novelty.
"""
from collections import Counter
from common import *
from models import Request
from core import preflight,issue,compatible,assemble

def baseline_scene(request,policy=None):
    r=Request.model_validate(request);p=read(HERE/'profiles.json') if policy is None else policy;errors=preflight(r,p)
    programs=[v for v in p['profiles'].values() if r.client.event_type in v['event_types']]
    if len(programs)!=1:raise GateError('EVENT_PROFILE_MISSING')
    program=programs[0];functions=set(program['required_functions']);invalid=[]
    for f in r.client.optional_functions:
        if f in program['optional_functions']:functions.add(f)
        else:invalid.append(f)
    if invalid:errors.append(issue('FUNCTION_NOT_SUPPORTED_BY_PROFILE','unsupported',','.join(sorted(set(invalid)))))
    amounts=Counter()
    for f in sorted(functions):
        for rule in p['functions'][f]['objects']:
            if rule['op']=='constant':q=rule['value']
            elif rule['op']=='guests':q=r.client.guest_count
            else:q=(r.client.guest_count+rule['divisor']-1)//rule['divisor']
            amounts[rule['class']]+=q
    removed={o.instance_id for o in r.venue.existing if o.status=='movable' and not o.protected and any(a.instance_id==o.instance_id and a.action=='remove' and a.approved for a in r.actions)}
    used=[]
    for cls in sorted(amounts):
        candidates=[]
        for obj in r.venue.existing:
            permitted=any(a.instance_id==obj.instance_id and a.action=='reuse' and a.approved for a in r.actions)
            if obj.instance_id in removed or obj.status=='uncertain' or obj.review_status!='approved' or not permitted:continue
            if not compatible(obj,p):
                errors.append(issue('REUSE_CATALOG_INCOMPATIBLE',identity=obj.instance_id));continue
            if obj.class_name==cls:candidates.append(obj.instance_id)
        for iid in sorted(candidates)[:amounts[cls]]:used.append(dict(instance_id=iid,**{'class':cls},origin='observed_existing'))
    # Reuse requests for classes with zero demand still have compatibility checks.
    for obj in r.venue.existing:
        if obj.class_name not in amounts and obj.instance_id not in removed and obj.status!='uncertain' and obj.review_status=='approved' and any(a.instance_id==obj.instance_id and a.action=='reuse' and a.approved for a in r.actions) and not compatible(obj,p):errors.append(issue('REUSE_CATALOG_INCOMPATIBLE',identity=obj.instance_id))
    return assemble(r,p,sorted(functions),dict(amounts),used,removed,errors,'CONVENTIONAL_RULE_ASSIGNMENT_BASELINE')
