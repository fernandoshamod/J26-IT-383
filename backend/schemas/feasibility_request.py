"""Input models for synthetic feasibility validation."""

from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class EventInput(BaseModel):
    """Event information required by the feasibility engine."""

    model_config = ConfigDict(extra="allow")

    event_id: str = Field(min_length=1)
    budget_lkr: float = Field(ge=0)
    guest_count: int = Field(ge=1)
    duration_hours: float = Field(gt=0)

    event_date: str = Field(min_length=1)
    start_time: str = Field(min_length=1)
    end_time: str = Field(min_length=1)


class VendorOptionInput(BaseModel):
    """Vendor service option with preserved research metadata."""

    model_config = ConfigDict(extra="allow")

    business_id: str = Field(min_length=1)
    pricing_basis: str = Field(min_length=1)
    unit_price_lkr: float = Field(ge=0)

    data_origin: str | None = None
    guest_capacity_applicability: str | None = None

    min_billable_guests: int | float | None = None
    min_billable_hours: int | float | None = None
    max_guests: int | float | None = None


class FeasibilityInput(BaseModel):
    """Request contract for package feasibility validation."""

    model_config = ConfigDict(extra="forbid")

    event: EventInput
    package_options: list[VendorOptionInput] = Field(
        min_length=1
    )
