from typing import Literal,Annotated
from pydantic import BaseModel,ConfigDict,Field,model_validator
Number=Annotated[float,Field(allow_inf_nan=False)]
Point=tuple[Number,Number]
class Strict(BaseModel):
    model_config=ConfigDict(extra='forbid',strict=True,allow_inf_nan=False)
    @model_validator(mode='after')
    def nonblank_strings(self):
        for name in type(self).model_fields:
            value=getattr(self,name)
            if isinstance(value,str) and not value.strip():raise ValueError('Blank string is not valid for '+name)
        return self
class Source(Strict):
    path:str
    sha256:str=Field(pattern=r'^[0-9a-f]{64}$')
    width_pixels:int=Field(gt=0)
    height_pixels:int=Field(gt=0)
    domain:Literal['real_source','controlled_synthetic']
class Control(Strict):
    point_a_px:list[Number]=Field(min_length=2,max_length=2)
    point_b_px:list[Number]=Field(min_length=2,max_length=2)
    known_distance_m:Number=Field(gt=0)
    evidence_ref:str=Field(min_length=1)
class Calibration(Strict):
    method:Literal['isotropic_two_point_controls']
    controls:list[Control]=Field(min_length=2)
    metric_origin_px:list[Number]=Field(min_length=2,max_length=2)
class ReviewDecision(Strict):
    status:Literal['pending','approved','rejected']
    reviewer_id:str=Field(min_length=1)
    evidence_ref:str=Field(min_length=1)
    scope:Literal['SIMULATED_FIXTURE_REVIEW','EXTERNAL_RESEARCH_REVIEW']
    geometry_confirmed:bool
    metric_dimensions_confirmed:bool
class ReviewedObject(Strict):
    object_id:str=Field(min_length=1)
    class_name:Literal['stage','buffet_counter','fixed_column','wall','restricted_zone']
    status:Literal['fixed','movable','uncertain']
    polygon_px:list[list[Number]]=Field(min_length=3)
    candidate_refs:list[str]
    decision_evidence_ref:str=Field(min_length=1)
class EvidenceArtifact(Strict):
    evidence_id:str=Field(min_length=1)
    path:str=Field(min_length=1)
    sha256:str=Field(pattern=r'^[0-9a-f]{64}$')
    source_sha256:str=Field(pattern=r'^[0-9a-f]{64}$')
class TwinReview(Strict):
    contract_id:Literal['COMPONENT1_REVIEWED_TWIN_V1']
    venue_id:str=Field(min_length=1)
    venue_version:int=Field(ge=1)
    source:Source
    candidate_bundle_sha256:str=Field(pattern=r'^[0-9a-f]{64}$')
    calibration:Calibration
    boundary_px:list[list[Number]]=Field(min_length=3)
    objects:list[ReviewedObject]=Field(min_length=1)
    review:ReviewDecision
    evidence_artifacts:list[EvidenceArtifact]=Field(default_factory=list)
class Hard(Strict):
    minimum_clearance_m:Number|None=None
    maximum_mean_stage_distance_m:Number|None=None
    maximum_total_movement_m:Number|None=None
class Quantities(Strict):
    round_table:int=Field(ge=1)
    chair:int=Field(ge=1)
class Party(Strict):
    requirement_id:str=Field(min_length=1)
    provenance_ref:str=Field(min_length=1)
    approval_status:Literal['approved','pending','rejected']
    guest_count:int|None=Field(default=None,gt=0)
    quantities:Quantities|None=None
    hard:Hard=Field(default_factory=Hard)
    alternative_preference:Literal['stage_proximity','minimum_disruption','balanced']|None=None
class Requirements(Strict):
    event_id:str=Field(min_length=1)
    event_type:Literal['Wedding']
    guest_count:int=Field(gt=0,le=240)
    seats_per_table:Literal[8]=8
    quantities:Quantities
    client:Party
    planner:Party
    protected_group_ids:list[str]=Field(default_factory=list)
    protected_object_ids:list[str]=Field(default_factory=list)
class Reference(Strict):
    run_id:str
    layout_id:str
    layout_sha256:str=Field(pattern=r'^[0-9a-f]{64}$')
    approval_id:str
class Permission(Strict):
    group_id:str
    action:Literal['move','remove']
    approved:bool
    reviewer_id:str=Field(min_length=1)
    reason:str=Field(min_length=1)
    scope:Literal['SIMULATED_FIXTURE_REVIEW','EXTERNAL_RESEARCH_REVIEW']
class Optimize(Strict):
    contract_id:Literal['COMPONENT1_PP1_EXECUTABLE_V1']
    mode:Literal['initial_design','adaptive_revision','guest_change']
    venue_id:str
    venue_version:int=Field(ge=1)
    twin_sha256:str=Field(pattern=r'^[0-9a-f]{64}$')
    requirements:Requirements
    seed:int=Field(ge=0,le=2147483647)
    reference:Reference|None=None
    affected_group_ids:list[str]=Field(default_factory=list)
    remove_group_ids:list[str]=Field(default_factory=list)
    permissions:list[Permission]=Field(default_factory=list)
class Approve(Strict):
    layout_id:str
    layout_sha256:str=Field(pattern=r'^[0-9a-f]{64}$')
    venue_version:int=Field(ge=1)
    reviewer_id:str=Field(min_length=1)
    evidence_ref:str=Field(min_length=1)
    scope:Literal['SIMULATED_FIXTURE_REVIEW','EXTERNAL_RESEARCH_REVIEW']
class Revoke(Strict):
    reviewer_id:str=Field(min_length=1)
    reason:str=Field(min_length=1)
