import json
import math
import time
from pathlib import Path

import numpy as np
from shapely.geometry import Point, Polygon
from pymoo.core.problem import ElementwiseProblem
from pymoo.algorithms.moo.nsga2 import NSGA2
from pymoo.optimize import minimize
from scipy.optimize import linear_sum_assignment
from scipy.spatial.distance import cdist

ROOT = Path(__file__).resolve().parents[1]
INPUT = ROOT / "outputs" / "e6a_feasible_initialization_v1.json"
BASE = ROOT / "outputs" / "full_layout_baseline_v1.json"
DEST = ROOT / "outputs" / "e6b_full_group_nsga2_v2.json"

RADIUS = 1.72
CLEARANCE = 0.5
SEED = 20261017
POPULATION = 60
GENERATIONS = 30

initial = json.loads(INPUT.read_text(encoding="utf-8"))
baseline = json.loads(BASE.read_text(encoding="utf-8"))

venue = Polygon(baseline["venue_boundary_m"])
fixed_records = [
    o for o in baseline["objects"]
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

valid_seeds = [
    np.asarray(a["table_centers"], dtype=float)
    for a in initial["alternatives"]
    if a["experimental_gate_pass"]
]

n = int(initial["requested_tables"])
chairs_per_table = int(initial["chairs_per_table"])

if not valid_seeds or n < 2:
    raise RuntimeError("No feasible initialization or invalid group count")

if any(v.shape != (n, 2) for v in valid_seeds):
    raise RuntimeError("Initialization dimensions mismatch")

reference = valid_seeds[0].copy()
xmin, ymin, xmax, ymax = venue.bounds

lower = np.tile(
    [xmin + RADIUS, ymin + RADIUS], n
)
upper = np.tile(
    [xmax - RADIUS, ymax - RADIUS], n
)

# Each circle's exact radius is conservative and includes
# the table and eight surrounding chairs.
def measure(x):
    centers = np.asarray(x, dtype=float).reshape(n, 2)
    envelopes = [
        Point(float(cx), float(cy)).buffer(
            RADIUS, resolution=32
        )
        for cx, cy in centers
    ]

    constraints = []
    distances = []

    # Polygon containment, including non-rectangular venues.
    for shape in envelopes:
        constraints.append(
            float(shape.difference(venue).area)
        )

    for shape in envelopes:
        for obstacle in fixed:
            d = shape.distance(obstacle)
            constraints.append(CLEARANCE - d)
            distances.append(d)

    for i in range(n):
        for j in range(i + 1, n):
            # Circular envelopes: exact inter-envelope gap.
            d = max(
                0.0,
                math.dist(centers[i], centers[j])
                - 2 * RADIUS
            )
            constraints.append(CLEARANCE - d)
            distances.append(d)

    stage_distance = float(np.mean([
        math.dist(
            center,
            [stage.centroid.x, stage.centroid.y]
        )
        for center in centers
    ]))

    minimum_gap = min(distances)
    # Initial design: seating groups are interchangeable.
    # Find the minimum one-to-one reference assignment.
    # Adaptive redesign of named/fixed groups requires
    # a separate identity-aware movement objective.
    assignment_cost = cdist(reference, centers)
    rows, columns = linear_sum_assignment(assignment_cost)
    total_displacement = float(
        assignment_cost[rows, columns].sum()
    )

    return {
        "objectives": [
            stage_distance,
            -minimum_gap,
            total_displacement,
        ],
        "constraints": constraints,
        "stage_proximity": stage_distance,
        "minimum_clearance": minimum_gap,
        "displacement": total_displacement,
        "feasible": all(g <= 1e-7 for g in constraints),
        "centers": centers,
    }


constraint_count = n + n * len(fixed) + n * (n - 1) // 2


class LayoutProblem(ElementwiseProblem):
    def __init__(self):
        super().__init__(
            n_var=2 * n,
            n_obj=3,
            n_ieq_constr=constraint_count,
            xl=lower,
            xu=upper,
        )

    def _evaluate(self, x, out, *args, **kwargs):
        m = measure(x)
        out["F"] = m["objectives"]
        out["G"] = m["constraints"]


rng = np.random.default_rng(SEED)
sampling = rng.uniform(
    lower, upper, size=(POPULATION, 2 * n)
)

for i, seed_layout in enumerate(valid_seeds[:POPULATION]):
    sampling[i] = seed_layout.flatten()

# Include modest neighbourhood variations without
# assuming that perturbations remain feasible.
for i in range(
    len(valid_seeds),
    min(20, POPULATION)
):
    sampling[i] = np.clip(
        reference.flatten()
        + rng.normal(0, 0.12, 2 * n),
        lower, upper
    )

for sample in sampling[:len(valid_seeds)]:
    assert measure(sample)["feasible"], "Invalid feasible seed"

start = time.perf_counter()

result = minimize(
    LayoutProblem(),
    NSGA2(
        pop_size=POPULATION,
        sampling=sampling,
        eliminate_duplicates=True,
    ),
    ("n_gen", GENERATIONS),
    seed=SEED,
    verbose=False,
)

runtime = time.perf_counter() - start

solutions = []
if result.X is not None:
    for x in np.atleast_2d(result.X):
        m = measure(x)
        if m["feasible"]:
            solutions.append(m)


def summary(m, label):
    return {
        "label": label,
        "average_stage_proximity_synthetic_m": round(
            m["stage_proximity"], 5
        ),
        "minimum_clearance_synthetic_m": round(
            m["minimum_clearance"], 5
        ),
        "total_displacement_synthetic_m": round(
            m["displacement"], 5
        ),
        "table_centers": m["centers"].round(5).tolist(),
        "group_count": n,
        "chair_count": n * chairs_per_table,
        "geometry_constraints_pass": m["feasible"],
    }


selected = []
if solutions:
    choices = [
        (
            "best_stage_proximity",
            min(solutions, key=lambda m: m["stage_proximity"])
        ),
        (
            "best_clearance",
            max(solutions, key=lambda m: m["minimum_clearance"])
        ),
        (
            "minimum_change",
            min(solutions, key=lambda m: m["displacement"])
        ),
    ]
    for label, entry in choices:
        if not any(
            np.allclose(
                entry["centers"], existing["centers"],
                atol=1e-4
            )
            for existing in selected
        ):
            selected.append({
                **entry,
                "selection_label": label,
            })

reference_metrics = measure(reference.flatten())

report = {
    "experiment": "PP1_E6B_FULL_GROUP_NSGA2_V2",
    "algorithm": "pymoo.NSGA2",
    "seed": SEED,
    "population": POPULATION,
    "generations": GENERATIONS,
    "evaluations": int(result.algorithm.evaluator.n_eval),
    "runtime_seconds": round(runtime, 4),
    "venue_source": "CONTROLLED_ASSUMPTION_NOT_REAL_VENUE",
    "requested_tables": n,
    "requested_chairs": n * chairs_per_table,
    "seating_group_radius": RADIUS,
    "experimental_clearance": CLEARANCE,
    "baseline": summary(reference_metrics, "reference"),
    "returned_feasible_nondominated": len(solutions),
    "selected": [
        summary(m, m["selection_label"])
        for m in selected
    ],
    "full_individual_furniture_replay": False,
    "stage_visibility_verified": False,
    "route_connectivity_verified": False,
    "real_venue_validated": False,
    "safety_certified": False,
    "independent_algorithm_benchmark": False,
    "movement_objective": "MINIMUM_BIPARTITE_ASSIGNMENT",
    "movement_semantics": "INITIAL_DESIGN_INTERCHANGEABLE_GROUPS",
    "stable_identity_reoptimization_implemented": False,
}

if DEST.exists():
    raise FileExistsError("Output exists; refusing overwrite")

DEST.write_text(
    json.dumps(report, indent=2),
    encoding="utf-8",
)

print("=== E6B FULL-GROUP NSGA-II ===")
print("Optimized groups:", n)
print("Represented chairs:", n * chairs_per_table)
print("Decision variables:", 2 * n)
print("Constraints:", constraint_count)
print("Evaluations:", report["evaluations"])
print("Baseline feasible:", reference_metrics["feasible"])
print("Returned feasible nondominated:", len(solutions))
print("Selected alternatives:", len(selected))

for entry in report["selected"]:
    print(
        entry["label"],
        "| stage distance:",
        entry["average_stage_proximity_synthetic_m"],
        "| clearance:",
        entry["minimum_clearance_synthetic_m"],
        "| movement:",
        entry["total_displacement_synthetic_m"],
        "| PASS:",
        entry["geometry_constraints_pass"],
    )

print("Individual furniture replay: NOT DONE")
print("Real-world validation: NOT DONE")
print("Output:", DEST)
print("E6B OPTIMIZATION RUN COMPLETE")