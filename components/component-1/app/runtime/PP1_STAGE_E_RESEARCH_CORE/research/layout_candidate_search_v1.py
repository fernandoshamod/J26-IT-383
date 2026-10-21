import json
import math
import random
from pathlib import Path

from shapely.geometry import Point, Polygon

ROOT = Path(__file__).resolve().parents[1]
REQ = ROOT / "outputs" / "event_objects_wedding_160_v1.json"
BASE = ROOT / "outputs" / "full_layout_baseline_v1.json"
DEST = ROOT / "outputs" / "layout_candidates_v1.json"

TABLE_RADIUS = 0.80
CHAIR_RADIUS = 0.27
SEATING_RING_RADIUS = 1.45
GROUP_BOUND_RADIUS = SEATING_RING_RADIUS + CHAIR_RADIUS


def circle(cx, cy, radius):
    return Point(cx, cy).buffer(radius, resolution=16)


def seating_group(cx, cy, chair_count, rotation):
    geometries = [circle(cx, cy, TABLE_RADIUS)]

    for seat in range(chair_count):
        angle = rotation + 2 * math.pi * seat / chair_count
        x = cx + SEATING_RING_RADIUS * math.cos(angle)
        y = cy + SEATING_RING_RADIUS * math.sin(angle)
        geometries.append(circle(x, y, CHAIR_RADIUS))

    return geometries


def search_layout(venue, fixed, table_count,
                  chairs_per_table, seed):
    rng = random.Random(seed)
    occupied = list(fixed)
    placed_groups = []

    xmin, ymin, xmax, ymax = venue.bounds
    attempts = 0

    # Multiple positions are sampled; not a prewritten grid.
    for group_index in range(table_count):
        chosen = None

        for _ in range(600):
            attempts += 1

            x = rng.uniform(
                xmin + GROUP_BOUND_RADIUS,
                xmax - GROUP_BOUND_RADIUS
            )
            y = rng.uniform(
                ymin + GROUP_BOUND_RADIUS,
                ymax - GROUP_BOUND_RADIUS
            )
            angle = rng.uniform(0, 2 * math.pi)

            shapes = seating_group(
                x, y, chairs_per_table, angle
            )

            # All proposed footprints must be inside the venue.
            if not all(venue.covers(s) for s in shapes):
                continue

            # Reject internal table/chair or chair/chair overlap.
            internal_collision = any(
                shapes[i].intersects(shapes[j])
                for i in range(len(shapes))
                for j in range(i + 1, len(shapes))
            )
            if internal_collision:
                continue

            # Protect previously placed furniture and fixed structures.
            if any(
                s.intersects(existing)
                for s in shapes
                for existing in occupied
            ):
                continue

            chosen = {
                "group_id": group_index + 1,
                "table_center": [round(x, 5), round(y, 5)],
                "rotation": round(angle, 6),
                "footprints": [
                    [
                        [round(a, 5), round(b, 5)]
                        for a, b in geom.exterior.coords
                    ]
                    for geom in shapes
                ],
            }
            occupied.extend(shapes)
            break

        if chosen is not None:
            placed_groups.append(chosen)

    placed_tables = len(placed_groups)
    placed_chairs = placed_tables * chairs_per_table

    return {
        "seed": seed,
        "attempted_candidates": attempts,
        "placed_groups": placed_groups,
        "placed_tables": placed_tables,
        "placed_chairs": placed_chairs,
        "unplaced_tables": table_count - placed_tables,
        "unplaced_chairs": (
            table_count - placed_tables
        ) * chairs_per_table,
        "fully_placed": placed_tables == table_count,
    }


def main():
    requirements = json.loads(
        REQ.read_text(encoding="utf-8")
    )
    baseline = json.loads(
        BASE.read_text(encoding="utf-8")
    )

    venue = Polygon(baseline["venue_boundary_m"])
    if not venue.is_valid or venue.area <= 0:
        raise ValueError("Invalid venue geometry")

    counts = requirements["requested_counts"]
    table_count = counts["round_table"]
    chair_count = counts["chair"]

    if table_count <= 0 or chair_count % table_count != 0:
        raise ValueError(
            "This baseline supports equal chairs per round table"
        )

    chairs_per_table = chair_count // table_count

    # Existing stage/buffet footprints from the prior
    # controlled baseline are treated as fixed for this test.
    # This is NOT a planner-approved real venue.
    fixed_records = [
        o for o in baseline["objects"]
        if o["class"] in {"stage", "buffet_counter"}
    ]
    fixed = [
        Polygon(o["footprint_coordinates_m"])
        for o in fixed_records
    ]

    if any(not venue.covers(g) for g in fixed):
        raise ValueError("Fixed footprint outside venue")

    alternatives = [
        search_layout(
            venue,
            fixed,
            table_count,
            chairs_per_table,
            seed
        )
        for seed in [11, 23, 37, 51, 79]
    ]

    # Reconstruct every accepted group independently.
    for alt in alternatives:
        all_geometries = list(fixed)

        for group in alt["placed_groups"]:
            shapes = [
                Polygon(ring)
                for ring in group["footprints"]
            ]

            assert all(
                shape.is_valid and venue.covers(shape)
                for shape in shapes
            )
            assert all(
                not shapes[i].intersects(shapes[j])
                for i in range(len(shapes))
                for j in range(i + 1, len(shapes))
            )
            assert all(
                not shape.intersects(previous)
                for shape in shapes
                for previous in all_geometries
            )

            all_geometries.extend(shapes)

        assert (
            alt["placed_tables"] + alt["unplaced_tables"]
            == table_count
        )
        assert (
            alt["placed_chairs"] + alt["unplaced_chairs"]
            == chair_count
        )

    report = {
        "experiment": "STAGE_E5_SPATIAL_CANDIDATES_V1",
        "venue_source": baseline["venue_source"],
        "venue_polygon": baseline["venue_boundary_m"],
        "requested_tables": table_count,
        "requested_chairs": chair_count,
        "chairs_per_table": chairs_per_table,
        "fixed_structure_count": len(fixed),
        "algorithm": "SEEDED_SPATIAL_CANDIDATE_SEARCH",
        "alternatives": alternatives,
        "nsga2_executed": False,
        "real_venue_approved": False,
        "route_connectivity_verified": False,
        "safety_certified": False,
    }

    if DEST.exists():
        raise FileExistsError(
            "Output exists; refusing overwrite"
        )

    DEST.write_text(
        json.dumps(report, indent=2),
        encoding="utf-8"
    )

    print("=== STAGE E5.2 SPATIAL CANDIDATE SEARCH ===")
    print("Requested tables:", table_count)
    print("Requested chairs:", chair_count)
    print("Fixed obstacles:", len(fixed))

    for alt in alternatives:
        print(
            "Seed", alt["seed"],
            "| placed tables:", alt["placed_tables"],
            "| placed chairs:", alt["placed_chairs"],
            "| unplaced tables:", alt["unplaced_tables"],
            "| candidate attempts:", alt["attempted_candidates"]
        )

    print("Geometry replay checks: PASS")
    print("NSGA-II: NOT EXECUTED")
    print("Real venue validation: NOT DONE")
    print("Output:", DEST)


if __name__ == "__main__":
    main()