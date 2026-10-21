import copy
import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "research"))

from f2b_live_research_engine_v1 import validate, run

OUT = ROOT / "outputs"
REQUEST = OUT / "f2b_test_request_v1.json"
ORIGINAL = OUT / "f2b_live_result_v1.json"
DEST = OUT / "f2c_live_engine_tests_v1.json"

def load(path):
    return json.loads(path.read_text(encoding="utf-8"))

def digest(data):
    raw = json.dumps(
        data, sort_keys=True, separators=(",", ":"),
        allow_nan=False
    ).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()

request = load(REQUEST)
original = load(ORIGINAL)

assert original["status"] == "success"
assert len(original["candidate_layouts"][0]["objects"]) == 183

cases = []

def check_denial(name, modify, expected_error):
    candidate = copy.deepcopy(request)
    modify(candidate)

    try:
        validate(candidate)
    except ValueError as error:
        actual = str(error)
        passed = actual == expected_error
    else:
        actual = "INCORRECTLY_ACCEPTED"
        passed = False

    cases.append({
        "case": name,
        "expected": expected_error,
        "actual": actual,
        "pass": passed
    })

    print(
        name,
        "|", actual,
        "|", "PASS" if passed else "FAIL"
    )

def change(path, value):
    def modify(document):
        cursor = document
        for key in path[:-1]:
            cursor = cursor[key]
        cursor[path[-1]] = value
    return modify

print("=== F2C INPUT NEGATIVE TESTS ===")

check_denial(
    "invalid_contract",
    change(["contract_id"], "UNKNOWN_CONTRACT"),
    "INVALID_CONTRACT"
)
check_denial(
    "adaptive_mode_not_yet_supported",
    change(["mode"], "adaptive_revision"),
    "UNSUPPORTED_MODE_REQUIRE_ADAPTIVE_ADAPTER"
)
check_denial(
    "unapproved_real_venue",
    change(["venue_twin", "source_type"], "verified_real"),
    "REAL_VENUE_NOT_APPROVED_FOR_THIS_ENGINE"
)
check_denial(
    "unverified_synthetic_venue",
    change(["venue_twin", "verification_status"], "pending"),
    "UNVERIFIED_SYNTHETIC_VENUE"
)
check_denial(
    "zero_guests",
    change(["event_requirements", "guest_count"], 0),
    "INVALID_GUEST_COUNT"
)
check_denial(
    "unsupported_event",
    change(["event_requirements", "event_type"], "Conference"),
    "EVENT_TYPE_NOT_YET_VALIDATED"
)
check_denial(
    "clearance_below_threshold",
    change(
        ["optimization_request", "experimental_clearance_m"],
        0.3
    ),
    "CLEARANCE_BELOW_EXPERIMENTAL_MINIMUM"
)
check_denial(
    "unsupported_optimizer",
    change(["optimization_request", "algorithm"], "GA"),
    "UNSUPPORTED_ALGORITHM"
)
check_denial(
    "unsupported_guest_count",
    change(["event_requirements", "guest_count"], 240),
    "GUEST_COUNT_OUTSIDE_TESTED_PP1_SCOPE"
)

assert all(case["pass"] for case in cases), (
    "Negative input validation failed"
)

print("Input tests:", len(cases), "/", len(cases), "PASS")

print("=== F2C SAME-SEED REPRODUCIBILITY ===")

# Run the actual live research algorithm again.
# Compare generated result with the saved F2B output.
rerun = run(copy.deepcopy(request))

original_hash = digest(original)
rerun_hash = digest(rerun)
exact_match = original_hash == rerun_hash

if not exact_match:
    # Report the first meaningful mismatch without changing
    # the original saved output.
    def first_difference(a, b, path="root"):
        if type(a) is not type(b):
            return path + ": type changed"
        if isinstance(a, dict):
            if a.keys() != b.keys():
                return path + ": keys changed"
            for k in a:
                d = first_difference(a[k], b[k], path + "." + k)
                if d:
                    return d
            return None
        if isinstance(a, list):
            if len(a) != len(b):
                return path + ": length changed"
            for i, (x, y) in enumerate(zip(a, b)):
                d = first_difference(x, y, f"{path}[{i}]")
                if d:
                    return d
            return None
        if a != b:
            return f"{path}: {a!r} != {b!r}"
        return None

    raise AssertionError(
        "Live engine output mismatch: "
        + str(first_difference(original, rerun))
    )

print("Original objects:", len(original["candidate_layouts"][0]["objects"]))
print("Rerun objects:", len(rerun["candidate_layouts"][0]["objects"]))
print("Original SHA-256:", original_hash)
print("Rerun SHA-256:", rerun_hash)
print("Exact JSON content match:", exact_match)

report = {
    "experiment": "PP1_F2C_LIVE_ENGINE_TESTS_V1",
    "negative_cases": cases,
    "negative_tests_pass": len(cases),
    "negative_tests_total": len(cases),
    "same_seed_exact_content_match": exact_match,
    "original_response_sha256": original_hash,
    "rerun_response_sha256": rerun_hash,
    "live_engine_called": True,
    "supported_scope": "CONTROLLED_SYNTHETIC_INITIAL_DESIGN",
    "adaptive_mode_integrated": False,
    "cross_machine_verified": False,
    "real_venue_verified": False
}

if DEST.exists():
    raise FileExistsError("F2C report already exists")

DEST.write_text(
    json.dumps(report, indent=2),
    encoding="utf-8"
)

print("=== F2C SUMMARY ===")
print("Negative validation:", len(cases), "/9 PASS")
print("Deterministic replay: PASS")
print("Adaptive mode: NOT INTEGRATED")
print("Real-venue validation: NOT DONE")
print("Output:", DEST)
print("F2C LIVE ENGINE TESTS COMPLETE")