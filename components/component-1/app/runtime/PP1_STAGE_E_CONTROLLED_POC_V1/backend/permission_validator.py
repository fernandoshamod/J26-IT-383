import json
from pathlib import Path

ALLOWED_STATUSES = {
    "unconfirmed", "fixed", "movable", "removable"
}
ACTIONS = {"move", "remove"}
DEMO_SCOPE = "SYNTHETIC_DEMO_ONLY"


def load_json(path):
    return json.loads(
        Path(path).read_text(encoding="utf-8-sig")
    )


def validate_config(scene, config):
    errors = []

    if config.get("schema_version") != "2.0":
        errors.append("Unsupported schema version")

    if config.get("mode") != "CONTROLLED_SYNTHETIC_POC":
        errors.append("Invalid execution mode")

    if config.get("scene_id") != scene.get("id"):
        errors.append("Scene mismatch")

    src = scene.get("event_instances", [])
    entries = config.get("objects", [])

    if not isinstance(src, list) or not isinstance(entries, list):
        return errors + ["Invalid object collection"]

    def ids(items):
        return [x.get("instance_id") for x in items]

    source_ids = ids(src)
    config_ids = ids(entries)

    if len(source_ids) != len(set(source_ids)):
        errors.append("Duplicate source IDs")

    if len(config_ids) != len(set(config_ids)):
        errors.append("Duplicate config IDs")

    if set(source_ids) != set(config_ids):
        errors.append("Source/config IDs mismatch")

    source_map = {x["instance_id"]: x for x in src}

    for obj in entries:
        oid = obj.get("instance_id")
        original = source_map.get(oid)

        if original is None:
            continue

        if obj.get("class") != original.get("class"):
            errors.append(f"Class mismatch: {oid}")

        source_fixed = original.get("fixed") is True

        if obj.get("source_fixed") is not source_fixed:
            errors.append(f"Source flag mismatch: {oid}")

        status = obj.get("planner_status")
        move = obj.get("move_allowed")
        remove = obj.get("remove_allowed")

        if status not in ALLOWED_STATUSES:
            errors.append(f"Unknown status: {oid}")
            continue

        if type(move) is not bool or type(remove) is not bool:
            errors.append(f"Permissions must be boolean: {oid}")
            continue

        if status == "movable":
            if not move or remove:
                errors.append(f"Invalid movable permissions: {oid}")
        elif status == "removable":
            if not remove or move:
                errors.append(f"Invalid removable permissions: {oid}")
        elif move or remove:
            errors.append(f"Locked status grants action: {oid}")

        if status != "unconfirmed":
            if not str(obj.get("approved_by") or "").strip():
                errors.append(f"Missing reviewer: {oid}")

            if not str(obj.get("approval_note") or "").strip():
                errors.append(f"Missing review note: {oid}")

            if obj.get("approval_scope") != DEMO_SCOPE:
                errors.append(f"Invalid approval scope: {oid}")

        if status == "unconfirmed":
            if (obj.get("approved_by") is not None
                or obj.get("approval_note") is not None
                or obj.get("approval_scope") is not None
                or obj.get("source_conflict_reviewed") is not False):
                errors.append(f"Unconfirmed object has approval: {oid}")

        if type(obj.get("source_conflict_reviewed")) is not bool:
            errors.append(f"Invalid conflict review flag: {oid}")

        if source_fixed and status in {"movable", "removable"}:
            if obj.get("source_conflict_reviewed") is not True:
                errors.append(
                    f"Source-fixed discrepancy not reviewed: {oid}"
                )

    return errors


def check_action(scene, config, object_id, action):
    errors = validate_config(scene, config)

    if errors:
        return {
            "allowed": False,
            "reason": "CONFIG_INVALID",
            "errors": errors
        }

    if action not in ACTIONS:
        return {"allowed": False, "reason": "UNKNOWN_ACTION"}

    obj = next(
        (x for x in config["objects"]
         if x["instance_id"] == object_id),
        None
    )

    if obj is None:
        return {"allowed": False, "reason": "UNKNOWN_OBJECT"}

    field = "move_allowed" if action == "move" else "remove_allowed"

    if obj.get(field) is True:
        return {
            "allowed": True,
            "reason": "EXPLICIT_SYNTHETIC_PERMISSION"
        }

    return {"allowed": False, "reason": "NOT_AUTHORIZED"}


if __name__ == "__main__":
    poc = Path(__file__).resolve().parents[1]
    root = poc.parent

    source = (
        root / "02_GENERATED_RESEARCH_DATA"
        / "STAGE_C_OBJECTS"
        / "C3_17_RENDERER_V3_MASTER_180"
        / "SB_0005_OUTDOOR_GARDEN_L_SHAPE.json"
    )

    config_file = (
        poc / "config" / "planner_permissions_v2.json"
    )

    scene = load_json(source)
    config = load_json(config_file)

    errors = validate_config(scene, config)

    print("=== PLANNER PERMISSION V2 ===")
    print("Schema:", config["schema_version"])
    print("Objects:", len(config["objects"]))
    print("Config valid:", not errors)

    for error in errors:
        print("ERROR:", error)

    for oid, action in [
        (1, "move"), (34, "remove"), (2, "move")
    ]:
        result = check_action(scene, config, oid, action)
        print(
            f"Object {oid} {action}: "
            f"{result['allowed']} - {result['reason']}"
        )