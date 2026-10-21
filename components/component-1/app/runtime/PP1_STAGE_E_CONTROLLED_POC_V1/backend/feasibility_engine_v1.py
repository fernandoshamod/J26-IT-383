import json
from pathlib import Path

from permission_validator import (
    validate_config,
    check_action,
)
from geometry_constraints_v1 import check_venue_boundary
from fixed_collision_v1 import (
    geometry_from_rings,
    check_fixed_collision,
    SOLID_STRUCTURE_CLASSES,
)
from restricted_zones_v1 import (
    get_restricted_zones,
    check_restricted_zone,
)
from exit_access_v1 import (
    get_access_areas,
    check_access_obstruction,
)
from minimum_clearance_v1 import (
    check_minimum_clearance,
    DEMO_MIN_CLEARANCE_M,
)


def build_protected_geometry(scene, moving_id):
    """
    Every OTHER event footprint is treated as occupied.
    This includes unconfirmed/locked objects and objects
    approved for movement but not moved in this operation.
    """
    protected = []

    for obj in scene["event_instances"]:
        oid = obj["instance_id"]
        if oid == moving_id:
            continue

        protected.append({
            "id": f"event_{oid}",
            "class": obj["class"],
            "geometry": geometry_from_rings(
                obj["polygons_m"]
            ),
        })

    for index, item in enumerate(
        scene["structural_geometry"]
    ):
        if item["name"] in SOLID_STRUCTURE_CLASSES:
            protected.append({
                "id": f"structure_{index}",
                "class": item["name"],
                "geometry": geometry_from_rings(
                    item["polygons_m"]
                ),
            })

    return protected


def evaluate_move(
    scene,
    permissions,
    moving_id,
    proposed_rings,
    clearance_m=DEMO_MIN_CLEARANCE_M,
):
    """
    Evaluates ONE proposed object move against the
    unchanged scene. Does not mutate scene or permissions.

    This is synthetic candidate feasibility only.
    """
    errors = validate_config(scene, permissions)
    if errors:
        return {
            "feasible": False,
            "reason": "INVALID_PERMISSION_CONFIG",
            "errors": errors,
            "checks": {},
        }

    source_ids = {
        x["instance_id"]
        for x in scene["event_instances"]
    }
    if moving_id not in source_ids:
        return {
            "feasible": False,
            "reason": "UNKNOWN_OBJECT",
            "checks": {},
        }

    authorization = check_action(
        scene, permissions, moving_id, "move"
    )

    if not authorization["allowed"]:
        return {
            "feasible": False,
            "reason": "MOVE_NOT_AUTHORIZED",
            "authorization": authorization,
            "checks": {},
        }

    try:
        protected = build_protected_geometry(
            scene, moving_id
        )
        access = get_access_areas(scene)
        restricted = get_restricted_zones(scene)

        checks = {
            "boundary": check_venue_boundary(
                scene["site_polygon_m"],
                proposed_rings,
            ),
            "fixed_and_existing_object_collision":
                check_fixed_collision(
                    proposed_rings, protected,
                    candidate_object_id=moving_id,
                ),
            "restricted_zone": check_restricted_zone(
                proposed_rings, restricted
            ),
            "access_area": check_access_obstruction(
                proposed_rings, access
            ),
            "minimum_clearance": check_minimum_clearance(
                proposed_rings,
                protected,
                minimum_clearance_m=clearance_m,
                candidate_object_id=moving_id,
            ),
        }

    except (ValueError, TypeError, KeyError) as exc:
        return {
            "feasible": False,
            "reason": "INVALID_SCENE_GEOMETRY",
            "detail": str(exc),
            "checks": {},
        }

    all_pass = all(
        item.get("passed") is True
        for item in checks.values()
    )

    return {
        "feasible": all_pass,
        "reason": (
            "CANDIDATE_CHECKS_PASS"
            if all_pass
            else "CANDIDATE_CONSTRAINT_VIOLATION"
        ),
        "authorization": authorization,
        "checks": checks,
        "route_connectivity_verified": False,
        "real_world_safety_approved": False,
        "whole_layout_validated": False,
        "optimization_executed": False,
    }


if __name__ == "__main__":
    import copy

    poc = Path(__file__).resolve().parents[1]
    project = poc.parent

    scene_path = (
        project / "02_GENERATED_RESEARCH_DATA"
        / "STAGE_C_OBJECTS"
        / "C3_17_RENDERER_V3_MASTER_180"
        / "SB_0005_OUTDOOR_GARDEN_L_SHAPE.json"
    )
    config_path = (
        poc / "config" / "planner_permissions_v2.json"
    )

    scene = json.loads(
        scene_path.read_text(encoding="utf-8-sig")
    )
    permissions = json.loads(
        config_path.read_text(encoding="utf-8-sig")
    )

    assert validate_config(scene, permissions) == []

    original_scene = copy.deepcopy(scene)
    original_permissions = copy.deepcopy(permissions)

    # Stage 1 is initially unconfirmed. It must be denied.
    outside = [[
        [60, 20], [63, 20],
        [63, 23], [60, 23]
    ]]

    denied = evaluate_move(
        scene, permissions, 1, outside
    )
    assert denied["feasible"] is False
    assert denied["reason"] == "MOVE_NOT_AUTHORIZED"

    # Controlled, in-memory planner authorization.
    trial = copy.deepcopy(permissions)
    stage = next(
        x for x in trial["objects"]
        if x["instance_id"] == 1
    )
    stage["planner_status"] = "movable"
    stage["move_allowed"] = True
    stage["remove_allowed"] = False
    stage["approved_by"] = "SYNTHETIC_TEST_PLANNER"
    stage["approval_note"] = (
        "Reviewed source-fixed discrepancy; demo only"
    )
    stage["approval_scope"] = "SYNTHETIC_DEMO_ONLY"
    stage["source_conflict_reviewed"] = True

    assert validate_config(scene, trial) == []

    # Authorization alone must never bypass geometry.
    boundary_denied = evaluate_move(
        scene, trial, 1, outside
    )

    assert boundary_denied["feasible"] is False
    assert (
        boundary_denied["checks"]["boundary"]["passed"]
        is False
    )

    # Deliberately overlap existing podium #34.
    podium = next(
        x for x in scene["event_instances"]
        if x["instance_id"] == 34
    )

    overlap_denied = evaluate_move(
        scene, trial, 1, podium["polygons_m"]
    )

    assert overlap_denied["feasible"] is False
    assert (
        overlap_denied["checks"][
            "fixed_and_existing_object_collision"
        ]["passed"] is False
    )

    # Tests must not alter source data or saved permissions.
    assert scene == original_scene
    assert permissions == original_permissions

    print("=== PP1 COMBINED FEASIBILITY TEST ===")
    print("Unconfirmed stage move: DENIED")
    print("Authorized outside-boundary move: DENIED")
    print("Authorized move overlapping podium: DENIED")
    print("Source scene unchanged: YES")
    print("Saved permissions unchanged: YES")
    print("ALL 5 INTEGRATION ASSERTIONS PASSED")
    print("Whole-layout validation: NOT PERFORMED")
    print("Route connectivity: NOT VERIFIED")
    print("Optimization: NOT EXECUTED")