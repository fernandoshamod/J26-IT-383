from shapely.geometry import Polygon
from shapely.validation import explain_validity


def make_polygon(points):
    if not isinstance(points, (list, tuple)) or len(points) < 3:
        raise ValueError("Polygon needs at least three points")

    polygon = Polygon(points)

    if polygon.is_empty or not polygon.is_valid:
        raise ValueError(
            f"Invalid polygon: {explain_validity(polygon)}"
        )

    if polygon.area <= 0:
        raise ValueError("Polygon area must be positive")

    return polygon


def check_venue_boundary(site_points, object_rings):
    """
    Checks whether every object footprint ring is fully
    covered by the synthetic venue boundary.

    Synthetic geometry only. Not safety certification.
    """
    try:
        site = make_polygon(site_points)

        if not object_rings:
            return {
                "passed": False,
                "reason": "MISSING_OBJECT_GEOMETRY"
            }

        footprints = [
            make_polygon(ring)
            for ring in object_rings
        ]

        outside_area = sum(
            poly.difference(site).area
            for poly in footprints
        )

        passed = all(
            site.covers(poly)
            for poly in footprints
        )

        return {
            "passed": passed,
            "reason": (
                "WITHIN_BOUNDARY"
                if passed else "BOUNDARY_VIOLATION"
            ),
            "outside_area_synthetic_m2": round(
                outside_area, 6
            )
        }

    except (ValueError, TypeError) as exc:
        return {
            "passed": False,
            "reason": "INVALID_GEOMETRY",
            "detail": str(exc)
        }


if __name__ == "__main__":
    import json
    from pathlib import Path

    project = Path(__file__).resolve().parents[2]

    source = (
        project / "02_GENERATED_RESEARCH_DATA"
        / "STAGE_C_OBJECTS"
        / "C3_17_RENDERER_V3_MASTER_180"
        / "SB_0005_OUTDOOR_GARDEN_L_SHAPE.json"
    )

    scene = json.loads(source.read_text(encoding="utf-8-sig"))

    site = scene["site_polygon_m"]
    stage = next(
        item for item in scene["event_instances"]
        if item["instance_id"] == 1
    )

    inside = check_venue_boundary(
        site, stage["polygons_m"]
    )

    outside_example = [
        [[60, 20], [63, 20], [63, 23], [60, 23]]
    ]

    outside = check_venue_boundary(
        site, outside_example
    )

    assert inside["passed"] is True, inside
    assert outside["passed"] is False, outside

    print("=== PP1 BOUNDARY CONSTRAINT TEST ===")
    print("Original source stage: WITHIN BOUNDARY")
    print("Artificial outside placement: REJECTED")
    print("BOTH CHECKS PASSED")