
"""Response schemas for synthetic package generation."""

from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class PackageGenerationSummary(BaseModel):
    """Generation results and rejection statistics."""

    model_config = ConfigDict(extra="forbid")

    packages: list[dict[str, Any]]

    total_generated: int = Field(ge=0)
    budget_rejected: int = Field(ge=0)
    duplicate_vendor_rejected: int = Field(ge=0)


class PackageGenerationResponse(BaseModel):
    """API response for a synthetic event's generated packages."""

    model_config = ConfigDict(extra="forbid")

    event_id: str = Field(min_length=1)
    required_services: list[str]
    currency: str
    data_origin: str
    is_vendor_confirmed: bool

    candidate_counts: dict[str, int]
    generation: PackageGenerationSummary
