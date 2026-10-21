import json
import math
import random
from pathlib import Path

from shapely.geometry import Point, Polygon

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "outputs" / "layout_candidates_v1.json"
BASE = ROOT / "outputs" / "full_layout_baseline_v1.json"
DEST = ROOT / "outputs" / "e6a_feasible_initialization_v1.json"

RADIUS = 1.72
CLEARANCE = 0.5
STEP = 2 * RADIUS + CLEARANCE + 0.20
SEEDS = [11, 23, 37, 51, 79]

source = json.loads(SOURCE.read_text(encoding="utf-8"))
baseline = json.loads(BASE.read_text(encoding="utf-8"))

venue = Polygon(source["venue_polygon"])
fixed = [
    Polygon(o["footprint_coordinates_m"])
    for o in baseline["objects"]
    if o["class"] in ("stage", "buffet_counter")
]

assert venue.is_valid and venue.area > 0
assert all(g.is_valid and venue.covers(g) for g in fixed)

required = int(source["requested_tables"])
chairs_per_table = int(source["chairs_per_table"])
assert required >= 0
assert chairs_per_table > 0

xmin, ymin, xmax, ymax = venue.bounds


def options_for_seed(seed):
    rng = random.Random(seed)
    points = []
    shift_x = rng.uniform(0, 0.17)
    shift_y = rng.uniform(0, 0.17)

    x = xmin + RADIUS + shift_x
    while x + RADIUS <= xmax + 1e-9:
        y = ymin + RADIUS + shift_y
        while y + RADIUS <= ymax + 1e-9:
            points.append((x, y))
            y += STEP
        x += STEP

    rng.shuffle(points)
    return points


def compute(seed):
    accepted = []
    envelopes = []
    checked = 0

    for x, y in options_for_seed(seed):
        if len(accepted) == required:
            break

        checked += 1
        envelope = Point(x, y).buffer(RADIUS, resolution=32)

        if not venue.covers(envelope):
            continue

        if any(
            envelope.distance(obstacle) < CLEARANCE
            for obstacle in fixed
        ):
            continue

        if any(
            envelope.distance(previous) < CLEARANCE
            for previous in envelopes
        ):
            continue

        accepted.append([round(x, 5), round(y, 5)])
        envelopes.append(envelope)

    # Independently recompute accepted candidate's gate.
    boundary_failures = sum(
        not venue.covers(e) for e in envelopes
    )
    fixed_failures = sum(
        e.distance(f) < CLEARANCE
        for e in envelopes for f in fixed
    )
    group_failures = sum(
        envelopes[i].distance(envelopes[j]) < CLEARANCE
        for i in range(len(envelopes))
        for j in range(i + 1, len(envelopes))
    )

    placed = len(accepted)
    return {
        "seed": seed,
        "candidate_positions_checked": checked,
        "table_centers": accepted,
        "placed_tables": placed,
        "placed_chairs": placed * chairs_per_table,
        "unplaced_tables": required - placed,
        "unplaced_chairs": (required - placed) * chairs_per_table,
        "boundary_failures": boundary_failures,
        "fixed_clearance_failures": fixed_failures,
        "group_clearance_failures": group_failures,
        "experimental_gate_pass": (
            placed == required
            and boundary_failures == 0
            and fixed_failures == 0
            and group_failures == 0
        ),
    }


results = [compute(seed) for seed in SEEDS]

# Only save valid research results with explicit provenance.
report = {
    "experiment": "PP1_STAGE_E6A_FEASIBLE_INITIALIZATION_V1",
    "source_venue": source["venue_source"],
    "source_experiment": source["experiment"],
    "search_method": "GEOMETRY_AWARE_STAGGER_FREE_LATTICE_MULTISTART",
    "candidate_grid_step_synthetic_m": STEP,
    "group_envelope_radius_synthetic_m": RADIUS,
    "experimental_minimum_clearance_m": CLEARANCE,
    "requested_tables": required,
    "chairs_per_table": chairs_per_table,
    "alternatives": results,
    "nsga2_executed": False,
    "real_venue_validated": False,
    "certified_safety": False,
}

if DEST.exists():
    raise FileExistsError(
        "Output exists; refusing overwrite: " + str(DEST)
    )

DEST.write_text(json.dumps(report, indent=2), encoding="utf-8")

print("=== E6A FEASIBLE INITIALIZATION ===")
for result in results:
    print(
        "Seed", result["seed"],
        "| tables:", result["placed_tables"], "/", required,
        "| chairs:", result["placed_chairs"],
        "| boundary failures:", result["boundary_failures"],
        "| fixed failures:", result["fixed_clearance_failures"],
        "| group failures:", result["group_clearance_failures"],
        "| gate:", "PASS" if result["experimental_gate_pass"] else "FAIL",
    )

print(
    "Passing candidates:",
    sum(r["experimental_gate_pass"] for r in results),
    "/", len(results)
)
print("Full furniture footprints separately replayed: NO")
print("NSGA-II executed: NO")
print("Real-world safety verified: NO")
print("Output:", DEST)