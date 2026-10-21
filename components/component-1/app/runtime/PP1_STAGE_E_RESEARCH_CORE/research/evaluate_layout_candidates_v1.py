import json
import math
from pathlib import Path

from shapely.geometry import Polygon
from shapely.ops import unary_union

ROOT = Path(__file__).resolve().parents[1]
INPUT = ROOT / "outputs" / "layout_candidates_v1.json"
BASE = ROOT / "outputs" / "full_layout_baseline_v1.json"
OUTPUT = ROOT / "outputs" / "layout_quality_v1.json"

data = json.loads(INPUT.read_text(encoding="utf-8"))
baseline = json.loads(BASE.read_text(encoding="utf-8"))

fixed_records = [
    o for o in baseline["objects"]
    if o["class"] in {"stage", "buffet_counter"}
]

stage_record = next(
    o for o in fixed_records if o["class"] == "stage"
)
stage = Polygon(stage_record["footprint_coordinates_m"])

obstacles = [
    Polygon(o["footprint_coordinates_m"])
    for o in fixed_records
]

evaluations = []

for alt in data["alternatives"]:
    groups = alt["placed_groups"]

    # Each group contains one table and its chairs.
    group_shapes = [
        unary_union([Polygon(ring) for ring in g["footprints"]])
        for g in groups
    ]

    centers = [g["table_center"] for g in groups]

    distances_between_groups = [
        group_shapes[i].distance(group_shapes[j])
        for i in range(len(groups))
        for j in range(i + 1, len(groups))
    ]

    distances_to_fixed = [
        group.distance(obstacle)
        for group in group_shapes
        for obstacle in obstacles
    ]

    clearance_values = (
        distances_between_groups + distances_to_fixed
    )

    table_spacing = [
        math.dist(centers[i], centers[j])
        for i in range(len(centers))
        for j in range(i + 1, len(centers))
    ]

    stage_distances = [
        math.dist(center, (
            stage.centroid.x,
            stage.centroid.y,
        ))
        for center in centers
    ]

    metrics = {
        "seed": alt["seed"],
        "placed_tables": alt["placed_tables"],
        "placed_chairs": alt["placed_chairs"],
        "minimum_group_clearance_m": (
            round(min(clearance_values), 5)
            if clearance_values else None
        ),
        "minimum_table_center_spacing_m": (
            round(min(table_spacing), 5)
            if table_spacing else None
        ),
        "average_stage_center_distance_m": (
            round(sum(stage_distances) / len(stage_distances), 5)
            if stage_distances else None
        ),
        "full_requested_layout": alt["fully_placed"],
    }

    evaluations.append(metrics)

report = {
    "experiment": "PP1_STAGE_E5_LAYOUT_QUALITY_V1",
    "source": "CONTROLLED_SYNTHETIC_GEOMETRY",
    "metrics": evaluations,
    "objective_directions": {
        "minimum_group_clearance_m": "maximize",
        "minimum_table_center_spacing_m": "maximize",
        "average_stage_center_distance_m": "minimize",
    },
    "stage_proximity_is_visibility": False,
    "real_world_safety_certified": False,
    "context_preferences_optimized": False,
    "nsga2_executed": False,
}

if OUTPUT.exists():
    raise FileExistsError("Output exists; no overwrite")

OUTPUT.write_text(
    json.dumps(report, indent=2),
    encoding="utf-8",
)

print("=== STAGE E5.3 LAYOUT QUALITY ===")
for result in evaluations:
    print(
        "Seed", result["seed"],
        "| clearance:", result["minimum_group_clearance_m"],
        "| table spacing:",
        result["minimum_table_center_spacing_m"],
        "| stage proximity:",
        result["average_stage_center_distance_m"]
    )

print("Alternatives evaluated:", len(evaluations))
print("Real venue validation: NO")
print("Stage visibility verified: NO")
print("NSGA-II: NOT EXECUTED")
print("Output:", OUTPUT)
print("STAGE E5.3 EVALUATION COMPLETE")