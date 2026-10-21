import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "outputs" / "e7a_adaptive_reoptimization_v1.json"
DEST = ROOT / "outputs" / "e8b_permission_gate_tests_v1.json"


def authorize_revision(request, permissions):
    if not isinstance(request, dict):
        return False, "INVALID_REQUEST"

    if not isinstance(permissions, dict):
        return False, "INVALID_PERMISSIONS"

    group_id = request.get("group_id")
    action = request.get("action")

    if not isinstance(group_id, str) or not group_id:
        return False, "MISSING_GROUP_ID"

    if action != "move":
        return False, "ACTION_NOT_SUPPORTED"

    permission = permissions.get(group_id)

    if not isinstance(permission, dict):
        return False, "NO_EXPLICIT_PERMISSION"

    if permission.get("status") != "movable":
        return False, "GROUP_NOT_MOVABLE"

    if permission.get("move_allowed") is not True:
        return False, "MOVE_NOT_APPROVED"

    if permission.get("scope") != "SYNTHETIC_DEMO_ONLY":
        return False, "INVALID_APPROVAL_SCOPE"

    reviewer = permission.get("approved_by")
    reason = permission.get("approval_reason")

    if not isinstance(reviewer, str) or not reviewer.strip():
        return False, "MISSING_REVIEWER"

    if not isinstance(reason, str) or not reason.strip():
        return False, "MISSING_APPROVAL_REASON"

    return True, "AUTHORIZED_SYNTHETIC_MOVE"


def run_tests():
    report = json.loads(SOURCE.read_text(encoding="utf-8"))
    group = report["movable_group_ids"][0]

    approved = {
        group: {
            "status": "movable",
            "move_allowed": True,
            "scope": "SYNTHETIC_DEMO_ONLY",
            "approved_by": "SIMULATED_PLANNER",
            "approval_reason": "Controlled research revision",
        }
    }

    cases = [
        ("approved_move", {"group_id": group, "action": "move"},
         approved, True),
        ("missing_permission", {"group_id": group, "action": "move"},
         {}, False),
        ("unconfirmed", {"group_id": group, "action": "move"},
         {group: {**approved[group], "status": "unconfirmed"}}, False),
        ("fixed_group", {"group_id": group, "action": "move"},
         {group: {**approved[group], "status": "fixed"}}, False),
        ("move_denied", {"group_id": group, "action": "move"},
         {group: {**approved[group], "move_allowed": False}}, False),
        ("wrong_scope", {"group_id": group, "action": "move"},
         {group: {**approved[group], "scope": "REAL_VENUE"}}, False),
        ("missing_reviewer", {"group_id": group, "action": "move"},
         {group: {**approved[group], "approved_by": ""}}, False),
        ("missing_reason", {"group_id": group, "action": "move"},
         {group: {**approved[group], "approval_reason": ""}}, False),
        ("different_group", {"group_id": "seating_group_0001",
                             "action": "move"}, approved, False),
        ("remove_action", {"group_id": group, "action": "remove"},
         approved, False),
    ]

    results = []

    for name, request, permissions, expected in cases:
        allowed, reason = authorize_revision(request, permissions)
        passed = allowed is expected

        results.append({
            "test": name,
            "expected_allowed": expected,
            "actual_allowed": allowed,
            "reason": reason,
            "pass": passed,
        })

        print(
            name,
            "|", "ALLOWED" if allowed else "DENIED",
            "|", reason,
            "|", "PASS" if passed else "FAIL"
        )

    assert all(r["pass"] for r in results)

    evidence = {
        "experiment": "PP1_E8B_PERMISSION_GATE_V1",
        "tests": results,
        "passed": len(results),
        "total": len(results),
        "authorization_gate_unit_tests_pass": True,
        "optimizer_entry_point_integrated": False,
        "actual_planner_approval": False,
        "synthetic_only": True,
    }

    if DEST.exists():
        raise FileExistsError("Output exists; refusing overwrite")

    DEST.write_text(
        json.dumps(evidence, indent=2),
        encoding="utf-8",
    )

    print("=== E8B PERMISSION GATE ===")
    print(f"Passed: {len(results)}/{len(results)}")
    print("Optimizer entry-point integration: PENDING")
    print("Actual planner approval: NO")
    print("Output:", DEST)


if __name__ == "__main__":
    run_tests()