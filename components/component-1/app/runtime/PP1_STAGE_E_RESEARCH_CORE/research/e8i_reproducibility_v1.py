import json
import math
import os
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RESEARCH = ROOT / "research"
OUT = ROOT / "outputs"
DEST = OUT / "e8i_reproducibility_v1.json"

EXPERIMENTS = [
    (
        "full_layout",
        "e6b_full_group_nsga2_v2.py",
        "e6b_full_group_nsga2_v2.json",
        False,
    ),
    (
        "adaptive_move",
        "e7a_permission_aware_reoptimization_v2.py",
        "e7a_adaptive_reoptimization_v2.json",
        True,
    ),
    (
        "guest_reduction",
        "e8f_reduced_requirement_adaptation_v1.py",
        "e8f_reduced_requirement_adaptation_v1.json",
        True,
    ),
    (
        "guest_addition",
        "e8g_increased_requirement_adaptation_v1.py",
        "e8g_increased_requirement_adaptation_v1.json",
        True,
    ),
]

IGNORE_KEYS = {"runtime_seconds"}
TOLERANCE = 0.0001


def compare(actual, expected, path="root"):
    if isinstance(actual, dict) and isinstance(expected, dict):
        keys_a = set(actual) - IGNORE_KEYS
        keys_b = set(expected) - IGNORE_KEYS

        if keys_a != keys_b:
            raise AssertionError(
                f"{path}: key mismatch: {keys_a ^ keys_b}"
            )

        for key in sorted(keys_a):
            compare(actual[key], expected[key], f"{path}.{key}")
        return

    if isinstance(actual, list) and isinstance(expected, list):
        if len(actual) != len(expected):
            raise AssertionError(f"{path}: list length mismatch")

        for i, (a, b) in enumerate(zip(actual, expected)):
            compare(a, b, f"{path}[{i}]")
        return

    if (
        isinstance(actual, (int, float))
        and not isinstance(actual, bool)
        and isinstance(expected, (int, float))
        and not isinstance(expected, bool)
    ):
        if not math.isclose(
            actual, expected, abs_tol=TOLERANCE, rel_tol=0
        ):
            raise AssertionError(
                f"{path}: rerun={actual}, original={expected}"
            )
        return

    if actual != expected:
        raise AssertionError(
            f"{path}: rerun={actual!r}, original={expected!r}"
        )


def execute(script, args):
    result = subprocess.run(
        [sys.executable, str(script), *args],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        timeout=300,
    )

    if result.returncode != 0:
        raise RuntimeError(
            f"Execution failed: {script.name}\n"
            + result.stdout[-3000:]
            + result.stderr[-3000:]
        )

    return result.stdout


def run_experiment(label, filename, output_name, gated):
    source = RESEARCH / filename
    original_output = OUT / output_name

    if not source.exists() or not original_output.exists():
        raise FileNotFoundError(
            f"Required source/evidence missing: {label}"
        )

    source_text = source.read_text(encoding="utf-8-sig")
    temp_output_name = "e8i_temp_" + output_name
    temp_output = OUT / temp_output_name

    if source_text.count(output_name) != 1:
        raise RuntimeError(
            f"Cannot safely redirect output in {filename}"
        )

    if temp_output.exists():
        raise FileExistsError(
            f"Temporary output already exists: {temp_output}"
        )

    fd, script_path = tempfile.mkstemp(
        prefix="e8i_rerun_",
        suffix=".py",
        dir=str(RESEARCH),
    )
    os.close(fd)
    temporary_script = Path(script_path)

    try:
        patched = source_text.replace(
            output_name, temp_output_name, 1
        )
        temporary_script.write_text(
            patched, encoding="utf-8"
        )

        # Permission-denied runs must not produce output.
        if gated:
            denied_stdout = execute(temporary_script, [])
            if "NSGA-II BLOCKED" not in denied_stdout:
                raise AssertionError(
                    f"{label}: denied run did not report blocking"
                )
            if temp_output.exists():
                raise AssertionError(
                    f"{label}: denied run wrote an output"
                )

        args = ["--simulate-approval"] if gated else []
        approved_stdout = execute(temporary_script, args)

        if not temp_output.is_file():
            raise AssertionError(
                f"{label}: rerun did not produce evidence"
            )

        actual = json.loads(
            temp_output.read_text(encoding="utf-8")
        )
        expected = json.loads(
            original_output.read_text(encoding="utf-8")
        )

        compare(actual, expected, path=label)

        print(
            label,
            "| numeric/data replay: PASS",
            "| denied gate:",
            "PASS" if gated else "N/A",
        )

        return {
            "experiment": label,
            "result_match_within_tolerance": True,
            "denied_gate_rechecked": gated,
            "source_script": filename,
            "compared_evidence": output_name,
        }

    finally:
        temporary_script.unlink(missing_ok=True)
        temp_output.unlink(missing_ok=True)


if DEST.exists():
    raise FileExistsError(
        "Final reproducibility report exists; refusing overwrite"
    )

print("=== E8I DETERMINISTIC REPRODUCIBILITY ===")

results = [
    run_experiment(*experiment)
    for experiment in EXPERIMENTS
]

report = {
    "experiment": "PP1_E8I_REPRODUCIBILITY_V1",
    "results": results,
    "all_replays_match": True,
    "absolute_numeric_tolerance": TOLERANCE,
    "runtime_comparison_excluded": True,
    "same_environment_replay": True,
    "cross_machine_reproducibility": False,
    "real_venue_validation": False,
    "stage_e_scope": "CONTROLLED_SYNTHETIC_PP1",
}

DEST.write_text(
    json.dumps(report, indent=2), encoding="utf-8"
)

print("Reproduced experiments:", len(results), "/4")
print("Reproducibility: PASS")
print("Cross-machine validation: NOT DONE")
print("Real-world validation: NOT DONE")
print("Output:", DEST)
print("E8I COMPLETE")