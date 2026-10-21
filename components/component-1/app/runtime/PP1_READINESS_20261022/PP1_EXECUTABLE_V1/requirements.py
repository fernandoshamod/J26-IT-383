from contracts import Requirements
from support import ResearchError
def reconcile(r:Requirements):
    if r.guest_count%8:raise ResearchError('GUEST_COUNT_REQUIRES_EXACT_EIGHT_SEAT_GROUPS')
    expected={'round_table':r.guest_count//8,'chair':r.guest_count}
    if r.quantities.model_dump()!=expected:raise ResearchError('FURNITURE_QUANTITY_CAPACITY_CONFLICT',{'expected':expected})
    clearances=[.5];stage=[];movement=[];preferences=[];trace=[]
    for origin,party in [('client',r.client),('planner',r.planner)]:
        if party.approval_status!='approved':raise ResearchError('REQUIREMENTS_NOT_APPROVED',{'origin':origin,'requirement_id':party.requirement_id})
        if party.guest_count is not None and party.guest_count!=r.guest_count:raise ResearchError('CLIENT_PLANNER_CAPACITY_CONFLICT',{'origin':origin,'declared':party.guest_count,'requested':r.guest_count})
        if party.quantities is not None and party.quantities.model_dump()!=expected:raise ResearchError('CLIENT_PLANNER_FURNITURE_CONFLICT',{'origin':origin})
        hard=party.hard
        if hard.minimum_clearance_m is not None:
            if hard.minimum_clearance_m<.5:raise ResearchError('CLEARANCE_BELOW_EXPERIMENTAL_MINIMUM')
            clearances.append(hard.minimum_clearance_m)
        if hard.maximum_mean_stage_distance_m is not None:
            if hard.maximum_mean_stage_distance_m<=0:raise ResearchError('INVALID_STAGE_DISTANCE_LIMIT')
            stage.append(hard.maximum_mean_stage_distance_m)
        if hard.maximum_total_movement_m is not None:
            if hard.maximum_total_movement_m<0:raise ResearchError('INVALID_MOVEMENT_LIMIT')
            movement.append(hard.maximum_total_movement_m)
        if party.alternative_preference:preferences.append(party.alternative_preference)
        trace.append(dict(origin=origin,requirement_id=party.requirement_id,provenance_ref=party.provenance_ref,hard=hard.model_dump(),alternative_preference=party.alternative_preference))
    if len(set(preferences))>1:raise ResearchError('CLIENT_PLANNER_SOFT_PREFERENCE_CONFLICT',{'preferences':preferences})
    if len(r.protected_group_ids)!=len(set(r.protected_group_ids)):raise ResearchError('DUPLICATE_PROTECTED_ID')
    return dict(guest_count=r.guest_count,groups=r.guest_count//8,quantities=expected,minimum_clearance_m=max(clearances),maximum_mean_stage_distance_m=min(stage) if stage else None,maximum_total_movement_m=min(movement) if movement else None,alternative_preference=preferences[0] if preferences else 'balanced',protected_group_ids=r.protected_group_ids,protected_object_ids=r.protected_object_ids,trace=trace,merge_policy='Hard requirements are conjunctions: larger minimum clearance, smaller upper bounds; no silent relaxation')
