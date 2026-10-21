import json
import math
import time
from pathlib import Path

import numpy as np
from shapely.geometry import Point, Polygon
from pymoo.core.problem import ElementwiseProblem
from pymoo.algorithms.moo.nsga2 import NSGA2
from pymoo.optimize import minimize

ROOT = Path(__file__).resolve().parents[1]
OPT = ROOT / "outputs" / "e6b_full_group_nsga2_v2.json"
BASE = ROOT / "outputs" / "full_layout_baseline_v1.json"
DEST = ROOT / "outputs" / "e7a_adaptive_reoptimization_v1.json"

RADIUS = 1.72
CLEARANCE = 0.5
SEED = 20261017
POP = 48
GENERATIONS = 35

opt = json.loads(OPT.read_text(encoding="utf-8"))
base = json.loads(BASE.read_text(encoding="utf-8"))

approved = next(
    item for item in opt["selected"]
    if item["label"] == "best_stage_proximity"
)

original = np.asarray(
    approved["table_centers"], dtype=float
)
assert original.shape == (20, 2)

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
stage_center = np.asarray(
    [stage.centroid.x, stage.centroid.y]
)

# Select the farthest group for a controlled planner
# request to improve stage proximity.
distances = np.linalg.norm(
    original - stage_center, axis=1
)
move_index = int(np.argmax(distances))
move_id = f"seating_group_{move_index + 1:04d}"
initial_xy = original[move_index].copy()

locked = [
    Point(float(x), float(y)).buffer(
        RADIUS, resolution=32
    )
    for i, (x, y) in enumerate(original)
    if i != move_index
]

assert venue.is_valid
assert all(venue.covers(g) for g in locked)

xmin, ymin, xmax, ymax = venue.bounds


def evaluate(xy):
    candidate = Point(
        float(xy[0]), float(xy[1])
    ).buffer(RADIUS, resolution=32)

    distances_to_protected = [
        candidate.distance(g) for g in locked + fixed
    ]

    constraints = [
        float(candidate.difference(venue).area),
        *[
            CLEARANCE - d
            for d in distances_to_protected
        ],
    ]

    movement = float(
        np.linalg.norm(np.asarray(xy) - initial_xy)
    )
    stage_distance = float(
        np.linalg.norm(np.asarray(xy) - stage_center)
    )

    return {
        "constraints": constraints,
        "feasible": all(c <= 1e-7 for c in constraints),
        "movement": movement,
        "stage_distance": stage_distance,
        "minimum_clearance": min(distances_to_protected),
    }


assert evaluate(initial_xy)["feasible"], (
    "Approved reference must satisfy experimental gate"
)


class RevisionProblem(ElementwiseProblem):
    def __init__(self):
        super().__init__(
            n_var=2,
            n_obj=2,
            n_ieq_constr=1 + len(locked) + len(fixed),
            xl=np.array([xmin + RADIUS, ymin + RADIUS]),
            xu=np.array([xmax - RADIUS, ymax - RADIUS]),
        )

    def _evaluate(self, x, out, *args, **kwargs):
        result = evaluate(x)
        out["F"] = [
            result["stage_distance"],
            result["movement"],
        ]
        out["G"] = result["constraints"]


rng = np.random.default_rng(SEED)
problem = RevisionProblem()
population = rng.uniform(
    problem.xl, problem.xu,
    size=(POP, 2)
)

population[0] = initial_xy
for index in range(1, 12):
    population[index] = np.clip(
        initial_xy + rng.normal(0, 0.5, 2),
        problem.xl, problem.xu
    )

start = time.perf_counter()
result = minimize(
    problem,
    NSGA2(
        pop_size=POP,
        sampling=population,
        eliminate_duplicates=True,
    ),
    ("n_gen", GENERATIONS),
    seed=SEED,
    verbose=False,
)
runtime = time.perf_counter() - start

solutions = []
if result.X is not None:
    for xy in np.atleast_2d(result.X):
        metrics = evaluate(xy)
        if metrics["feasible"]:
            solutions.append((xy, metrics))


def make_record(label, xy, metrics):
    proposed = original.copy()
    proposed[move_index] = xy

    assert np.array_equal(
        np.delete(proposed, move_index, axis=0),
        np.delete(original, move_index, axis=0)
    )

    return {
        "label": label,
        "moved_group_id": move_id,
        "old_position": initial_xy.tolist(),
        "new_position": np.asarray(xy).tolist(),
        "movement_synthetic_m": round(
            metrics["movement"], 6
        ),
        "stage_distance_synthetic_m": round(
            metrics["stage_distance"], 6
        ),
        "minimum_protected_clearance_synthetic_m": round(
            metrics["minimum_clearance"], 6
        ),
        "geometry_pass": metrics["feasible"],
        "unchanged_group_count": 19,
        "all_group_centers": proposed.tolist(),
    }


reference = make_record(
    "original_approved_layout",
    initial_xy,
    evaluate(initial_xy),
)

selected = []
if solutions:
    best_stage = min(
        solutions,
        key=lambda s: s[1]["stage_distance"]
    )
    selected.append(
        make_record("improved_stage_proximity_candidate",
                    best_stage[0], best_stage[1])
    )

    # A lower-movement alternative that actually
    # improves stage proximity, if one exists.
    improved = [
        s for s in solutions
        if s[1]["stage_distance"]
        < reference["stage_distance_synthetic_m"] - 1e-4
    ]
    if improved:
        minimum_change = min(
            improved,
            key=lambda s: s[1]["movement"]
        )
        if not np.allclose(
            minimum_change[0], best_stage[0],
            atol=1e-5
        ):
            selected.append(make_record(
                "minimum_change_improvement",
                minimum_change[0],
                minimum_change[1],
            ))

report = {
    "experiment": "PP1_E7A_PERMISSION_AWARE_REVISION_V1",
    "source_approved_layout": opt["experiment"],
    "permission_scope": "SYNTHETIC_PLANNER_SCENARIO",
    "movable_group_ids": [move_id],
    "locked_group_count": 19,
    "algorithm": "pymoo.NSGA2",
    "seed": SEED,
    "evaluations": int(result.algorithm.evaluator.n_eval),
    "runtime_seconds": round(runtime, 4),
    "reference": reference,
    "returned_feasible_solutions": len(solutions),
    "selected": selected,
    "actual_planner_approval": False,
    "full_multi_group_adaptation": False,
    "real_venue_validated": False,
    "route_connectivity_verified": False,
    "safety_certified": False,
}

if DEST.exists():
    raise FileExistsError("Output exists; no overwrite")

DEST.write_text(
    json.dumps(report, indent=2),
    encoding="utf-8",
)

print("=== STAGE E7A ADAPTIVE RE-OPTIMIZATION ===")
print("Requested movable group:", move_id)
print("Locked groups:", 19)
print("Optimization evaluations:", report["evaluations"])
print(
    "Original stage distance:",
    reference["stage_distance_synthetic_m"]
)
print("Feasible returned solutions:", len(solutions))

for entry in selected:
    print(
        entry["label"],
        "| stage distance:",
        entry["stage_distance_synthetic_m"],
        "| movement:",
        entry["movement_synthetic_m"],
        "| clearance:",
        entry["minimum_protected_clearance_synthetic_m"],
        "| unchanged:", entry["unchanged_group_count"],
        "| PASS:", entry["geometry_pass"],
    )

print("Actual planner approval: NO")
print("Full adaptive optimization: NOT IMPLEMENTED")
print("Real-world validation: NO")
print("Output:", DEST)
print("E7A EXPERIMENT COMPLETED")