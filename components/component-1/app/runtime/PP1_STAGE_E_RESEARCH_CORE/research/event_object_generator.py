import json
import math
from pathlib import Path


SUPPORTED_CLASSES = {
    "round_table",
    "chair",
    "rectangular_table",
    "stage",
    "podium",
    "buffet_counter",
    "dance_floor",
}


def nonnegative_integer(value, name):
    if type(value) is not int or value < 0:
        raise ValueError(
            f"{name} must be a nonnegative integer"
        )
    return value


def build_event_objects(client, planner):
    if not isinstance(client, dict):
        raise ValueError("Client requirements must be a dictionary")
    if not isinstance(planner, dict):
        raise ValueError("Planner requirements must be a dictionary")

    event_type = client.get("event_type")
    if not isinstance(event_type, str) or not event_type.strip():
        raise ValueError("Event type is required")

    guests = nonnegative_integer(
        client.get("guest_count"), "guest_count"
    )
    tables = nonnegative_integer(
        client.get("round_tables"), "round_tables"
    )
    chairs_per_table = nonnegative_integer(
        client.get("chairs_per_table"), "chairs_per_table"
    )

    additional = client.get("additional_objects", {})
    if not isinstance(additional, dict):
        raise ValueError("additional_objects must be a dictionary")

    if set(additional) - SUPPORTED_CLASSES:
        raise ValueError("Unsupported object class requested")

    if "round_table" in additional or "chair" in additional:
        raise ValueError(
            "Round tables and chairs must use their dedicated fields"
        )

    for name, count in additional.items():
        nonnegative_integer(count, name)

    if guests > 0 and tables == 0 and chairs_per_table > 0:
        raise ValueError(
            "Seated event requires tables or a different seating model"
        )

    required_chairs = tables * chairs_per_table

    warnings = []
    if required_chairs < guests:
        warnings.append({
            "code": "SEATING_SHORTFALL",
            "requested_guests": guests,
            "specified_chairs": required_chairs,
            "shortfall": guests - required_chairs,
        })
    elif required_chairs > guests:
        warnings.append({
            "code": "CHAIRS_EXCEED_GUESTS",
            "guest_count": guests,
            "specified_chairs": required_chairs,
        })

    if not planner.get("arrangement_priority"):
        raise ValueError("Planner arrangement priority is required")

    counts = {
        "round_table": tables,
        "chair": required_chairs,
    }

    for name in sorted(additional):
        counts[name] = additional[name]

    objects = []
    for class_name, count in counts.items():
        for number in range(1, count + 1):
            objects.append({
                "object_id": f"{class_name}_{number:04d}",
                "class": class_name,
                "source": "client_requirements",
                "planning_status": "unplaced",
                "geometry": None,
                "position": None,
                "rotation_degrees": None,
                "fixed": False,
            })

    return {
        "schema": "PP1_EVENT_OBJECTS_V1",
        "event_type": event_type,
        "guest_count": guests,
        "planner_requirements": planner,
        "requested_counts": counts,
        "generated_object_count": len(objects),
        "objects": objects,
        "warnings": warnings,
        "venue_geometry_loaded": False,
        "geometry_scale_verified": False,
        "spatial_feasibility_verified": False,
        "layout_generated": False,
        "optimization_executed": False,
    }


def main():
    root = Path(__file__).resolve().parents[1]

    client = {
        "event_type": "Wedding",
        "guest_count": 160,
        "round_tables": 20,
        "chairs_per_table": 8,
        "additional_objects": {
            "stage": 1,
            "buffet_counter": 2,
        },
    }
    planner = {
        "arrangement_priority": "balanced",
        "visibility_priority": "high",
        "circulation_priority": "high",
        "minimum_change_priority": "medium",
    }

    result = build_event_objects(client, planner)

    assert result["requested_counts"]["round_table"] == 20
    assert result["requested_counts"]["chair"] == 160
    assert result["requested_counts"]["stage"] == 1
    assert result["requested_counts"]["buffet_counter"] == 2
    assert result["generated_object_count"] == 183
    assert len(set(
        obj["object_id"] for obj in result["objects"]
    )) == 183
    assert all(
        obj["planning_status"] == "unplaced"
        for obj in result["objects"]
    )

    # Negative validation: invalid quantities must be rejected.
    invalid = dict(client)
    invalid["round_tables"] = -1
    try:
        build_event_objects(invalid, planner)
        raise AssertionError("Negative quantity accepted")
    except ValueError:
        pass

    # Explicitly test that under-seating is reported.
    shortage = dict(client)
    shortage["guest_count"] = 200
    shortage_result = build_event_objects(shortage, planner)
    assert any(
        w["code"] == "SEATING_SHORTFALL"
        and w["shortfall"] == 40
        for w in shortage_result["warnings"]
    )

    destination = root / "outputs" / "event_objects_wedding_160_v1.json"
    if destination.exists():
        raise FileExistsError(
            f"Refusing to overwrite existing output: {destination}"
        )

    destination.write_text(
        json.dumps(result, indent=2),
        encoding="utf-8",
    )

    print("=== PP1 STAGE E — OBJECT GENERATION ===")
    print("Event:", result["event_type"])
    print("Guests:", result["guest_count"])

    for name, count in result["requested_counts"].items():
        print(name, ":", count)

    print("Generated objects:", result["generated_object_count"])
    print("Unique IDs:", len(set(
        x["object_id"] for x in result["objects"]
    )))
    print("Count integrity: PASS")
    print("Negative validation: PASS")
    print("Seating-shortfall validation: PASS")
    print("Spatial placement: NOT EXECUTED")
    print("NSGA-II: NOT EXECUTED")
    print("Output:", destination)
    print("STAGE E OBJECT GENERATION TEST COMPLETE")


if __name__ == "__main__":
    main()