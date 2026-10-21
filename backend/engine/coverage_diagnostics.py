"""Evidence-based recovery diagnostics for empty dynamic searches.

This function only runs after a generation result has zero recommendations. It
uses the same source option rows, event-type/location normalization and price
validator as the production candidate/search path. It does not infer real-world
availability or vendor collaboration.
"""

import math

from backend.engine.candidate_selection import select_candidates_for_event
from backend.engine.validation_helpers import validate_service_option_lkr


def _supports_event(value, event_type):
    return event_type.strip().casefold() in {
        part.strip().casefold() for part in str(value).split(";")
    }


def _price(option, event):
    try:
        result = validate_service_option_lkr(
            option,
            guest_count=int(event["guest_count"]),
            duration_hours=float(event["duration_hours"]),
            budget_lkr=float(event["budget_lkr"]),
        )
        cost = result.get("estimated_cost_lkr")
        if cost is None or not math.isfinite(float(cost)):
            return None
        if result.get("capacity_status") == "Fail":
            return None
        return round(float(cost), 2)
    except (ValueError, TypeError, OverflowError, KeyError):
        return None


def diagnose_generation(event, services, options, generation):
    """Classify observed empty-result causes without treating truncated search as exhaustive."""
    city = str(event["city"]).strip().casefold()
    state = str(event["state"]).strip().casefold()
    location_mask = (
        options["simulated_service_city"].astype(str).str.strip().str.casefold().eq(city)
        & options["simulated_service_state"].astype(str).str.strip().str.casefold().eq(state)
    )
    location_rows = options.loc[location_mask]
    stages = {}
    eligible_minima = {}
    reasons = []

    if location_rows.empty:
        reasons.append({
            "code": "NO_LOCATION_COVERAGE",
            "message": "No source service-option rows cover the selected city and state.",
        })

    for service in services:
        source = options.loc[options["service_category"].eq(service)]
        at_location = source.loc[location_mask]
        event_rows = at_location.loc[
            at_location["supported_event_types"].fillna("").map(
                lambda value: _supports_event(value, str(event["event_type"]))
            )
        ]
        capacity_rows = event_rows.loc[
            event_rows["service_category"].ne("Catering")
            | event_rows["max_guests"].ge(event["guest_count"])
        ]
        priced = [
            cost for option in capacity_rows.to_dict("records")
            if (cost := _price(option, event)) is not None
        ]
        affordable = [cost for cost in priced if cost <= float(event["budget_lkr"])]
        stages[service] = {
            "source_rows": len(source),
            "location_rows": len(at_location),
            "event_type_rows": len(event_rows),
            "capacity_eligible_rows": len(capacity_rows),
            "priceable_rows": len(priced),
            "individually_affordable_rows": len(affordable),
            "minimum_observed_eligible_cost_lkr": min(priced) if priced else None,
        }
        if priced:
            eligible_minima[service] = min(priced)
        if at_location.empty:
            reasons.append({
                "code": "NO_SERVICE_COVERAGE", "service": service,
                "message": f"No {service} option rows cover this location.",
            })
        elif event_rows.empty:
            reasons.append({
                "code": "NO_SERVICE_COVERAGE", "service": service,
                "message": f"No {service} rows here support {event['event_type']} events.",
            })
        elif capacity_rows.empty:
            reasons.append({
                "code": "NO_SERVICE_COVERAGE", "service": service,
                "message": f"No {service} rows here meet the recorded guest-capacity filter.",
            })
        elif not priced:
            reasons.append({
                "code": "UNPRICEABLE_OPTIONS", "service": service,
                "message": f"The matching {service} rows lack a usable price under current pricing rules.",
            })
        elif not affordable:
            reasons.append({
                "code": "BUDGET_INSUFFICIENT", "service": service,
                "message": f"No individually eligible {service} option fits the current LKR budget.",
            })

    lower_bound = (
        round(sum(eligible_minima[service] for service in services), 2)
        if all(service in eligible_minima for service in services) else None
    )
    if lower_bound is not None and lower_bound > float(event["budget_lkr"]):
        if not any(item["code"] == "BUDGET_INSUFFICIENT" and "service" not in item for item in reasons):
            reasons.append({
                "code": "BUDGET_INSUFFICIENT",
                "message": "The sum of the cheapest individually eligible options exceeds the budget.",
            })

    search = generation.get("search", {})
    search_attempted = bool(search.get("nodes_visited", 0))
    truncated = search_attempted and bool(
        search.get("candidate_limit_reached") or search.get("node_limit_reached")
    )
    if truncated:
        reasons.append({
            "code": "SEARCH_LIMIT_REACHED",
            "message": "The bounded search did not examine every possible combination; no global absence can be concluded.",
        })
    elif (
        len(eligible_minima) == len(services)
        and lower_bound is not None
        and lower_bound <= float(event["budget_lkr"])
        and not generation.get("packages")
    ):
        reasons.append({
            "code": "NO_COMPATIBLE_COMBINATION",
            "message": "No examined complete package met distinct-vendor, budget and simulation-feasibility constraints. Category scores did not exclude candidates.",
        })
    if not reasons and not generation.get("packages"):
        reasons.append({
            "code": "UNKNOWN_CAUSE",
            "message": "The available counts do not establish a specific cause; review the search metadata.",
        })

    # First intersect category/location coverage using the same event-type and
    # catering-capacity conditions. Then price-check only candidate locations,
    # stopping after five confirmed suggestions. This runs only for zero results.
    location_sets = []
    eligible_by_service = {}
    for service in services:
        matching = options.loc[
            options["service_category"].eq(service)
            & options["supported_event_types"].fillna("").map(
                lambda value: _supports_event(value, str(event["event_type"]))
            )
        ]
        if service == "Catering":
            matching = matching.loc[matching["max_guests"].ge(event["guest_count"])]
        matching = matching.copy()
        matching["_location_key"] = (
            matching["simulated_service_city"].astype(str).str.strip().str.casefold()
            + "|"
            + matching["simulated_service_state"].astype(str).str.strip().str.casefold()
        )
        eligible_by_service[service] = matching
        location_sets.append({
            (str(row.simulated_service_city).strip(), str(row.simulated_service_state).strip())
            for row in matching[["simulated_service_city", "simulated_service_state"]]
                .drop_duplicates().itertuples(index=False)
        })
    possible = set.intersection(*location_sets) if location_sets else set()
    suggestions = []
    for city_name, state_name in sorted(possible, key=lambda pair: (pair[0].casefold(), pair[1].casefold())):
        if (city_name.casefold(), state_name.casefold()) == (city, state):
            continue
        key = city_name.casefold() + "|" + state_name.casefold()
        if all(
            any(
                _price(row, event) is not None
                for row in eligible_by_service[service].loc[
                    eligible_by_service[service]["_location_key"].eq(key)
                ].to_dict("records")
            )
            for service in services
        ):
            suggestions.append({"city": city_name, "state": state_name})
            if len(suggestions) == 5:
                break

    # This list uses the event-type and capacity filters plus canonical pricing.
    current_available = [
        service for service in sorted(options["service_category"].dropna().unique())
        if service in stages and stages[service]["priceable_rows"] > 0
    ]
    if location_rows.empty:
        current_available = []
    else:
        other = sorted(set(location_rows["service_category"].dropna()) - set(services))
        for service in other:
            candidate = select_candidates_for_event(event, [service], options)[service]
            if any(_price(row, event) is not None for row in candidate.to_dict("records")):
                current_available.append(service)
        current_available.sort()

    return {
        "reasons": reasons,
        "source_service_option_rows": len(options),
        "location_matching_rows": len(location_rows),
        "service_stages": stages,
        "minimum_observed_package_lower_bound_lkr": lower_bound,
        "available_priceable_services_here": current_available,
        "suggested_locations": suggestions[:5],
        "suggestion_basis": "Same event type, guest-capacity rule and pricing validator; all requested categories have at least one priceable option. Budget, distinct vendors, feasibility and search limits can still prevent a package.",
        "category_compatibility_candidates_removed": 0,
        "category_compatibility_is_a_filter": False,
        "search_attempted": search_attempted,
        "data_origin": "synthetic_simulation",
        "availability_status": "unverified",
        "is_vendor_confirmed": False,
    }