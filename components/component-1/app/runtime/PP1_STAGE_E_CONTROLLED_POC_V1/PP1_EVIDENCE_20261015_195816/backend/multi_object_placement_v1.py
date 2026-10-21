import copy
import math
from pathlib import Path

from shapely.affinity import translate
from shapely.geometry import Polygon

from permission_validator import (
    load_json, validate_config, check_action
)
from feasibility_engine_v1 import evaluate_move
from fixed_collision_v1 import geometry_from_rings

POC = Path(__file__).resolve().parents[1]
PROJECT = POC.parent

SOURCE = (
    PROJECT / "02_GENERATED_RESEARCH_DATA"
    / "STAGE_C_OBJECTS"
    / "C3_17_RENDERER_V3_MASTER_180"
    / "SB_0005_OUTDOOR_GARDEN_L_SHAPE.json"
)
CONFIG = POC / "config" / "planner_permissions_v2.json"

OBJECT_IDS = (2, 3)
MAX_CHECKS_PER_OBJECT = 1500

scene = load_json(SOURCE)
baseline = load_json(CONFIG)

assert validate_config(scene, baseline) == []

source_map = {
    x["instance_id"]: x
    for x in scene["event_instances"]
}

for oid in OBJECT_IDS:
    assert oid in source_map, f"Missing object {oid}"
    assert source_map[oid]["fixed"] is False

trial = copy.deepcopy(baseline)

for oid in OBJECT_IDS:
    entry = next(
        x for x in trial["objects"]
        if x["instance_id"] == oid
    )
    entry.update({
        "planner_status": "movable",
        "move_allowed": True,
        "remove_allowed": False,
        "approved_by": "SYNTHETIC_TEST_PLANNER",
        "approval_note": "Joint layout placement test only",
        "approval_scope": "SYNTHETIC_DEMO_ONLY",
        "source_conflict_reviewed": False,
    })

assert validate_config(scene, trial) == []

for oid in OBJECT_IDS:
    assert check_action(
        scene, trial, oid, "move"
    )["allowed"] is True

working = copy.deepcopy(scene)
site = geometry_from_rings(scene["site_polygon_m"])
minx, miny, maxx, maxy = site.bounds

positions = {}
counts = {}

def relocate(rings, dx, dy):
    result = []
    for ring in rings:
        polygon = translate(
            Polygon(ring),
            xoff=dx,
            yoff=dy,
        )
        result.append([
            list(point)
            for point in polygon.exterior.coords
        ])
    return result


def find_placement(oid):
    source_obj = source_map[oid]
    shape = geometry_from_rings(source_obj["polygons_m"])
    fx1, fy1, _, _ = shape.bounds

    tested = 0

    # Deterministic grid search, not an optimizer.
    for xi in range(math.floor(minx), math.ceil(maxx) + 1):
        for yi in range(math.floor(miny), math.ceil(maxy) + 1):
            dx = xi - fx1
            dy = yi - fy1

            if math.hypot(dx, dy) < 1.0:
                continue

            candidate = relocate(
                source_obj["polygons_m"], dx, dy
            )
            outcome = evaluate_move(
                working, trial, oid, candidate
            )
            tested += 1

            if outcome["feasible"]:
                return candidate, (dx, dy), tested

            if tested >= MAX_CHECKS_PER_OBJECT:
                return None, None, tested

    return None, None, tested


for oid in OBJECT_IDS:
    geometry, offset, tested = find_placement(oid)
    counts[str(oid)] = tested

    if geometry is None:
        print("JOINT PLACEMENT NOT ESTABLISHED")
        print("Object:", oid)
        print("Candidates tested:", tested)
        print("No success claim.")
        raise SystemExit(2)

    item = next(
        x for x in working["event_instances"]
        if x["instance_id"] == oid
    )
    item["polygons_m"] = geometry
    positions[oid] = offset

# Final joint evaluation: temporarily restore each moving
# object to its source position, while retaining every
# other object's final position.
for oid in OBJECT_IDS:
    final_obj = next(
        x for x in working["event_instances"]
        if x["instance_id"] == oid
    )
    final_geometry = copy.deepcopy(final_obj["polygons_m"])

    inspection_scene = copy.deepcopy(working)
    inspection_obj = next(
        x for x in inspection_scene["event_instances"]
        if x["instance_id"] == oid
    )
    inspection_obj["polygons_m"] = copy.deepcopy(
        source_map[oid]["polygons_m"]
    )

    outcome = evaluate_move(
        inspection_scene, trial, oid, final_geometry
    )
    assert outcome["feasible"], (oid, outcome)

# Only the two explicitly approved objects may differ.
for original in scene["event_instances"]:
    oid = original["instance_id"]
    updated = next(
        x for x in working["event_instances"]
        if x["instance_id"] == oid
    )

    if oid not in OBJECT_IDS:
        assert updated == original, (
            f"Unauthorized object changed: {oid}"
        )

# No modification to original loaded source / permissions.
assert validate_config(scene, baseline) == []

print("=== PP1 MULTI-OBJECT JOINT PLACEMENT ===")
print("Source scene:", scene["id"])

for oid in OBJECT_IDS:
    print(
        f"Object {oid} ({source_map[oid]['class']}): "
        f"offset={positions[oid]}, "
        f"candidates_tested={counts[str(oid)]}"
    )

print("Joint final candidate checks: PASS")
print("Other 33 event objects: UNCHANGED")
print("Source files modified: NO")
print("Full route connectivity verified: NO")
print("Whole-layout safety certified: NO")
print("MULTI-OBJECT PLACEMENT POC PASS")