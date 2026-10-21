import copy
import json
import math
import sys
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
from shapely.affinity import translate
from shapely.geometry import Polygon
from pymoo.algorithms.moo.nsga2 import NSGA2
from pymoo.core.problem import ElementwiseProblem
from pymoo.optimize import minimize

from permission_validator import load_json, validate_config
from feasibility_engine_v1 import (
    evaluate_move,
    build_protected_geometry,
)
from fixed_collision_v1 import geometry_from_rings

POC = Path(__file__).resolve().parents[1]
PROJECT = POC.parent
SOURCE = (
    PROJECT / "02_GENERATED_RESEARCH_DATA"
    / "STAGE_C_OBJECTS"
    / "C3_17_RENDERER_V3_MASTER_180"
    / "SB_0005_OUTDOOR_GARDEN_L_SHAPE.json"
)
PERMISSIONS = POC / "config" / "planner_permissions_v2.json"
OUTPUT = POC / "outputs" / "nsga2_round_table_v1.json"

OBJECT_ID = 2
MIN_CHANGE_M = 1.0       # Synthetic revision requirement
MIN_CLEARANCE_M = 0.5    # Illustrative; NOT a safety standard
RANDOM_SEED = 42

scene = load_json(SOURCE)
base_permissions = load_json(PERMISSIONS)
assert validate_config(scene, base_permissions) == []

obj = next(
    x for x in scene["event_instances"]
    if x["instance_id"] == OBJECT_ID
)
assert obj["class"] == "round_table"
assert obj["fixed"] is False

# A separate temporary planner approval; nothing is saved.
permissions = copy.deepcopy(base_permissions)
entry = next(
    x for x in permissions["objects"]
    if x["instance_id"] == OBJECT_ID
)
entry.update({
    "planner_status": "movable",
    "move_allowed": True,
    "remove_allowed": False,
    "approved_by": "SYNTHETIC_TEST_PLANNER",
    "approval_note": "Controlled synthetic optimization only",
    "approval_scope": "SYNTHETIC_DEMO_ONLY",
    "source_conflict_reviewed": False,
})
assert validate_config(scene, permissions) == []

original_polygons = [
    Polygon(ring) for ring in obj["polygons_m"]
]
original_shape = geometry_from_rings(obj["polygons_m"])
site = geometry_from_rings(scene["site_polygon_m"])
protected = build_protected_geometry(scene, OBJECT_ID)

sx1, sy1, sx2, sy2 = site.bounds
ox1, oy1, ox2, oy2 = original_shape.bounds

xl = np.array([sx1 - ox1, sy1 - oy1], dtype=float)
xu = np.array([sx2 - ox2, sy2 - oy2], dtype=float)

if np.any(xl >= xu):
    raise RuntimeError("Invalid translation search bounds")


def shifted_rings(dx, dy):
    return [
        [list(p) for p in translate(
            poly, xoff=float(dx), yoff=float(dy)
        ).exterior.coords]
        for poly in original_polygons
    ]


def measure(dx, dy):
    rings = shifted_rings(dx, dy)
    outcome = evaluate_move(
        scene, permissions, OBJECT_ID, rings,
        clearance_m=MIN_CLEARANCE_M,
    )
    distance = math.hypot(float(dx), float(dy))

    clearance = outcome.get("checks", {}).get(
        "minimum_clearance", {}
    )
    nearest = clearance.get(
        "nearest_distance_synthetic_m", 0.0
    )

    return outcome, distance, float(nearest)


class LayoutProblem(ElementwiseProblem):
    def __init__(self):
        # Five spatial checks + mandatory minimum displacement.
        super().__init__(
            n_var=2, n_obj=2, n_ieq_constr=6,
            xl=xl, xu=xu,
        )

    def _evaluate(self, x, out, *args, **kwargs):
        outcome, distance, nearest = measure(x[0], x[1])
        checks = outcome.get("checks", {})

        keys = [
            "boundary",
            "fixed_and_existing_object_collision",
            "restricted_zone",
            "access_area",
            "minimum_clearance",
        ]
        violations = [
            0.0 if checks.get(k, {}).get("passed") is True
            else 1.0
            for k in keys
        ]
        violations.append(MIN_CHANGE_M - distance)

        # pymoo minimizes both objectives.
        out["F"] = [distance, -nearest]
        out["G"] = violations


# Compute feasible initialization points from the scene,
# rather than prewriting three "optimized" layouts.
seeds = []
for x in np.arange(sx1, sx2 + 0.01, 1.0):
    for y in np.arange(sy1, sy2 + 0.01, 1.0):
        dx, dy = float(x - ox1), float(y - oy1)

        if math.hypot(dx, dy) < MIN_CHANGE_M:
            continue

        outcome, _, _ = measure(dx, dy)
        if outcome["feasible"]:
            seeds.append([dx, dy])
        if len(seeds) >= 12:
            break
    if len(seeds) >= 12:
        break

