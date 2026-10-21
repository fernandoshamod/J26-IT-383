"""Pydantic response schema for feasibility validation."""

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class FeasibilityResponse(BaseModel):
    """Synthetic package feasibility validation result."""

    model_config = ConfigDict(extra="forbid")

    event_id: str

    total_cost_lkr: float
    budget_lkr: float
    budget_remaining_lkr: float

    passed_checks: int = Field(ge=0)
    pending_checks: int = Field(ge=0)
    failed_checks: int = Field(ge=0)

    final_status: Literal[
        "Fail",
        "Verification Required",
        "Pass in Simulation",
    ]

    evidence_scope: Literal[
        "Synthetic simulation only"
    ]
