import json
import math
import random
import sys
from pathlib import Path

import numpy as np
from shapely.geometry import Point, Polygon
from pymoo.core.problem import ElementwiseProblem
from pymoo.algorithms.moo.nsga2 import NSGA2
from pymoo.optimize import minimize

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "outputs"
DEST = OUT / "e8g_increased_requirement_adaptation_v1.json"

def load(name):
    return json.loads((OUT / name).read_text(encoding="utf-8"))

opt = load("e6b_full_group_nsga2_v2.json")
base = load("full_layout_baseline_v1.json")
init = load("e6a_feasible_initialization_v1.json")

existing = np.asarray(
    opt["baseline"]["table_centers"], dtype=float
)
assert existing.shape == (20, 2)

venue = Polygon(base["venue_boundary_m"])
fixed_records = [
    o for o in base["objects"]
    if o["class"] in ("stage", "buffet_counter")
]
fixed = [
    Polygon(o["footprint_coordinates_m"])
    for o in fixed_records
]
stage = next(
    Polygon(o["footprint_coordinates_m"])
    for o in fixed_records if o["class"] == "stage"
)

RADIUS = 1.72
CLEARANCE = 0.5
SEATS = 8
NEW_COUNT = 5
SEED = 20261016

new_ids = [
    f"seating_group_{i:04d}" for i in range(21, 26)
]
locked_ids = [
    f"seating_group_{i:04d}" for i in range(1, 21)
]

# Fail closed: every new group must have explicit
# simulated permission to be added.
simulate = "--simulate-approval" in sys.argv

permissions = {}
if simulate:
    permissions = {
        gid: {
            "action": "add",
            "approved": True,
            "scope": "SYNTHETIC_DEMO_ONLY",
            "reviewer": "SIMULATED_PLANNER",
            "reason": "Guest count increased from 160 to 200",
        }
        for gid in new_ids
    }

def authorized_add(gid):
    p = permissions.get(gid)
    return (
        gid not in locked_ids
        and isinstance(p, dict)
        and p.get("action") == "add"
        and p.get("approved") is True
        and p.get("scope") == "SYNTHETIC_DEMO_ONLY"
        and isinstance(p.get("reviewer"), str)
        and bool(p["reviewer"].strip())
        and isinstance(p.get("reason"), str)
        and bool(p["reason"].strip())
    )

print("=== E8G ADDITION AUTHORIZATION ===")
print("Guests: 160 -> 200")
print("Existing locked groups:", len(locked_ids))
print("Requested added groups:", new_ids)

if not all(authorized_add(gid) for gid in new_ids):
    print("AUTHORIZATION: DENIED")
    print("NSGA-II BLOCKED; no output written")
    sys.exit(0)

print("AUTHORIZATION: SIMULATED APPROVAL ACCEPTED")

assert venue.is_valid and venue.area > 0
assert len(fixed) == 3

stage_xy = np.array(
    [stage.centroid.x, stage.centroid.y], dtype=float
)
xmin, ymin, xmax, ymax = venue.bounds

existing_envelopes = [
    Point(float(x), float(y)).buffer(
        RADIUS, resolution=32
    )
    for x, y in existing
]

assert all(venue.covers(g) for g in existing_envelopes)

def feasible_new(center, previous):
    candidate = Point(*map(float, center)).buffer(
        RADIUS, resolution=32
    )

    if not venue.covers(candidate):
        return False

    if any(
        candidate.distance(obj) < CLEARANCE - 1e-7
        for obj in fixed
    ):
        return False

    if any(
        np.linalg.norm(np.asarray(center) - other)
        < 2 * RADIUS + CLEARANCE - 1e-7
        for other in list(existing) + list(previous)
    ):
        return False

    return True

# Reconstruct the same controlled feasible lattice
# used for E6A seed 11, without moving existing groups.
rng = random.Random(11)
shift_x = rng.uniform(0, 0.17)
shift_y = rng.uniform(0, 0.17)
step = 2 * RADIUS + CLEARANCE + 0.20