if not seeds:
    print("NO FEASIBLE INITIALIZATION FOUND")
    print("Optimization not executed.")
    sys.exit(1)

rng = np.random.default_rng(RANDOM_SEED)
population = rng.uniform(xl, xu, size=(40, 2))
population[:len(seeds)] = np.array(seeds)

problem = LayoutProblem()
algorithm = NSGA2(
    pop_size=40,
    sampling=population,
    eliminate_duplicates=True,
)

result = minimize(
    problem,
    algorithm,
    ("n_gen", 30),
    seed=RANDOM_SEED,
    verbose=False,
)

solutions = []
if result.X is not None:
    xs = np.atleast_2d(result.X)
    for x in xs:
        outcome, distance, nearest = measure(x[0], x[1])

        if (
            outcome["feasible"]
            and distance + 1e-8 >= MIN_CHANGE_M
        ):
            solutions.append({
                "dx": round(float(x[0]), 5),
                "dy": round(float(x[1]), 5),
                "relocation_synthetic_m": round(distance, 5),
                "nearest_protected_synthetic_m": round(
                    nearest, 5
                ),
                "footprints_m": shifted_rings(x[0], x[1]),
                "checks": outcome["checks"],
            })

# Select up to three *different* outcomes from the
# returned feasible nondominated solution set.
chosen = []
if solutions:
    minimum_change = min(
        solutions, key=lambda v: v["relocation_synthetic_m"]
    )
    maximum_clearance = max(
        solutions,
        key=lambda v: v["nearest_protected_synthetic_m"]
    )

    dvals = [
        s["relocation_synthetic_m"] for s in solutions
    ]
    cvals = [
        s["nearest_protected_synthetic_m"] for s in solutions
    ]

    dmin, dmax = min(dvals), max(dvals)
    cmin, cmax = min(cvals), max(cvals)

    def balanced_score(s):
        normalized_distance = (
            (s["relocation_synthetic_m"] - dmin)
            / max(dmax - dmin, 1e-9)
        )
        normalized_clearance_loss = (
            (cmax - s["nearest_protected_synthetic_m"])
            / max(cmax - cmin, 1e-9)
        )
        return normalized_distance + normalized_clearance_loss

    balanced = min(solutions, key=balanced_score)

    for label, solution in [
        ("minimum_change", minimum_change),
        ("maximum_clearance", maximum_clearance),
        ("balanced", balanced),
    ]:
        if all(
            math.hypot(
                solution["dx"] - prev["dx"],
                solution["dy"] - prev["dy"]
            ) > 0.05
            for prev in chosen
        ):
            record = dict(solution)
            record["selection_label"] = label
            chosen.append(record)

report = {
    "experiment": "PP1_CONTROLLED_SINGLE_OBJECT_NSGA2_V1",
    "generated_utc": datetime.now(timezone.utc).isoformat(),
    "scene_id": scene["id"],
    "object_id": OBJECT_ID,
    "object_class": obj["class"],
    "seed": RANDOM_SEED,
    "algorithm": "pymoo.NSGA2",
    "population": 40,
    "generations": 30,
    "evaluations": int(result.algorithm.evaluator.n_eval),
    "initial_feasible_seeds": len(seeds),
    "mandatory_relocation_synthetic_m": MIN_CHANGE_M,
    "demo_clearance_synthetic_m": MIN_CLEARANCE_M,
    "objectives": [
        "minimize_relocation_distance",
        "maximize_nearest_protected_footprint_distance",
    ],
    "returned_feasible_nondominated_count": len(solutions),
    "selected_alternatives": chosen,
    "route_topology_verified": False,
    "real_world_safety_approved": False,
    "whole_layout_certified": False,
    "synthetic_planner_permission_only": True,
}

if OUTPUT.exists():
    raise RuntimeError(
        "Output already exists; refusing to overwrite: "
        + str(OUTPUT)
    )

OUTPUT.write_text(
    json.dumps(report, indent=2),
    encoding="utf-8",
)

print("=== PP1 CONSTRAINED NSGA-II RESULT ===")
print("Object:", OBJECT_ID, obj["class"])
print("Evaluations:", report["evaluations"])
print("Initial feasible seeds:", len(seeds))
print("Feasible nondominated results:", len(solutions))
print("Selected alternatives:", len(chosen))

for index, item in enumerate(chosen, 1):
    print(
        f"{index}. {item['selection_label']}: "
        f"distance={item['relocation_synthetic_m']}, "
        f"clearance={item['nearest_protected_synthetic_m']}"
    )

print("Saved report:", OUTPUT)
print("Real-world safety validation: NO")
print("Whole-layout certification: NO")