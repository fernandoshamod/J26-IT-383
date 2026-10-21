"""Bounded request-time search and transparent package scoring."""

import math
import os

from backend.engine.validation_helpers import validate_service_option_lkr
from backend.engine.dynamic_feasibility import validate_dynamic_package
from backend.engine.package_explanations import explain_package


def _positive_limit(name, default):
    raw = os.getenv(name, str(default))
    try:
        value = int(raw)
    except ValueError as exc:
        raise ValueError(f"{name} must be a positive integer") from exc
    if value < 1:
        raise ValueError(f"{name} must be a positive integer")
    return value


def _ranking_weights():
    defaults = {"cost": 0.4, "risk": 0.4, "compatibility": 0.2}
    weights = {}
    for component, default in defaults.items():
        name = f"PLANOVISION_WEIGHT_{component.upper()}"
        try:
            weight = float(os.getenv(name, str(default)))
        except ValueError as exc:
            raise ValueError(f"{name} must be a nonnegative finite number") from exc
        if not math.isfinite(weight) or weight < 0:
            raise ValueError(f"{name} must be a nonnegative finite number")
        weights[component] = weight
    if weights["cost"] <= 0:
        raise ValueError("PLANOVISION_WEIGHT_COST must be positive")
    return weights


def _select_diverse_candidates(eligible, limit, risk_lookup):
    """Reserve slots for low cost and strong existing rule-derived risk signals."""
    by_cost = sorted(
        eligible,
        key=lambda item: (
            item["estimated_cost_lkr"],
            str(item["business_id"]),
            str(item["service_option_id"]),
        ),
    )
    by_risk = sorted(
        (
            item for item in eligible
            if risk_lookup.get(str(item["business_id"]), {}).get("rule_risk_score")
            is not None
        ),
        key=lambda item: (
            -risk_lookup[str(item["business_id"])]["rule_risk_score"],
            item["estimated_cost_lkr"],
            str(item["business_id"]),
            str(item["service_option_id"]),
        ),
    )
    selected = []
    option_ids = set()
    vendor_ids = set()

    def take(pool, target, unique_vendors=True):
        for item in pool:
            if len(selected) >= target:
                break
            option_id = str(item["service_option_id"])
            vendor_id = str(item["business_id"])
            if option_id in option_ids or (unique_vendors and vendor_id in vendor_ids):
                continue
            selected.append(item)
            option_ids.add(option_id)
            vendor_ids.add(vendor_id)

    take(by_cost, (limit + 1) // 2)
    take(by_risk, limit)
    take(by_cost, limit)
    if len(selected) < limit:
        take(by_cost, limit, unique_vendors=False)
    return selected


def _package_risk(options, risk_lookup):
    vendors = []
    scores = []
    for option in options:
        vendor_id = str(option["business_id"])
        signal = risk_lookup.get(vendor_id, {
            "vendor_id": vendor_id,
            "vendor_name": None,
            "predicted_risk_level": None,
            "rule_risk_level": None,
            "rule_risk_score": None,
            "risk_status": "profile_not_found",
            "risk_provenance": "unknown",
        })
        vendors.append(signal)
        if signal["rule_risk_score"] is not None:
            scores.append(signal["rule_risk_score"])
    complete = len(scores) == len(options)
    return {
        "status": "complete" if complete else ("partial" if scores else "unknown"),
        "mean_rule_risk_score": round(sum(scores) / len(scores), 4)
        if complete else None,
        "known_vendor_count": len(scores),
        "total_vendor_count": len(options),
        "vendors": vendors,
        "label_origin": "rule_generated_from_review_features",
        "independent_real_world_validation": False,
    }


def _ranking(total_cost, budget, risk, compatibility, weights):
    components = {
        "cost": 1 - total_cost / budget,
        "risk": (
            risk["mean_rule_risk_score"] / 100
            if risk["mean_rule_risk_score"] is not None else None
        ),
        "compatibility": (
            compatibility["score"] / 100
            if compatibility["score"] is not None else None
        ),
    }
    active = {
        name: weight for name, weight in weights.items()
        if components[name] is not None and weight > 0
    }
    divisor = sum(active.values())
    effective = {name: weight / divisor for name, weight in active.items()}
    score = 100 * sum(
        effective[name] * components[name] for name in effective
    )
    return score, {
        "cost_efficiency": round(components["cost"], 6),
        "budget_utilization": round(total_cost / budget, 6),
        "service_coverage": 1.0,
        "risk_score": risk["mean_rule_risk_score"],
        "compatibility_score": compatibility["score"],
        "configured_weights": weights,
        "effective_weights": {
            name: round(weight, 6) for name, weight in effective.items()
        },
        "unknown_components": [
            name for name, value in components.items() if value is None
        ],
    }


def generate_bounded_packages(
    event, selected_services, candidate_groups, top_k,
    risk_lookup=None, compatibility=None,
):
    """Search current option records without materializing the Cartesian product."""
    risk_lookup = risk_lookup or {}
    compatibility = compatibility or {
        "status": "unknown", "score": None, "pairs": [],
        "unknown_pairs": [], "provenance": "unavailable",
        "is_vendor_collaboration_evidence": False,
    }
    candidate_limit = _positive_limit(
        "PLANOVISION_MAX_CANDIDATES_PER_SERVICE", 12
    )
    node_limit = _positive_limit("PLANOVISION_MAX_SEARCH_NODES", 5000)
    weights = _ranking_weights()
    budget = float(event["budget_lkr"])
    groups = {}
    eligible_counts = {}
    known_risk_counts = {}
    cheapest_eligible = {}
    candidate_truncated = False

    for service in selected_services:
        eligible = []
        for option in candidate_groups[service].to_dict("records"):
            result = validate_service_option_lkr(
                option,
                guest_count=int(event["guest_count"]),
                duration_hours=float(event["duration_hours"]),
                budget_lkr=budget,
            )
            cost = result.get("estimated_cost_lkr")
            if (
                cost is None
                or not math.isfinite(float(cost))
                or result.get("capacity_status") == "Fail"
            ):
                continue
            option["estimated_cost_lkr"] = round(float(cost), 2)
            eligible.append(option)
        eligible_counts[service] = len(eligible)
        known_risk_counts[service] = sum(
            risk_lookup.get(str(item["business_id"]), {}).get("rule_risk_score")
            is not None for item in eligible
        )
        candidate_truncated |= len(eligible) > candidate_limit
        cheapest_eligible[service] = (
            min(item["estimated_cost_lkr"] for item in eligible)
            if eligible else None
        )
        groups[service] = _select_diverse_candidates(
            eligible, candidate_limit, risk_lookup
        )

    missing = [
        service for service in selected_services if not groups[service]
    ]
    ordered_services = sorted(
        selected_services, key=lambda service: (len(groups[service]), service)
    )
    search_space = math.prod(len(groups[service]) for service in selected_services)
    minimum_possible_cost = (
        round(sum(cheapest_eligible.values()), 2) if not missing else None
    )
    budget_impossible = (
        minimum_possible_cost is not None and minimum_possible_cost > budget
    )
    packages = []
    nodes_visited = 0
    combinations_evaluated = 0
    feasible_combinations_seen = 0
    budget_rejected = 0
    duplicate_vendor_rejected = 0
    node_truncated = False
    feasibility_counts = {"PASS_IN_SIMULATION": 0, "VERIFICATION_REQUIRED": 0, "FAIL": 0}

    def sort_key(package):
        return (
            0 if package["feasibility"]["final_status"] == "PASS_IN_SIMULATION" else 1,
            -package["_raw_score"],
            package["total_cost_lkr"],
            tuple(package["option_ids"]),
        )

    def search(depth, chosen, used_vendors, running_cost):
        nonlocal nodes_visited, combinations_evaluated
        nonlocal feasible_combinations_seen, budget_rejected
        nonlocal duplicate_vendor_rejected, node_truncated
        if node_truncated:
            return
        if depth == len(ordered_services):
            combinations_evaluated += 1
            by_service = {
                option["service_category"]: option for option in chosen
            }
            ordered_options = [by_service[service] for service in selected_services]
            feasibility = validate_dynamic_package(event, ordered_options, selected_services)
            feasibility_counts[feasibility["final_status"]] += 1
            if feasibility["final_status"] == "FAIL":
                return
            feasible_combinations_seen += 1
            risk = _package_risk(ordered_options, risk_lookup)
            score, factors = _ranking(
                running_cost, budget, risk, compatibility, weights
            )
            breakdown = []
            for option in ordered_options:
                signal = risk_lookup.get(str(option["business_id"]), {})
                breakdown.append({
                    "service": option["service_category"],
                    "vendor_id": str(option["business_id"]),
                    "vendor_name": signal.get("vendor_name"),
                    "option_id": str(option["service_option_id"]),
                    "option_tier": str(option.get("option_tier", "")),
                    "estimated_cost_lkr": option["estimated_cost_lkr"],
                    "predicted_risk_level": signal.get("predicted_risk_level"),
                    "rule_risk_score": signal.get("rule_risk_score"),
                    "risk_status": signal.get("risk_status", "profile_not_found"),
                    "data_origin": "synthetic_simulation",
                    "is_vendor_confirmed": False,
                })
            warnings = ["vendor_availability_unverified"]
            if risk["status"] != "complete":
                warnings.append("missing_vendor_risk_data")
            if compatibility["status"] in ("partial", "unknown"):
                warnings.append("unknown_service_compatibility_pairs")
            package = {
                "_raw_score": score,
                "option_ids": [row["option_id"] for row in breakdown],
                "vendor_ids": [row["vendor_id"] for row in breakdown],
                "service_coverage": list(selected_services),
                "service_breakdown": breakdown,
                "total_cost_lkr": round(running_cost, 2),
                "remaining_budget_lkr": round(budget - running_cost, 2),
                "ranking_score": round(score, 4),
                "ranking_factors": factors,
                "risk": risk,
                "compatibility": compatibility,
                "feasibility": feasibility,
                "warnings": warnings,
                "package_options": ordered_options,
                "data_origin": "synthetic_simulation",
                "is_vendor_confirmed": False,
                "availability_status": "unverified",
            }
            package["explanation"] = explain_package(package)
            packages.append(package)
            packages.sort(key=sort_key)
            if len(packages) > top_k:
                packages.pop()
            return

        service = ordered_services[depth]
        for option in groups[service]:
            if nodes_visited >= node_limit:
                node_truncated = True
                return
            nodes_visited += 1
            vendor_id = str(option["business_id"])
            if vendor_id in used_vendors:
                duplicate_vendor_rejected += 1
                continue
            next_cost = running_cost + option["estimated_cost_lkr"]
            if next_cost > budget:
                budget_rejected += 1
                continue
            chosen.append(option)
            used_vendors.add(vendor_id)
            search(depth + 1, chosen, used_vendors, next_cost)
            used_vendors.remove(vendor_id)
            chosen.pop()
            if node_truncated:
                return

    if not missing and not budget_impossible:
        search(0, [], set(), 0.0)

    for rank, package in enumerate(packages, 1):
        package.pop("_raw_score")
        package["package_id"] = f"PKG-{rank:04d}"
        package["rank"] = rank

    truncated = candidate_truncated or node_truncated
    if missing:
        status = "no_matching_candidates"
        message = f"No matching, priceable options for: {', '.join(missing)}."
    elif budget_impossible:
        status = "no_budget_feasible_combinations"
        message = "Even the cheapest eligible option per service exceeds the LKR budget."
    elif truncated:
        status = "search_limit_reached"
        message = (
            "Search limits were reached; results cover only the examined "
            "candidate options and combinations."
        )
    elif not packages and feasibility_counts["FAIL"]:
        status = "no_feasible_combinations"
        message = "All examined complete combinations failed feasibility checks."
    elif not packages:
        status = "no_budget_feasible_combinations"
        message = "No complete combination of distinct vendors fits the LKR budget."
    else:
        status = "ok"
        message = "Ranked packages generated from current option and profile records."

    return {
        "status": status,
        "message": message,
        "packages": packages,
        "total_generated": combinations_evaluated,
        "feasible_combinations_seen": feasible_combinations_seen,
        "budget_rejected": budget_rejected,
        "duplicate_vendor_rejected": duplicate_vendor_rejected,
        "feasibility_counts": feasibility_counts,
        "missing_services": missing,
        "candidate_counts": eligible_counts,
        "known_risk_candidate_counts": known_risk_counts,
        "selected_candidate_counts": {
            service: len(groups[service]) for service in selected_services
        },
        "search": {
            "complete": bool(missing) or budget_impossible or not truncated,
            "candidate_limit_reached": candidate_truncated,
            "node_limit_reached": node_truncated,
            "max_candidates_per_service": candidate_limit,
            "max_search_nodes": node_limit,
            "nodes_visited": nodes_visited,
            "combinations_evaluated": combinations_evaluated,
            "all_examined_combinations_validated": True,
            "feasibility_priority": ["PASS_IN_SIMULATION", "VERIFICATION_REQUIRED"],
            "selected_search_space_upper_bound": search_space,
            "minimum_possible_cost_lkr": minimum_possible_cost,
            "top_k": top_k,
            "candidate_selection": (
                "half lowest cost with distinct vendors, then highest existing "
                "rule-derived risk score with distinct vendors; fill remaining by cost"
            ),
        },
        "ranking_formula": (
            "100 * weighted mean of available normalized components: "
            "cost = 1 - budget_utilization; risk = mean existing rule_risk_score / 100; "
            "compatibility = mean known service-pair base_score / 100 only when all "
            "pairs are known. Unknown components are omitted and weights renormalized."
        ),
        "configured_weights": weights,
    }
