import copy
import json
import math
import time
from pathlib import Path

import numpy as np
from shapely.affinity import translate
from shapely.geometry import Polygon
from pymoo.algorithms.moo.nsga2 import NSGA2
from pymoo.core.problem import ElementwiseProblem
from pymoo.optimize import minimize

from permission_validator import load_json, validate_config
from planning_workflow_v1 import run_planning
from feasibility_engine_v1 import evaluate_move
from fixed_collision_v1 import geometry_from_rings

POC = Path(__file__).resolve().parents[1]
PROJECT = POC.parent
OUTPUT = POC / "outputs" / "multi_object_nsga2_v1.json"

IDS = (2, 3)
SEED = 42
MIN_MOVE = 1.0
POP_SIZE = 40
GENERATIONS = 20

scene = load_json(
    PROJECT / "02_GENERATED_RESEARCH_DATA"
    / "STAGE_C_OBJECTS"
    / "C3_17_RENDERER_V3_MASTER_180"
    / "SB_0005_OUTDOOR_GARDEN_L_SHAPE.json"
)
baseline_permissions = load_json(
    POC / "config" / "planner_permissions_v2.json"
)

assert validate_config(scene, baseline_permissions) == []

permissions = copy.deepcopy(baseline_permissions)
for oid in IDS:
    entry = next(
        p for p in permissions["objects"]
        if p["instance_id"] == oid
    )
    if entry["source_fixed"]:
        raise RuntimeError("Unexpected source-fixed object")
    entry.update({
        "planner_status": "movable",
        "move_allowed": True,
        "remove_allowed": False,
        "approved_by": "SYNTHETIC_TEST_PLANNER",
        "approval_note": "Two-object NSGA-II experiment only",
        "approval_scope": "SYNTHETIC_DEMO_ONLY",
        "source_conflict_reviewed": False,
    })

assert validate_config(scene, permissions) == []

client = {
    "event_type": "conference",
    "guest_count": 80,
    "required_objects": {
        "chair": 28,
        "round_table": 4,
    },
    "preference": "Clear stage visibility",
}
planner = {
    "circulation_priority": "high",
    "visibility_priority": "high",
    "utilization_priority": "medium",
    "minimum_change_priority": "high",
}

# Deterministic joint-placement baseline.
start = time.perf_counter()
baseline = run_planning(
    scene, permissions, client, planner,
    max_objects=2
)
baseline_seconds = time.perf_counter() - start

if baseline["status"] != "CONTROLLED_PLACEMENTS_FOUND":
    raise RuntimeError(
        "Baseline joint placement unavailable: "
        + baseline["status"]
    )

if [p["instance_id"] for p in baseline["placements"]] != list(IDS):
    raise RuntimeError("Unexpected baseline object IDs")

sources = {
    oid: next(
        o for o in scene["event_instances"]
        if o["instance_id"] == oid
    )
    for oid in IDS
}
source_shapes = {
    oid: [Polygon(r) for r in sources[oid]["polygons_m"]]
    for oid in IDS
}

site = geometry_from_rings(scene["site_polygon_m"])
sx1, sy1, sx2, sy2 = site.bounds

lower = []
upper = []
for oid in IDS:
    bx1, by1, bx2, by2 = geometry_from_rings(
        sources[oid]["polygons_m"]
    ).bounds
    lower.extend([sx1 - bx1, sy1 - by1])
    upper.extend([sx2 - bx2, sy2 - by2])

lower = np.array(lower, dtype=float)
upper = np.array(upper, dtype=float)


def rings_at(oid, dx, dy):
    return [
        [
            list(pt)
            for pt in translate(
                p, xoff=float(dx), yoff=float(dy)
            ).exterior.coords
        ]
        for p in source_shapes[oid]
    ]


