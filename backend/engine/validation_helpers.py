"""Original validation helpers from the research notebook."""

import pandas as pd

USD_TO_LKR = 330.777


def validate_service_option(option, guest_count, duration_hours, budget):
    basis = option["pricing_basis"]
    price = float(option["unit_price"])

    if basis == "per_person":
        minimum = option["min_billable_guests"]

        if pd.isna(minimum):
            return {"status": "Verification Required",
                    "reason": "Missing minimum guest billing rule"}

        billable_guests = max(guest_count, float(minimum))
        estimated_cost = price * billable_guests

    elif basis == "fixed_package":
        estimated_cost = price

    elif basis == "per_hour":
        minimum = option["min_billable_hours"]

        if pd.isna(minimum):
            return {"status": "Verification Required",
                    "reason": "Missing minimum hourly billing rule"}

        billable_hours = max(duration_hours, float(minimum))
        estimated_cost = price * billable_hours

    else:
        return {"status": "Verification Required",
                "reason": "Unsupported pricing basis"}

    capacity_type = option["guest_capacity_applicability"]
    maximum = option["max_guests"]

    if capacity_type == "simulated_catering_limit":
        if pd.isna(maximum):
            capacity_status = "Verification Required"
        elif guest_count > float(maximum):
            capacity_status = "Fail"
        else:
            capacity_status = "Pass"
    else:
        capacity_status = "Verification Required"

    budget_status = (
        "Pass" if estimated_cost <= budget else "Fail"
    )

    return {
        "estimated_cost_usd": round(estimated_cost, 2),
        "budget_status": budget_status,
        "capacity_status": capacity_status,
        "data_origin": option["data_origin"]
    }


def validate_service_option_lkr(
    option, guest_count, duration_hours, budget_lkr
):
    option_lkr = option.copy()

    option_lkr["unit_price"] = option["unit_price_lkr"]

    result = validate_service_option(
        option=option_lkr,
        guest_count=guest_count,
        duration_hours=duration_hours,
        budget=budget_lkr
    )

    if "estimated_cost_usd" in result:
        result["estimated_cost_lkr"] = result.pop(
            "estimated_cost_usd"
        )

    result["currency"] = "LKR"
    result["exchange_rate_used"] = USD_TO_LKR
    result["price_origin"] = "synthetic_converted_from_usd"

    return result


def validate_vendor_availability(event, business_id, availability_df):
    records = availability_df.loc[
        (availability_df["event_id"] == event["event_id"])
        & (availability_df["business_id"] == business_id)
        & (availability_df["event_date"].astype(str)
           == str(event["event_date"]))
    ]

    if records.empty:
        return {
            "availability_result": "Verification Required",
            "reason": "No matching event-specific availability record"
        }

    event_start = str(event["start_time"])
    event_end = str(event["end_time"])

    covering = records.loc[
        (records["checked_interval_start"].astype(str) <= event_start)
        & (records["checked_interval_end"].astype(str) >= event_end)
    ]

    if covering.empty:
        return {
            "availability_result": "Verification Required",
            "reason": "Event time interval is not fully covered"
        }

    statuses = set(covering["availability_status"].astype(str))

    if "unavailable" in statuses:
        decision = "Fail"
    elif statuses == {"available"}:
        decision = "Simulated Available"
    else:
        decision = "Verification Required"

    return {
        "availability_result": decision,
        "recorded_statuses": sorted(statuses),
        "data_origin": "synthetic",
        "is_vendor_confirmed": False
    }


def validate_vendor_collaboration(
    event_id, vendor_a_id, vendor_b_id, collaboration_df
):
    if vendor_a_id == vendor_b_id:
        return {
            "conflict_result": "Verification Required",
            "reason": "Same vendor selected twice; requires role validation"
        }

    records = collaboration_df.loc[
        (collaboration_df["event_id"] == event_id)
        & (
            (
                (collaboration_df["vendor_a_id"] == vendor_a_id)
                & (collaboration_df["vendor_b_id"] == vendor_b_id)
            )
            |
            (
                (collaboration_df["vendor_a_id"] == vendor_b_id)
                & (collaboration_df["vendor_b_id"] == vendor_a_id)
            )
        )
    ]

    if records.empty:
        return {
            "conflict_result": "Verification Required",
            "reason": "No event-specific collaboration evidence"
        }

    labels = set(records["simulated_conflict"].dropna())

    if 1 in labels:
        decision = "Simulated Conflict Detected"
    elif labels == {0}:
        decision = "No Conflict in Simulation"
    else:
        decision = "Verification Required"

    return {
        "conflict_result": decision,
        "recorded_labels": sorted(labels),
        "data_origin": "synthetic",
        "is_actual_collaboration": False
    }
