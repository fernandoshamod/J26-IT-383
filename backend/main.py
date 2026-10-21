from backend.api.events import router as events_router
from backend.api.feasibility import router as feasibility_router
from backend.api.admin import router as admin_router
from backend.api.vendor_demo import router as vendor_demo_router
from fastapi import FastAPI

app = FastAPI(
    title="PlanoVision Vendor Intelligence API",
    description="Vendor Intelligence and Smart Package Recommendation Engine",
    version="0.1.0"
)


from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from backend.engine.json_serializer import to_json_safe


@app.exception_handler(RequestValidationError)
async def finite_validation_error_response(request, exc):
    """Keep rejected non-finite JSON numbers from breaking the 422 response."""
    return JSONResponse(
        status_code=422,
        content=to_json_safe({"detail": jsonable_encoder(exc.errors())}),
    )

app.include_router(events_router)
app.include_router(admin_router)
app.include_router(vendor_demo_router)

@app.get("/")
def root():
    return {
        "application": "PlanoVision",
        "component": "Vendor Intelligence",
        "status": "running"
    }

@app.get("/health")
def health_check():
    return {
        "status": "healthy",
        "service": "vendor-intelligence-api"
    }

app.include_router(feasibility_router)

# Package Generation API
from backend.api import packages as package_routes_277
app.include_router(package_routes_277.router)

from backend.api import locations
app.include_router(locations.router)





