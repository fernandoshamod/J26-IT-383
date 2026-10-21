import json
import math
import random
from pathlib import Path
from shapely.geometry import Point, Polygon

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "outputs"
DEST = OUT / "e8e_requirement_scenarios_v1.json"

base = json.loads(
    (OUT / "full_layout_baseline_v1.json").read_text(encoding="utf-8")
)

venue = Polygon(base["venue_boundary_m"])
fixed = [
    Polygon(o["footprint_coordinates_m"])
    for o in base["objects"]
    if o["class"] in {"stage", "buffet_counter"}
]

assert venue.is_valid and venue.area > 0
assert len(fixed) == 3

# Experimental assumptions; not regulatory standards.
table_radius = 0.80
chair_radius = 0.27
chair_ring = 1.45
group_radius = chair_ring + chair_radius
min_clearance = 0.50

scenarios = [
    {"name": "reduced_attendance", "guests": 120, "seats_per_table": 8},
    {"name": "original_attendance", "guests": 160, "seats_per_table": 8},
    {"name": "increased_attendance", "guests": 200, "seats_per_table": 8},
]

xmin, ymin, xmax, ymax = venue.bounds


def furniture(center, seats):
    cx, cy = center
    shapes = [Point(cx, cy).buffer(table_radius, resolution=24)]
    for seat in range(seats):
        angle = 2 * math.pi * seat / seats
        shapes.append(
            Point(
                cx + chair_ring * math.cos(angle),
                cy + chair_ring * math.sin(angle)
            ).buffer(chair_radius, resolution=12)
        )
    return shapes


def evaluate_scenario(scenario):
    guests = scenario["guests"]
    seats = scenario["seats_per_table"]

    if guests <= 0 or seats <= 0:
        raise ValueError("Guest count and seats must be positive")

    table_count = math.ceil(guests / seats)

    # A bounded multistart lattice search.
    # Candidate positions are derived from venue geometry.
    results = []
    step = 2 * group_radius + min_clearance + 0.20

    for seed in [11, 23, 37, 51, 79]:
        rng = random.Random(seed)
        candidates = []

        shift_x = rng.uniform(0, 0.17)
        shift_y = rng.uniform(0, 0.17)

        x = xmin + group_radius + shift_x
        while x + group_radius <= xmax + 1e-9:
            y = ymin + group_radius + shift_y
            while y + group_radius <= ymax + 1e-9:
                candidates.append((x, y))
                y += step
            x += step

        rng.shuffle(candidates)

        chosen = []
        envelopes = []

        for cx, cy in candidates:
            if len(chosen) >= table_count:
                break

            envelope = Point(cx, cy).buffer(
                group_radius, resolution=32
            )

            if not venue.covers(envelope):
                continue

            if any(
                envelope.distance(o) < min_clearance
                for o in fixed
            ):
                continue

            if any(
                envelope.distance(p) < min_clearance
                for p in envelopes
            ):
                continue

            chosen.append((cx, cy))
            envelopes.append(envelope)

        all_shapes = list(fixed)
        for center in chosen:
            all_shapes.extend(furniture(center, seats))

        outside = sum(not venue.covers(s) for s in all_shapes)
        overlaps = sum(
            all_shapes[i].intersection(all_shapes[j]).area > 1e-8
            for i in range(len(all_shapes))
            for j in range(i + 1, len(all_shapes))
        )

        full = len(chosen) == table_count
        geometry_pass = full and outside == 0 and overlaps == 0

        results.append({
            "seed": seed,
            "requested_tables": table_count,
            "placed_tables": len(chosen),
            "represented_chairs": len(chosen) * seats,
            "total_reconstructed_objects": len(all_shapes),
            "outside_count": outside,
            "overlap_pairs": overlaps,
            "full_requirement_met": full,
            "experimental_geometry_pass": geometry_pass,
        })

    return {
        "scenario": scenario["name"],
        "guests": guests,
        "seats_per_table": seats,
        "tables_required": table_count,
        "chairs_requested": table_count * seats,
        "total_objects_requested": table_count * (1 + seats) + len(fixed),
        "runs": results,
        "passing_runs": sum(
            r["experimental_geometry_pass"] for r in results
        ),
    }


evaluations = [evaluate_scenario(s) for s in scenarios]

report = {
    "experiment": "PP1_E8E_REQUIREMENT_SCENARIOS_V1",
    "venue": "CONTROLLED_SYNTHETIC_ASSUMPTION",
    "minimum_clearance_synthetic_m": min_clearance,
    "scenarios": evaluations,
    "optimizer": "CONSTRAINT_AWARE_LATTICE_MULTISTART_NOT_NSGA2",
    "planner_permission_checked": False,
    "adaptive_reoptimization_executed": False,
    "real_venue_validated": False,
    "safety_certified": False,
}

if DEST.exists():
    raise FileExistsError("Report exists; refusing overwrite")

DEST.write_text(json.dumps(report, indent=2), encoding="utf-8")

print("=== E8E REQUIREMENT CHANGE EXPERIMENTS ===")
for e in evaluations:
    print(
        e["scenario"],
        "| guests:", e["guests"],
        "| tables:", e["tables_required"],
        "| objects:", e["total_objects_requested"],
        "| passing runs:", str(e["passing_runs"]) + "/5",
        "| best placed:", max(r["placed_tables"] for r in e["runs"])
    )

print("Changed-requirement NSGA-II: NOT EXECUTED")
print("Planner authorization: NOT TESTED FOR ADD/REMOVE")
print("Real-world safety: NOT VERIFIED")
print("Output:", DEST)
print("E8E EXPERIMENT COMPLETED")