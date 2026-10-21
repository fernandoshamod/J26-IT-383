import math
from pathlib import Path
from PIL import Image
from shapely.geometry import Polygon
from contracts import TwinReview
from support import ROOT,digest,filehash,ResearchError
from evidence import verify_evidence_artifacts
open_source_image=Image.open
def reviewed_metric_twin(review:TwinReview,candidate:dict):
    if candidate.get('schema')!='IMAGE_SPACE_TWIN_CANDIDATE_V2':raise ResearchError('UNSUPPORTED_CANDIDATE_BUNDLE_SCHEMA')
    src=review.source;p=Path(src.path).resolve()
    if not p.is_relative_to(ROOT.resolve()) or not p.is_file():raise ResearchError('SOURCE_OUTSIDE_WORKSPACE_OR_MISSING')
    if filehash(p)!=src.sha256:raise ResearchError('SOURCE_HASH_MISMATCH')
    try:
        with open_source_image(p,formats=['PNG','JPEG']) as im:
            if im.size!=(src.width_pixels,src.height_pixels):raise ResearchError('SOURCE_DIMENSION_MISMATCH')
    except (OSError,Image.DecompressionBombError):raise ResearchError('INVALID_SOURCE_IMAGE')
    try:candidate_sha=digest(candidate)
    except (ValueError,TypeError):raise ResearchError('CANDIDATE_BUNDLE_NOT_FINITE_JSON')
    if candidate_sha!=review.candidate_bundle_sha256:raise ResearchError('CANDIDATE_BUNDLE_HASH_MISMATCH')
    source=candidate.get('source',{})
    if source.get('sha256')!=src.sha256:raise ResearchError('CANDIDATE_SOURCE_MISMATCH')
    if source!=src.model_dump():raise ResearchError('CANDIDATE_SOURCE_METADATA_MISMATCH')
    entries=candidate.get('objects')
    if not isinstance(entries,list) or any(not isinstance(o,dict) or not isinstance(o.get('id'),str) or not o['id'].strip() for o in entries):raise ResearchError('INVALID_CANDIDATE_OBJECT_RECORDS')
    ids=[o['id'] for o in entries]
    if len(ids)!=len(set(ids)):raise ResearchError('CANDIDATE_IDS_NOT_UNIQUE')
    decision=review.review
    if decision.status!='approved' or not decision.geometry_confirmed or not decision.metric_dimensions_confirmed:raise ResearchError('REVIEW_NOT_APPROVED')
    scope='SIMULATED_FIXTURE_REVIEW' if src.domain=='controlled_synthetic' else 'EXTERNAL_RESEARCH_REVIEW'
    if decision.scope!=scope:raise ResearchError('REVIEW_SCOPE_SOURCE_DOMAIN_MISMATCH')
    evidence=verify_evidence_artifacts(review.model_dump())
    def bounded(pt):return len(pt)==2 and all(math.isfinite(v) for v in pt) and 0<=pt[0]<=src.width_pixels and 0<=pt[1]<=src.height_pixels
    ratios=[]
    for control in review.calibration.controls:
        if not bounded(control.point_a_px) or not bounded(control.point_b_px):raise ResearchError('CALIBRATION_POINT_OUTSIDE_IMAGE')
        distance=math.dist(control.point_a_px,control.point_b_px)
        if distance<=1:raise ResearchError('DEGENERATE_CALIBRATION_CONTROL')
        ratios.append(control.known_distance_m/distance)
    # Controls must be genuinely distinct; repeated entries are not independent support.
    normalized=[tuple(sorted((tuple(c.point_a_px),tuple(c.point_b_px)))) for c in review.calibration.controls]
    if len(set(normalized))!=len(normalized):raise ResearchError('DUPLICATE_CALIBRATION_CONTROL')
    if (max(ratios)-min(ratios))/max(ratios)>.02:raise ResearchError('INCONSISTENT_CALIBRATION_CONTROLS')
    scale=sum(ratios)/len(ratios);origin=review.calibration.metric_origin_px
    if not bounded(origin):raise ResearchError('INVALID_METRIC_ORIGIN')
    def polygon(ring):
        if not all(bounded(pt) for pt in ring):raise ResearchError('REVIEW_POLYGON_OUTSIDE_SOURCE')
        p=Polygon(ring)
        if not p.is_valid or p.area<=0:raise ResearchError('INVALID_REVIEW_POLYGON')
        return p
    def metric(ring):return [[(pt[0]-origin[0])*scale,(pt[1]-origin[1])*scale] for pt in ring]
    boundary=polygon(review.boundary_px);objects=[];shapes=[];object_ids=set()
    for ob in review.objects:
        if ob.object_id in object_ids:raise ResearchError('DUPLICATE_REVIEWED_OBJECT_ID')
        object_ids.add(ob.object_id)
        if ob.status!='fixed':raise ResearchError('UNRESOLVED_OR_UNSUPPORTED_VENUE_OBJECT_STATUS',{'object_id':ob.object_id,'status':ob.status})
        if not set(ob.candidate_refs).issubset(set(ids)):raise ResearchError('UNKNOWN_REVIEWED_CANDIDATE_REFERENCE')
        # Manually added structures are allowed only with their explicit decision evidence.
        shape=polygon(ob.polygon_px)
        if not boundary.covers(shape):raise ResearchError('REVIEWED_OBJECT_OUTSIDE_BOUNDARY')
        for other in shapes:
            if other.intersection(shape).area>1e-8:raise ResearchError('FIXED_REVIEWED_OBJECTS_OVERLAP')
        shapes.append(shape);objects.append(dict(object_id=ob.object_id,**{'class':ob.class_name},group_id=None,footprint_coordinates_m=metric(list(shape.exterior.coords)),decision_evidence_ref=ob.decision_evidence_ref,candidate_refs=ob.candidate_refs))
    if sum(o['class']=='stage' for o in objects)!=1:raise ResearchError('EXACTLY_ONE_REVIEWED_STAGE_REQUIRED')
    return dict(schema='COMPONENT1_METRIC_TWIN_V1',venue_id=review.venue_id,venue_version=review.venue_version,source=src.model_dump(),candidate_bundle_sha256=review.candidate_bundle_sha256,candidate_bundle=candidate,review_record_sha256=digest(review.model_dump()),review_record=review.model_dump(),review=decision.model_dump(),calibration=review.calibration.model_dump(),evidence_verification=evidence,metres_per_pixel=scale,boundary_polygon_m=metric(list(boundary.exterior.coords)),fixed_objects=objects,approval_origin='EXPLICIT_LOCAL_EXTERNAL_INPUT_NOT_AUTHENTICATED',independent_real_venue_validation=False,safety_certified=False)
