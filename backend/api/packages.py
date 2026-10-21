
"""FastAPI routes for synthetic package generation."""

from fastapi import APIRouter, HTTPException

from backend.schemas.package_request import (
    PackageGenerationRequest
)
from backend.schemas.package_response import (
    PackageGenerationResponse
)
from backend.engine.package_service import (
    generate_packages_for_event_id
)


router = APIRouter(
    prefix="/api/packages",
    tags=["Package Generation"]
)


@router.post(
    "/generate",
    response_model=PackageGenerationResponse
)
def generate_event_packages(
    request: PackageGenerationRequest
):
    """Generate packages for an existing synthetic event."""

    try:
        result = generate_packages_for_event_id(
            request.event_id
        )

    except LookupError as exc:
        raise HTTPException(
            status_code=404,
            detail=str(exc)
        ) from exc

    except ValueError as exc:
        raise HTTPException(
            status_code=422,
            detail=str(exc)
        ) from exc

    return result


from backend.schemas.dynamic_package_request import DynamicPackageRequest
from backend.engine.dynamic_package_service import generate_dynamic_packages
from backend.engine.risk_signals import RiskModelUnavailable


@router.post("/generate-dynamic")
def generate_dynamic_event_packages(request: DynamicPackageRequest):
    """Generate new package combinations from user-entered requirements."""
    try:
        return generate_dynamic_packages(request)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except RiskModelUnavailable as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
