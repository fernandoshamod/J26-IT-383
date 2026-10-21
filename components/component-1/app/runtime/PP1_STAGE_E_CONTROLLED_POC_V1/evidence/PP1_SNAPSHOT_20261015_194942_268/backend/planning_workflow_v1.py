import copy
import math
from pathlib import Path

from shapely.affinity import translate
from shapely.geometry import Polygon

from permission_validator import load_json, check_action
from requirement_conflicts_v1 import diagnose
from feasibility_engine_v1 import evaluate_move
from fixed_collision_v1 import geometry_from_rings


def move_geometry(rings, dx, dy):
    return [
        [list(point) for point in translate(
            Polygon(ring), xoff=dx, yoff=dy
        ).exterior.coords]
        for ring in rings
    ]


def run_planning(scene, permissions, client, planner,
                 max_objects=2, max_checks=1500):
    diagnosis = diagnose(
        scene, permissions, client, planner
    )

    if diagnosis["blocking_errors"]:
        return {
            "status": "BLOCKED_INVALID_INPUT",
            "diagnosis": diagnosis,
            "placements": [],
        }

    if diagnosis["unresolved_requirements"]:
        return {
            "status": "BLOCKED_UNRESOLVED_REQUIREMENTS",
            "diagnosis": diagnosis,
            "placements": [],
        }

    approved = diagnosis["approved_movable_ids"]

    if not approved:
        return {
            "status": "NO_AUTHORIZED_MOVEMENTS",
            "diagnosis": diagnosis,
            "placements": [],
        }

    if not isinstance(max_objects, int) or max_objects < 1:
        raise ValueError("Invalid max_objects")

    if not isinstance(max_checks, int) or max_checks < 1:
        raise ValueError("Invalid max_checks")

    selected = approved[:max_objects]
    working = copy.deepcopy(scene)
    site = geometry_from_rings(scene["site_polygon_m"])
    minx, miny, maxx, maxy = site.bounds
    placements = []

    for oid in selected:
        if not check_action(
            scene, permissions, oid, "move"
        )["allowed"]:
            return {
                "status": "BLOCKED_PERMISSION",
                "diagnosis": diagnosis,
                "placements": placements,
            }

        original = next(
            x for x in scene["event_instances"]
            if x["instance_id"] == oid
        )
        shape = geometry_from_rings(original["polygons_m"])
        ox, oy, _, _ = shape.bounds

        found = None
        tested = 0

        for x in range(math.floor(minx), math.ceil(maxx) + 1):
            if found is not None or tested >= max_checks:
                break

            for y in range(math.floor(miny), math.ceil(maxy) + 1):
                dx, dy = x - ox, y - oy

                if math.hypot(dx, dy) < 1.0:
                    continue

                candidate = move_geometry(
                    original["polygons_m"], dx, dy
                )
                outcome = evaluate_move(
                    working, permissions, oid, candidate
                )
                tested += 1

                if outcome["feasible"]:
                    found = {
                        "instance_id": oid,
                        "class": original["class"],
                        "dx": round(dx, 5),
                        "dy": round(dy, 5),
                        "footprints_m": candidate,
                        "checks": outcome["checks"],
                        "candidates_tested": tested,
                    }
                    break

                if tested >= max_checks:
                    break

        if found is None:
            return {
                "status": "NO_FEASIBLE_PLACEMENT_FOUND",
                "diagnosis": diagnosis,
                "placements": placements,
                "failed_object_id": oid,
                "full_requested_plan_generated": False,
            }

        item = next(
            x for x in working["event_instances"]
            if x["instance_id"] == oid
        )
        item["polygons_m"] = found["footprints_m"]
        placements.append(found)

    # Recheck each final position with all other
    # objects at their proposed final positions.
    for record in placements:
        oid = record["instance_id"]
        inspection_scene = copy.deepcopy(working)
        item = next(
            x for x in inspection_scene["event_instances"]
            if x["instance_id"] == oid
        )
        source_item = next(
            x for x in scene["event_instances"]
            if x["instance_id"] == oid
        )
        item["polygons_m"] = copy.deepcopy(
            source_item["polygons_m"]
        )

        recheck = evaluate_move(
            inspection_scene, permissions, oid,
            record["footprints_m"]
        )
        if not recheck["feasible"]:
            return {
                "status": "JOINT_VALIDATION_FAILED",
                "diagnosis": diagnosis,
                "placements": placements,
                "full_requested_plan_generated": False,
            }

    # Confirm no unapproved object changed.
    selected_ids = set(selected)
    for before, after in zip(
        scene["event_instances"],
        working["event_instances"]
    ):
        if before["instance_id"] != after["instance_id"]:
            raise RuntimeError("Object order changed")
        if before["instance_id"] not in selected_ids:
            if before != after:
                raise RuntimeError(
                    "Unauthorized object modification"
                )

    return {
        "status": "CONTROLLED_PLACEMENTS_FOUND",
        "diagnosis": diagnosis,
        "placements": placements,
        "final_event_instances": working["event_instances"],
        "full_requested_plan_generated": False,
        "whole_layout_safety_certified": False,
        "route_connectivity_verified": False,
        "multi_object_nsga2_executed": False,
    }


if __name__ == "__main__":
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

    demo = copy.deepcopy(permissions)
    for oid in [2, 3]:
        item = next(
            x for x in demo["objects"]
            if x["instance_id"] == oid
        )
        item.update({
            "planner_status": "movable",
            "move_allowed": True,
            "remove_allowed": False,
            "approved_by": "SYNTHETIC_TEST_PLANNER",
            "approval_note": "Controlled workflow test",
            "approval_scope": "SYNTHETIC_DEMO_ONLY",
            "source_conflict_reviewed": False,
        })

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
            "round_table": 4
        },
        "preference": "Clear stage visibility",
    }

    blocked = run_planning(
        scene, demo, client, planner
    )
    assert blocked["status"] == (
        "BLOCKED_UNRESOLVED_REQUIREMENTS"
    )
    assert blocked["placements"] == []

    client["required_objects"]["chair"] = 28

    planned = run_planning(
        scene, demo, client, planner
    )

    print("=== PP1 REQUIREMENTS-DRIVEN PLANNING ===")
    print("Chairs=40:", blocked["status"])
    print("Chairs=28:", planned["status"])
    print(
        "Joint placements:",
        len(planned.get("placements", []))
    )
    print("Multi-object NSGA-II: NOT EXECUTED")
    print("Full requirement fulfillment: NOT VERIFIED")
    print("Route connectivity: NOT VERIFIED")

    assert planned["status"] == "CONTROLLED_PLACEMENTS_FOUND"
    assert len(planned["placements"]) == 2
    print("WORKFLOW TESTS PASSED")