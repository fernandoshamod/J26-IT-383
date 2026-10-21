import copy
import sys
from pathlib import Path

POC = Path(__file__).resolve().parents[1]
PROJECT = POC.parent

sys.path.insert(0, str(POC / "backend"))

from permission_validator import (
    load_json, validate_config, check_action
)

scene = load_json(
    PROJECT / "02_GENERATED_RESEARCH_DATA"
    / "STAGE_C_OBJECTS"
    / "C3_17_RENDERER_V3_MASTER_180"
    / "SB_0005_OUTDOOR_GARDEN_L_SHAPE.json"
)

baseline = load_json(
    POC / "config" / "planner_permissions_v2.json"
)

assert validate_config(scene, baseline) == []

def stage_entry(config):
    return next(
        x for x in config["objects"]
        if x["instance_id"] == 1
    )

# 1. Unconfirmed stage is locked.
assert check_action(scene, baseline, 1, "move")["allowed"] is False

# 2. Simulated planner marks stage movable.
trial = copy.deepcopy(baseline)
stage = stage_entry(trial)

stage["planner_status"] = "movable"
stage["move_allowed"] = True
stage["remove_allowed"] = False
stage["approved_by"] = "SYNTHETIC_TEST_PLANNER"
stage["approval_note"] = "Portable event stage; simulation only"
stage["approval_scope"] = "SYNTHETIC_DEMO_ONLY"

# Source initially says fixed, so discrepancy review required.
assert validate_config(scene, trial) != []
assert check_action(scene, trial, 1, "move")["allowed"] is False

# 3. Explicit discrepancy review.
stage["source_conflict_reviewed"] = True

assert validate_config(scene, trial) == []
assert check_action(scene, trial, 1, "move")["allowed"] is True

# 4. Move permission must not imply removal.
assert check_action(scene, trial, 1, "remove")["allowed"] is False

# 5. Missing reviewer identity fails closed.
invalid = copy.deepcopy(trial)
stage_entry(invalid)["approved_by"] = None

assert validate_config(scene, invalid) != []
assert check_action(scene, invalid, 1, "move")["allowed"] is False

# 6. Other unconfirmed objects remain locked.
assert check_action(scene, trial, 34, "move")["allowed"] is False

print("=== PP1 PERMISSION V2 TEST ===")
print("Unconfirmed stage move: DENIED")
print("Unreviewed source discrepancy: DENIED")
print("Reviewed simulated stage move: ALLOWED")
print("Stage removal without permission: DENIED")
print("Missing reviewer identity: DENIED")
print("Other unconfirmed objects: LOCKED")
print("ALL 6 CHECKS PASSED")