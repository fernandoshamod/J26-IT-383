import json
import math
from pathlib import Path

from shapely.geometry import Point, Polygon
from shapely.strtree import STRtree

ROOT = Path(__file__).resolve().parents[1]
OPT = ROOT / "outputs" / "e6b_full_group_nsga2_v2.json"
BASE = ROOT / "outputs" / "full_layout_baseline_v1.json"
REQ = ROOT / "outputs" / "event_objects_wedding_160_v1.json"
DEST = ROOT / "outputs" / "e6c_individual_geometry_replay_v1.json"

opt = json.loads(OPT.read_text(encoding="utf-8"))
base = json.loads(BASE.read_text(encoding="utf-8"))
req = json.loads(REQ.read_text(encoding="utf-8"))

venue = Polygon(base["venue_boundary_m"])
assert venue.is_valid and venue.area > 0

fixed_records = [
    o for o in base["objects"]
    if o["class"] in ("stage", "buffet_counter")
]

fixed = [
    (o["object_id"], Polygon(o["footprint_coordinates_m"]))
    for o in fixed_records
]

TABLE_R = 0.80
CHAIR_R = 0.27
RING_R = 1.45
GROUP_R = 1.72
MIN_CLEARANCE = 0.5

assert opt["requested_tables"] == 20
assert opt["requested_chairs"] == 160
assert len(fixed) == 3
assert len(req["objects"]) == 183

results = []

for alt in opt["selected"]:
    centers = alt["table_centers"]

    assert len(centers) == 20

    items = list(fixed)
    groups = []

    for index, (cx, cy) in enumerate(centers):
        table_id = f"round_table_{index + 1:04d}"

        table = Point(cx, cy).buffer(TABLE_R, resolution=24)
        items.append((table_id, table))

        for seat in range(8):
            angle = 2 * math.pi * seat / 8
            x = cx + RING_R * math.cos(angle)
            y = cy + RING_R * math.sin(angle)

            chair_id = f"chair_{index * 8 + seat + 1:04d}"
            chair = Point(x, y).buffer(CHAIR_R, resolution=12)

            items.append((chair_id, chair))

        groups.append(
            Point(cx, cy).buffer(GROUP_R, resolution=32)
        )

    assert len(items) == 183
    assert len({name for name, _ in items}) == 183

    # Every actual individual footprint must lie inside
    # the assumed experimental venue.
    outside = [
        name for name, shape in items
        if not venue.covers(shape)
    ]

    # Check all unordered pairs. STRtree is unnecessary
    # for only 183 footprints.
    collisions = []
    for i in range(len(items)):
        for j in range(i + 1, len(items)):
            name_a, shape_a = items[i]
            name_b, shape_b = items[j]

            if shape_a.intersection(shape_b).area > 1e-8:
                collisions.append([name_a, name_b])

    # Re-evaluate the experimental group envelope gate.
    group_boundary_failures = sum(
        not venue.covers(group) for group in groups
    )

    fixed_clearance_failures = sum(
        group.distance(shape) < MIN_CLEARANCE - 1e-6
        for group in groups
        for _, shape in fixed
    )

    group_clearance_failures = sum(
        groups[i].distance(groups[j]) < MIN_CLEARANCE - 1e-6
        for i in range(len(groups))
        for j in range(i + 1, len(groups))
    )

    passed = (
        len(outside) == 0
        and len(collisions) == 0
        and group_boundary_failures == 0
        and fixed_clearance_failures == 0
        and group_clearance_failures == 0
    )

    entry = {
        "alternative": alt["label"],
        "total_objects": len(items),
        "outside_object_count": len(outside),
        "overlap_pair_count": len(collisions),
        "group_boundary_failures": group_boundary_failures,
        "fixed_clearance_failures": fixed_clearance_failures,
        "group_clearance_failures": group_clearance_failures,
        "experimental_geometry_pass": passed,
        "outside_preview": outside[:10],
        "collision_preview": collisions[:10],
    }
    results.append(entry)

    print(
        alt["label"],
        "| objects:", len(items),
        "| outside:", len(outside),
        "| overlaps:", len(collisions),
        "| envelope failures:",
        group_boundary_failures
        + fixed_clearance_failures
        + group_clearance_failures,
        "| PASS:", passed,
    )

report = {
    "experiment": "PP1_E6C_INDIVIDUAL_GEOMETRY_REPLAY_V1",
    "optimizer_source": opt["experiment"],
    "results": results,
    "all_alternatives_pass": all(
        r["experimental_geometry_pass"] for r in results
    ),
    "source_geometry": "CONTROLLED_SYNTHETIC_ASSUMPTIONS",
    "rotation_optimized": False,
    "visibility_verified": False,
    "route_connectivity_verified": False,
    "real_venue_validated": False,
    "safety_certified": False,
}

if DEST.exists():
    raise FileExistsError("Output exists; refusing overwrite")

DEST.write_text(
    json.dumps(report, indent=2),
    encoding="utf-8"
)

print("=== E6C REPLAY SUMMARY ===")
print("Alternatives:", len(results))
print("All geometry replay checks:", report["all_alternatives_pass"])
print("Real-world safety certified: NO")
print("Output:", DEST)

if not report["all_alternatives_pass"]:
    raise SystemExit("E6C GEOMETRY REPLAY FAILED")

print("E6C GEOMETRY REPLAY PASS")