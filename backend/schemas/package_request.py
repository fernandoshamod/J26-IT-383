
"""Request schema for synthetic package generation."""

from pydantic import BaseModel, Field, field_validator


class PackageGenerationRequest(BaseModel):
    """Identify an existing synthetic event."""

    event_id: str = Field(
        ...,
        min_length=1,
        description="Existing synthetic event identifier"
    )

    @field_validator("event_id")
    @classmethod
    def validate_event_id(cls, value: str) -> str:
        cleaned = value.strip()

        if not cleaned:
            raise ValueError("event_id cannot be empty")

        return cleaned
