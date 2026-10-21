import json
from pathlib import Path

from shapely.geometry import Polygon, box
from shapely.ops import unary_union
from shapely.validation import explain_validity

SOLID_STRUCTURE_CLASSES = {
    "fixed_obstacle",
    "fixed_water_feature",
}


def geometry_from_rings(rings):
    if not isinstance(rings, list) or not rings:
        raise ValueError("Missing polygon geometry")

    polygons = []
    for ring in rings:
        polygon = Polygon(ring)

        if (
            polygon.is_empty
            or not polygon.is_valid
            or polygon.area <= 0
        ):
            raise ValueError(
                "Invalid polygon: " + explain_validity(polygon)
            )

        polygons.append(polygon)

    return unary_union(polygons)


def protected_objects(scene):
    protected = []

    for obj in scene["event_instances"]:
        if obj.get("fixed") is True:
            protected.append({
                "id": f"event_{obj['instance_id']}",
                "class": obj["class"],
                "geometry": geometry_from_rings(
                    obj["polygons_m"]
                ),
            })

    for index, item in enumerate(
        scene["structural_geometry"]
    ):
        if item.get("name") in SOLID_STRUCTURE_CLASSES:
            protected.append({
                "id": f"structure_{index}",
                "class": item["name"],
                "geometry": geometry_from_rings(
                    item["polygons_m"]
                ),
            })

    return protected


def check_fixed_collision(
    candidate_rings,
    protected,
    candidate_object_id=None,
):
    try:
        candidate = geometry_from_rings(candidate_rings)
        collisions = []

        for item in protected:
            if (
                candidate_object_id is not None
                and item["id"] == f"event_{candidate_object_id}"
            ):
                continue

            overlap_area = candidate.intersection(
                item["geometry"]
            ).area

            # Shared polygon edges alone are not an
            # area collision in this initial POC.
            if overlap_area > 1e-8:
                collisions.append({
                    "protected_id": item["id"],
                    "class": item["class"],
                    "overlap_area_synthetic_m2": round(
                        overlap_area, 6
                    ),
                })

        return {
            "passed": len(collisions) == 0,
            "reason": (
                "NO_FIXED_COLLISION"
                if not collisions
                else "FIXED_COLLISION"
            ),
            "collisions": collisions,
        }

    except (ValueError, TypeError) as exc:
        return {
            "passed": False,
            "reason": "INVALID_GEOMETRY",
            "detail": str(exc),
            "collisions": [],
        }


if __name__ == "__main__":
    project = Path(__file__).resolve().parents[2]
    source = (
        project / "02_GENERATED_RESEARCH_DATA"
        / "STAGE_C_OBJECTS"
        / "C3_17_RENDERER_V3_MASTER_180"
        / "SB_0005_OUTDOOR_GARDEN_L_SHAPE.json"
    )

    scene = json.loads(
        source.read_text(encoding="utf-8-sig")
    )
    protected = protected_objects(scene)

    stage = next(
        obj for obj in scene["event_instances"]
        if obj["instance_id"] == 1
    )

    # Artificial movable candidate covering the stage:
    # collision must be detected.
    collision_result = check_fixed_collision(
        stage["polygons_m"], protected
    )

    assert collision_result["reason"] == "FIXED_COLLISION"
    assert any(
        c["protected_id"] == "event_1"
        for c in collision_result["collisions"]
    )

    # Find a small synthetic test square inside the site,
    # sufficiently separated from known protected footprints.
    site = geometry_from_rings(scene["site_polygon_m"])
    safe_example = None

    minx, miny, maxx, maxy = site.bounds
    x = minx + 1

    while x < maxx - 1 and safe_example is None:
        y = miny + 1

        while y < maxy - 1:
            square = box(x, y, x + 0.5, y + 0.5)

            if site.covers(square) and all(
                square.distance(obj["geometry"]) > 0.2
                for obj in protected
            ):
                safe_example = [
                    list(square.exterior.coords)
                ]
                break

            y += 1

        x += 1

    assert safe_example is not None, (
        "No clear test square found in synthetic site"
    )

    clear_result = check_fixed_collision(
        safe_example, protected
    )

    assert clear_result["reason"] == "NO_FIXED_COLLISION"
    assert clear_result["passed"] is True

    print("=== PP1 FIXED COLLISION TEST ===")
    print("Protected objects:", len(protected))
    print("Artificial stage overlap:", collision_result["reason"])
    print("Separated test square:", clear_result["reason"])
    print("BOTH CHECKS PASSED")