candidate_points = []
x = xmin + RADIUS + shift_x

while x + RADIUS <= xmax + 1e-9:
    y = ymin + RADIUS + shift_y
    while y + RADIUS <= ymax + 1e-9:
        candidate_points.append((x, y))
        y += step
    x += step

rng.shuffle(candidate_points)

added_reference = []

for center in candidate_points:
    if feasible_new(center, added_reference):
        added_reference.append(center)
    if len(added_reference) == NEW_COUNT:
        break

if len(added_reference) != NEW_COUNT:
    raise RuntimeError(
        "Cannot initialize five additions in this controlled "
        "scenario. This does not prove venue capacity is insufficient."
    )

added_reference = np.asarray(
    added_reference, dtype=float
)

# Stable IDs: only the five new groups can move.
def evaluate(x):
    new_centers = np.asarray(
        x, dtype=float
    ).reshape(NEW_COUNT, 2)

    shapes = [
        Point(float(cx), float(cy)).buffer(
            RADIUS, resolution=32
        )
        for cx, cy in new_centers
    ]

    constraints = []
    gaps = []

    for shape in shapes:
        constraints.append(
            float(shape.difference(venue).area)
        )

    for shape in shapes:
        for obstacle in fixed:
            d = shape.distance(obstacle)
            gaps.append(d)
            constraints.append(CLEARANCE - d)

    all_centers = np.vstack(
        [existing, new_centers]
    )

    for i in range(20, 25):
        for j in range(i):
            gap = max(
                0.0,
                float(np.linalg.norm(
                    all_centers[i] - all_centers[j]
                )) - 2 * RADIUS
            )
            gaps.append(gap)
            constraints.append(CLEARANCE - gap)

    for i in range(20, 25):
        for j in range(i + 1, 25):
            gap = max(
                0.0,
                float(np.linalg.norm(
                    all_centers[i] - all_centers[j]
                )) - 2 * RADIUS
            )
            gaps.append(gap)
            constraints.append(CLEARANCE - gap)

    avg_stage = float(
        np.mean(np.linalg.norm(
            all_centers - stage_xy, axis=1
        ))
    )

    placement_movement = float(
        np.linalg.norm(
            new_centers - added_reference,
            axis=1
        ).sum()
    )

    return {
        "F": [avg_stage, placement_movement],
        "G": constraints,
        "feasible": all(g <= 1e-7 for g in constraints),
        "clearance": min(gaps),
        "new_centers": new_centers,
    }

start_x = added_reference.flatten()
assert evaluate(start_x)["feasible"]

class AdditionProblem(ElementwiseProblem):
    def __init__(self):
        initial_g = evaluate(start_x)["G"]

        super().__init__(
            n_var=10,
            n_obj=2,
            n_ieq_constr=len(initial_g),
            xl=np.tile(
                [xmin + RADIUS, ymin + RADIUS], NEW_COUNT
            ),
            xu=np.tile(
                [xmax - RADIUS, ymax - RADIUS], NEW_COUNT
            ),
        )

    def _evaluate(self, x, out, *args, **kwargs):
        m = evaluate(x)
        out["F"] = m["F"]
        out["G"] = m["G"]

problem = AdditionProblem()

np_rng = np.random.default_rng(SEED)
population = np_rng.uniform(
    problem.xl, problem.xu, size=(60, 10)
)
population[0] = start_x

for i in range(1, 30):
    population[i] = np.clip(
        start_x + np_rng.normal(0, 0.12, 10),
        problem.xl, problem.xu
    )

result = minimize(
    problem,
    NSGA2(
        pop_size=60,
        sampling=population,
        eliminate_duplicates=True
    ),
    ("n_gen", 35),
    seed=SEED,
    verbose=False
)

