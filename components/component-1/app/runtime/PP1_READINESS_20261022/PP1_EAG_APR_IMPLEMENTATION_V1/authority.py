"""Local simulated scope enforcement, not identity authentication."""
from runtime import *

def qualify(packet,spec,reference=None):
    r=packet['scene'];c=packet['context'];issues=[]
    expected={'version','scope','scenario','protected_object_ids','allowed_groups','new_supply_permitted','requested_group','object_moves','reference_sha256'}
    if set(c)!=expected:issues.append('UNKNOWN_OR_MISSING_CONTEXT_FIELDS')
    try:
        e=packet['authority'];p=Path(e['path']).resolve()
        if not p.is_relative_to(ROOT) or filehash(p)!=e['sha256'] or read(p)!=dict(scene_sha256=digest(r),context=c,scope='SIMULATED_FIXTURE_NOT_AUTHENTICATED_AUTHORITY'):issues.append('AUTHORITY_EVIDENCE_BINDING')
    except (OSError,ValueError,KeyError):issues.append('AUTHORITY_EVIDENCE_MISSING')
    if c['scope']!='SIMULATED_FIXTURE' or c['scenario'] not in ['CONTROLLED_NOMINAL','CONTROLLED_OPERATIONAL_RESTRICTION']:issues.append('CONTEXT_SCOPE_UNSUPPORTED')
    if type(c['version']) is not int or c['version']<1:issues.append('CONTEXT_VERSION_INVALID')
    if len(c['protected_object_ids'])!=len(set(c['protected_object_ids'])) or len(c['allowed_groups'])!=len(set(c['allowed_groups'])):issues.append('DUPLICATE_CONTEXT_IDS')
    if reference:
        if c['reference_sha256']!=digest(reference['layout']):issues.append('REFERENCE_HASH_MISMATCH')
        groups=set(reference['layout']['group_centers_m']);objects={o['object_id']:o for o in reference['layout']['objects']}
        if not set(c['allowed_groups'])<=groups or not set(c['protected_object_ids'])<=set(objects):issues.append('UNKNOWN_PERMISSION_OR_LOCK_ID')
        for move in c['object_moves']:
            ob=next((o for o in r['venue']['existing'] if o['instance_id']==move.get('object_id')),None)
            if not ob or ob['protected'] or ob['status']=='fixed' or not move.get('approved') or move.get('actor_id')!=r['planner']['actor_id']:issues.append('PROTECTED_OR_UNAUTHORIZED_STOCK_MOVE')
            else:issues.append('OBSERVED_STOCK_RELOCATION_UNSUPPORTED')
        if r['client']['guest_count']>reference['request']['client']['guest_count'] and not c['new_supply_permitted']:issues.append('NEW_SUPPLY_PERMISSION_REQUIRED')
        if c['requested_group']:
            target=c['requested_group']
            if target not in c['allowed_groups']:issues.append('MOVE_PERMISSION_REQUIRED')
            if any(o['group_id']==target and o['object_id'] in c['protected_object_ids'] for o in objects.values()):issues.append('PROTECTED_GROUP_MOVE')
    elif c['reference_sha256'] is not None or c['requested_group'] or c['object_moves']:issues.append('REFERENCE_REQUIRED')
    if spec['status']!='accepted':
        return ('pending' if spec['status']=='pending_review' else 'unsupported' if spec['status']=='unsupported' else 'refused'),issues+[i['code'] for i in spec['issues']]
    if issues:return ('unsupported' if all(i.endswith('UNSUPPORTED') for i in issues) else 'refused'),issues
    return 'qualified',[]
