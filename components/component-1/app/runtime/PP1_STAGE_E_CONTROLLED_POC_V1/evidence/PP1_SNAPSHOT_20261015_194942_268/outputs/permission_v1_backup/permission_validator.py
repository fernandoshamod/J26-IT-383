import json
from pathlib import Path


ALLOWED_STATUSES = {"fixed", "movable", "removable", "unconfirmed"}


def load_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8-sig"))


def validate_config(scene, config):
    errors = []

    if config.get("schema_version") != "1.0":
        errors.append("Unsupported permission schema version")

    if config.get("mode") != "CONTROLLED_SYNTHETIC_POC":
        errors.append("Invalid execution mode")

    if config.get("scene_id") != scene.get("id"):
        errors.append("Scene identity mismatch")

    source_objects = scene.get("event_instances", [])
    permission_objects = config.get("objects", [])

    source_ids = [obj.get("instance_id") for obj in source_objects]
    permission_ids = [obj.get("instance_id") for obj in permission_objects]

    if len(source_ids) != len(set(source_ids)):
        errors.append("Duplicate source object IDs")

    if len(permission_ids) != len(set(permission_ids)):
        errors.append("Duplicate permission object IDs")

    if set(source_ids) != set(permission_ids):
        errors.append("Source and permission object IDs do not match")

    source_map = {obj["instance_id"]: obj for obj in source_objects}

    for item in permission_objects:
        object_id = item.get("instance_id")
        source = source_map.get(object_id)

        if source is None:
            continue

        if item.get("class") != source.get("class"):
            errors.append(f"Class mismatch for object {object_id}")

        source_fixed = source.get("fixed") is True

        if item.get("source_fixed") is not source_fixed:
            errors.append(f"Source-fixed mismatch for object {object_id}")

        status = item.get("planner_status")

        if status not in ALLOWED_STATUSES:
            errors.append(f"Invalid status for object {object_id}")

        if source_fixed:
            if status != "fixed":
                errors.append(f"Source-fixed object {object_id} must stay fixed")
            if item.get("move_allowed") is not False:
                errors.append(f"Source-fixed object {object_id} cannot move")
            if item.get("remove_allowed") is not False:
                errors.append(f"Source-fixed object {object_id} cannot be removed")

        if status in {"fixed", "unconfirmed"}:
            if item.get("move_allowed") is not False:
                errors.append(f"Locked object {object_id} has move permission")
            if item.get("remove_allowed") is not False:
                errors.append(f"Locked object {object_id} has remove permission")

        if status == "movable":
            if item.get("move_allowed") is not True:
                errors.append(f"Movable object {object_id} lacks move permission")
            if item.get("remove_allowed") is not False:
                errors.append(f"Movable object {object_id} cannot be removed")

        if status == "removable":
            if item.get("remove_allowed") is not True:
                errors.append(f"Removable object {object_id} lacks remove permission")
            if item.get("move_allowed") is not False:
                errors.append(f"Removable object {object_id} cannot move")

        if status in {"movable", "removable"}:
            if not item.get("approved_by"):
                errors.append(f"Object {object_id} lacks approval identity")

    return errors


def check_action(scene, config, object_id, action):
    errors = validate_config(scene, config)

    if errors:
        return {
            "allowed": False,
            "reason": "CONFIG_INVALID",
            "errors": errors,
        }

    if action not in {"move", "remove"}:
        return {"allowed": False, "reason": "UNKNOWN_ACTION"}

    entries = {
        obj["instance_id"]: obj
        for obj in config["objects"]
    }

    obj = entries.get(object_id)

    if obj is None:
        return {"allowed": False, "reason": "UNKNOWN_OBJECT"}

    if obj["source_fixed"]:
        return {"allowed": False, "reason": "SOURCE_FIXED_LOCK"}

    required_field = "move_allowed" if action == "move" else "remove_allowed"

    if obj.get(required_field) is True:
        return {"allowed": True, "reason": "EXPLICIT_PERMISSION"}

    return {"allowed": False, "reason": "NOT_AUTHORIZED"}


if __name__ == "__main__":
    root = Path(__file__).resolve().parents[2]

    scene_path = (
        root
        / "02_GENERATED_RESEARCH_DATA"
        / "STAGE_C_OBJECTS"
        / "C3_17_RENDERER_V3_MASTER_180"
        / "SB_0005_OUTDOOR_GARDEN_L_SHAPE.json"
    )

    config_path = (
        Path(__file__).resolve().parents[1]
        / "config"
        / "planner_permissions_v1.json"
    )

    scene = load_json(scene_path)
    config = load_json(config_path)

    errors = validate_config(scene, config)

    print("=== PP1 PERMISSION VALIDATION ===")
    print("Scene:", scene["id"])
    print("Objects:", len(config["objects"]))
    print("Config valid:", len(errors) == 0)

    if errors:
        for error in errors:
            print("ERROR:", error)

    for object_id, action in [
        (1, "move"),
        (34, "remove"),
        (2, "move"),
    ]:
        result = check_action(scene, config, object_id, action)
        print(
            f"Object {object_id} | {action} | "
            f"allowed={result['allowed']} | reason={result['reason']}"
        )