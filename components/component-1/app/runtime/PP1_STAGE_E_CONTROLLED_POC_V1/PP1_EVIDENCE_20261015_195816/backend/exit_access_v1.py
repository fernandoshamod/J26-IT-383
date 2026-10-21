import json
from pathlib import Path

from shapely.geometry import box

from fixed_collision_v1 import geometry_from_rings

ACCESS_CLASSES = {
    "circulation_path",
    "entrance_exit_access",
    "door_or_gate_opening",
}

AREA_TOLERANCE = 1e-8


def get_access_areas(scene):
    areas = []

    for index, item in enumerate(
        scene.get("structural_geometry", [])
    ):
        if item.get("name") in ACCESS_CLASSES:
            geometry = geometry_from_rings(
                item["polygons_m"]
            )
            areas.append({
                "id": f"structure_{index}",
                "class": item["name"],
                "geometry": geometry,
            })

    return areas


def check_access_obstruction(candidate_rings, access_areas):
    # Missing access information cannot be treated as safe.
    if not access_areas:
        return {
            "passed": False,
            "reason": "ACCESS_GEOMETRY_UNVERIFIED",
            "obstructions": [],
            "route_connectivity_verified": False,
        }

    try:
        candidate = geometry_from_rings(candidate_rings)
        obstructions = []

        for area in access_areas:
            overlap = candidate.intersection(
                area["geometry"]
            ).area

            if overlap > AREA_TOLERANCE:
                obstructions.append({
                    "access_id": area["id"],
                    "class": area["class"],
                    "overlap_area_synthetic_m2": round(
                        overlap, 6
                    ),
                })

        return {
            "passed": not obstructions,
            "reason": (
                "NO_ACCESS_AREA_OBSTRUCTION"
                if not obstructions
                else "ACCESS_AREA_OBSTRUCTION"
            ),
            "obstructions": obstructions,
            "route_connectivity_verified": False,
        }

    except (ValueError, TypeError) as exc:
        return {
            "passed": False,
            "reason": "INVALID_GEOMETRY",
            "detail": str(exc),
            "obstructions": [],
            "route_connectivity_verified": False,
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

    areas = get_access_areas(scene)
    assert areas, "No access areas found"

    # Negative test: artificial object covers an access area.
    access_geometry = areas[0]["geometry"]
    blocked = check_access_obstruction(
        [list(access_geometry.envelope.exterior.coords)],
        areas,
    )

    assert blocked["passed"] is False, blocked
    assert blocked["reason"] == "ACCESS_AREA_OBSTRUCTION"

    # Positive test for THIS CHECK ONLY:
    # Find a small square inside the site away from access polygons.
    site = geometry_from_rings(scene["site_polygon_m"])
    clear_rings = None

    minx, miny, maxx, maxy = site.bounds

    x = minx + 0.5
    while x < maxx - 0.5 and clear_rings is None:
        y = miny + 0.5

        while y < maxy - 0.5:
            square = box(x, y, x + 0.4, y + 0.4)

            if site.covers(square) and all(
                square.distance(a["geometry"]) > 0.2
                for a in areas
            ):
                clear_rings = [
                    [list(p) for p in square.exterior.coords]
                ]
                break

            y += 0.5

        x += 0.5

    assert clear_rings is not None, (
        "No access-area-clear test square found"
    )

    clear = check_access_obstruction(clear_rings, areas)

    assert clear["passed"] is True, clear
    assert clear["reason"] == "NO_ACCESS_AREA_OBSTRUCTION"

    # Crucial research limitation:
    assert clear["route_connectivity_verified"] is False

    missing = check_access_obstruction(
        clear_rings, []
    )
    assert missing["passed"] is False

    print("=== PP1 ACCESS-AREA OBSTRUCTION TEST ===")
    print("Access areas:", len(areas))
    print("Artificial access overlap:", blocked["reason"])
    print("Separated test square:", clear["reason"])
    print("Missing access geometry: DENIED")
    print("Route connectivity verified: False")
    print("ALL 4 CHECKS PASSED")