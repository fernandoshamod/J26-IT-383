import json
from pathlib import Path

from shapely.geometry import Point, Polygon

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "outputs" / "layout_candidates_v1.json"
BASE = ROOT / "outputs" / "full_layout_baseline_v1.json"
DEST = ROOT / "outputs" / "e6_feasibility_gate_v1.json"

# Controlled demonstration assumptions only.
GROUP_RADIUS = 1.45 + 0.27
MIN_CLEARANCE = 0.5

data = json.loads(SOURCE.read_text(encoding="utf-8"))
baseline = json.loads(BASE.read_text(encoding="utf-8"))

venue = Polygon(data["venue_polygon"])
assert venue.is_valid and venue.area > 0

fixed = [
    Polygon(obj["footprint_coordinates_m"])
    for obj in baseline["objects"]
    if obj["class"] in ("stage", "buffet_counter")
]

assert len(fixed) == data["fixed_structure_count"]

evaluations = []

for alternative in data["alternatives"]:
    groups = alternative["placed_groups"]

    # A conservative envelope contains each table and its chairs.
    envelopes = [
        Point(*group["table_center"]).buffer(
            GROUP_RADIUS, resolution=32
        )
        for group in groups
    ]

    boundary_failures = sum(
        not venue.covers(envelope)
        for envelope in envelopes
    )

    fixed_failures = sum(
        envelope.distance(obstacle) < MIN_CLEARANCE
        for envelope in envelopes
        for obstacle in fixed
    )

    group_failures = sum(
        envelopes[i].distance(envelopes[j]) < MIN_CLEARANCE
        for i in range(len(envelopes))
        for j in range(i + 1, len(envelopes))
    )

    distances = (
        [
            envelopes[i].distance(envelopes[j])
            for i in range(len(envelopes))
            for j in range(i + 1, len(envelopes))
        ]
        + [
            envelope.distance(obstacle)
            for envelope in envelopes
            for obstacle in fixed
        ]
    )

    result = {
        "seed": alternative["seed"],
        "placed_groups": len(groups),
        "boundary_failures": boundary_failures,
        "fixed_clearance_failures": fixed_failures,
        "group_clearance_failures": group_failures,
        "minimum_envelope_clearance": (
            round(min(distances), 5) if distances else None
        ),
        "experimental_gate_pass": (
            boundary_failures == 0
            and fixed_failures == 0
            and group_failures == 0
            and alternative["fully_placed"]
        ),
    }
    evaluations.append(result)

report = {
    "experiment": "PP1_STAGE_E6_GROUP_FEASIBILITY_GATE_V1",
    "source": data["experiment"],
    "minimum_clearance_synthetic_m": MIN_CLEARANCE,
    "conservative_group_radius_synthetic_m": GROUP_RADIUS,
    "evaluations": evaluations,
    "real_venue_approved": False,
    "regulatory_clearance_verified": False,
    "nsga2_executed": False,
}

if DEST.exists():
    raise FileExistsError("Output exists; refusing overwrite")

DEST.write_text(
    json.dumps(report, indent=2),
    encoding="utf-8",
)

print("=== E6 GROUP FEASIBILITY GATE ===")

for entry in evaluations:
    print(
        "Seed", entry["seed"],
        "| boundary failures:", entry["boundary_failures"],
        "| fixed clearance failures:",
        entry["fixed_clearance_failures"],
        "| group clearance failures:",
        entry["group_clearance_failures"],
        "| gate:", "PASS" if entry["experimental_gate_pass"] else "FAIL",
    )

print(
    "Passing alternatives:",
    sum(x["experimental_gate_pass"] for x in evaluations),
    "/", len(evaluations),
)
print("Real-world safety: NOT VERIFIED")
print("NSGA-II: NOT EXECUTED")
print("Output:", DEST)