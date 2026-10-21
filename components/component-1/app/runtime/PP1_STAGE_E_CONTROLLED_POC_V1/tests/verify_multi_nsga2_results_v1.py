import copy
import json
import math
import sys
from pathlib import Path

POC = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(POC / "backend"))

from permission_validator import load_json, validate_config
from feasibility_engine_v1 import evaluate_move

PROJECT = POC.parent
scene = load_json(
    PROJECT / "02_GENERATED_RESEARCH_DATA"
    / "STAGE_C_OBJECTS"
    / "C3_17_RENDERER_V3_MASTER_180"
    / "SB_0005_OUTDOOR_GARDEN_L_SHAPE.json"
)
config = load_json(
    POC / "config" / "planner_permissions_v2.json"
)
report = load_json(
    POC / "outputs" / "multi_object_nsga2_v1.json"
)

assert report["scene_id"] == scene["id"]
assert set(report["object_ids"]) == {2, 3}

# Reconstruct the documented simulated authorization.
permissions = copy.deepcopy(config)
for oid in report["object_ids"]:
    entry = next(
        p for p in permissions["objects"]
        if p["instance_id"] == oid
    )
    assert not entry["source_fixed"]
    entry.update({
        "planner_status": "movable",
        "move_allowed": True,
        "remove_allowed": False,
        "approved_by": "INDEPENDENT_SYNTHETIC_RECHECK",
        "approval_note": "Rechecking saved PP1 result",
        "approval_scope": "SYNTHETIC_DEMO_ONLY",
        "source_conflict_reviewed": False,
    })

assert validate_config(scene, permissions) == []

total_checks = 0

for alternative in report["selected_alternatives"]:
    working = copy.deepcopy(scene)
    positions = alternative["positions"]
    assert {p["instance_id"] for p in positions} == {2, 3}

    # Reconstruct both proposed positions first.
    for position in positions:
        target = next(
            x for x in working["event_instances"]
            if x["instance_id"] == position["instance_id"]
        )
        target["polygons_m"] = position["footprints_m"]

    # Ensure other 33 event objects remain unchanged.
    for source_obj, current_obj in zip(
        scene["event_instances"],
        working["event_instances"]
    ):
        assert source_obj["instance_id"] == current_obj["instance_id"]
        if source_obj["instance_id"] not in {2, 3}:
            assert source_obj == current_obj

    distance = 0.0
    minimum_clearance = float("inf")

    for position in positions:
        oid = position["instance_id"]
        result = evaluate_move(
            working,
            permissions,
            oid,
            position["footprints_m"],
            clearance_m=0.5,
        )

        assert result["feasible"], (
            alternative["label"], oid, result
        )
        assert len(result["checks"]) == 5
        assert all(
            item["passed"] is True
            for item in result["checks"].values()
        )

        total_checks += 5
        distance += math.hypot(
            position["dx"], position["dy"]
        )
        minimum_clearance = min(
            minimum_clearance,
            result["checks"]["minimum_clearance"][
                "nearest_distance_synthetic_m"
            ],
        )

    assert abs(
        distance -
        alternative["total_relocation_synthetic_m"]
    ) < 0.001

    assert abs(
        minimum_clearance -
        alternative["minimum_clearance_synthetic_m"]
    ) < 0.001

    print(
        alternative["label"],
        "| geometry checks: 10 PASS",
        "| total relocation:", round(distance, 4),
        "| clearance:", round(minimum_clearance, 4)
    )

assert total_checks == 30

print("=== PP1 INDEPENDENT RESULT RECHECK ===")
print("Recomputed constraint checks: 30/30 PASS")
print("Recorded objective metrics: MATCH")
print("Unapproved objects: UNCHANGED")
print("Route connectivity: NOT VERIFIED")
print("Real-world safety: NOT CERTIFIED")
print("INDEPENDENT GEOMETRY RECHECK PASS")