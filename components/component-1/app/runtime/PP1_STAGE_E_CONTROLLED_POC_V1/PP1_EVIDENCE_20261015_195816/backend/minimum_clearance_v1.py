from shapely.geometry import Polygon

from fixed_collision_v1 import geometry_from_rings

# Synthetic research demonstration parameter only.
# NOT a legal, regulatory, accessibility or safety threshold.
DEMO_MIN_CLEARANCE_M = 0.5


def check_minimum_clearance(
    candidate_rings,
    protected,
    minimum_clearance_m=DEMO_MIN_CLEARANCE_M,
    candidate_object_id=None,
):
    if (
        isinstance(minimum_clearance_m, bool)
        or not isinstance(minimum_clearance_m, (int, float))
        or not (0 < minimum_clearance_m < float("inf"))
    ):
        return {
            "passed": False,
            "reason": "INVALID_CLEARANCE_THRESHOLD",
            "violations": [],
            "threshold_validated_for_real_world": False,
        }

    if not protected:
        return {
            "passed": False,
            "reason": "PROTECTED_GEOMETRY_MISSING",
            "violations": [],
            "threshold_validated_for_real_world": False,
        }

    try:
        candidate = geometry_from_rings(candidate_rings)
        violations = []
        nearest_distance = None

        for item in protected:
            if (
                candidate_object_id is not None
                and item["id"] == f"event_{candidate_object_id}"
            ):
                continue

            distance = candidate.distance(item["geometry"])

            if nearest_distance is None or distance < nearest_distance:
                nearest_distance = distance

            if distance + 1e-9 < minimum_clearance_m:
                violations.append({
                    "protected_id": item["id"],
                    "class": item["class"],
                    "distance_synthetic_m": round(distance, 6),
                })

        if nearest_distance is None:
            return {
                "passed": False,
                "reason": "NO_APPLICABLE_PROTECTED_OBJECTS",
                "violations": [],
                "threshold_validated_for_real_world": False,
            }

        return {
            "passed": not violations,
            "reason": (
                "MINIMUM_CLEARANCE_PASS"
                if not violations
                else "MINIMUM_CLEARANCE_VIOLATION"
            ),
            "required_clearance_synthetic_m": minimum_clearance_m,
            "nearest_distance_synthetic_m": round(
                nearest_distance, 6
            ),
            "violations": violations,
            "threshold_validated_for_real_world": False,
        }

    except (ValueError, TypeError, KeyError) as exc:
        return {
            "passed": False,
            "reason": "INVALID_GEOMETRY",
            "detail": str(exc),
            "violations": [],
            "threshold_validated_for_real_world": False,
        }


if __name__ == "__main__":
    from pathlib import Path
    import json

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

    # Confirm source fixture has protected object geometry.
    from fixed_collision_v1 import protected_objects
    source_protected = protected_objects(scene)
    assert len(source_protected) == 4

    # Isolated deterministic geometries for exact distances.
    test_protected = [{
        "id": "test_fixed",
        "class": "fixed_obstacle",
        "geometry": Polygon([
            (0, 0), (2, 0), (2, 2), (0, 2)
        ]),
    }]

    near = [[
        [2.2, 0.5], [2.6, 0.5],
        [2.6, 1.0], [2.2, 1.0]
    ]]

    far = [[
        [3.0, 0.5], [3.4, 0.5],
        [3.4, 1.0], [3.0, 1.0]
    ]]

    overlap = [[
        [1.5, 0.5], [2.5, 0.5],
        [2.5, 1.0], [1.5, 1.0]
    ]]

    result_near = check_minimum_clearance(
        near, test_protected, 0.5
    )
    result_far = check_minimum_clearance(
        far, test_protected, 0.5
    )
    result_overlap = check_minimum_clearance(
        overlap, test_protected, 0.5
    )
    result_invalid = check_minimum_clearance(
        far, test_protected, -1
    )
    result_missing = check_minimum_clearance(
        far, [], 0.5
    )

    assert result_near["passed"] is False, result_near
    assert abs(
        result_near["nearest_distance_synthetic_m"] - 0.2
    ) < 1e-6

    assert result_far["passed"] is True, result_far
    assert abs(
        result_far["nearest_distance_synthetic_m"] - 1.0
    ) < 1e-6

    assert result_overlap["passed"] is False, result_overlap
    assert result_invalid["passed"] is False, result_invalid
    assert result_missing["passed"] is False, result_missing

    print("=== PP1 MINIMUM CLEARANCE TEST ===")
    print("Source protected objects:", len(source_protected))
    print("Demo threshold: 0.5 synthetic metres")
    print("Near object (0.2 m):", result_near["reason"])
    print("Far object (1.0 m):", result_far["reason"])
    print("Overlapping object:", result_overlap["reason"])
    print("Invalid threshold:", result_invalid["reason"])
    print("Missing protected geometry:", result_missing["reason"])
    print("ALL 5 TEST CASES PASSED")
    print("REAL-WORLD THRESHOLD VALIDATION: NOT PERFORMED")