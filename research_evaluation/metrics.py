"""Pure evaluation calculations; missing results remain None."""

import math
import statistics


def mean(values):
    values = [float(value) for value in values if value is not None]
    return sum(values) / len(values) if values else None


def percentile(values, percent):
    values = sorted(float(value) for value in values if value is not None)
    if not values:
        return None
    position = (len(values) - 1) * percent / 100
    low = math.floor(position)
    high = math.ceil(position)
    return values[low] + (values[high] - values[low]) * (position - low)


def fraction(numerator, denominator):
    return numerator / denominator if denominator else None


def identity(package):
    return tuple(package["option_ids"])


def rank_pool(pool, approach, top_k, weights=None):
    """All approaches rank the same already validated package pool."""
    if approach == "cost_only":
        key = lambda p: (
            0 if p["feasibility_status"] == "PASS_IN_SIMULATION" else 1,
            p["total_cost_lkr"], identity(p))
    else:
        from backend.engine.bounded_package_generator import _ranking
        def key(p):
            score, _ = _ranking(p["total_cost_lkr"], p["budget_lkr"],
                                p["risk"], p["compatibility"], weights)
            return (0 if p["feasibility_status"] == "PASS_IN_SIMULATION" else 1,
                    -score, p["total_cost_lkr"], identity(p))
    return sorted(pool, key=key)[:top_k]


def overlap(first, second):
    """Overlap coefficient; undefined if either list is empty."""
    if not first or not second:
        return None
    return len({identity(p) for p in first} & {identity(p) for p in second}) / min(len(first), len(second))


def mean_rank_shift(first, second):
    """Absolute position change for shared packages only."""
    positions = {identity(p): index for index, p in enumerate(first, 1)}
    shifts = [abs(positions[identity(p)] - index)
              for index, p in enumerate(second, 1) if identity(p) in positions]
    return mean(shifts)


def vendor_diversity(packages):
    slots = [vendor for p in packages for vendor in p["vendor_ids"]]
    return fraction(len(set(slots)), len(slots))


def recommendation_metrics(packages):
    risk = [p["risk"]["mean_rule_risk_score"] for p in packages]
    compatibility = [p["compatibility"]["score"] for p in packages]
    slots = sum(p["risk"]["total_vendor_count"] for p in packages)
    known = sum(p["risk"]["known_vendor_count"] for p in packages)
    multiservice = [p for p in packages if len(p["option_ids"]) > 1]
    unknown = sum(p["compatibility"]["status"] in ("partial", "unknown")
                  for p in multiservice)
    return {
        "recommended_count": len(packages),
        "mean_cost_lkr": mean(p["total_cost_lkr"] for p in packages),
        "mean_risk_score_known": mean(risk),
        "mean_compatibility_score_known": mean(compatibility),
        "missing_risk_fraction": fraction(slots - known, slots),
        "unknown_compatibility_fraction": fraction(unknown, len(multiservice)),
        "vendor_diversity": vendor_diversity(packages),
    }


def aggregate(event_rows, package_rows, baseline_rows):
    count = len(event_rows)
    recommended = [row for row in package_rows if row["package_rank"] is not None]
    risk = [row["risk_score"] for row in recommended if row["risk_score"] is not None]
    compatibility = [row["compatibility_score"] for row in recommended
                     if row["compatibility_score"] is not None]
    vendor_slots = sum(row["vendor_count"] for row in recommended)
    known_slots = sum(row["known_risk_vendor_count"] for row in recommended)
    multiservice = [row for row in recommended if row["service_count"] > 1]
    statuses = {name: sum(row["feasibility_status"] == name for row in recommended)
                for name in ("PASS_IN_SIMULATION", "VERIFICATION_REQUIRED", "FAIL")}
    latencies = [row["execution_ms"] for row in event_rows]
    compared = [row for row in baseline_rows if row["top_k_overlap"] is not None]
    cost_differences = [row["cost_difference_lkr"] for row in baseline_rows
                        if row["cost_difference_lkr"] is not None]
    candidate_counts = {}
    for row in event_rows:
        for service, value in row["candidate_counts"].items():
            candidate_counts.setdefault(service, []).append(value)
    all_vendors = [vendor for row in recommended for vendor in row["vendor_ids"]]
    return {
        "events_evaluated": count,
        "request_success_rate": fraction(sum(row["http_status"] == 200 for row in event_rows), count),
        "recommendation_yield_rate": fraction(sum(row["recommended_count"] > 0 for row in event_rows), count),
        "required_service_coverage_rate": fraction(
            sum(row["coverage_exact"] for row in recommended), len(recommended)),
        "budget_feasible_package_rate": fraction(
            sum(row["budget_feasible"] for row in recommended), len(recommended)),
        "average_recommended_packages_per_event": mean(row["recommended_count"] for row in event_rows),
        "feasibility_status_counts": statuses,
        "feasibility_status_denominator": len(recommended),
        "mean_vendor_risk_score_known": mean(risk),
        "risk_score_distribution_known": {
            "count": len(risk), "min": min(risk) if risk else None,
            "median": statistics.median(risk) if risk else None,
            "p95": percentile(risk, 95), "max": max(risk) if risk else None},
        "missing_risk_fraction": fraction(vendor_slots - known_slots, vendor_slots),
        "mean_service_compatibility_score_known": mean(compatibility),
        "unknown_compatibility_fraction": fraction(
            sum(row["compatibility_status"] in ("partial", "unknown") for row in multiservice),
            len(multiservice)),
        "vendor_diversity_top_k": fraction(len(set(all_vendors)), len(all_vendors)),
        "mean_execution_ms": mean(latencies),
        "median_execution_ms": statistics.median(latencies) if latencies else None,
        "p95_execution_ms": percentile(latencies, 95),
        "min_execution_ms": min(latencies) if latencies else None,
        "max_execution_ms": max(latencies) if latencies else None,
        "search_truncation_frequency": fraction(
            sum(row["candidate_limit_reached"] or row["node_limit_reached"] for row in event_rows), count),
        "candidate_counts_per_service": {
            service: {"observations": len(values), "mean": mean(values), "min": min(values), "max": max(values)}
            for service, values in sorted(candidate_counts.items())},
        "evaluated_package_combinations": sum(row["combinations_evaluated"] for row in event_rows),
        "baseline_proposed_top_k_overlap_mean": mean(row["top_k_overlap"] for row in compared),
        "baseline_proposed_overlap_event_count": len(compared),
        "mean_absolute_rank_shift_common": mean(row["mean_absolute_rank_shift"] for row in compared),
        "average_recommended_package_cost_difference_lkr": mean(cost_differences),
        "cost_difference_event_count": len(cost_differences),
        "recommended_package_count": len(recommended),
        "risk_known_package_count": len(risk),
        "compatibility_known_package_count": len(compatibility),
        "multiservice_package_count": len(multiservice),
        "vendor_slot_count": vendor_slots,
    }
