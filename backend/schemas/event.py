from datetime import date, time
from pydantic import BaseModel, Field, field_validator, model_validator
from backend.schemas.dynamic_package_request import SERVICES

class EventRequest(BaseModel):
    event_type: str = Field(min_length=1)
    event_date: date
    start_time: time
    end_time: time
    city: str = Field(min_length=1)
    state: str = Field(min_length=1)
    guest_count: int = Field(gt=0)
    budget_lkr: float = Field(gt=0, allow_inf_nan=False)
    required_services: list[str] = Field(min_length=1)
    top_k: int = Field(default=10, ge=1, le=50)

    @field_validator("event_type", "city", "state")
    @classmethod
    def clean_text(cls, value: str) -> str: return value.strip()

    @field_validator("event_type")
    @classmethod
    def validate_event_type(cls, value: str) -> str:
        supported = {"Wedding", "Birthday", "Corporate"}
        match = next((item for item in supported if item.casefold() == value.casefold()), None)
        if match is None: raise ValueError(f"Unsupported event type: {value}")
        return match

    @field_validator("required_services")
    @classmethod
    def validate_services(cls, value: list[str]) -> list[str]:
        cleaned = list(dict.fromkeys(item.strip() for item in value))
        invalid = set(cleaned) - SERVICES
        if invalid: raise ValueError(f"Unsupported services: {sorted(invalid)}")
        return cleaned

    @model_validator(mode="after")
    def validate_duration(self):
        from datetime import datetime, timedelta
        if self.event_date < date.today(): raise ValueError("Event date must be today or later")
        start = datetime.combine(self.event_date, self.start_time)
        end = datetime.combine(self.event_date, self.end_time)
        if end <= start: end += timedelta(days=1)
        if (end - start).total_seconds() / 3600 > 24: raise ValueError("Event duration must be within 24 hours")
        return self
