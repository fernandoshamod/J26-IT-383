import json
import math
import sys
from pathlib import Path

import numpy as np
from shapely.geometry import Point, Polygon
from pymoo.core.problem import ElementwiseProblem
from pymoo.algorithms.moo.nsga2 import NSGA2
from pymoo.optimize import minimize

from e8b_permission_gate_v1 import authorize_revision
from engine_support import validate_metric as validate_initial, select_nondominated, limits

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "outputs"
RADIUS = 1.72

def load(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))

def polygon_coords(p):
    return [list(map(float, xy)) for xy in p.exterior.coords]

def build_objects(centers, fixed):
    items = [
        {
            "object_id": o["object_id"],
            "class": o["class"],
            "group_id": None,
            "footprint_coordinates_m": o["footprint_coordinates_m"],
        }
        for o in fixed
    ]
    for gid, (cx, cy) in sorted(centers.items()):
        items.append({
            "object_id": gid + "_table",
            "class": "round_table",
            "group_id": gid,
            "footprint_coordinates_m":
                polygon_coords(Point(cx, cy).buffer(0.8, resolution=24)),
        })
        for k in range(8):
            angle = 2 * math.pi * k / 8
            chair = Point(
                cx + 1.45 * math.cos(angle),
                cy + 1.45 * math.sin(angle),
            ).buffer(0.27, resolution=12)
            items.append({
                "object_id": gid + f"_chair_{k+1:02d}",
                "class": "chair",
                "group_id": gid,
                "footprint_coordinates_m": polygon_coords(chair),
            })
    return items

def replay(items, venue, centers, obstacles, clearance):
    polygons = [Polygon(o["footprint_coordinates_m"]) for o in items]
    outside = sum(not venue.covers(p) for p in polygons)
    overlaps = sum(
        polygons[i].intersection(polygons[j]).area > 1e-8
        for i in range(len(polygons))
        for j in range(i + 1, len(polygons))
    )
    envelopes = [
        Point(*xy).buffer(RADIUS, resolution=32)
        for xy in centers.values()
    ]
    failures = sum(
        envelopes[i].distance(envelopes[j]) < clearance - 1e-6
        for i in range(len(envelopes))
        for j in range(i + 1, len(envelopes))
    )
    failures += sum(
        e.distance(o) < clearance - 1e-6
        for e in envelopes for o in obstacles
    )
    return {
        "object_count": len(items),
        "outside_count": outside,
        "overlap_count": overlaps,
        "clearance_failures": failures,
        "synthetic_geometry_pass":
            outside == 0 and overlaps == 0 and failures == 0,
    }

