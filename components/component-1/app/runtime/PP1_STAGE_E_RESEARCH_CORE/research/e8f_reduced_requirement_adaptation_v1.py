import json
import math
import sys
from pathlib import Path

import numpy as np
from scipy.spatial.distance import cdist
from shapely.geometry import Point, Polygon
from pymoo.core.problem import ElementwiseProblem
from pymoo.algorithms.moo.nsga2 import NSGA2
from pymoo.optimize import minimize

from e8b_permission_gate_v1 import authorize_revision

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "outputs"
DEST = OUT / "e8f_reduced_requirement_adaptation_v1.json"

opt = json.loads(
    (OUT / "e6b_full_group_nsga2_v2.json").read_text()
)
base = json.loads(
    (OUT / "full_layout_baseline_v1.json").read_text()
)

reference = np.asarray(
    opt["baseline"]["table_centers"], dtype=float
)
assert reference.shape == (20, 2)

venue = Polygon(base["venue_boundary_m"])
fixed = [
    Polygon(o["footprint_coordinates_m"])
    for o in base["objects"]
    if o["class"] in ("stage", "buffet_counter")
]
stage = next(
    Polygon(o["footprint_coordinates_m"])
    for o in base["objects"]
    if o["class"] == "stage"
)
stage_xy = np.array([stage.centroid.x, stage.centroid.y])

RADIUS = 1.72
CLEARANCE = 0.5
GUESTS_BEFORE = 160
GUESTS_AFTER = 120
CHAIRS_PER_TABLE = 8

def group_id(i):
    return f"seating_group_{i+1:04d}"

# Deterministic test policy: remove five farthest groups.
# This policy is experimental, not a planner preference model.
distance = np.linalg.norm(reference-stage_xy, axis=1)
removed = sorted(
    np.argsort(distance)[-5:].tolist()
)
retained = [i for i in range(20) if i not in removed]

# Among retained groups, two may move.
move_indices = sorted(
    retained,
    key=lambda i: distance[i],
    reverse=True
)[:2]
locked_indices = [
    i for i in retained if i not in move_indices
]

assert len(removed) == 5
assert len(retained) == 15
assert len(move_indices) == 2
assert len(locked_indices) == 13

# Explicit experimental permissions, denied by default.
simulate = "--simulate-approval" in sys.argv
permissions = {}

if simulate:
    for i in removed:
        permissions[group_id(i)] = {
            "action": "remove",
            "approved": True,
            "scope": "SYNTHETIC_DEMO_ONLY",
            "reviewer": "SIMULATED_PLANNER",
        }

    for i in move_indices:
        permissions[group_id(i)] = {
            "status": "movable",
            "move_allowed": True,
            "scope": "SYNTHETIC_DEMO_ONLY",
            "approved_by": "SIMULATED_PLANNER",
            "approval_reason": "Controlled guest-count reduction",
        }

def authorize_removal(i):
    permission = permissions.get(group_id(i), {})
    return (
        permission.get("action") == "remove"
        and permission.get("approved") is True
        and permission.get("scope") == "SYNTHETIC_DEMO_ONLY"
        and bool(permission.get("reviewer"))
    )

removal_allowed = all(authorize_removal(i) for i in removed)
movement_results = [
    authorize_revision(
        {"group_id": group_id(i), "action": "move"},
        permissions
    )[0]
    for i in move_indices
]
movement_allowed = all(movement_results)

print("=== E8F REQUIREMENT-CHANGE AUTHORIZATION ===")
print("Guests:", GUESTS_BEFORE, "->", GUESTS_AFTER)
print("Groups to remove:", [group_id(i) for i in removed])
print("Groups allowed to move:", [group_id(i) for i in move_indices])
print("Other retained groups locked:", len(locked_indices))

if not removal_allowed or not movement_allowed:
    print("AUTHORIZATION: DENIED")
    print("NSGA-II BLOCKED; no output written")
    sys.exit(0)

print("AUTHORIZATION: SIMULATED APPROVAL ACCEPTED")

xmin, ymin, xmax, ymax = venue.bounds

def evaluate(x):
    moved = np.asarray(x, dtype=float).reshape(2, 2)
    positions = {
        i: reference[i].copy()
        for i in locked_indices
    }
    for k, i in enumerate(move_indices):
        positions[i] = moved[k]

    envelopes = {
        i: Point(*positions[i]).buffer(RADIUS, resolution=32)
        for i in retained
    }

    constraints = [
        envelopes[i].difference(venue).area
        for i in retained
    ]

    gaps = []
    for i in retained:
        for obstacle in fixed:
            gap = envelopes[i].distance(obstacle)
            gaps.append(gap)
            constraints.append(CLEARANCE-gap)

    for a, i in enumerate(retained):
        for j in retained[a+1:]:
            gap = max(
                0.0,
                float(np.linalg.norm(positions[i]-positions[j]))
                - 2*RADIUS
            )
            gaps.append(gap)
            constraints.append(CLEARANCE-gap)

    stage_distance = float(np.mean([
        np.linalg.norm(positions[i]-stage_xy)
        for i in retained
    ]))

    movement = float(sum(
        np.linalg.norm(positions[i]-reference[i])
        for i in move_indices
    ))

    return {
        "F": [stage_distance, movement],
        "G": constraints,
        "feasible": all(g <= 1e-7 for g in constraints),
        "clearance": min(gaps),
        "positions": positions,
    }

