
"""Service layer for synthetic package generation."""

import contextlib
import io

from backend.engine.package_data_loader import load_package_data
from backend.engine.candidate_selection import (
    select_candidates_for_event
)
from backend.engine.package_generator import (
    generate_packages_for_event
)
from backend.engine.json_serializer import to_json_safe


def generate_packages_for_event_id(event_id: str):
    """Generate packages for an existing synthetic event."""

    if not isinstance(event_id, str) or not event_id.strip():
        raise ValueError("event_id must be a non-empty string")

    event_id = event_id.strip()

    events_lkr, options_lkr = load_package_data()

    matched_events = events_lkr.loc[
        events_lkr["event_id"].astype(str) == event_id
    ]

    if matched_events.empty:
        raise LookupError(f"Event not found: {event_id}")

    selected_event = matched_events.iloc[0]

    selected_services = [
        service.strip()
        for service in str(
            selected_event["required_services"]
        ).split(";")
        if service.strip()
    ]

    if not selected_services:
        raise ValueError(
            f"Event has no required services: {event_id}"
        )

    candidate_groups = select_candidates_for_event(
        selected_event,
        selected_services,
        options_lkr
    )

    # Suppress notebook-oriented diagnostic printing.
    with contextlib.redirect_stdout(io.StringIO()):
        generation_result = generate_packages_for_event(
            selected_event,
            selected_services,
            candidate_groups
        )

    response = {
        "event_id": event_id,
        "required_services": selected_services,
        "currency": "LKR",
        "data_origin": "synthetic_simulation",
        "is_vendor_confirmed": False,
        "candidate_counts": {
            service: len(candidate_groups.get(service, []))
            for service in selected_services
        },
        "generation": generation_result
    }

    return to_json_safe(response)
