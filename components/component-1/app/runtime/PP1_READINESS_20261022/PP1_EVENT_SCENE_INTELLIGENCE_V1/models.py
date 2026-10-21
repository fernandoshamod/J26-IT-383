from typing import Literal,Annotated
from pydantic import BaseModel,ConfigDict,Field,model_validator
Num=Annotated[float,Field(allow_inf_nan=False)]
Pt=Annotated[list[Num],Field(min_length=2,max_length=2)]
Ring=list[Pt]
Event=Literal['wedding','birthday','anniversary','corporate','conference','musical_show','concert']
class Strict(BaseModel):
    model_config=ConfigDict(extra='forbid',strict=True,allow_inf_nan=False)
    @model_validator(mode='after')
    def strings(self):
        for v in self.__dict__.values():
            if isinstance(v,str) and not v.strip():raise ValueError('BLANK_STRING')
        return self
class Evidence(Strict):
    path:str
    sha256:str=Field(pattern='^[0-9a-f]{64}$')
    source_sha256:str=Field(pattern='^[0-9a-f]{64}$')
class Control(Strict):
    a_px:list[Num]=Field(min_length=2,max_length=2)
    b_px:list[Num]=Field(min_length=2,max_length=2)
    distance_m:Num=Field(gt=0)
class Source(Strict):
    path:str
    sha256:str=Field(pattern='^[0-9a-f]{64}$')
    width_px:int=Field(gt=0)
    height_px:int=Field(gt=0)
    domain:Literal['controlled_synthetic','real_source','plan_derived_controlled']
    origin:Literal['CONTROLLED_GENERATOR','MODEL_CANDIDATES','PLAN_DRAWING_INTERPRETATION']
class Review(Strict):
    status:Literal['approved','pending','rejected']
    reviewer_id:str
    scope:Literal['SIMULATED_FIXTURE','EXTERNAL_REVIEW','PLAN_DERIVED_SIMULATED']
    evidence:Evidence
class Existing(Strict):
    instance_id:str
    class_name:str
    footprint_m:Ring=Field(min_length=4)
    status:Literal['fixed','movable','uncertain']
    review_status:Literal['approved','pending','rejected']
    protected:bool=False
    candidate_ref:str
class Venue(Strict):
    venue_id:str
    version:int=Field(ge=1)
    source:Source
    boundary_px:Ring=Field(min_length=4)
    origin_px:list[Num]=Field(min_length=2,max_length=2)
    controls:list[Control]=Field(min_length=2)
    boundary_m:Ring=Field(min_length=4)
    existing:list[Existing]
    review:Review
class Hard(Strict):
    minimum_clearance_m:Num=Field(default=.5,ge=.5)
    maximum_mean_stage_distance_m:Num|None=Field(default=None,gt=0)
    maximum_assignment_movement_m:Num|None=Field(default=None,ge=0)
class Party(Strict):
    role:Literal['client','planner']
    actor_id:str
    scope:Literal['SIMULATED_FIXTURE','EXTERNAL_REVIEW','PLAN_DERIVED_SIMULATED']
    approval_status:Literal['approved','pending','rejected']
    policy_sha256:str=Field(pattern='^[0-9a-f]{64}$')
    event_type:Event
    guest_count:int=Field(gt=0,le=1000)
    optional_functions:list[str]=Field(default_factory=list)
    hard:Hard=Field(default_factory=Hard)
    evidence:Evidence
class Action(Strict):
    instance_id:str
    action:Literal['reuse','remove','move']
    approved:bool
    actor_id:str
    scope:Literal['SIMULATED_FIXTURE','EXTERNAL_REVIEW','PLAN_DERIVED_SIMULATED']
class Placement(Strict):
    class_name:str
    ordinal:int=Field(ge=1)
    footprint_m:Ring=Field(min_length=4)
class Request(Strict):
    schema_id:Literal['EVENT_SCENE_INPUT_V1']='EVENT_SCENE_INPUT_V1'
    event_id:str
    venue:Venue
    client:Party
    planner:Party
    actions:list[Action]=Field(default_factory=list)
    placements:list[Placement]=Field(default_factory=list)
    dance_zone_m:Ring|None=None
    @model_validator(mode='after')
    def roles(self):
        if self.client.role!='client' or self.planner.role!='planner':raise ValueError('ACTOR_ROLE_MISMATCH')
        return self

def venue_payload(v):
    data=v.model_dump();data['review'].pop('evidence');return data
def party_payload(p):return p.model_dump(exclude={'evidence'})
def planner_payload(r):return dict(party=party_payload(r.planner),actions=[a.model_dump() for a in r.actions],placements=[p.model_dump() for p in r.placements],dance_zone_m=r.dance_zone_m)
