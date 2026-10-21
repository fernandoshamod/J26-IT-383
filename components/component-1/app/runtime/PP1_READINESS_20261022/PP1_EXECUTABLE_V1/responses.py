"""Frozen PP1 response envelopes. Geometry/XAI are supplied without filtering."""
from typing import Any,Literal
from contracts import Strict,Number
from pydantic import Field

class LayoutObject(Strict):
    object_id:str
    class_name:Literal['stage','buffet_counter','fixed_column','wall','restricted_zone','round_table','chair']=Field(alias='class')
    group_id:str|None
    footprint_coordinates_m:list[list[Number]]
class ConstraintResults(Strict):
    independently_verified:bool
    outside_count:int
    overlap_count:int
    locked_object_changes:int
    minimum_clearance_m:Number
class Layout(Strict):
    layout_id:str
    objects:list[LayoutObject]
    group_centers_m:dict[str,list[Number]]
    objective_metrics:dict[str,Number|str]
    constraint_results:ConstraintResults

class Success(Strict):
    contract_id:Literal['COMPONENT1_PP1_EXECUTABLE_V1']
    run_id:str
    status:Literal['success']
    source_domain:Literal['controlled_synthetic','real_source']
    venue_id:str
    venue_version:int
    twin_sha256:str
    actual_boundary_polygon_m:list[list[float]]
    actual_fixed_geometry_sha256:str
    source_image_sha256:str
    candidate_layouts:list[Layout]
    selected_layout_id:str
    resolved_requirements:dict[str,Any]
    group_changes:dict[str,Any]
    initialization_or_retained_reference_m:dict[str,list[float]]
    verification:dict[str,Any]
    optimizer_evaluations:int
    provenance:dict[str,Any]
    real_planner_authentication:bool
    independent_real_venue_validation:bool
    safety_certified:bool
    xai:dict[str,Any]
class NonSuccess(Strict):
    contract_id:Literal['COMPONENT1_PP1_EXECUTABLE_V1']
    run_id:str
    status:Literal['rejected','denied','infeasible','error']
    reason:str
    details:dict[str,Any]
    candidate_layouts:list[dict[str,Any]]
    optimizer_evaluations:int
    scope:Literal['local_research']
    real_planner_authentication:bool
    xai:dict[str,Any]
OptimizationResponse=Success|NonSuccess
class StoredRun(Strict):
    request:dict[str,Any]
    response:OptimizationResponse
class TwinReceipt(Strict):
    venue_id:str
    venue_version:int
    twin_sha256:str
    metric_twin:dict[str,Any]
class ImageReceipt(Strict):
    image_id:str
    image_path:str
    sha256:str
    width_pixels:int
    height_pixels:int
    physical_real_venue_provenance_verified:bool
class ArtifactLink(Strict):
    sha256:str
    url:str
class AnalysisReceipt(Strict):
    analysis_id:str
    status:Literal['review_required']
    candidate_bundle:dict[str,Any]
    pending_review_template:dict[str,Any]
    model_report:dict[str,Any]
    gate:dict[str,Any]
    artifacts:dict[str,ArtifactLink]
class ApprovalReceipt(Strict):
    approval_id:str
    status:Literal['approved']
    approval_origin:str
class RevocationReceipt(Strict):
    approval_id:str
    status:Literal['revoked']
class GateError(Strict):
    reason:str
    details:dict[str,Any]
class RunIndexEntry(Strict):
    run_id:str
    status:str
    response_sha:str
class RunIndex(Strict):
    runs:list[RunIndexEntry]
class Health(Strict):
    status:Literal['ready']
    scope:Literal['local_research']
    real_authentication:bool
    database:str
