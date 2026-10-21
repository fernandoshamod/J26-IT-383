"""Profile the unchanged dynamic request path with standard-library instrumentation."""
import cProfile
import hashlib
import io
import json
import pstats
import sys
from contextlib import ExitStack
from pathlib import Path
from statistics import median
from time import perf_counter
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
from backend.engine import dynamic_package_service as service
from backend.engine import bounded_package_generator as generator
from backend.engine import dynamic_feasibility, package_explanations
from backend.schemas.dynamic_package_request import DynamicPackageRequest

SCENARIOS = {
    "wedding": {"event_type": "Wedding", "event_date": "2026-10-21",
                "start_time": "10:00", "end_time": "18:00",
                "city": "Philadelphia", "state": "PA", "guest_count": 50,
                "budget_lkr": 1000000,
                "required_services": ["Photography", "Decoration"], "top_k": 3},
    "corporate": {"event_type": "Corporate", "event_date": "2026-10-22",
                  "start_time": "09:00", "end_time": "17:00",
                  "city": "Philadelphia", "state": "PA", "guest_count": 40,
                  "budget_lkr": 1000000,
                  "required_services": ["Photography", "Audio Visual"], "top_k": 3},
    "small": {"event_type": "Birthday", "event_date": "2026-10-23",
              "start_time": "10:00", "end_time": "14:00",
              "city": "Philadelphia", "state": "PA", "guest_count": 20,
              "budget_lkr": 600000,
              "required_services": ["Photography"], "top_k": 3},
}
STAGES = [
    (service, "load_service_options", "source_csv"),
    (service, "select_candidates_for_event", "candidate_selection"),
    (service, "load_risk_signals", "risk_inference_including_model_verification"),
    (service, "load_compatibility_rules", "matrix_csv"),
    (service, "service_compatibility", "compatibility_calculation"),
    (service, "generate_bounded_packages", "bounded_generation"),
    (generator, "validate_dynamic_package", "feasibility_calls"),
    (generator, "_ranking", "ranking_calls"),
    (generator, "explain_package", "explanation_calls"),
]


def run_one(scenario, optimized_selector=None, profile=False):
    request = DynamicPackageRequest.model_validate(SCENARIOS[scenario])
    timings = {}
    calls = {}
    profiler = cProfile.Profile() if profile else None
    with ExitStack() as stack:
        for module, name, label in STAGES:
            original = optimized_selector if (module is service and
                name == "select_candidates_for_event" and optimized_selector) else getattr(module, name)
            def wrapped(*args, _original=original, _label=label, **kwargs):
                begin = perf_counter()
                try:
                    return _original(*args, **kwargs)
                finally:
                    timings[_label] = timings.get(_label, 0.0) + (perf_counter() - begin)
                    calls[_label] = calls.get(_label, 0) + 1
            stack.enter_context(patch.object(module, name, wrapped))
        begin = perf_counter()
        if profiler:
            profiler.enable()
        try:
            response = service.generate_dynamic_packages(request)
        finally:
            if profiler:
                profiler.disable()
        elapsed = perf_counter() - begin
    generation = response["generation"]
    record = {
        "scenario": scenario, "event_id": response["event_id"],
        "elapsed_ms": round(elapsed * 1000, 3),
        "stage_ms": {k: round(v * 1000, 3) for k, v in timings.items()},
        "stage_calls": calls,
        "status": generation["status"], "search": generation["search"],
        "returned_packages": len(generation["packages"]),
        "combinations_evaluated": generation["search"]["combinations_evaluated"],
        "candidate_counts": generation["candidate_counts"],
        "selected_candidate_counts": generation["selected_candidate_counts"],
    }
    if profiler:
        stream = io.StringIO()
        pstats.Stats(profiler, stream=stream).sort_stats("cumulative").print_stats(30)
        record["cprofile_top30"] = stream.getvalue()
    return record, response


def main():
    output = []
    for scenario in SCENARIOS:
        for repeat in range(2):
            result, _ = run_one(scenario, profile=(repeat == 0))
            result["repeat"] = repeat + 1
            output.append(result)
            print(scenario, repeat + 1, result["elapsed_ms"], result["stage_ms"], flush=True)
    summary = {
        scenario: {
            "median_ms": median(row["elapsed_ms"] for row in output if row["scenario"] == scenario),
            "min_ms": min(row["elapsed_ms"] for row in output if row["scenario"] == scenario),
            "max_ms": max(row["elapsed_ms"] for row in output if row["scenario"] == scenario),
        } for scenario in SCENARIOS
    }
    target = HERE / "profile_results.json"
    with target.open("x", encoding="utf-8") as stream:
        json.dump({"interpreter": sys.executable, "repeats_per_scenario": 2,
                   "timing_unit": "milliseconds", "memory": "not_measured",
                   "results": output, "summary": summary}, stream, indent=2)
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()