import json
import math
from pathlib import Path

from shapely.geometry import Point, box
from shapely.ops import unary_union

ROOT = Path(__file__).resolve().parents[1]
INPUT = ROOT / "outputs" / "event_objects_wedding_160_v1.json"
OUTPUT = ROOT / "outputs" / "full_layout_baseline_v1.json"

# Controlled experimental geometry, NOT a measured venue.
VENUE_WIDTH = 32.0
VENUE_HEIGHT = 24.0

TABLE_RADIUS = 0.80
CHAIR_RADIUS = 0.27
CHAIR_RING_RADIUS = 1.45

venue = box(0, 0, VENUE_WIDTH, VENUE_HEIGHT)


def geometry_for(kind, cx, cy):
    if kind == "round_table":
        return Point(cx, cy).buffer(TABLE_RADIUS, resolution=24)
    if kind == "chair":
        return Point(cx, cy).buffer(CHAIR_RADIUS, resolution=12)
    raise ValueError("Unsupported circular object")


def serialize(object_id, kind, geom, center=None):
    record = {
        "object_id": object_id,
        "class": kind,
        "footprint_coordinates_m": [
            [round(x, 5), round(y, 5)]
            for x, y in geom.exterior.coords
        ],
        "placement_status": "placed",
    }
    if center is not None:
        record["center_m"] = [
            round(center[0], 5),
            round(center[1], 5),
        ]
    return record


data = json.loads(INPUT.read_text(encoding="utf-8"))
objects = data["objects"]

counts = {}
for obj in objects:
    kind = obj["class"]
    counts[kind] = counts.get(kind, 0) + 1

assert counts == data["requested_counts"]
assert len({x["object_id"] for x in objects}) == len(objects)

tables = sorted(
    [o for o in objects if o["class"] == "round_table"],
    key=lambda o: o["object_id"],
)
chairs = sorted(
    [o for o in objects if o["class"] == "chair"],
    key=lambda o: o["object_id"],
)
stages = [o for o in objects if o["class"] == "stage"]
buffets = sorted(
    [o for o in objects if o["class"] == "buffet_counter"],
    key=lambda o: o["object_id"],
)

if not (
    len(tables) == 20
    and len(chairs) == 160
    and len(stages) == 1
    and len(buffets) == 2
):
    raise ValueError(
        "This controlled baseline requires exactly "
        "20 tables, 160 chairs, 1 stage and 2 buffets. "
        "Other requirements need a separate candidate search."
    )

placed = []
shapes = []

def add(obj, geom, center=None):
    if not venue.covers(geom):
        raise ValueError(f"Object outside venue: {obj['object_id']}")
    for other, other_geom in zip(placed, shapes):
        if geom.intersects(other_geom):
            raise ValueError(
                f"Spatial overlap: {obj['object_id']} "
                f"and {other['object_id']}"
            )
    placed.append(serialize(
        obj["object_id"], obj["class"], geom, center
    ))
    shapes.append(geom)


# Twenty full seating groups: 5 columns x 4 rows.
# These coordinates are a deterministic BASELINE,
# not an NSGA-II solution and not learned preferences.
centers = [
    (3.8 + column * 6.0, 3.7 + row * 4.7)
    for row in range(4)
    for column in range(5)
]

for index, ((cx, cy), table) in enumerate(zip(centers, tables)):
    add(
        table,
        geometry_for("round_table", cx, cy),
        (cx, cy),
    )

    for seat in range(8):
        chair = chairs[index * 8 + seat]
        angle = 2 * math.pi * seat / 8
        x = cx + CHAIR_RING_RADIUS * math.cos(angle)
        y = cy + CHAIR_RING_RADIUS * math.sin(angle)
        add(
            chair,
            geometry_for("chair", x, y),
            (x, y),
        )

# Fixed-size example stage and buffet footprints.
# NOT obtained from the uploaded venue.
add(stages[0], box(12, 20.5, 20, 23))
add(buffets[0], box(2, 21, 4.5, 22.2))
add(buffets[1], box(27, 21, 29.5, 22.2))

assert len(placed) == len(objects)
assert len(shapes) == len(objects)

placed_ids = {p["object_id"] for p in placed}
assert placed_ids == {o["object_id"] for o in objects}

minimum_distance = min(
    shapes[i].distance(shapes[j])
    for i in range(len(shapes))
    for j in range(i + 1, len(shapes))
)

result = {
    "experiment": "PP1_STAGE_E_FULL_LAYOUT_BASELINE_V1",
    "input_schema": data["schema"],
    "input_file": str(INPUT),
    "venue_source": "CONTROLLED_ASSUMPTION_NOT_REAL_VENUE",
    "venue_dimensions_m": [VENUE_WIDTH, VENUE_HEIGHT],
    "venue_boundary_m": list(venue.exterior.coords),
    "object_dimensions_source": "CONTROLLED_ASSUMPTIONS",
    "generated_count": len(objects),
    "placed_count": len(placed),
    "unplaced_count": len(objects) - len(placed),
    "placed_by_class": counts,
    "minimum_pairwise_distance_m": round(minimum_distance, 5),
    "objects": placed,
    "checks": {
        "all_requested_ids_accounted_for": True,
        "all_objects_inside_assumed_venue": True,
        "no_object_footprint_overlaps": True,
    },
    "algorithm": "DETERMINISTIC_SEATING_GRID_BASELINE",
    "nsga2_executed": False,
    "context_priorities_optimized": False,
    "access_route_verified": False,
    "real_venue_geometry_verified": False,
    "safety_certified": False,
}

if OUTPUT.exists():
    raise FileExistsError(
        "Output already exists; refusing overwrite"
    )

OUTPUT.write_text(
    json.dumps(result, indent=2),
    encoding="utf-8",
)

print("=== STAGE E FULL LAYOUT BASELINE ===")
print("Input requested objects:", len(objects))
print("Placed:", result["placed_count"])
print("Unplaced:", result["unplaced_count"])
print("20 tables + 160 chairs:", "PASS")
print("Stage and buffets:", "PASS")
print("Boundary containment:", "PASS")
print("Object footprint overlap:", "0 detected")
print("Minimum pairwise distance:", round(minimum_distance, 4))
print("NSGA-II optimization: NOT EXECUTED")
print("Real venue safety: NOT VERIFIED")
print("Output:", OUTPUT)
print("E4/E5 CONTROLLED BASELINE COMPLETE")