import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "outputs"
DEST = OUTPUT / "e8d_baseline_optimizer_comparison_v1.json"

def load(filename):
    return json.loads(
        (OUTPUT / filename).read_text(encoding="utf-8")
    )

opt = load("e6b_full_group_nsga2_v2.json")
replay = load("e6c_individual_geometry_replay_v1.json")
adaptive = load("e7a_adaptive_reoptimization_v2.json")
gate = load("e8b_permission_gate_tests_v1.json")

baseline = opt["baseline"]
alternatives = opt["selected"]

def metric(record, name):
    return float(record[name])

baseline_stage = metric(
    baseline, "average_stage_proximity_synthetic_m"
)
baseline_clearance = metric(
    baseline, "minimum_clearance_synthetic_m"
)

comparisons = []

for alt in alternatives:
    stage_distance = metric(
        alt, "average_stage_proximity_synthetic_m"
    )
    clearance = metric(
        alt, "minimum_clearance_synthetic_m"
    )
    movement = metric(
        alt, "total_displacement_synthetic_m"
    )

    improvement = baseline_stage - stage_distance
    improvement_percent = (
        100 * improvement / baseline_stage
        if baseline_stage > 0 else None
    )

    comparisons.append({
        "alternative": alt["label"],
        "stage_distance": stage_distance,
        "stage_distance_improvement_m": round(
            improvement, 6
        ),
        "stage_distance_improvement_percent": (
            round(improvement_percent, 4)
            if improvement_percent is not None else None
        ),
        "minimum_clearance": clearance,
        "clearance_change_m": round(
            clearance - baseline_clearance, 6
        ),
        "assignment_based_relocation_m": movement,
        "geometry_pass": alt["geometry_constraints_pass"],
    })

assert replay["all_alternatives_pass"]
assert all(x["geometry_pass"] for x in comparisons)
assert gate["authorization_gate_unit_tests_pass"]
assert adaptive["authorization_gate_integrated"]
assert adaptive["authorization_result"] == \
    "AUTHORIZED_SYNTHETIC_MOVE"

reference = adaptive["reference"]
adaptive_results = []

for item in adaptive["selected"]:
    adaptive_results.append({
        "alternative": item["label"],
        "stage_distance_improvement_m": round(
            reference["stage_distance_synthetic_m"]
            - item["stage_distance_synthetic_m"], 6
        ),
        "relocation_m": item["movement_synthetic_m"],
        "unchanged_groups": item["unchanged_group_count"],
        "geometry_pass": item["geometry_pass"],
    })

report = {
    "experiment": "PP1_E8D_COMPARATIVE_EVALUATION_V1",
    "scope": "SINGLE_CONTROLLED_SYNTHETIC_SCENARIO",
    "reference": {
        "stage_distance": baseline_stage,
        "minimum_clearance": baseline_clearance,
    },
    "optimizer_comparison": comparisons,
    "adaptive_comparison": adaptive_results,
    "optimizer_evaluations": opt["evaluations"],
    "adaptive_evaluations": adaptive["evaluations"],
    "individual_geometry_replay_pass": True,
    "permission_gate_unit_tests_pass": True,
    "optimizer_permission_gate_integrated": True,
    "real_planner_approved": False,
    "independent_benchmark": False,
    "multi_scenario_statistical_significance": False,
    "real_venue_validated": False,
    "safety_certified": False,
}

if DEST.exists():
    raise FileExistsError("Report exists; refusing overwrite")

DEST.write_text(
    json.dumps(report, indent=2),
    encoding="utf-8"
)

print("=== E8D BASELINE VS OPTIMIZER ===")
print("Reference stage distance:", baseline_stage)
print("Reference clearance:", baseline_clearance)

for x in comparisons:
    print(
        x["alternative"],
        "| stage improvement:",
        x["stage_distance_improvement_m"],
        "| improvement %:",
        x["stage_distance_improvement_percent"],
        "| clearance change:",
        x["clearance_change_m"],
        "| relocation:",
        x["assignment_based_relocation_m"]
    )

print("=== ADAPTIVE REVISION COMPARISON ===")
for x in adaptive_results:
    print(
        x["alternative"],
        "| stage improvement:",
        x["stage_distance_improvement_m"],
        "| relocation:", x["relocation_m"],
        "| locked unchanged:", x["unchanged_groups"]
    )

print("Independent benchmark: NO")
print("Multi-scenario evaluation: NOT DONE")
print("Real-world validation: NO")
print("Output:", DEST)
print("E8D COMPARISON COMPLETE")