"""
The full execution-phase loop, closed: solve, detect divergence
(twin), predict the cascade of doing nothing (simulation), then actually
decide what to do about it (re-optimisation) and report the cost signal
that would go to Component 4. Sections 4.2.1 and 4.2.2 in full.

Run from the repository root:
    python -m examples.run_reoptimization_example
"""

import time

from examples.run_simulation_example import build_disrupted_wedding, format_minutes
from scheduling_engine import reoptimize


def main() -> None:
    wedding, resources, schedule, twin, now_minutes, divergences, predicted_extra_duration = (
        build_disrupted_wedding()
    )

    print(f"--- Re-optimising at t={format_minutes(now_minutes)} ---")
    started = time.time()
    result = reoptimize(
        wedding.activities, resources, schedule, twin, now_minutes,
        predicted_extra_duration_minutes=predicted_extra_duration,
        time_limit_seconds=5.0,
    )
    wall_time = time.time() - started

    print(f"Feasible: {result.is_feasible} | status: {result.status_name}")
    print(f"Solver-reported time: {result.solve_time_seconds:.3f}s | wall time: {wall_time:.3f}s "
          f"(target: under 5s)\n")

    if not result.is_feasible:
        print("Conflicting locked activities:", result.conflicting_pinned_activity_ids)
        return

    print("Revised schedule (only activities that moved vs. the original plan):")
    for activity_id, revised in sorted(result.schedule.activities.items(), key=lambda kv: kv[1].start_minutes):
        original = schedule.activities[activity_id]
        if revised.start_minutes == original.start_minutes and revised.end_minutes == original.end_minutes:
            continue
        print(
            f"  {activity_id:<20} {format_minutes(original.start_minutes)}-{format_minutes(original.end_minutes)}"
            f"  ->  {format_minutes(revised.start_minutes)}-{format_minutes(revised.end_minutes)}"
        )

    print(f"\nCost signal to Component 4:")
    print(f"  total_delay_minutes:      {result.cost_signal.total_delay_minutes}")
    print(f"  delayed_activity_ids:     {result.cost_signal.delayed_activity_ids}")
    print(f"  resource_overtime_minutes: {result.cost_signal.resource_overtime_minutes}")


if __name__ == "__main__":
    main()
