import json
from pathlib import Path

from shapely.geometry import box

from fixed_collision_v1 import geometry_from_rings

RESTRICTED_CLASSES = {"service_restricted"}


def get_restricted_zones(scene):
    zones = []

    for index, item in enumerate(
        scene.get("structural_geometry", [])
    ):
        if item.get("name") in RESTRICTED_CLASSES:
            zones.append({
                "id": f"structure_{index}",
                "class": item["name"],
                "geometry": geometry_from_rings(
                    item["polygons_m"]
                ),
            })

    return zones


def check_restricted_zone(candidate_rings, zones):
    try:
        candidate = geometry_from_rings(candidate_rings)
        intrusions = []

        for zone in zones:
            overlap = candidate.intersection(
                zone["geometry"]
            ).area

            if overlap > 1e-8:
                intrusions.append({
                    "zone_id": zone["id"],
                    "class": zone["class"],
                    "overlap_area_synthetic_m2": round(
                        overlap, 6
                    ),
                })

        return {
            "passed": len(intrusions) == 0,
            "reason": (
                "NO_RESTRICTED_INTRUSION"
                if not intrusions
                else "RESTRICTED_ZONE_INTRUSION"
            ),
            "intrusions": intrusions,
        }

    except (ValueError, TypeError) as exc:
        return {
            "passed": False,
            "reason": "INVALID_GEOMETRY",
            "detail": str(exc),
            "intrusions": [],
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

    zones = get_restricted_zones(scene)
    assert zones, "No restricted zones in source fixture"

    # Positive detection: an artificial candidate exactly
    # covering a restricted polygon.
    restricted = next(
        item for item in scene["structural_geometry"]
        if item["name"] == "service_restricted"
    )

    blocked = check_restricted_zone(
        restricted["polygons_m"], zones
    )

    assert blocked["passed"] is False, blocked
    assert blocked["reason"] == "RESTRICTED_ZONE_INTRUSION"

    # Find a small square within the source venue,
    # away from all restricted zones.
    site = geometry_from_rings(scene["site_polygon_m"])
    clear_square = None

    minx, miny, maxx, maxy = site.bounds

    x = minx + 0.5
    while x < maxx - 0.5 and clear_square is None:
        y = miny + 0.5

        while y < maxy - 0.5:
            square = box(x, y, x + 0.4, y + 0.4)

            if (
                site.covers(square)
                and all(
                    square.distance(z["geometry"]) > 0.2
                    for z in zones
                )
            ):
                clear_square = [
                    [list(pt) for pt in square.exterior.coords]
                ]
                break

            y += 0.5

        x += 0.5

    assert clear_square is not None, (
        "No restricted-zone-clear test square found"
    )

    clear = check_restricted_zone(
        clear_square, zones
    )

    assert clear["passed"] is True, clear
    assert clear["reason"] == "NO_RESTRICTED_INTRUSION"

    print("=== PP1 RESTRICTED ZONE TEST ===")
    print("Restricted zones:", len(zones))
    print("Artificial zone overlap:", blocked["reason"])
    print("Separated test square:", clear["reason"])
    print("BOTH CHECKS PASSED")