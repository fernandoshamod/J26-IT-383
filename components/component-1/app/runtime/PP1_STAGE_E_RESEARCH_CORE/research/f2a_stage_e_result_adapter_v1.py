import hashlib
import json
import math
from pathlib import Path

import numpy as np
from shapely.geometry import Point, Polygon

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "outputs"
FROZEN = ROOT / "PP1_STAGE_E_FROZEN_V1"
DEST = OUT / "f2a_stage_e_adapter_validation_v1.json"

MANIFEST = FROZEN / "STAGE_E_FREEZE_MANIFEST_V1.json"
CONTRACT = FROZEN / "STAGE_E_CONTRACT_V1.json"


def read_json(path):
    return json.loads(path.read_text(encoding="utf-8"))


def sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


manifest = read_json(MANIFEST)
contract = read_json(CONTRACT)

assert contract["contract_id"] == "STAGE_E_PP1_V1"
assert manifest["freeze_id"] == "PP1_STAGE_E_FROZEN_V1"

# Reject silently modified research sources.
for name, expected in manifest["evidence_files"].items():
    path = OUT / name
    assert path.is_file(), f"Missing evidence: {name}"
    assert sha256(path) == expected, f"Evidence changed: {name}"

for name, expected in manifest["research_scripts"].items():
    path = ROOT / "research" / name
    assert path.is_file(), f"Missing script: {name}"
    assert sha256(path) == expected, f"Script changed: {name}"

baseline = read_json(OUT / "full_layout_baseline_v1.json")
full = read_json(OUT / "e6b_full_group_nsga2_v2.json")
reduction = read_json(
    OUT / "e8f_reduced_requirement_adaptation_v1.json"
)
addition = read_json(
    OUT / "e8g_increased_requirement_adaptation_v1.json"
)

venue = Polygon(baseline["venue_boundary_m"])
fixed_records = [
    record for record in baseline["objects"]
    if record["class"] in ("stage", "buffet_counter")
]

assert venue.is_valid and venue.area > 0
assert len(fixed_records) == 3

fixed_ids = [r["object_id"] for r in fixed_records]
assert len(set(fixed_ids)) == 3

RADIUS = 1.72
CLEARANCE = 0.5

existing = np.asarray(
    full["baseline"]["table_centers"], dtype=float
)
assert existing.shape == (20, 2)


def polygon_record(object_id, category, polygon, group_id=None):
    if not polygon.is_valid or polygon.area <= 0:
        raise ValueError(f"Invalid polygon: {object_id}")
    return {
        "object_id": object_id,
        "class": category,
        "group_id": group_id,
        "footprint_coordinates_m": [
            [round(float(x), 6), round(float(y), 6)]
            for x, y in list(polygon.exterior.coords)
        ],
    }


def generate_objects(centers_by_id):
    objects = [
        {
            "object_id": r["object_id"],
            "class": r["class"],
            "group_id": None,
            "footprint_coordinates_m": r["footprint_coordinates_m"],
        }
        for r in fixed_records
    ]

    for group_id, center in sorted(centers_by_id.items()):
        cx, cy = [float(v) for v in center]

        objects.append(polygon_record(
            group_id + "_table",
            "round_table",
            Point(cx, cy).buffer(0.8, resolution=24),
            group_id,
        ))

        for seat in range(8):
            angle = 2 * math.pi * seat / 8
            chair = Point(
                cx + 1.45 * math.cos(angle),
                cy + 1.45 * math.sin(angle)
            ).buffer(0.27, resolution=12)

            objects.append(polygon_record(
                group_id + f"_chair_{seat+1:02d}",
                "chair",
                chair,
                group_id,
            ))

    return objects


def verify_geometry(objects, centers_by_id):
    ids = [obj["object_id"] for obj in objects]
    assert len(ids) == len(set(ids)), "Duplicate furniture IDs"

    shapes = [
        Polygon(obj["footprint_coordinates_m"])
        for obj in objects
    ]

    outside = sum(
        not shape.is_valid or not venue.covers(shape)
        for shape in shapes
    )
    overlaps = sum(
        shapes[i].intersection(shapes[j]).area > 1e-8
        for i in range(len(shapes))
        for j in range(i + 1, len(shapes))
    )

    envelopes = [
        Point(*map(float, center)).buffer(
            RADIUS, resolution=32
        )
        for center in centers_by_id.values()
    ]

    fixed_shapes = [
        Polygon(r["footprint_coordinates_m"])
        for r in fixed_records
    ]

    clearance_failures = sum(
        envelopes[i].distance(envelopes[j]) < CLEARANCE - 1e-6
        for i in range(len(envelopes))
        for j in range(i + 1, len(envelopes))
    )

    clearance_failures += sum(
        envelope.distance(obstacle) < CLEARANCE - 1e-6
        for envelope in envelopes
        for obstacle in fixed_shapes
    )

    return {
        "object_count": len(objects),
        "outside_count": outside,
        "overlap_count": overlaps,
        "clearance_failure_count": clearance_failures,
        "synthetic_geometry_pass": (
            outside == 0
            and overlaps == 0
            and clearance_failures == 0
        ),
    }


