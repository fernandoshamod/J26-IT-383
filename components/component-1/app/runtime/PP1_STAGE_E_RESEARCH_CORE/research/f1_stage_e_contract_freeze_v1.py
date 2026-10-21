import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "outputs"
FREEZE = ROOT / "PP1_STAGE_E_FROZEN_V1"

SOURCE_FILES = [
    "event_objects_wedding_160_v1.json",
    "full_layout_baseline_v1.json",
    "layout_candidates_v1.json",
    "e6_feasibility_gate_v1.json",
    "e6a_feasible_initialization_v1.json",
    "e6b_full_group_nsga2_v2.json",
    "e6c_individual_geometry_replay_v1.json",
    "e7a_adaptive_reoptimization_v1.json",
    "e7a_adaptive_reoptimization_v2.json",
    "e8_research_evidence_audit_v1.json",
    "e8b_permission_gate_tests_v1.json",
    "e8d_baseline_optimizer_comparison_v1.json",
    "e8e_requirement_scenarios_v1.json",
    "e8f_reduced_requirement_adaptation_v1.json",
    "e8g_increased_requirement_adaptation_v1.json",
    "e8h_evidence_integrity_v1.json",
    "e8i_reproducibility_v2.json",
]

RESEARCH_SCRIPTS = [
    "e6b_full_group_nsga2_v2.py",
    "e7a_permission_aware_reoptimization_v2.py",
    "e8b_permission_gate_v1.py",
    "e8f_reduced_requirement_adaptation_v1.py",
    "e8g_increased_requirement_adaptation_v1.py",
    "e8i_reproducibility_v2.py",
]

def load(path):
    return json.loads(path.read_text(encoding="utf-8-sig"))

def sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

if FREEZE.exists():
    raise FileExistsError(
        "Freeze directory already exists; refusing overwrite"
    )

sources = {}
for filename in SOURCE_FILES:
    path = OUT / filename
    if not path.is_file():
        raise FileNotFoundError(path)
    sources[filename] = load(path)

for filename in RESEARCH_SCRIPTS:
    path = ROOT / "research" / filename
    if not path.is_file():
        raise FileNotFoundError(path)

full = sources["e6b_full_group_nsga2_v2.json"]
geometry = sources["e6c_individual_geometry_replay_v1.json"]
move = sources["e7a_adaptive_reoptimization_v2.json"]
reduced = sources["e8f_reduced_requirement_adaptation_v1.json"]
increased = sources["e8g_increased_requirement_adaptation_v1.json"]
repro = sources["e8i_reproducibility_v2.json"]

assert full["requested_tables"] == 20
assert full["requested_chairs"] == 160
assert full["evaluations"] == 1800
assert geometry["all_alternatives_pass"] is True

assert move["authorization_gate_integrated"] is True
assert move["evaluations"] == 1680

assert reduced["nsga2_evaluations"] == 2100
assert len(reduced["removed_group_ids"]) == 5

assert increased["evaluations"] == 2100
assert len(increased["added_group_ids"]) == 5

assert repro["all_replays_match"] is True
assert len(repro["results"]) == 4
assert all(
    item["result_match_within_tolerance"]
    for item in repro["results"]
)

