"""Context-qualified machine-checkable records, no signatures/regulatory claims."""
from runtime import *

def issue(packet,body):
    cert=dict(schema='EAG_CONTEXTUAL_VALIDITY_CERTIFICATE_V1',context_version=packet['context']['version'],venue_version=packet['scene']['venue']['version'],fingerprint=facts(packet),verified_evidence_dependencies=[dict(path=p,sha256=h) for p,h in facts(packet)['artifacts'].items()],active_hard_constraints=body['spec']['hard'],protected_object_ids=packet['context']['protected_object_ids'],mandatory_functions=body['spec']['functions'],validation=body['validation'],status=body['status'],recommendation_ready=body['status']=='eligible' and bool(body['candidate_layouts']),result_payload_sha256=digest(body),reasons=body['reasons'],global_infeasibility_proven=False,regulatory_certification=False,authenticated_identity=False)
    cert['certificate_sha256']=digest(cert)
    claims=[dict(layout_id=l['layout_id'],layout_sha256=digest(l),constraint_ids=sorted(body['graph_constraint_ids']),counts=body['validation'][l['layout_id']]['geometry']['allocated_counts'],mean_stage_distance_m=l['objective_metrics']['mean_stage_distance_m'],initializer_assignment_movement_m=l['objective_metrics']['initializer_assignment_movement_m'],stable_group_relocation_m=body['validation'][l['layout_id']]['stable_group_relocation_m']) for l in body['candidate_layouts']]
    xai=dict(certificate_sha256=cert['certificate_sha256'],context_sha256=digest(packet['context']),request_sha256=digest(packet['scene']),evidence_ids=cert['verified_evidence_dependencies'],claims=claims,reasons=body['reasons'],weather_used=False,sgcn_used=False,causal_claim=False)
    return dict(body,certificate=cert,xai=xai)

def is_current(packet,certificate):return certificate.get('fingerprint')==facts(packet) and certificate.get('certificate_sha256')==digest({k:v for k,v in certificate.items() if k!='certificate_sha256'})
