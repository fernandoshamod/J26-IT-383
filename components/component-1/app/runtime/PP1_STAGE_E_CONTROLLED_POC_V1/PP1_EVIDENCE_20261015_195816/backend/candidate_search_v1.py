import copy
import json
from pathlib import Path

from shapely.affinity import translate
from shapely.geometry import Polygon

from permission_validator import validate_config
from feasibility_engine_v1 import evaluate_move
from fixed_collision_v1 import geometry_from_rings


POC = Path(__file__).resolve().parents[1]
PROJECT = POC.parent

scene_path = (
    PROJECT / "02_GENERATED_RESEARCH_DATA"
    / "STAGE_C_OBJECTS"
    / "C3_17_RENDERER_V3_MASTER_180"
    / "SB_0005_OUTDOOR_GARDEN_L_SHAPE.json"
)
permission_path = POC / "config" / "planner_permissions_v2.json"

scene = json.loads(scene_path.read_text(encoding="utf-8-sig"))
baseline = json.loads(
    permission_path.read_text(encoding="utf-8-sig")
)

assert validate_config(scene, baseline) == []

OBJECT_ID = 2
original = next(
    x for x in scene["event_instances"]
    if x["instance_id"] == OBJECT_ID
)

assert original["fixed"] is False

# Simulated authorization lives in memory only.
trial = copy.deepcopy(baseline)
entry = next(
    x for x in trial["objects"]
    if x["instance_id"] == OBJECT_ID
)

entry["planner_status"] = "movable"
entry["move_allowed"] = True
entry["remove_allowed"] = False
entry["approved_by"] = "SYNTHETIC_TEST_PLANNER"
entry["approval_note"] = "Controlled placement search"
entry["approval_scope"] = "SYNTHETIC_DEMO_ONLY"
entry["source_conflict_reviewed"] = False

assert validate_config(scene, trial) == []

site = geometry_from_rings(scene["site_polygon_m"])
footprint = geometry_from_rings(original["polygons_m"])

minx, miny, maxx, maxy = site.bounds
fx1, fy1, fx2, fy2 = footprint.bounds

tested = 0
feasible = []
reason_counts = {}

# Deterministic grid, synthetic generator-local metres.
# Evaluate up to 600 different non-original placements.
stop = False

for xi in range(int(minx), int(maxx) + 1):
    if stop:
        break

    for yi in range(int(miny), int(maxy) + 1):
        dx = xi - fx1
        dy = yi - fy1

        if abs(dx) < 0.01 and abs(dy) < 0.01:
            continue

        shifted_rings = []
        for ring in original["polygons_m"]:
            poly = translate(
                Polygon(ring),
                xoff=dx,
                yoff=dy,
            )
            shifted_rings.append(
                [list(p) for p in poly.exterior.coords]
            )

        result = evaluate_move(
            scene,
            trial,
            OBJECT_ID,
            shifted_rings,
        )
        tested += 1

        if result["feasible"]:
            feasible.append({
                "x_offset": round(dx, 3),
                "y_offset": round(dy, 3),
                "travel_synthetic_m": round(
                    (dx * dx + dy * dy) ** 0.5, 3
                ),
            })
            if len(feasible) >= 3:
                stop = True
                break
        else:
            reason = result["reason"]
            reason_counts[reason] = (
                reason_counts.get(reason, 0) + 1
            )

        if tested >= 600:
            stop = True
            break

print("=== PP1 CANDIDATE SEARCH ===")
print("Object:", OBJECT_ID, original["class"])
print("Candidates evaluated:", tested)
print("Feasible candidates found:", len(feasible))
print("Candidate examples:", feasible)
print("Rejection summary:", reason_counts)
print("Optimizer executed: NO")
print("Original scene modified: NO")
print("Real-world safety certified: NO")
print("Full route connectivity verified: NO")

if feasible:
    print("CONTROLLED FEASIBLE MOVE FOUND")
else:
    print("NO FEASIBLE MOVE FOUND UNDER CURRENT DEMO RULES")