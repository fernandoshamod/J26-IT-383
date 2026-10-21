from datetime import date
from typing import Literal

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field

from backend.vendor_demo_db import (
    create_availability,
    create_service,
    dashboard,
    delete_availability,
    delete_service,
    get_profile,
    list_availability,
    list_services,
    update_availability,
    update_profile,
    update_service,
)

router = APIRouter(prefix="/api/vendor-demo", tags=["Vendor Portal Demo"])


class ProfileRequest(BaseModel):
    business_name: str = Field(min_length=1, max_length=160)
    description: str = Field(default="", max_length=1000)
    email: str = Field(min_length=3, max_length=200)
    phone: str = Field(min_length=3, max_length=50)
    city: str = Field(min_length=1, max_length=100)
    state: str = Field(min_length=1, max_length=100)


class ServiceRequest(BaseModel):
    service_name: str = Field(min_length=1, max_length=160)
    description: str = Field(default="", max_length=1000)
    price_lkr: float = Field(ge=0, le=100000000)
    active: bool = True


class AvailabilityRequest(BaseModel):
    availability_date: date
    status: Literal["available", "unavailable"]
    note: str = Field(default="", max_length=500)


@router.get("/dashboard")
def get_vendor_dashboard():
    return {"dashboard": dashboard(), "scope": "academic_demo_vendor", "authentication": "not_implemented"}


@router.get("/profile")
def get_vendor_profile():
    return {"profile": get_profile(), "data_origin": "operational_demo_vendor_tables"}


@router.put("/profile")
def save_vendor_profile(request: ProfileRequest):
    return {"profile": update_profile(request.model_dump()), "data_origin": "operational_demo_vendor_tables"}


@router.get("/services")
def get_vendor_services():
    return {"services": list_services(), "data_origin": "operational_demo_vendor_tables"}


@router.post("/services", status_code=status.HTTP_201_CREATED)
def add_vendor_service(request: ServiceRequest):
    return {"service": create_service(request.model_dump()), "data_origin": "operational_demo_vendor_tables"}


@router.put("/services/{service_id}")
def save_vendor_service(service_id: str, request: ServiceRequest):
    service = update_service(service_id, request.model_dump())
    if not service:
        raise HTTPException(status_code=404, detail="Vendor service not found for demo vendor")
    return {"service": service, "data_origin": "operational_demo_vendor_tables"}


@router.delete("/services/{service_id}", status_code=status.HTTP_204_NO_CONTENT)
def remove_vendor_service(service_id: str):
    if not delete_service(service_id):
        raise HTTPException(status_code=404, detail="Vendor service not found for demo vendor")


@router.get("/availability")
def get_vendor_availability():
    return {"availability": list_availability(), "data_origin": "operational_demo_vendor_tables"}


@router.post("/availability", status_code=status.HTTP_201_CREATED)
def add_vendor_availability(request: AvailabilityRequest):
    return {"availability": create_availability(request.model_dump()), "data_origin": "operational_demo_vendor_tables"}


@router.put("/availability/{availability_id}")
def save_vendor_availability(availability_id: str, request: AvailabilityRequest):
    availability = update_availability(availability_id, request.model_dump())
    if not availability:
        raise HTTPException(status_code=404, detail="Availability record not found for demo vendor")
    return {"availability": availability, "data_origin": "operational_demo_vendor_tables"}


@router.delete("/availability/{availability_id}", status_code=status.HTTP_204_NO_CONTENT)
def remove_vendor_availability(availability_id: str):
    if not delete_availability(availability_id):
        raise HTTPException(status_code=404, detail="Availability record not found for demo vendor")
