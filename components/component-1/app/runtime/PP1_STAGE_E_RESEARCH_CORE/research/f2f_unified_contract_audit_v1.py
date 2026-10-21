import copy
import json
import math
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "outputs"
DEST = OUT / "f2f_unified_contract_audit_v1.json"

sys.path.insert(0, str(ROOT / "research"))
from f2e_unified_dispatcher_v1 import dispatch

def load(name):
    return json.loads(
        (OUT / name).read_text(encoding="utf-8")
    )

initial_request = load("f2b_test_request_v1.json")
adaptive_request = load("f2d_approved_request_v1.json")

initial = load("f2e_initial_result_v1.json")
denied = load("f2e_denied_result_v1.json")
adaptive = load("f2e_adaptive_result_v1.json")

checks = []

def check(name, condition):
    passed = bool(condition)
    checks.append({"name": name, "passed": passed})
    print(name, "|", "PASS" if passed else "FAIL")
    if not passed:
        raise AssertionError(name)

print("=== F2F UNIFIED CONTRACT AUDIT ===")

check(
    "contract_version",
    all(
        x["contract_id"] == "STAGE_E_PP1_V1"
        for x in (initial, denied, adaptive)
    )
)

check(
    "initial_success",
    initial["status"] == "success"
    and len(initial["candidate_layouts"]) == 1
    and initial["provenance"]["optimizer_evaluations"] == 1200
)

check(
    "denied_no_optimizer",
    denied["status"] == "denied"
    and denied["candidate_layouts"] == []
    and denied["provenance"]["optimizer_evaluations"] == 0
)

check(
    "adaptive_success",
    adaptive["status"] == "success"
    and len(adaptive["candidate_layouts"]) == 2
    and adaptive["provenance"]["optimizer_evaluations"] == 1680
)

reference = adaptive_request[
    "approved_reference_layout"
]["group_centers_m"]

authorized = adaptive_request[
    "revision_request"
]["group_id"]

check(
    "reference_20_unique_groups",
    len(reference) == 20
    and len(set(reference.keys())) == 20
)

def identities_valid(layout):
    objects = layout["objects"]
    ids = [x["object_id"] for x in objects]
    return (
        len(objects) == 183
        and len(ids) == len(set(ids))
        and len(layout["group_centers_m"]) == 20
    )

check(
    "all_successful_furniture_id_counts",
    all(
        identities_valid(item)
        for response in (initial, adaptive)
        for item in response["candidate_layouts"]
    )
)

def locked_preserved(layout):
    centers = layout["group_centers_m"]
    return all(
        centers[gid] == original_xy
        for gid, original_xy in reference.items()
        if gid != authorized
    )

check(
    "nineteen_locked_groups_preserved",
    all(
        locked_preserved(layout)
        for layout in adaptive["candidate_layouts"]
    )
)

check(
    "all_geometry_reports_pass",
    all(
        layout["constraint_results"]["synthetic_geometry_pass"]
        for response in (initial, adaptive)
        for layout in response["candidate_layouts"]
    )
)

check(
    "no_real_world_approval_claim",
    all(
        not response["validation_flags"]["planner_approval_verified"]
        and not response["validation_flags"]["real_venue_validated"]
        and not response["validation_flags"]["route_connectivity_verified"]
        and not response["validation_flags"]["safety_certified"]
        for response in (initial, denied, adaptive)
    )
)

def expected_rejection(name, request, code):
    try:
        dispatch(request)
    except ValueError as error:
        check(name, str(error) == code)
    else:
        check(name, False)

bad_contract = copy.deepcopy(initial_request)
bad_contract["contract_id"] = "UNKNOWN"

expected_rejection(
    "invalid_contract_denied",
    bad_contract,
    "INVALID_CONTRACT"
)

bad_mode = copy.deepcopy(initial_request)
bad_mode["mode"] = "unsupported"

expected_rejection(
    "unsupported_mode_denied",
    bad_mode,
    "UNSUPPORTED_MODE"
)

bad_group = copy.deepcopy(adaptive_request)
bad_group["revision_request"]["group_id"] = (
    "seating_group_9999"
)

expected_rejection(
    "unknown_revision_target_denied",
    bad_group,
    "INVALID_REVISION_TARGET"
)

check(
    "simulated_permission_explicitly_labelled",
    adaptive["provenance"].get(
        "simulated_permission_only"
    ) is True
)

# Replay the existing approved layout's stable-ID property.
check(
    "stable_group_ids_in_both_adaptive_alternatives",
    all(
        set(layout["group_centers_m"]) == set(reference)
        for layout in adaptive["candidate_layouts"]
    )
)

report = {
    "experiment": "PP1_F2F_UNIFIED_CONTRACT_AUDIT_V1",
    "checks": checks,
    "passed": sum(x["passed"] for x in checks),
    "total": len(checks),
    "all_passed": all(x["passed"] for x in checks),
    "live_optimizer_rerun": False,
    "actual_planner_approval": False,
    "real_venue_validated": False,
}

if DEST.exists():
    raise FileExistsError(
        "Output exists; refusing overwrite"
    )

DEST.write_text(
    json.dumps(report, indent=2),
    encoding="utf-8"
)

print("=== F2F SUMMARY ===")
print(
    "Checks:", report["passed"], "/", report["total"]
)
print("All contract checks:", report["all_passed"])
print("Actual planner approval: NO")
print("Real venue validation: NO")
print("Output:", DEST)
print("F2F AUDIT COMPLETE")