def evaluate_joint(x):
    # Construct full proposed layout in memory.
    working = copy.deepcopy(scene)

    for index, oid in enumerate(IDS):
        dx, dy = x[2 * index:2 * index + 2]
        entry = next(
            o for o in working["event_instances"]
            if o["instance_id"] == oid
        )
        entry["polygons_m"] = rings_at(oid, dx, dy)

    checks = {}
    distances = []
    clearances = []
    constraints = []

    names = (
        "boundary",
        "fixed_and_existing_object_collision",
        "restricted_zone",
        "access_area",
        "minimum_clearance",
    )

    for index, oid in enumerate(IDS):
        dx, dy = x[2 * index:2 * index + 2]
        proposed = next(
            o for o in working["event_instances"]
            if o["instance_id"] == oid
        )["polygons_m"]

        # evaluate_move excludes the object being moved and
        # checks against ALL other FINAL-position footprints.
        result = evaluate_move(
            working, permissions, oid, proposed,
            clearance_m=0.5,
        )
        checks[str(oid)] = result

        for name in names:
            passed = result.get("checks", {}).get(
                name, {}
            ).get("passed") is True
            constraints.append(0.0 if passed else 1.0)

        dist = math.hypot(float(dx), float(dy))
        distances.append(dist)
        constraints.append(MIN_MOVE - dist)

        clear = result.get("checks", {}).get(
            "minimum_clearance", {}
        )
        nearest = clear.get(
            "nearest_distance_synthetic_m", 0.0
        )
        clearances.append(float(nearest))

    total_distance = sum(distances)
    worst_clearance = min(clearances)

    feasible = (
        all(c <= 0 for c in constraints)
        and all(
            result.get("feasible") is True
            for result in checks.values()
        )
    )

    return {
        "feasible": feasible,
        "total_relocation": total_distance,
        "minimum_clearance": worst_clearance,
        "constraints": constraints,
        "checks": checks,
        "positions": [
            {
                "instance_id": oid,
                "dx": float(x[2 * i]),
                "dy": float(x[2 * i + 1]),
                "footprints_m": rings_at(
                    oid, x[2 * i], x[2 * i + 1]
                ),
            }
            for i, oid in enumerate(IDS)
        ],
    }


baseline_x = []
for oid in IDS:
    record = next(
        p for p in baseline["placements"]
        if p["instance_id"] == oid
    )
    baseline_x.extend([record["dx"], record["dy"]])

baseline_x = np.array(baseline_x, dtype=float)
baseline_metrics = evaluate_joint(baseline_x)

if not baseline_metrics["feasible"]:
    raise RuntimeError(
        "Baseline does not pass final joint feasibility"
    )


class JointLayoutProblem(ElementwiseProblem):
    def __init__(self):
        super().__init__(
            n_var=4,
            n_obj=2,
            n_ieq_constr=12,
            xl=lower,
            xu=upper,
        )

    def _evaluate(self, x, out, *args, **kwargs):
        measured = evaluate_joint(x)
        out["F"] = [
            measured["total_relocation"],
            -measured["minimum_clearance"],
        ]
        out["G"] = measured["constraints"]


# Seed the optimizer with a real, computed baseline,
# plus local variations and broad samples.
rng = np.random.default_rng(SEED)
population = rng.uniform(
    lower, upper, size=(POP_SIZE, 4)
)
population[0] = baseline_x

for i in range(1, 14):
    perturb = rng.normal(0.0, 0.15, size=4)
    population[i] = np.clip(
        baseline_x + perturb, lower, upper
    )

algorithm = NSGA2(
    pop_size=POP_SIZE,
    sampling=population,
    eliminate_duplicates=True,
)

start = time.perf_counter()
result = minimize(
    JointLayoutProblem(),
    algorithm,
    ("n_gen", GENERATIONS),
    seed=SEED,
    verbose=False,
)
optimizer_seconds = time.perf_counter() - start

feasible = []
if result.X is not None:
    for x in np.atleast_2d(result.X):
        measured = evaluate_joint(x)
        if measured["feasible"]:
            feasible.append(measured)


