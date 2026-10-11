"""
Benchmark validation harness (proposal Objective 6: "evaluate the
component against PSPLIB benchmark instances for scheduling correctness
and solve time"; Section 3.6 "Correctness validation").

For every instance: solve it, independently re-verify the result with
conflict_detection.verify_schedule (not trusting the solver's own
feasibility claim), and check the makespan never drops below the
instance's own critical-path lower bound (a bug canary — resource
contention can only add delay, never remove it).

Solved with minimize_makespan=False: this harness checks feasibility and
conflict-freedom (Objective 6's "scheduling correctness"), not makespan
optimality, and we have no official published-optimal values to compare
against here anyway (see data/psplib/README.md). Proving optimality would
also be the wrong thing to measure through psplib.py's unit-materialised
resource model specifically, since many interchangeable identical units
make the "is this provably the shortest possible makespan" search far
harder than feasibility itself, for no planner-visible benefit — see the
note on this in solver.py's solve_planning_phase docstring.

Run from the repository root:
    python -m examples.validate_psplib                  # all 480 j30 instances
    python -m examples.validate_psplib --limit 30        # a quick subset
"""

from __future__ import annotations

import argparse
import statistics
import time
from pathlib import Path

from scheduling_engine.conflict_detection import verify_schedule
from scheduling_engine.psplib import parse_sm, to_scheduling_model
from scheduling_engine.solver import solve_planning_phase

INSTANCE_DIR = Path(__file__).resolve().parent.parent / "data" / "psplib" / "j30"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--limit", type=int, default=None, help="only run the first N instances")
    parser.add_argument("--time-limit", type=float, default=10.0, help="per-instance solver time limit, seconds")
    parser.add_argument(
        "--optimize-makespan",
        action="store_true",
        help="also search for a provably-minimal makespan (much slower; see module docstring)",
    )
    args = parser.parse_args()

    instance_paths = sorted(INSTANCE_DIR.glob("*.sm"))
    if args.limit:
        instance_paths = instance_paths[: args.limit]

    solve_times: list[float] = []
    feasible_count = 0
    conflict_free_count = 0
    below_lower_bound_count = 0
    timeout_count = 0
    other_failures: list[str] = []

    started = time.time()
    for i, path in enumerate(instance_paths, start=1):
        instance = parse_sm(path)
        event, resources = to_scheduling_model(instance)

        schedule = solve_planning_phase(
            [event],
            resources,
            time_limit_seconds=args.time_limit,
            minimize_makespan=args.optimize_makespan,
        )
        solve_times.append(schedule.solve_time_seconds)

        if not schedule.is_feasible:
            if schedule.status_name == "UNKNOWN":
                timeout_count += 1
            else:
                other_failures.append(f"{instance.name}: {schedule.status_name}")
            continue

        feasible_count += 1
        conflicts = verify_schedule(event.activities, resources, schedule.activities)
        if not conflicts:
            conflict_free_count += 1
        else:
            other_failures.append(f"{instance.name}: {len(conflicts)} conflict(s) in solver output")

        if schedule.makespan_minutes < instance.critical_path_lower_bound:
            below_lower_bound_count += 1
            other_failures.append(
                f"{instance.name}: makespan {schedule.makespan_minutes} < "
                f"lower bound {instance.critical_path_lower_bound}"
            )

        if i % 50 == 0 or i == len(instance_paths):
            print(f"  ...{i}/{len(instance_paths)} instances processed")

    total = len(instance_paths)
    elapsed = time.time() - started

    print()
    print(f"Instances run:            {total}")
    print(f"Feasible:                 {feasible_count}/{total} ({feasible_count / total:.1%})")
    print(f"Conflict-free (verified): {conflict_free_count}/{total} ({conflict_free_count / total:.1%})")
    print(f"Solver timeouts:          {timeout_count}")
    print(f"Below critical-path bound (bug canary): {below_lower_bound_count}")
    print(f"Solve time (s): mean={statistics.mean(solve_times):.3f} "
          f"median={statistics.median(solve_times):.3f} max={max(solve_times):.3f}")
    print(f"Total wall time: {elapsed:.1f}s")

    if other_failures:
        print(f"\n{len(other_failures)} issue(s):")
        for msg in other_failures[:20]:
            print("  -", msg)
        if len(other_failures) > 20:
            print(f"  ... and {len(other_failures) - 20} more")


if __name__ == "__main__":
    main()
