from shapely.geometry import Polygon
from shapely.validation import explain_validity


def is_point(value):
    return (
        isinstance(value, (list, tuple))
        and len(value) == 2
        and all(isinstance(v, (int, float)) for v in value)
    )


def make_polygon(points):
    if not isinstance(points, (list, tuple)):
        raise ValueError("Polygon coordinates must be an array")

    if len(points) < 3 or not all(is_point(p) for p in points):
        raise ValueError("Polygon requires at least three XY points")

    polygon = Polygon(points)

    if polygon.is_empty or not polygon.is_valid:
        raise ValueError(
            f"Invalid polygon: {explain_validity(polygon)}"
        )

    if polygon.area <= 0:
        raise ValueError("Polygon area must be positive")

    return polygon


def normalize_site(site_points):
    # Source JSON stores site_polygon_m as [polygon_points].
    if (
        isinstance(site_points, (list, tuple))
        and len(site_points) == 1
        and isinstance(site_points[0], (list, tuple))
    ):
        site_points = site_points[0]

    if (
        isinstance(site_points, (list, tuple))
        and len(site_points) >= 3
        and all(is_point(p) for p in site_points)
    ):
        return site_points

    raise ValueError("Invalid site polygon coordinate structure")


def normalize_rings(object_rings):
    if not isinstance(object_rings, (list, tuple)):
        raise ValueError("Object footprints must be an array")

    # Single polygon represented directly as XY points.
    if object_rings and all(is_point(p) for p in object_rings):
        return [object_rings]

    # Multiple polygons, each represented as XY points.
    if object_rings and all(
        isinstance(ring, (list, tuple))
        and len(ring) >= 3
        and all(is_point(p) for p in ring)
        for ring in object_rings
    ):
        return object_rings

    raise ValueError("Invalid object polygon nesting")


def check_venue_boundary(site_points, object_rings):
    """
    Generator-local synthetic geometry boundary test.
    Does not certify real-world safety.
    """
    try:
        site = make_polygon(normalize_site(site_points))

        footprints = [
            make_polygon(ring)
            for ring in normalize_rings(object_rings)
        ]

        passed = all(
            site.covers(poly)
            for poly in footprints
        )

        outside_area = sum(
            poly.difference(site).area
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

    scene = json.loads(
        source.read_text(encoding="utf-8-sig")
    )

    site = scene["site_polygon_m"]
    stage = next(
        item for item in scene["event_instances"]
        if item["instance_id"] == 1
    )

    inside = check_venue_boundary(
        site, stage["polygons_m"]
    )

    outside = check_venue_boundary(
        site,
        [[[60, 20], [63, 20], [63, 23], [60, 23]]]
    )

    assert inside["passed"] is True, inside
    assert outside["reason"] == "BOUNDARY_VIOLATION", outside

    print("=== PP1 BOUNDARY CONSTRAINT TEST ===")
    print("Original source stage:", inside)
    print("Artificial outside placement:", outside)
    print("BOTH CHECKS PASSED")