feasible = []
if result.X is not None:
    for x in np.atleast_2d(result.X):
        m = evaluate(x)
        if m["feasible"]:
            feasible.append((x, m))

# The original feasible candidate is a valid fallback.
reference_pair = (start_x, evaluate(start_x))

def replay(label, pair):
    x, m = pair
    all_centers = np.vstack(
        [existing, m["new_centers"]]
    )

    # Full individual-furniture replay.
    objects = list(fixed)
    for cx, cy in all_centers:
        objects.append(
            Point(cx, cy).buffer(0.8, resolution=24)
        )
        for seat in range(SEATS):
            angle = 2 * math.pi * seat / SEATS
            objects.append(
                Point(
                    cx + 1.45 * math.cos(angle),
                    cy + 1.45 * math.sin(angle)
                ).buffer(0.27, resolution=12)
            )

    outside = sum(
        not venue.covers(shape) for shape in objects
    )
    overlaps = sum(
        objects[i].intersection(objects[j]).area > 1e-8
        for i in range(len(objects))
        for j in range(i + 1, len(objects))
    )

    locked_same = np.array_equal(
        all_centers[:20], existing
    )

    passed = (
        len(objects) == 228
        and outside == 0
        and overlaps == 0
        and locked_same
        and m["feasible"]
    )

    if not passed:
        raise RuntimeError(
            "Individual geometry replay failed: " + label
        )

    return {
        "label": label,
        "stage_distance": round(m["F"][0], 6),
        "new_group_movement": round(m["F"][1], 6),
        "minimum_clearance": round(m["clearance"], 6),
        "objects": len(objects),
        "outside": outside,
        "overlaps": overlaps,
        "locked_unchanged": locked_same,
        "geometry_pass": passed,
        "new_groups_by_id": {
            gid: [float(v) for v in center]
            for gid, center in zip(
                new_ids, m["new_centers"]
            )
        },
    }

reference_record = replay(
    "addition_reference", reference_pair
)

selected = []
if feasible:
    best_stage = min(
        feasible, key=lambda item: item[1]["F"][0]
    )
    min_move = min(
        feasible, key=lambda item: item[1]["F"][1]
    )
    selected = [
        replay("best_stage_proximity", best_stage),
        replay("minimum_movement", min_move),
    ]

report = {
    "experiment": "PP1_E8G_INCREASED_REQUIREMENT_V1",
    "scope": "CONTROLLED_SYNTHETIC_ONLY",
    "guests_before": 160,
    "guests_after": 200,
    "locked_group_ids": locked_ids,
    "added_group_ids": new_ids,
    "simulated_addition_permission_enforced": True,
    "algorithm": "pymoo.NSGA2",
    "n_variables": 10,
    "evaluations": int(result.algorithm.evaluator.n_eval),
    "returned_feasible": len(feasible),
    "reference": reference_record,
    "selected": selected,
    "real_planner_approval": False,
    "real_venue_validated": False,
    "route_connectivity_verified": False,
    "safety_certified": False,
}

if DEST.exists():
    raise FileExistsError(
        "Output exists; refusing overwrite"
    )

DEST.write_text(
    json.dumps(report, indent=2),
    encoding="utf-8"
)

print("=== E8G INCREASED REQUIREMENT ===")
print("Existing locked groups:", len(locked_ids))
print("Added groups:", len(new_ids))
print("Total reconstructed objects: 228")
print("NSGA-II evaluations:", report["evaluations"])
print("Returned feasible solutions:", len(feasible))

for r in [reference_record] + selected:
    print(
        r["label"],
        "| stage:", r["stage_distance"],
        "| movement:", r["new_group_movement"],
        "| clearance:", r["minimum_clearance"],
        "| geometry:", r["geometry_pass"]
    )

print("Real planner approval: NO")
print("Real-world safety: NOT VERIFIED")
print("Output:", DEST)
print("E8G COMPLETE")