from collections import Counter

EVENT_TYPES = {
    "conference", "wedding", "concert",
    "exhibition", "corporate_event", "other"
}
PRIORITIES = {"low", "medium", "high"}


def validate_requirements(scene, client, planner):
    errors = []
    warnings = []

    if not isinstance(client, dict) or not isinstance(planner, dict):
        return {
            "valid": False,
            "errors": ["Client and planner inputs must be objects"],
            "warnings": []
        }

    if client.get("event_type") not in EVENT_TYPES:
        errors.append("Invalid event type")

    guests = client.get("guest_count")
    if type(guests) is not int or guests <= 0:
        errors.append("Guest count must be a positive integer")

    required = client.get("required_objects")
    if not isinstance(required, dict):
        errors.append("Required objects must be a dictionary")
        required = {}

    inventory = Counter(
        item.get("class")
        for item in scene.get("event_instances", [])
    )

    for name, count in required.items():
        if type(count) is not int or count < 0:
            errors.append(f"Invalid required count: {name}")
        elif name not in inventory:
            warnings.append(
                f"{name}: not in this scene's existing object inventory"
            )
        elif count > inventory[name]:
            warnings.append(
                f"{name}: requested {count}, existing {inventory[name]}; "
                "additional supply/placement needs review"
            )

    for field in (
        "circulation_priority",
        "visibility_priority",
        "utilization_priority",
        "minimum_change_priority",
    ):
        if planner.get(field) not in PRIORITIES:
            errors.append(f"Invalid planner priority: {field}")

    preference = client.get("preference", "")
    if not isinstance(preference, str):
        errors.append("Client preference must be text")

    return {
        "valid": len(errors) == 0,
        "errors": errors,
        "warnings": warnings,
        "client": client,
        "planner": planner,
        "spatial_feasibility_checked": False,
        "optimization_executed": False,
    }


if __name__ == "__main__":
    import json
    from pathlib import Path

    project = Path(__file__).resolve().parents[2]
    source = (
        project / "02_GENERATED_RESEARCH_DATA"
        / "STAGE_C_OBJECTS"
        / "C3_17_RENDERER_V3_MASTER_180"
        / "SB_0005_OUTDOOR_GARDEN_L_SHAPE.json"
    )
    scene = json.loads(source.read_text(encoding="utf-8-sig"))

    client = {
        "event_type": "conference",
        "guest_count": 80,
        "required_objects": {"chair": 28, "round_table": 4},
        "preference": "Clear stage visibility",
    }

    planner = {
        "circulation_priority": "high",
        "visibility_priority": "high",
        "utilization_priority": "medium",
        "minimum_change_priority": "high",
    }

    result = validate_requirements(scene, client, planner)

    assert result["valid"] is True
    assert result["spatial_feasibility_checked"] is False
    assert result["optimization_executed"] is False

    invalid = dict(client)
    invalid["guest_count"] = -5
    assert validate_requirements(
        scene, invalid, planner
    )["valid"] is False

    print("=== PP1 REQUIREMENTS BACKEND ===")
    print("Structured input validation: PASS")
    print("Invalid guest count rejected: PASS")
    print("Spatial feasibility: NOT TESTED")
    print("Optimization: NOT EXECUTED")