# Target contract: specifications for the future adapter.
# This is not a claim that existing optimizers already
# accept or return this exact unified structure.
contract = {
    "contract_id": "STAGE_E_PP1_V1",
    "contract_status": "SPECIFIED_NOT_YET_INTEGRATED",
    "units": "synthetic_metres_for_current_experiments",
    "input": {
        "venue_twin": {
            "venue_id": "string",
            "source_type": "synthetic|verified_real",
            "boundary_polygon_m": "array_of_xy_pairs",
            "fixed_obstacles": "array_of_object_records",
            "verification_status": "string"
        },
        "event_requirements": {
            "event_id": "string",
            "event_type": "string",
            "guest_count": "positive_integer",
            "furniture_requirements": "object_count_map"
        },
        "planner_context": {
            "priorities": "objective_preferences",
            "permissions": "explicit_permission_records",
            "approved_reference_layout": "optional_layout",
            "review_status": "string"
        },
        "optimization_request": {
            "mode": "initial_design|adaptive_revision",
            "algorithm": "NSGA2",
            "experimental_clearance_m": "positive_number",
            "seed": "integer"
        }
    },
    "output": {
        "run_id": "string",
        "status": "success|infeasible|denied|error",
        "event_id": "string",
        "candidate_layouts": [
            {
                "layout_id": "string",
                "objects": "stable_id_and_polygon_records",
                "group_centers_m": "group_id_to_xy_map",
                "objective_metrics": "numeric_metric_map",
                "constraint_results": "validation_results"
            }
        ],
        "permission_decisions": "decision_records",
        "validation_flags": {
            "synthetic_geometry_pass": "boolean",
            "planner_approval_verified": "boolean",
            "real_venue_validated": "boolean",
            "route_connectivity_verified": "boolean",
            "safety_certified": "boolean"
        },
        "provenance": {
            "algorithm_version": "string",
            "source_hashes": "sha256_map",
            "random_seed": "integer"
        }
    },
    "requirements": [
        "Deny unauthorized adaptive requests before optimization",
        "Preserve locked object identities and positions",
        "Never treat simulated permission as real approval",
        "Report unplaced objects and infeasibility explicitly",
        "Do not report route safety from collision checks",
        "Do not silently substitute synthetic venue geometry"
    ]
}

manifest = {
    "freeze_id": "PP1_STAGE_E_FROZEN_V1",
    "created_utc": datetime.now(timezone.utc).isoformat(),
    "research_status": "CONTROLLED_PP1_PROTOTYPE_VERIFIED",
    "full_research_complete": False,
    "evidence_files": {
        name: sha256(OUT / name)
        for name in SOURCE_FILES
    },
    "research_scripts": {
        name: sha256(ROOT / "research" / name)
        for name in RESEARCH_SCRIPTS
    },
    "reproducibility": {
        "experiments": 4,
        "passed": 4,
        "same_environment": True,
        "cross_machine": False
    },
    "verified_scope": {
        "venue_source": "CONTROLLED_SYNTHETIC",
        "original_guest_count": 160,
        "full_layout_objects": 183,
        "reduced_layout_objects": 138,
        "increased_layout_objects": 228,
        "optimizer": "NSGA2",
        "permission_type": "SIMULATED"
    },
    "limitations": [
        "Real venue geometry not approved",
        "Route connectivity not independently verified",
        "No regulatory safety certification",
        "Historical S-GCN not trained",
        "Weather context not integrated",
        "No independent multi-venue generalization study",
        "Unified research adapter not yet implemented",
        "Frontend and backend not yet integrated"
    ]
}

FREEZE.mkdir(parents=False)

contract_path = FREEZE / "STAGE_E_CONTRACT_V1.json"
manifest_path = FREEZE / "STAGE_E_FREEZE_MANIFEST_V1.json"

contract_path.write_text(
    json.dumps(contract, indent=2), encoding="utf-8"
)
manifest_path.write_text(
    json.dumps(manifest, indent=2), encoding="utf-8"
)

# Re-read and independently verify frozen documents.
assert load(contract_path)["contract_id"] == "STAGE_E_PP1_V1"
assert len(load(manifest_path)["evidence_files"]) == 17
assert len(load(manifest_path)["research_scripts"]) == 6

for name, recorded_hash in manifest["evidence_files"].items():
    assert sha256(OUT / name) == recorded_hash

for name, recorded_hash in manifest["research_scripts"].items():
    assert sha256(ROOT / "research" / name) == recorded_hash

print("=== STAGE E PP1 F1 FREEZE ===")
print("Evidence JSON files:", len(SOURCE_FILES))
print("Research scripts:", len(RESEARCH_SCRIPTS))
print("Reproduced optimizer experiments: 4/4")
print("Source SHA-256 verification: PASS")
print("Target input/output contract: CREATED")
print("Unified adapter implemented: NO")
print("Real-world validation: NO")
print("Full research completed: NO")
print("Freeze directory:", FREEZE)
print("F1 FREEZE MANIFEST PASS")