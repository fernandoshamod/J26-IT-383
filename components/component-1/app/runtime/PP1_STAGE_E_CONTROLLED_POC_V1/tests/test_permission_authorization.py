import copy
import sys
from pathlib import Path

poc_root = Path(__file__).resolve().parents[1]
project_root = poc_root.parent

sys.path.insert(0, str(poc_root / "backend"))

from permission_validator import (
    load_json, validate_config, check_action
)

scene_path = (
    project_root
    / "02_GENERATED_RESEARCH_DATA"
    / "STAGE_C_OBJECTS"
    / "C3_17_RENDERER_V3_MASTER_180"
    / "SB_0005_OUTDOOR_GARDEN_L_SHAPE.json"
)

config_path = (
    poc_root / "config" / "planner_permissions_v1.json"
)

scene = load_json(scene_path)
config = load_json(config_path)

assert validate_config(scene, config) == []

# Baseline: object 2 is unconfirmed and locked.
baseline = check_action(scene, config, 2, "move")
assert baseline["allowed"] is False

# Simulated authorization: in memory only.
approved = copy.deepcopy(config)

obj2 = next(
    item for item in approved["objects"]
    if item["instance_id"] == 2
)

assert obj2["source_fixed"] is False

obj2["planner_status"] = "movable"
obj2["move_allowed"] = True
obj2["remove_allowed"] = False
obj2["approved_by"] = "SYNTHETIC_TEST_PLANNER"
obj2["approval_note"] = "Controlled unit test only"

assert validate_config(scene, approved) == []

move_result = check_action(scene, approved, 2, "move")
remove_result = check_action(scene, approved, 2, "remove")
fixed_result = check_action(scene, approved, 1, "move")

assert move_result["allowed"] is True
assert remove_result["allowed"] is False
assert fixed_result["allowed"] is False

# No approval identity: must fail closed.
missing_approval = copy.deepcopy(approved)
missing_obj2 = next(
    item for item in missing_approval["objects"]
    if item["instance_id"] == 2
)

missing_obj2["approved_by"] = None

assert validate_config(scene, missing_approval) != []

rejected = check_action(
    scene, missing_approval, 2, "move"
)
assert rejected["allowed"] is False

print("=== PLANNER AUTHORIZATION TEST ===")
print("Unconfirmed move: DENIED")
print("Simulated approved move: ALLOWED")
print("Approved movable removal: DENIED")
print("Source-fixed stage move: DENIED")
print("Missing approval identity: DENIED")
print("ALL 5 CHECKS PASSED")