def group_map(centers):
    return {
        f"seating_group_{i+1:04d}": [
            float(x), float(y)
        ]
        for i, (x, y) in enumerate(centers)
    }


def build_response(scenario):
    # Explicitly supported frozen scenarios only.
    if scenario == "initial_160":
        chosen = next(
            item for item in full["selected"]
            if item["label"] == "best_stage_proximity"
        )
        groups = group_map(chosen["table_centers"])
        guests = 160
        source_name = "e6b_full_group_nsga2_v2.json"
        metrics = {
            "stage_distance": chosen[
                "average_stage_proximity_synthetic_m"
            ],
            "clearance": chosen[
                "minimum_clearance_synthetic_m"
            ],
        }
        permission_mode = "NOT_APPLICABLE_INITIAL_DESIGN"

    elif scenario == "reduced_120":
        chosen = next(
            item for item in reduction["selected"]
            if item["label"] == "best_stage_proximity"
        )
        groups = chosen["group_centers_by_id"]
        guests = 120
        source_name = (
            "e8f_reduced_requirement_adaptation_v1.json"
        )
        metrics = {
            "stage_distance": chosen["stage_distance"],
            "clearance": chosen["clearance"],
        }
        permission_mode = "SIMULATED_APPROVAL_ONLY"

    elif scenario == "increased_200":
        chosen = next(
            item for item in addition["selected"]
            if item["label"] == "best_stage_proximity"
        )
        groups = group_map(existing)
        groups.update(chosen["new_groups_by_id"])
        guests = 200
        source_name = (
            "e8g_increased_requirement_adaptation_v1.json"
        )
        metrics = {
            "stage_distance": chosen["stage_distance"],
            "clearance": chosen["minimum_clearance"],
        }
        permission_mode = "SIMULATED_APPROVAL_ONLY"

    else:
        raise ValueError(
            f"UNSUPPORTED_FROZEN_SCENARIO: {scenario}"
        )

    objects = generate_objects(groups)
    verification = verify_geometry(objects, groups)

    expected_count = 3 + 9 * (guests // 8)
    assert len(objects) == expected_count
    assert verification["synthetic_geometry_pass"]

    return {
        "contract_id": "STAGE_E_PP1_V1",
        "run_id": f"FROZEN_{scenario.upper()}",
        "status": "success",
        "event_id": f"CONTROLLED_WEDDING_{guests}",
        "candidate_layouts": [{
            "layout_id": f"{scenario}_best_stage_proximity",
            "objects": objects,
            "group_centers_m": groups,
            "objective_metrics": metrics,
            "constraint_results": verification,
        }],
        "permission_decisions": [{
            "scope": permission_mode,
            "real_planner_approval": False,
        }],
        "validation_flags": {
            "synthetic_geometry_pass": True,
            "planner_approval_verified": False,
            "real_venue_validated": False,
            "route_connectivity_verified": False,
            "safety_certified": False,
        },
        "provenance": {
            "algorithm_version": "FROZEN_STAGE_E_PP1",
            "source_evidence": source_name,
            "source_hashes": {
                source_name:
                    manifest["evidence_files"][source_name]
            },
            "random_seed": None,
        },
        "adapter_status": "FROZEN_EVIDENCE_NORMALIZATION_ONLY",
    }


scenarios = ["initial_160", "reduced_120", "increased_200"]
results = {}

print("=== F2A STAGE E CONTRACT ADAPTER ===")
print("Frozen SHA-256 source verification: PASS")

for scenario in scenarios:
    response = build_response(scenario)
    candidate = response["candidate_layouts"][0]
    check = candidate["constraint_results"]

    assert response["status"] == "success"
    assert check["synthetic_geometry_pass"]
    assert len(candidate["objects"]) == check["object_count"]

    results[scenario] = response

    print(
        scenario,
        "| objects:", check["object_count"],
        "| outside:", check["outside_count"],
        "| overlaps:", check["overlap_count"],
        "| clearance failures:",
        check["clearance_failure_count"],
        "| PASS:", check["synthetic_geometry_pass"],
    )

# Fail closed for unsupported scenarios.
rejected = False
try:
    build_response("arbitrary_real_venue")
except ValueError:
    rejected = True

assert rejected, "Unsupported scenario was not rejected"

report = {
    "experiment": "PP1_STAGE_E_F2A_ADAPTER_V1",
    "contract_id": "STAGE_E_PP1_V1",
    "validated_scenarios": results,
    "unsupported_scenario_rejected": rejected,
    "frozen_source_hashes_verified": True,
    "live_optimizer_integrated": False,
    "dynamic_venue_input_supported": False,
    "production_backend_integrated": False,
    "real_venue_validated": False,
}

if DEST.exists():
    raise FileExistsError("F2A evidence already exists")

DEST.write_text(
    json.dumps(report, indent=2), encoding="utf-8"
)

print("Unsupported scenario: REJECTED")
print("Unified output contract: VALIDATED FOR 3 FROZEN CASES")
print("Live research optimizer integration: PENDING")
print("Real venue validation: NOT DONE")
print("Output:", DEST)
print("F2A ADAPTER VALIDATION COMPLETE")