"""Package generation using the verified notebook algorithm.

Outputs are simulation candidates, not confirmed vendor bookings.
"""

import pandas as pd
from itertools import product
from .validation_helpers import validate_service_option_lkr


def generate_packages_for_event(selected_event, selected_services, candidate_groups):
    service_option_lists = [
        candidate_groups[service].to_dict("records")
        for service in selected_services
    ]
    package_candidates = []
    total_generated = 0
    duplicate_vendor_rejected = 0
    budget_rejected = 0
    for package in product(*service_option_lists):
        total_generated += 1
    
        vendor_ids = [option["business_id"] for option in package]
    
        # Reject repeated vendors across services
        if len(vendor_ids) != len(set(vendor_ids)):
            duplicate_vendor_rejected += 1
            continue
    
        costs = []
    
        for option in package:
            result = validate_service_option_lkr(
                option,
                guest_count=int(selected_event["guest_count"]),
                duration_hours=float(selected_event["duration_hours"]),
                budget_lkr=float(selected_event["budget_lkr"])
            )
    
            costs.append(result.get("estimated_cost_lkr", float("nan")))
    
        if any(pd.isna(cost) for cost in costs):
            budget_rejected += 1
            continue
    
        total_cost = round(sum(costs), 2)
    
        if total_cost > float(selected_event["budget_lkr"]):
            budget_rejected += 1
            continue
    
        package_candidates.append({
            "package_id": f"PKG-{len(package_candidates)+1:04d}",
            "option_ids": [option["service_option_id"] for option in package],
            "vendor_ids": vendor_ids,
            "total_cost_lkr": total_cost,
            "remaining_budget_lkr": round(
                float(selected_event["budget_lkr"]) - total_cost, 2
            ),
            "package_options": package
        })
    for package in sorted(
        package_candidates,
        key=lambda p: p["total_cost_lkr"]
    )[:5]:
        print(
            package["package_id"],
            "| Cost: Rs.",
            f"{package['total_cost_lkr']:,.2f}",
            "| Vendors:",
            package["vendor_ids"]
        )
    return {
        'packages': package_candidates,
        'total_generated': total_generated,
        'duplicate_vendor_rejected': duplicate_vendor_rejected,
        'budget_rejected': budget_rejected
    }
