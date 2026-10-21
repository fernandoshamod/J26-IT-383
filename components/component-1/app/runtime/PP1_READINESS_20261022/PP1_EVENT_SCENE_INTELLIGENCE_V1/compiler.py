"""Reusable explicit policy interpreter and deterministic existing/new reconciliation."""
import math
from common import *
from models import Request
from core import preflight,issue,compatible,assemble

def compile_scene(request,policy=None):
    r=Request.model_validate(request);policy=read(HERE/'profiles.json') if policy is None else policy
    issues=preflight(r,policy)
    profile=next((p for p in policy['profiles'].values() if r.client.event_type in p['event_types']),None)
    if profile is None:raise GateError('EVENT_PROFILE_MISSING')
    unknown=set(r.client.optional_functions)-set(profile['optional_functions'])
    if unknown:issues.append(issue('FUNCTION_NOT_SUPPORTED_BY_PROFILE','unsupported',','.join(sorted(unknown))))
    functions=sorted(set(profile['required_functions'])|(set(r.client.optional_functions)-unknown));demand={}
    for f in functions:
        for rule in policy['functions'][f]['objects']:
            n=r.client.guest_count if rule['op']=='guests' else rule['value'] if rule['op']=='constant' else math.ceil(r.client.guest_count/rule['divisor'])
            demand[rule['class']]=demand.get(rule['class'],0)+n
    actions={(a.instance_id,a.action):a for a in r.actions};removed=set();reused=[]
    for obj in sorted(r.venue.existing,key=lambda o:o.instance_id):
        removal=actions.get((obj.instance_id,'remove'))
        if removal and removal.approved and obj.status=='movable' and not obj.protected:removed.add(obj.instance_id);continue
        use=actions.get((obj.instance_id,'reuse'))
        if not use or not use.approved or obj.status=='uncertain' or obj.review_status!='approved':continue
        if not compatible(obj,policy):issues.append(issue('REUSE_CATALOG_INCOMPATIBLE',identity=obj.instance_id));continue
        if sum(a['class']==obj.class_name for a in reused)<demand.get(obj.class_name,0):reused.append(dict(instance_id=obj.instance_id,**{'class':obj.class_name},origin='observed_existing'))
    return assemble(r,policy,functions,demand,reused,removed,issues,'POLICY_DERIVATION_AND_RECONCILIATION')