def execute(req):
    if req.get("contract_id") != "STAGE_E_PP1_V1":
        raise ValueError("INVALID_CONTRACT")
    if req.get("mode") != "adaptive_revision":
        raise ValueError("UNSUPPORTED_ADAPTIVE_MODE")

    # Use the already tested F2B geometry/input validation,
    # without calling its initial-design optimizer.
    base_request = dict(req)
    base_request["mode"] = "initial_design"
    venue, obstacles, fixed, count, clearance, seed = (
        validate_initial(base_request)
    )

    ref = req.get("approved_reference_layout", {})
    groups = ref.get("group_centers_m")
    if not isinstance(groups, dict) or len(groups) != count:
        raise ValueError("INVALID_REFERENCE_GROUPS")

    ids = [f"seating_group_{i:04d}" for i in range(1, count + 1)]
    if set(groups) != set(ids):
        raise ValueError("UNEXPECTED_GROUP_IDS")

    original = {}
    for gid in ids:
        xy = groups[gid]
        if (
            not isinstance(xy, list) or len(xy) != 2
            or any(
                type(v) not in (int, float) or not math.isfinite(v)
                for v in xy
            )
        ):
            raise ValueError("INVALID_REFERENCE_COORDINATES")
        original[gid] = [float(xy[0]), float(xy[1])]

    # Refuse a reference that fails the same experimental
    # geometric gate used for new layouts.
    original_items = build_objects(original, fixed)
    original_check = replay(
        original_items, venue, original, obstacles, clearance
    )
    if (
        len(original_items) != len(fixed) + count * 9
        or not original_check["synthetic_geometry_pass"]
    ):
        raise ValueError("REFERENCE_GEOMETRY_INVALID")

    revision = req.get("revision_request", {})
    move_id = revision.get("group_id")
    if move_id not in original or revision.get("action") != "move":
        raise ValueError("INVALID_REVISION_TARGET")

    permission = req.get("planner_context", {}).get("permissions", {})
    allowed, reason = authorize_revision(revision, permission)

    if not allowed:
        return {
            "contract_id": "STAGE_E_PP1_V1",
            "status": "denied",
            "event_id": req["event_requirements"]["event_id"],
            "candidate_layouts": [],
            "permission_decisions": [{
                "group_id": move_id,
                "allowed": False,
                "reason": reason,
            }],
            "validation_flags": {
                "synthetic_geometry_pass": False,
                "planner_approval_verified": False,
                "real_venue_validated": False,
                "route_connectivity_verified": False,
                "safety_certified": False,
            },
            "provenance": {
                "algorithm_version": "F2D_ADAPTIVE_V1",
                "optimizer_evaluations": 0,
                "random_seed": seed,
            },
        }

    stage = next(
        p for o, p in zip(fixed, obstacles)
        if o["class"] == "stage"
    )
    stage_xy = np.array([stage.centroid.x, stage.centroid.y])
    start = np.array(original[move_id])
    locked = {
        gid: xy for gid, xy in original.items()
        if gid != move_id
    }
    protected = obstacles + [
        Point(*xy).buffer(RADIUS, resolution=32)
        for xy in locked.values()
    ]
    xmin, ymin, xmax, ymax = venue.bounds

    def measure(x):
        xy = np.asarray(x, dtype=float)
        shape = Point(*xy).buffer(RADIUS, resolution=32)
        gaps = [shape.distance(p) for p in protected]
        constraints = [
            float(shape.difference(venue).area),
            *[clearance - d for d in gaps],
        ]
        all_mean = (sum(math.dist(v,stage_xy) for k,v in original.items() if k != move_id) + float(np.linalg.norm(xy-stage_xy))) / count
        constraints.extend(limits(req,all_mean,float(np.linalg.norm(xy-start))))
        return {
            "F": [
                float(np.linalg.norm(xy - stage_xy)),
                float(np.linalg.norm(xy - start)),
            ],
            "G": constraints,
            "clearance": min(gaps),
            "feasible": all(g <= 1e-7 for g in constraints),
        }

    if any(g > 1e-7 for g in measure(start)["G"][:len(protected)+1]):
        raise ValueError("REFERENCE_PERMISSION_GEOMETRY_INVALID")

    class Problem(ElementwiseProblem):
        def __init__(self):
            super().__init__(
                n_var=2, n_obj=2,
                n_ieq_constr=len(protected) + 1 + len(limits(req,0.0,0.0)),
                xl=np.array([xmin + RADIUS, ymin + RADIUS]),
                xu=np.array([xmax - RADIUS, ymax - RADIUS]),
            )

        def _evaluate(self, x, out, *args, **kwargs):
            m = measure(x)
            out["F"], out["G"] = m["F"], m["G"]

    problem = Problem()
    rng = np.random.default_rng(seed)
    samples = rng.uniform(problem.xl, problem.xu, (48, 2))
    samples[0] = start
    for i in range(1, 12):
        samples[i] = np.clip(
            start + rng.normal(0, 0.5, 2),
            problem.xl, problem.xu
        )

    result = minimize(
        problem,
        NSGA2(
            pop_size=48, sampling=samples,
            eliminate_duplicates=True,
        ),
        ("n_gen", 35),
        seed=seed,
        verbose=False,
    )

    feasible = [(start, measure(start))]
    if result.X is not None:
        feasible.extend(
            (x, measure(x))
            for x in np.atleast_2d(result.X)
            if measure(x)["feasible"]
        )

    selected = select_nondominated([xy for xy,m in feasible], measure)
    choices = [(f'pareto_{i:03d}', (xy, measure(xy))) for i,xy in enumerate(selected)]
    candidates = []
    for label, (xy, metrics) in choices:
        centers = {k: list(v) for k, v in original.items()}
        centers[move_id] = [float(xy[0]), float(xy[1])]
        items = build_objects(centers, fixed)
        check = replay(items, venue, centers, obstacles, clearance)
        if len(items) != len(fixed) + count * 9 or not check["synthetic_geometry_pass"]:
            raise RuntimeError("ADAPTIVE_FURNITURE_REPLAY_FAILED")
        if any(centers[k] != original[k] for k in locked):
            raise RuntimeError("LOCKED_GROUP_MOVED")
        candidates.append({
            "layout_id": label,
            "objects": items,
            "group_centers_m": centers,
            "objective_metrics": {
                "stage_distance_m": metrics["F"][0],
                "identity_based_relocation_m": metrics["F"][1],
                "minimum_protected_clearance_m":
                    metrics["clearance"],
            },
            "constraint_results": check,
        })

    return {
        "contract_id": "STAGE_E_PP1_V1",
        "run_id": f"F2D_{seed}_{move_id}",
        "status": "success",
        "event_id": req["event_requirements"]["event_id"],
        "candidate_layouts": candidates,
        "permission_decisions": [{
            "group_id": move_id,
            "allowed": True,
            "reason": reason,
            "scope": "SYNTHETIC_DEMO_ONLY",
        }],
        "validation_flags": {
            "synthetic_geometry_pass": True,
            "planner_approval_verified": False,
            "real_venue_validated": False,
            "route_connectivity_verified": False,
            "safety_certified": False,
        },
        "provenance": {
            "algorithm_version": "F2D_ADAPTIVE_V1",
            "optimizer_evaluations":
                int(result.algorithm.evaluator.n_eval),
            "random_seed": seed,
            "simulated_permission_only": True,
        },
    }
