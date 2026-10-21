import hashlib
import json
import math
from pathlib import Path

import numpy as np
from shapely.geometry import Polygon

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "outputs"
DEST = OUT / "e8h_evidence_integrity_v1.json"

names = [
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
]

records = {}
hashes = {}

for name in names:
    path = OUT / name
    if not path.is_file():
        raise FileNotFoundError(path)

    raw = path.read_bytes()
    records[name] = json.loads(raw)
    hashes[name] = hashlib.sha256(raw).hexdigest()

opt = records["e6b_full_group_nsga2_v2.json"]
replay = records["e6c_individual_geometry_replay_v1.json"]
adaptive = records["e7a_adaptive_reoptimization_v2.json"]
permissions = records["e8b_permission_gate_tests_v1.json"]
reduction = records["e8f_reduced_requirement_adaptation_v1.json"]
addition = records["e8g_increased_requirement_adaptation_v1.json"]
base = records["full_layout_baseline_v1.json"]

assert replay["all_alternatives_pass"] is True
assert opt["evaluations"] == 1800
assert adaptive["authorization_gate_integrated"] is True
assert adaptive["authorization_result"] == "AUTHORIZED_SYNTHETIC_MOVE"
assert permissions["passed"] == permissions["total"] == 10

assert reduction["guests_before"] == 160
assert reduction["guests_after"] == 120
assert len(reduction["removed_group_ids"]) == 5
assert len(reduction["movable_group_ids"]) == 2
assert len(reduction["locked_group_ids"]) == 13
assert reduction["nsga2_evaluations"] == 2100

assert addition["guests_before"] == 160
assert addition["guests_after"] == 200
assert len(addition["locked_group_ids"]) == 20
assert len(addition["added_group_ids"]) == 5
assert addition["evaluations"] == 2100
assert addition["simulated_addition_permission_enforced"] is True

for result in [reduction["baseline"]] + reduction["selected"]:
    assert result["objects"] == 138
    assert result["geometry_pass"] is True
    assert result["locked_unchanged"] is True
    assert result["outside"] == 0
    assert result["overlaps"] == 0

for result in [addition["reference"]] + addition["selected"]:
    assert result["objects"] == 228
    assert result["geometry_pass"] is True
    assert result["locked_unchanged"] is True
    assert result["outside"] == 0
    assert result["overlaps"] == 0

# Independently re-evaluate the recorded average stage
# proximity from saved table centres for E8G.
fixed_stage = next(
    o for o in base["objects"] if o["class"] == "stage"
)
stage = Polygon(fixed_stage["footprint_coordinates_m"])
stage_xy = np.array([stage.centroid.x, stage.centroid.y])

existing = np.asarray(
    opt["baseline"]["table_centers"], dtype=float
)
assert existing.shape == (20, 2)

def recheck_stage_distance(record):
    new = np.array([
        record["new_groups_by_id"][gid]
        for gid in addition["added_group_ids"]
    ], dtype=float)
    assert new.shape == (5, 2)
    all_centres = np.vstack([existing, new])
    measured = float(
        np.linalg.norm(all_centres-stage_xy, axis=1).mean()
    )
    assert math.isclose(
        measured, record["stage_distance"],
        abs_tol=0.00001, rel_tol=0
    )
    return round(measured, 6)

stage_rechecks = {}
for record in [addition["reference"]] + addition["selected"]:
    stage_rechecks[record["label"]] = recheck_stage_distance(record)

report = {
    "experiment": "PP1_E8H_EVIDENCE_INTEGRITY_V1",
    "scope": "CONTROLLED_SYNTHETIC_STAGE_E",
    "files_verified": len(hashes),
    "sha256_manifest": hashes,
    "permission_unit_tests_pass": 10,
    "full_layout_nsga2_evaluations": opt["evaluations"],
    "reduction_nsga2_evaluations": reduction["nsga2_evaluations"],
    "addition_nsga2_evaluations": addition["evaluations"],
    "reduction_object_count": 138,
    "addition_object_count": 228,
    "addition_stage_distance_independent_rechecks": stage_rechecks,
    "record_consistency_checks_pass": True,
    "denied_run_no_optimizer_verified_by_terminal": True,
    "implemented": [
        "exact controlled event object counts",
        "synthetic geometry constrained placement",
        "full seating-group NSGA-II",
        "individual furniture collision replay",
        "single and two-group adaptive NSGA-II",
        "simulated permission-gated move/remove/add",
        "120/160/200 guest controlled scenarios",
    ],
    "not_yet_demonstrated": [
        "historical preference learning with S-GCN",
        "real venue spatial twin geometry approval",
        "weather-context optimization",
        "real authenticated planner approval",
        "safe routes and regulatory clearance",
        "multi-venue independent evaluation",
        "generalized event-type layout objectives",
        "end-to-end research pipeline integration",
    ],
    "full_deterministic_rerun_performed": False,
    "real_venue_validated": False,
    "safety_certified": False,
}

if DEST.exists():
    raise FileExistsError("Evidence manifest exists; refusing overwrite")

DEST.write_text(
    json.dumps(report, indent=2), encoding="utf-8"
)

print("=== E8H EVIDENCE INTEGRITY ===")
print("Evidence files hashed:", len(hashes))
print("Full-layout evaluations:", opt["evaluations"])
print("Reduction evaluations:", reduction["nsga2_evaluations"])
print("Addition evaluations:", addition["evaluations"])
print("Permission unit tests: 10/10")
print("Reduction objects: 138")
print("Addition objects: 228")
print("E8G stage distances independently recalculated:")
for label, value in stage_rechecks.items():
    print(" ", label, ":", value)
print("Record consistency: PASS")
print("Full deterministic rerun: NOT DONE")
print("Real venue validation: NOT DONE")
print("Output:", DEST)
print("E8H INTEGRITY AUDIT COMPLETE")