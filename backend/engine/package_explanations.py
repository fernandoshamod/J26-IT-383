"""Deterministic explanation of observed scoring and feasibility fields."""


def explain_package(package):
    factors = package["ranking_factors"]
    risk = package["risk"]
    compatibility = package["compatibility"]
    feasibility = package["feasibility"]
    reasons = [
        f"Covers {len(package['service_coverage'])} required services with distinct vendors.",
        f"Estimated LKR {package['total_cost_lkr']:.2f}; LKR {package['remaining_budget_lkr']:.2f} remains.",
        f"Ranking score {package['ranking_score']:.4f}/100 uses effective cost/risk/compatibility weights "
        f"{factors['effective_weights']}.",
    ]
    if risk["mean_rule_risk_score"] is not None:
        reasons.append(
            f"Mean rule-derived low-risk favorability {risk['mean_rule_risk_score']:.4f}/100 (higher is more favorable; Low=100, Medium=60, High=20) "
            "for matched vendors; model labels are not verified failure predictions."
        )
    if compatibility["score"] is not None:
        reasons.append(
            f"Service-category compatibility rule mean {compatibility['score']:.4f}/100; "
            "this is not evidence of vendor collaboration."
        )
    tradeoffs = []
    if factors["unknown_components"]:
        tradeoffs.append(
            f"Unknown ranking components {factors['unknown_components']} were omitted and "
            "available weights renormalized."
        )
    if risk["status"] != "complete":
        tradeoffs.append("Risk signals are missing for at least one vendor.")
    if compatibility["status"] in ("partial", "unknown"):
        tradeoffs.append("Some service-pair compatibility rules are unknown.")
    tradeoffs.append(
        f"Feasibility is {feasibility['final_status']}; "
        f"{len(feasibility['pending_checks'])} checks require verification."
    )
    return {
        "reasons": reasons,
        "tradeoffs": tradeoffs,
        "verification_steps": feasibility["verification_requirements"],
        "provenance": "Deterministic summary of package cost, ranking factors, risk and compatibility records, and USER-event feasibility checks.",
    }
