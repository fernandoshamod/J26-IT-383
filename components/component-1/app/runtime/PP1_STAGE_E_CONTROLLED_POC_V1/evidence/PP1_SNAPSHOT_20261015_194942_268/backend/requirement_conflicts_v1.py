from collections import Counter

from permission_validator import validate_config
from requirements_v1 import validate_requirements


def diagnose(scene, permissions, client, planner):
    validation = validate_requirements(scene, client, planner)
    permission_errors = validate_config(scene, permissions)

    blockers = []
    unresolved = []

    if not validation["valid"]:
        blockers.extend(validation["errors"])

    if permission_errors:
        blockers.extend(permission_errors)

    inventory = Counter(
        obj["class"] for obj in scene["event_instances"]
    )

    required = client.get("required_objects", {})
    if isinstance(required, dict):
        for name, amount in required.items():
            if type(amount) is int and amount >= 0:
                available = inventory.get(name, 0)
                if amount > available:
                    unresolved.append({
                        "code": "ADDITIONAL_SUPPLY_REQUIRED",
                        "class": name,
                        "requested": amount,
                        "existing": available,
                        "shortfall": amount - available,
                        "note": (
                            "Supply and physical placement "
                            "must be verified separately"
                        ),
                    })

    approved_movable = [
        item["instance_id"]
        for item in permissions.get("objects", [])
        if item.get("planner_status") == "movable"
        and item.get("move_allowed") is True
    ]

    return {
        "structured_inputs_valid": not blockers,
        "blocking_errors": blockers,
        "unresolved_requirements": unresolved,
        "approved_movable_ids": (
            approved_movable if not blockers else []
        ),
        "ready_for_full_requirement_fulfillment_claim": False,
        "spatial_feasibility_verified": False,
        "whole_layout_optimized": False,
    }


if __name__ == "__main__":
    from pathlib import Path
    from permission_validator import load_json

    poc = Path(__file__).resolve().parents[1]
    project = poc.parent

    scene = load_json(
        project / "02_GENERATED_RESEARCH_DATA"
        / "STAGE_C_OBJECTS"
        / "C3_17_RENDERER_V3_MASTER_180"
        / "SB_0005_OUTDOOR_GARDEN_L_SHAPE.json"
    )

    permissions = load_json(
        poc / "config" / "planner_permissions_v2.json"
    )

    planner = {
        "circulation_priority": "high",
        "visibility_priority": "high",
        "utilization_priority": "medium",
        "minimum_change_priority": "high",
    }

    client = {
        "event_type": "conference",
        "guest_count": 80,
        "required_objects": {
            "chair": 40,
            "round_table": 4,
        },
        "preference": "Clear view of the stage",
    }

    result = diagnose(
        scene, permissions, client, planner
    )

    assert result["structured_inputs_valid"] is True
    assert len(result["unresolved_requirements"]) == 1
    assert (
        result["unresolved_requirements"][0]["shortfall"]
        == 12
    )
    assert result["approved_movable_ids"] == []
    assert result[
        "ready_for_full_requirement_fulfillment_claim"
    ] is False

    print("=== PP1 REQUIREMENT CONFLICT GATE ===")
    print("Input validation: PASS")
    print("Additional chairs needed: 12")
    print("Unconfirmed objects remain locked: PASS")
    print("Full requirement fulfillment: NOT CLAIMED")
    print("Spatial feasibility: NOT VERIFIED")
    print("ALL 5 ASSERTIONS PASSED")