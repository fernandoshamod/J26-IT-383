from backend.schemas.feasibility_request import FeasibilityInput
from backend.schemas.feasibility import FeasibilityResponse
'PlanoVision package feasibility API.'
from typing import Any
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from backend.engine.feasibility_service import validate_package
router = APIRouter(prefix='/api/feasibility', tags=['Feasibility'])

class FeasibilityRequest(BaseModel):
    event: dict[str, Any]
    package_options: list[dict[str, Any]] = Field(min_length=1)

@router.post('/validate', response_model=FeasibilityResponse)
def validate_feasibility(request: FeasibilityInput):
    """Validate a package using synthetic simulation evidence."""
    try:
        result = validate_package(request.event.model_dump(mode='python'), tuple((option.model_dump(mode='python') for option in request.package_options)))
        return result
    except (KeyError, ValueError, TypeError) as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

@router.post('/validate-dynamic')
def validate_dynamic_feasibility(request: FeasibilityInput):
    """Validate USER options against current source records, never client prices."""
    import math

    from pydantic import ValidationError
    from backend.engine.dynamic_feasibility import validate_dynamic_package
    from backend.engine.json_serializer import to_json_safe
    from backend.engine.package_data_loader import load_service_options
    from backend.schemas.dynamic_package_request import DynamicPackageRequest

    event = request.event.model_dump(mode='python')
    if not event['event_id'].startswith('USER-'):
        raise HTTPException(status_code=422, detail='Expected a USER-* event ID')
    raw_services = event.get('required_services')
    services = (
        [part.strip() for part in raw_services.split(';')]
        if isinstance(raw_services, str) else raw_services
    )
    try:
        checked_event = DynamicPackageRequest.model_validate({
            **event, 'required_services': services,
        })
    except ValidationError as exc:
        raise HTTPException(status_code=422, detail=to_json_safe(exc.errors(include_context=False))) from exc
    if not math.isfinite(float(event['duration_hours'])):
        raise HTTPException(status_code=422, detail='duration_hours must be finite')
    if len(request.package_options) != len(checked_event.required_services):
        raise HTTPException(
            status_code=422,
            detail='Submit exactly one option for each required service',
        )

    source = load_service_options()
    material_fields = (
        'business_id', 'service_category', 'unit_price_lkr', 'pricing_basis',
        'min_billable_guests', 'min_billable_hours',
        'guest_capacity_applicability', 'max_guests',
        'simulated_service_city', 'simulated_service_state',
        'supported_event_types', 'is_vendor_confirmed', 'data_origin',
    )
    canonical_options = []
    for submitted_model in request.package_options:
        submitted = submitted_model.model_dump(mode='python', exclude_unset=True)
        option_id = str(submitted.get('service_option_id', '')).strip()
        if not option_id:
            raise HTTPException(status_code=422, detail='service_option_id is required for USER-event feasibility')
        matches = source.loc[source['service_option_id'].astype(str).eq(option_id)]
        if len(matches) != 1:
            raise HTTPException(status_code=422, detail=f'Unknown or ambiguous service_option_id: {option_id}')
        canonical = to_json_safe(matches.iloc[0].to_dict())
        for field in material_fields:
            if field not in submitted:
                continue
            actual, expected = submitted[field], canonical[field]
            equal = (
                math.isclose(float(actual), float(expected), rel_tol=0, abs_tol=0.005)
                if isinstance(actual, (int, float)) and not isinstance(actual, bool)
                and isinstance(expected, (int, float)) and not isinstance(expected, bool)
                else actual == expected
            )
            if not equal:
                raise HTTPException(
                    status_code=422,
                    detail=f'Option {option_id} has conflicting {field}; use the current source record',
                )
        canonical_options.append(canonical)
    return validate_dynamic_package(event, canonical_options)