start_xy = np.array(
    [reference[i] for i in move_indices]
).reshape(-1)
assert evaluate(start_xy)["feasible"]

class Problem(ElementwiseProblem):
    def __init__(self):
        super().__init__(
            n_var=4,
            n_obj=2,
            n_ieq_constr=len(evaluate(start_xy)["G"]),
            xl=np.tile([xmin+RADIUS, ymin+RADIUS], 2),
            xu=np.tile([xmax-RADIUS, ymax-RADIUS], 2),
        )

    def _evaluate(self, x, out, *args, **kwargs):
        record = evaluate(x)
        out["F"] = record["F"]
        out["G"] = record["G"]

problem = Problem()
rng = np.random.default_rng(20261016)
population = rng.uniform(
    problem.xl, problem.xu, (60, 4)
)
population[0] = start_xy

for i in range(1, 20):
    population[i] = np.clip(
        start_xy + rng.normal(0, 0.35, 4),
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
    seed=20261016,
    verbose=False,
)

feasible = []
if result.X is not None:
    for x in np.atleast_2d(result.X):
        m = evaluate(x)
        if m["feasible"]:
            feasible.append((x, m))

if not feasible:
    print("NO FEASIBLE OPTIMIZED SOLUTIONS")
    raise SystemExit(1)

best_stage = min(feasible, key=lambda z: z[1]["F"][0])
minimum_move = min(feasible, key=lambda z: z[1]["F"][1])

def pack(label, item):
    x, m = item

    # Reconstruct actual 15 tables and 120 chairs, plus
    # three original fixed objects.
    shapes = list(fixed)
    for i in retained:
        cx, cy = m["positions"][i]
        shapes.append(Point(cx, cy).buffer(0.8, resolution=24))
        for seat in range(8):
            angle = 2*math.pi*seat/8
            shapes.append(
                Point(
                    cx+1.45*math.cos(angle),
                    cy+1.45*math.sin(angle)
                ).buffer(0.27, resolution=12)
            )

    outside = sum(not venue.covers(s) for s in shapes)
    overlaps = sum(
        shapes[i].intersection(shapes[j]).area > 1e-8
        for i in range(len(shapes))
        for j in range(i+1, len(shapes))
    )

    locked_unchanged = all(
        np.array_equal(m["positions"][i], reference[i])
        for i in locked_indices
    )

    passed = (
        len(shapes) == 138
        and outside == 0
        and overlaps == 0
        and locked_unchanged
        and m["feasible"]
    )
    if not passed:
        raise RuntimeError(f"Geometry replay failed: {label}")

    return {
        "label": label,
        "stage_distance": round(m["F"][0], 6),
        "movement": round(m["F"][1], 6),
        "clearance": round(m["clearance"], 6),
        "objects": len(shapes),
        "outside": outside,
        "overlaps": overlaps,
        "locked_unchanged": locked_unchanged,
        "geometry_pass": passed,
        "group_centers_by_id": {
            group_id(i): m["positions"][i].tolist()
            for i in retained
        },
    }

baseline = pack("post_removal_reference", (start_xy, evaluate(start_xy)))
selected = [
    pack("best_stage_proximity", best_stage),
    pack("minimum_movement", minimum_move)
]

report = {
    "experiment": "PP1_E8F_REQUIREMENT_ADAPTATION_V1",
    "venue": "CONTROLLED_SYNTHETIC",
    "guests_before": 160,
    "guests_after": 120,
    "removed_group_ids": [group_id(i) for i in removed],
    "movable_group_ids": [group_id(i) for i in move_indices],
    "locked_group_ids": [group_id(i) for i in locked_indices],
    "simulated_authorization_enforced": True,
    "nsga2_evaluations": int(result.algorithm.evaluator.n_eval),
    "feasible_solutions": len(feasible),
    "baseline": baseline,
    "selected": selected,
    "real_planner_approval": False,
    "historical_preferences_learned": False,
    "real_venue_validated": False,
    "safety_certified": False,
}

if DEST.exists():
    raise FileExistsError("Output already exists")

DEST.write_text(json.dumps(report, indent=2), encoding="utf-8")

print("=== E8F ADAPTIVE REQUIREMENT EXPERIMENT ===")
print("Requested objects after reduction: 138")
print("Removed groups:", len(removed))
print("Locked retained groups:", len(locked_indices))
print("Movable retained groups:", len(move_indices))
print("NSGA-II evaluations:", report["nsga2_evaluations"])
print("Feasible returned:", len(feasible))

for s in [baseline] + selected:
    print(
        s["label"],
        "| stage:", s["stage_distance"],
        "| movement:", s["movement"],
        "| clearance:", s["clearance"],
        "| objects:", s["objects"],
        "| geometry PASS:", s["geometry_pass"]
    )

print("Actual planner approval: NO")
print("Real-world safety: NOT VERIFIED")
print("Output:", DEST)
print("E8F COMPLETE")