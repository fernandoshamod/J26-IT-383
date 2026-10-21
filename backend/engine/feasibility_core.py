"""Original package feasibility validator.
Extracted from research notebook Cell 377.
Dependencies will be integrated separately.
"""

def validate_package_feasibility(event, package_options):
    budget = float(event["budget_lkr"])
    total_cost = 0.0
    checks = []

    for option in package_options:
        result = validate_service_option_lkr(
            option,
            guest_count=int(event["guest_count"]),
            duration_hours=float(event["duration_hours"]),
            budget_lkr=budget
        )

        cost = result.get("estimated_cost_lkr")

        if cost is None:
            checks.append("Verification Required")
        else:
            total_cost += cost

        checks.append(result.get("capacity_status", "Verification Required"))

        availability_result = validate_vendor_availability(
            event,
            option["business_id"],
            availability
        )["availability_result"]

        checks.append({
            "Fail": "Fail",
            "Simulated Available": "Pass"
        }.get(availability_result, "Verification Required"))

    if total_cost > budget:
        checks.append("Fail")
    elif any(
        validate_service_option_lkr(
            option,
            int(event["guest_count"]),
            float(event["duration_hours"]),
            budget
        ).get("estimated_cost_lkr") is None
        for option in package_options
    ):
        checks.append("Verification Required")
    else:
        checks.append("Pass")

    for option_a, option_b in combinations(package_options, 2):
        conflict = validate_vendor_collaboration(
            event["event_id"],
            option_a["business_id"],
            option_b["business_id"],
            collaboration
        )["conflict_result"]

        checks.append({
            "Simulated Conflict Detected": "Fail",
            "No Conflict in Simulation": "Pass"
        }.get(conflict, "Verification Required"))

    if "Fail" in checks:
        final_status = "Fail"
    elif "Verification Required" in checks:
        final_status = "Verification Required"
    else:
        final_status = "Pass in Simulation"

    return {
        "event_id": event["event_id"],
        "total_cost_lkr": round(total_cost, 2),
        "budget_lkr": budget,
        "budget_remaining_lkr": round(budget - total_cost, 2),
        "passed_checks": checks.count("Pass"),
        "pending_checks": checks.count("Verification Required"),
        "failed_checks": checks.count("Fail"),
        "final_status": final_status,
        "evidence_scope": "Synthetic simulation only"
    }
