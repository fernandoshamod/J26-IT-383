"""USER-event feasibility checks based only on submitted event and current options."""

import math
from datetime import datetime, timedelta
from itertools import combinations

import pandas as pd

from backend.engine.validation_helpers import validate_service_option_lkr

PASS = "PASS_IN_SIMULATION"
PENDING = "VERIFICATION_REQUIRED"
FAIL = "FAIL"


def _present(value):
    return value is not None and not pd.isna(value) and bool(str(value).strip())


def validate_dynamic_package(event, package_options, required_services=None):
    """Never use sample-event availability or collaboration for USER events."""
    options = list(package_options)
    required = list(required_services if required_services is not None else
                    str(event.get("required_services", "")).split(";"))
    required = [str(item).strip() for item in required if str(item).strip()]
    checks = []

    def add(code, status, message, origin="current_option_record"):
        checks.append({"code": code, "status": status, "message": message,
                       "evidence_origin": origin})

    services = [str(o.get("service_category", "")).strip() for o in options]
    add("service_coverage",
        PASS if required and len(services) == len(required) and set(services) == set(required) else FAIL,
        "Every required service is covered exactly once." if required and len(services) == len(required) and set(services) == set(required)
        else f"Required services {required}; selected services {services}.")
    vendors = [str(o.get("business_id", "")).strip() for o in options]
    add("unique_vendors", PASS if all(vendors) and len(set(vendors)) == len(vendors) else FAIL,
        "All selected vendors are distinct." if all(vendors) and len(set(vendors)) == len(vendors)
        else "A vendor is missing or selected more than once.")

    try:
        start = datetime.fromisoformat(f"{event['event_date']}T{event['start_time']}")
        end = datetime.fromisoformat(f"{event['event_date']}T{event['end_time']}")
        if end <= start:
            end += timedelta(days=1)
        hours = (end - start).total_seconds() / 3600
        matches = math.isclose(hours, float(event["duration_hours"]), abs_tol=0.001)
        add("event_duration", PASS if matches else FAIL,
            f"Event interval is {hours:g} hours." if matches else "Duration differs from event time interval.",
            "submitted_event")
    except (ValueError, TypeError, KeyError):
        add("event_duration", PENDING, "Confirm event date, times and duration.", "submitted_event")

    budget = float(event["budget_lkr"])
    total = 0.0
    priced_all = True
    for option in options:
        vendor = str(option.get("business_id", "unknown"))
        service = str(option.get("service_category", "unknown"))
        label = f"{service} / {vendor}"
        types = option.get("supported_event_types")
        if _present(types):
            supported = {part.strip().casefold() for part in str(types).split(";")}
            matches = str(event.get("event_type", "")).strip().casefold() in supported
            add(f"event_type:{vendor}:{service}", PASS if matches else FAIL,
                f"{label}: event type {'matches' if matches else 'does not match'} option support.")
        else:
            add(f"event_type:{vendor}:{service}", PENDING, f"{label}: event type support unknown.",
                "missing_evidence")
        city, state = option.get("simulated_service_city"), option.get("simulated_service_state")
        if _present(city) and _present(state):
            matches = (str(city).strip().casefold() == str(event.get("city", "")).strip().casefold()
                       and str(state).strip().casefold() == str(event.get("state", "")).strip().casefold())
            add(f"location:{vendor}:{service}", PASS if matches else FAIL,
                f"{label}: simulated location {city}, {state}; event {event.get('city')}, {event.get('state')}.")
        else:
            add(f"location:{vendor}:{service}", PENDING, f"{label}: service location unknown.",
                "missing_evidence")
        try:
            result = validate_service_option_lkr(option, int(event["guest_count"]),
                                                 float(event["duration_hours"]), budget)
            cost = result.get("estimated_cost_lkr")
            if cost is None or not math.isfinite(float(cost)):
                raise ValueError("unpriceable option")
            total += float(cost)
            add(f"cost:{vendor}:{service}", PASS,
                f"{label}: estimated LKR {float(cost):.2f} from current synthetic option.")
            capacity = result.get("capacity_status")
            add(f"capacity:{vendor}:{service}",
                FAIL if capacity == "Fail" else PASS if capacity == "Pass" else PENDING,
                f"{label}: " + ("guest count exceeds simulated limit." if capacity == "Fail"
                               else "guest count fits simulated limit." if capacity == "Pass"
                               else "vendor capacity is unverified."),
                "current_option_record" if capacity in ("Fail", "Pass") else "missing_evidence")
        except (KeyError, ValueError, TypeError, OverflowError):
            priced_all = False
            add(f"cost:{vendor}:{service}", PENDING, f"{label}: quotation cannot be calculated.",
                "missing_evidence")
            add(f"capacity:{vendor}:{service}", PENDING, f"{label}: capacity cannot be established.",
                "missing_evidence")
        add(f"availability:{vendor}:{service}", PENDING,
            f"{label}: confirm availability for this event and time.", "missing_event_specific_evidence")
        add(f"scheduling:{vendor}:{service}", PENDING,
            f"{label}: confirm setup, travel and schedule fit.", "missing_event_specific_evidence")

    if priced_all:
        add("budget", PASS if total <= budget else FAIL,
            f"Estimated LKR {total:.2f} {'fits' if total <= budget else 'exceeds'} budget LKR {budget:.2f}.")
    else:
        add("budget", PENDING, "Budget fit unknown until every option is priced.", "missing_evidence")
    for first, second in combinations(vendors, 2):
        add(f"vendor_collaboration:{first}:{second}", PENDING,
            f"Confirm whether vendors {first} and {second} can work together.",
            "missing_event_specific_evidence")
    add("venue_suitability", PENDING,
        "Confirm venue capacity, access, equipment and service suitability.", "missing_venue_evidence")
    passed = [c for c in checks if c["status"] == PASS]
    pending = [c for c in checks if c["status"] == PENDING]
    failed = [c for c in checks if c["status"] == FAIL]
    return {
        "event_id": event["event_id"],
        "final_status": FAIL if failed else PENDING if pending else PASS,
        "total_cost_lkr": round(total, 2) if priced_all else None,
        "budget_lkr": budget,
        "budget_remaining_lkr": round(budget - total, 2) if priced_all else None,
        "passed_checks": passed, "pending_checks": pending, "failed_checks": failed,
        "verification_requirements": [c["message"] for c in pending],
        "evidence_scope": "Synthetic option checks only; USER-event availability, collaboration, venue and scheduling unverified.",
        "is_real_world_feasible": False,
    }