def simplify(entry, label):
    return {
        "label": label,
        "total_relocation_synthetic_m": round(
            entry["total_relocation"], 5
        ),
        "minimum_clearance_synthetic_m": round(
            entry["minimum_clearance"], 5
        ),
        "positions": entry["positions"],
        "checks": entry["checks"],
    }


selected = []
if feasible:
    closest = min(
        feasible,
        key=lambda s: s["total_relocation"]
    )
    safest_gap = max(
        feasible,
        key=lambda s: s["minimum_clearance"]
    )

    dmin = min(s["total_relocation"] for s in feasible)
    dmax = max(s["total_relocation"] for s in feasible)
    cmin = min(s["minimum_clearance"] for s in feasible)
    cmax = max(s["minimum_clearance"] for s in feasible)

    balanced = min(
        feasible,
        key=lambda s: (
            (s["total_relocation"] - dmin)
            / max(dmax - dmin, 1e-9)
            + (cmax - s["minimum_clearance"])
            / max(cmax - cmin, 1e-9)
        ),
    )

    for label, entry in [
        ("minimum_change", closest),
        ("maximum_clearance", safest_gap),
        ("balanced", balanced),
    ]:
        signature = [
            coordinate
            for position in entry["positions"]
            for coordinate in (
                position["dx"], position["dy"]
            )
        ]
        if all(
            math.dist(signature, previous["signature"])
            > 0.1
            for previous in selected
        ):
            record = simplify(entry, label)
            record["signature"] = signature
            selected.append(record)

    for record in selected:
        record.pop("signature")

report = {
    "experiment": "PP1_TWO_OBJECT_NSGA2_V1",
    "scene_id": scene["id"],
    "object_ids": list(IDS),
    "seed": SEED,
    "algorithm": "pymoo.NSGA2",
    "population_size": POP_SIZE,
    "generations": GENERATIONS,
    "evaluations": int(
        result.algorithm.evaluator.n_eval
    ),
    "baseline": simplify(
        baseline_metrics, "deterministic_joint_search"
    ),
    "baseline_runtime_seconds": round(
        baseline_seconds, 4
    ),
    "optimizer_runtime_seconds": round(
        optimizer_seconds, 4
    ),
    "returned_feasible_nondominated_count": len(feasible),
    "selected_alternatives": selected,
    "requested_chairs": 28,
    "existing_chairs": 28,
    "simulated_planner_approval_only": True,
    "objectives_implemented": [
        "minimize_total_relocation",
        "maximize_worst_protected_clearance",
    ],
    "guest_capacity_optimized": False,
    "visibility_optimized": False,
    "circulation_priority_optimized": False,
    "whole_layout_safety_certified": False,
    "route_connectivity_verified": False,
    "real_world_metric_validated": False,
    "comparison_is_independent_benchmark": False,
}

if OUTPUT.exists():
    raise RuntimeError(
        "Output exists, refusing overwrite: "
        + str(OUTPUT)
    )

OUTPUT.write_text(
    json.dumps(report, indent=2),
    encoding="utf-8",
)

print("=== PP1 MULTI-OBJECT NSGA-II ===")
print("Object IDs:", IDS)
print("Baseline feasible:", baseline_metrics["feasible"])
print(
    "Baseline total relocation:",
    round(baseline_metrics["total_relocation"], 4)
)
print(
    "Baseline minimum clearance:",
    round(baseline_metrics["minimum_clearance"], 4)
)
print("Optimizer evaluations:", report["evaluations"])
print("Feasible nondominated:", len(feasible))
print("Selected alternatives:", len(selected))

for entry in selected:
    print(
        entry["label"],
        "| relocation:",
        entry["total_relocation_synthetic_m"],
        "| clearance:",
        entry["minimum_clearance_synthetic_m"],
    )

print("Report:", OUTPUT)
print("Independent benchmark: NO")
print("Full venue safety validation: NO")
print("MULTI-OBJECT NSGA-II RUN COMPLETED")