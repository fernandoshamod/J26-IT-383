"""Request-time package generation for a user-entered event."""

from datetime import datetime, timedelta
from uuid import uuid4

from backend.engine.bounded_package_generator import generate_bounded_packages
from backend.engine.candidate_selection import select_candidates_for_event
from backend.engine.json_serializer import to_json_safe
from backend.engine.package_data_loader import load_service_options
from backend.engine.risk_signals import load_risk_signals
from backend.engine.service_compatibility import (
    load_compatibility_rules, service_compatibility,
)


def generate_dynamic_packages(request):
    options_lkr = load_service_options()
    location = (request.city.casefold(), request.state.casefold())
    available_locations = set(
        zip(
            options_lkr["simulated_service_city"].astype(str).str.strip().str.casefold(),
            options_lkr["simulated_service_state"].astype(str).str.strip().str.casefold(),
        )
    )
    if location not in available_locations:
        raise ValueError(
            f"Unsupported location: {request.city}, {request.state}. "
            "Choose a city and state listed by GET /api/locations."
        )

    start = datetime.combine(request.event_date, request.start_time)
    end = datetime.combine(request.event_date, request.end_time)
    if end <= start:
        end += timedelta(days=1)
    duration_hours = (end - start).total_seconds() / 3600
    event_id = f"USER-{uuid4().hex[:12].upper()}"
    selected_event = {
        "event_id": event_id,
        "event_type": request.event_type,
        "event_date": request.event_date.isoformat(),
        "start_time": request.start_time.isoformat(),
        "end_time": request.end_time.isoformat(),
        "city": request.city,
        "state": request.state,
        "guest_count": request.guest_count,
        "budget_lkr": request.budget_lkr,
        "duration_hours": duration_hours,
        "required_services": ";".join(request.required_services),
        "currency": "LKR",
    }
    candidate_groups = select_candidates_for_event(
        selected_event, request.required_services, options_lkr
    )
    business_ids = {
        str(business_id)
        for group in candidate_groups.values()
        for business_id in group["business_id"]
    }
    risk_lookup, risk_audit = load_risk_signals(business_ids)
    compatibility = service_compatibility(
        request.required_services, load_compatibility_rules()
    )
    generation = generate_bounded_packages(
        selected_event,
        request.required_services,
        candidate_groups,
        request.top_k,
        risk_lookup=risk_lookup,
        compatibility=compatibility,
    )
    return to_json_safe({
        "event_id": event_id,
        "event": selected_event,
        "required_services": request.required_services,
        "currency": "LKR",
        "data_origin": "synthetic_simulation",
        "is_vendor_confirmed": False,
        "availability_status": "unverified",
        "generation_mode": "dynamic_user_request",
        "candidate_counts": generation["candidate_counts"],
        "risk_data_audit": risk_audit,
        "generation": generation,
    })
