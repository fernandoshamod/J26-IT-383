import json
import math
import sys
from pathlib import Path

import numpy as np
from scipy.optimize import linear_sum_assignment
from scipy.spatial.distance import cdist
from shapely.geometry import Point, Polygon
from pymoo.core.problem import ElementwiseProblem
from pymoo.algorithms.moo.nsga2 import NSGA2
from pymoo.optimize import minimize

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "outputs"
BASE = OUT / "full_layout_baseline_v1.json"

GROUP_RADIUS = 1.72
TABLE_RADIUS = 0.80
CHAIR_RADIUS = 0.27
CHAIR_RING = 1.45


def read(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def fail(message):
    raise ValueError(message)


from engine_support import validate_metric as validate, select_nondominated, limits

def initialize(venue, fixed, count, clearance, seed):
    xmin, ymin, xmax, ymax = venue.bounds
    step = 2 * GROUP_RADIUS + clearance + 0.20
    rng = np.random.default_rng(seed)

    xs = np.arange(xmin + GROUP_RADIUS,
                   xmax - GROUP_RADIUS + 1e-8, step)
    ys = np.arange(ymin + GROUP_RADIUS,
                   ymax - GROUP_RADIUS + 1e-8, step)

    candidates = [(float(x), float(y)) for x in xs for y in ys]
    rng.shuffle(candidates)

    chosen = []
    for x, y in candidates:
        e = Point(x, y).buffer(GROUP_RADIUS, resolution=32)
        if not venue.covers(e):
            continue
        if any(e.distance(f) < clearance for f in fixed):
            continue
        if any(
            math.dist((x, y), other) < 2 * GROUP_RADIUS + clearance
            for other in chosen
        ):
            continue
        chosen.append((x, y))
        if len(chosen) == count:
            break

    if len(chosen) != count:
        fail("NO_COMPLETE_INITIALIZATION_FOUND")

    return np.asarray(chosen, dtype=float)


def assignment_movement(reference, proposed):
    reference = np.asarray(reference, dtype=float)
    proposed = np.asarray(proposed, dtype=float)

    if (
        reference.shape != proposed.shape
        or reference.ndim != 2
        or reference.shape[1] != 2
    ):
        raise ValueError("INVALID_ASSIGNMENT_COORDINATES")

    matrix = cdist(reference, proposed)
    rows, columns = linear_sum_assignment(matrix)
    return float(matrix[rows, columns].sum())


def run(req):
    venue, fixed, records, count, clearance, seed = validate(req)
    reference = initialize(venue, fixed, count, clearance, seed)
    stage = next(
        p for o, p in zip(records, fixed) if o["class"] == "stage"
    )
    stage_xy = np.array([stage.centroid.x, stage.centroid.y])
    xmin, ymin, xmax, ymax = venue.bounds

    def measure(x):
        centers = np.asarray(x).reshape(count, 2)
        envelopes = [
            Point(float(cx), float(cy)).buffer(
                GROUP_RADIUS, resolution=32
            )
            for cx, cy in centers
        ]

        constraints = [
            float(e.difference(venue).area) for e in envelopes
        ]
        gaps = []

        for e in envelopes:
            for f in fixed:
                d = e.distance(f)
                gaps.append(d)
                constraints.append(clearance - d)

        for i in range(count):
            for j in range(i + 1, count):
                d = max(
                    0.0, math.dist(centers[i], centers[j])
                    - 2 * GROUP_RADIUS
                )
                gaps.append(d)
                constraints.append(clearance - d)

        stage_distance = float(np.linalg.norm(
            centers - stage_xy, axis=1
        ).mean())
        displacement = assignment_movement(
            reference, centers
        )

        constraints.extend(limits(req, stage_distance, displacement))
        return {
            "F": [stage_distance, displacement],
            "G": constraints,
            "centers": centers,
            "minimum_clearance": min(gaps),
            "feasible": all(g <= 1e-7 for g in constraints),
        }

    n_constraints = count + count * len(fixed) + count * (count - 1) // 2 + len(limits(req,0.0,0.0))

    class LayoutProblem(ElementwiseProblem):
        def __init__(self):
            super().__init__(
                n_var=2 * count, n_obj=2,
                n_ieq_constr=n_constraints,
                xl=np.tile(
                    [xmin + GROUP_RADIUS, ymin + GROUP_RADIUS], count
                ),
                xu=np.tile(
                    [xmax - GROUP_RADIUS, ymax - GROUP_RADIUS], count
                ),
            )

        def _evaluate(self, x, out, *args, **kwargs):
            m = measure(x)
            out["F"] = m["F"]
            out["G"] = m["G"]

    # Geometry initializer remains original; additional hard upper bounds may
    # require search before a feasible result is found. No failed reference is exported.

    problem = LayoutProblem()
    population_size = 48
    rng = np.random.default_rng(seed)
    samples = rng.uniform(
        problem.xl, problem.xu, (population_size, 2 * count)
    )
    samples[0] = reference.flatten()

    for i in range(1, 20):
        samples[i] = np.clip(
            reference.flatten()
            + rng.normal(0, 0.08, 2 * count),
            problem.xl, problem.xu
        )

    optimization = minimize(
        problem,
        NSGA2(
            pop_size=population_size,
            sampling=samples,
            eliminate_duplicates=True
        ),
        ("n_gen", 25),
        seed=seed,
        verbose=False
    )

    solutions = [reference.flatten()]
    if optimization.X is not None:
        for x in np.atleast_2d(optimization.X):
            if measure(x)["feasible"]:
                solutions.append(x)

    candidates = []
    for alternative_index, best in enumerate(select_nondominated(solutions, measure)):
        m = measure(best)

        # Reconstruct all individual physical footprints.
        objects = [
            {
                "object_id": r["object_id"],
                "class": r["class"],
                "group_id": None,
                "footprint_coordinates_m": r["footprint_coordinates_m"]
            }
            for r in records
        ]

        for i, (cx, cy) in enumerate(m["centers"]):
            gid = f"seating_group_{i+1:04d}"

            def put(name, category, shape):
                objects.append({
                    "object_id": name,
                    "class": category,
                    "group_id": gid,
                    "footprint_coordinates_m": [
                        list(pt) for pt in shape.exterior.coords
                    ]
                })

            put(
                gid + "_table", "round_table",
                Point(cx, cy).buffer(TABLE_RADIUS, resolution=24)
            )

            for seat in range(8):
                a = 2 * math.pi * seat / 8
                chair = Point(
                    cx + CHAIR_RING * math.cos(a),
                    cy + CHAIR_RING * math.sin(a)
                ).buffer(CHAIR_RADIUS, resolution=12)
                put(gid + f"_chair_{seat+1:02d}", "chair", chair)

        shapes = [
            Polygon(o["footprint_coordinates_m"]) for o in objects
        ]
        outside = sum(not venue.covers(s) for s in shapes)
        overlaps = sum(
            shapes[i].intersection(shapes[j]).area > 1e-8
            for i in range(len(shapes))
            for j in range(i + 1, len(shapes))
        )
        valid_ids = len({
            o["object_id"] for o in objects
        }) == len(objects)

        passed = (
            len(objects) == len(records) + count * 9
            and valid_ids and outside == 0
            and overlaps == 0 and m["feasible"]
        )
        if not passed:
            fail("FULL_OBJECT_REPLAY_FAILED")

        candidates.append({'layout_id': f'pareto_{alternative_index:03d}', 'objects': objects, 'group_centers_m': {f'seating_group_{i + 1:04d}': center.tolist() for i, center in enumerate(m['centers'])}, 'objective_metrics': {'average_stage_distance_m': m['F'][0], 'reference_displacement_m': m['F'][1], 'movement_semantics': 'MINIMUM_BIPARTITE_ASSIGNMENT', 'minimum_group_clearance_m': m['minimum_clearance']}, 'constraint_results': {'object_count': len(objects), 'outside_count': outside, 'overlap_count': overlaps, 'synthetic_geometry_pass': passed}})

    return {
        "contract_id": "STAGE_E_PP1_V1",
        "run_id": f"LIVE_SEED_{seed}_GUESTS_{count*8}",
        "status": "success",
        "event_id": req["event_requirements"]["event_id"],
        "candidate_layouts": candidates,
        "permission_decisions": [{
            "scope": "INITIAL_DESIGN_NO_REVISION",
            "real_planner_approval": False
        }],
        "validation_flags": {
            "synthetic_geometry_pass": passed,
            "planner_approval_verified": False,
            "real_venue_validated": False,
            "route_connectivity_verified": False,
            "safety_certified": False
        },
        "provenance": {
            "algorithm_version": "F2B_LIVE_NSGA2_V2",
            "source_hashes": {},
            "random_seed": seed,
            "optimizer_evaluations":
                int(optimization.algorithm.evaluator.n_eval)
        },
        "adapter_status": "LIVE_CONTROLLED_SYNTHETIC_INITIAL_DESIGN_V2"
    }
