"""Strict local CLI contracts, not new frozen backend HTTP routes."""
from typing import Literal
from pydantic import BaseModel,ConfigDict,Field,model_validator
class Strict(BaseModel):model_config=ConfigDict(extra='forbid',strict=True,allow_inf_nan=False)
class StockMove(Strict):
    object_id:str=Field(min_length=1)
    approved:bool
    actor_id:str=Field(min_length=1)
class Context(Strict):
    version:int=Field(ge=1)
    scope:Literal['SIMULATED_FIXTURE']
    scenario:Literal['CONTROLLED_NOMINAL','CONTROLLED_OPERATIONAL_RESTRICTION']
    protected_object_ids:list[str]
    allowed_groups:list[str]
    new_supply_permitted:bool
    requested_group:str|None
    object_moves:list[StockMove]
    reference_sha256:str|None=Field(pattern='^[0-9a-f]{64}$')
    @model_validator(mode='after')
    def unique(self):
        if len(set(self.protected_object_ids))!=len(self.protected_object_ids) or len(set(self.allowed_groups))!=len(self.allowed_groups):raise ValueError('DUPLICATE_CONTEXT_IDENTITIES')
        return self
class AuthorityArtifact(Strict):
    path:str=Field(min_length=1)
    sha256:str=Field(pattern='^[0-9a-f]{64}$')
class Packet(Strict):
    scene:dict
    context:Context
    authority:AuthorityArtifact
