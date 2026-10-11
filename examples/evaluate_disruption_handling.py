"""
Disruption-handling evaluation (proposal Section 3.6 "Comparative
performance validation"; Objective 6; Table 6's metrics).

"Two hundred generated scenarios containing disruptions of known type,
magnitude and timing are processed by the proposed method and by each of
the three baselines. Because the same scenario and the same disruption
are presented to every method, observed differences are attributable to
the method rather than to scenario variation."

Four strategies are compared on each generated scenario:
  - no_reschedule        (Table 5 lower bound)
  - naive_forward_shift  (Table 5)
  - greedy               (Table 5's "absorb into slack, respect locks" —
                           implemented as simulate_cascade; see baselines.py)
  - cp_reoptimize        (this project's own Objective 5 contribution)

By default this runs THREE generator configurations back to back and
prints all three tables, rather than one replacing another:
  - tight     the original generator, no deliberate slack at all (every
              result reported before `include_buffer` existed used this)
  - buffered  the same generator with a declared, randomised contingency
              buffer added after each precedence edge
              (`generate_scenario(..., include_buffer=True)`) — testing
              whether PRECEDENCE slack closes the gap to the proposal's
              60% delay-absorbed target. It didn't.
  - generous  the same (unbuffered) generator but with every resource
              role given 2 units instead of the normal mix (three
              singleton roles) (`generate_scenario(..., generous_resources=True)`)
              — testing whether RESOURCE slack, instead of precedence
              slack, is the real bottleneck.
Each is kept deliberately, not as a historical artifact: comparing them
is the point, and the proposal's own validation strategy (Section 3.6)
calls for limitations to be stated directly rather than quietly
superseded by a later, better-looking run.

Run from the repository root:
    python -m examples.evaluate_disruption_handling                   # all three configurations, 200 scenarios each
    python -m examples.evaluate_disruption_handling --count 20        # a quick subset of all three
    python -m examples.evaluate_disruption_handling --only tight      # just the original
    python -m examples.evaluate_disruption_handling --only buffered   # just the precedence-buffer version
    python -m examples.evaluate_disruption_handling --only generous   # just the generous-resources version
"""

from __future__ import annotations

import argparse
import statistics
import time
from dataclasses import dataclass, field

from scheduling_engine.baselines import naive_forward_shift, no_reschedule
from scheduling_engine.conflict_detection import verify_schedule
from scheduling_engine.models import Schedule
from scheduling_engine.reoptimization import reoptimize
from scheduling_engine.scenario_generation import generate_scenario, inject_disruption
from scheduling_engine.simulation import simulate_cascade

STRATEGIES = ["no_reschedule", "naive_forward_shift", "greedy", "cp_reoptimize"]


@dataclass
class StrategyOutcome:
    schedule: Schedule | None
    solve_time_seconds: float
    conflict_count: int | None = None  # None only when infeasible (no schedule to check)
    proportion_delay_absorbed: float | None = None
    total_overtime_minutes: int | None = None


@dataclass
class StrategyStats:
    conflict_free_count: int = 0
    infeasible_count: int = 0
    total: int = 0
    solve_times: list[float] = field(default_factory=list)
    absorbed_fractions: list[float] = field(default_factory=list)
    overtime_minutes: list[int] = field(default_factory=list)


def _overall_end(schedule: Schedule) -> int:
    return max(s.end_minutes for s in schedule.activities.values())


def _total_overtime_minutes(original: Schedule, revised: Schedule, resources) -> int:
    total = 0
    for r in resources:
        original_last_use = max(
            (s.end_minutes for s in original.activities.values() if r.id in s.assigned_resource_ids),
            default=None,
        )
        revised_last_use = max(
            (s.end_minutes for s in revised.activities.values() if r.id in s.assigned_resource_ids),
            default=None,
        )
        if original_last_use is not None and revised_last_use is not None:
            total += max(0, revised_last_use - original_last_use)
    return total


def _evaluate(activities, resources, original_schedule, revised_schedule, injected_delay, elapsed) -> StrategyOutcome:
    conflicts = verify_schedule(activities, resources, revised_schedule.activities)
    conflict_count = len(conflicts)

    # A schedule with a precedence or resource conflict isn't physically
    # realizable, so comparing its nominal end time to the original plan
    # is meaningless — e.g. no_reschedule doesn't touch any downstream
    # activity's recorded time at all, so it would otherwise show up as
    # "100% delay absorbed" simply because nothing was ever updated, not
    # because the disruption was actually handled. Only report
    # delay-absorbed/overtime for outcomes that are actually conflict-free.
    absorbed = None
    overtime = None
    if conflict_count == 0:
        final_delay = _overall_end(revised_schedule) - _overall_end(original_schedule)
        absorbed = max(0.0, min(1.0, 1 - final_delay / injected_delay)) if injected_delay > 0 else 1.0
        overtime = _total_overtime_minutes(original_schedule, revised_schedule, resources)

    return StrategyOutcome(
        schedule=revised_schedule,
        solve_time_seconds=elapsed,
        conflict_count=conflict_count,
        proportion_delay_absorbed=absorbed,
        total_overtime_minutes=overtime,
    )


def run_one_scenario(
    seed: int, include_buffer: bool, generous_resources: bool
) -> dict[str, StrategyOutcome] | None:
    event, resources, schedule = generate_scenario(
        seed, include_buffer=include_buffer, generous_resources=generous_resources
    )
    if not schedule.is_feasible:
        return None
    scenario = inject_disruption(event, resources, schedule, seed)
    activities = event.activities

    outcomes: dict[str, StrategyOutcome] = {}

    t0 = time.time()
    revised = no_reschedule(schedule, scenario.disrupted_activity_id, scenario.injected_delay_minutes)
    outcomes["no_reschedule"] = _evaluate(
        activities, resources, schedule, revised, scenario.injected_delay_minutes, time.time() - t0
    )

    t0 = time.time()
    revised = naive_forward_shift(schedule, scenario.disrupted_activity_id, scenario.injected_delay_minutes)
    outcomes["naive_forward_shift"] = _evaluate(
        activities, resources, schedule, revised, scenario.injected_delay_minutes, time.time() - t0
    )

    t0 = time.time()
    cascade = simulate_cascade(
        activities, resources, schedule, scenario.twin, scenario.now_minutes,
        predicted_extra_duration_minutes=scenario.predicted_extra_duration_minutes,
    )
    elapsed = time.time() - t0
    revised = Schedule(is_feasible=True, activities=cascade.predicted_activities)
    outcomes["greedy"] = _evaluate(
        activities, resources, schedule, revised, scenario.injected_delay_minutes, elapsed
    )

    t0 = time.time()
    result = reoptimize(
        activities, resources, schedule, scenario.twin, scenario.now_minutes,
        predicted_extra_duration_minutes=scenario.predicted_extra_duration_minutes,
        time_limit_seconds=5.0,
    )
    elapsed = time.time() - t0
    if result.is_feasible:
        outcomes["cp_reoptimize"] = _evaluate(
            activities, resources, schedule, result.schedule, scenario.injected_delay_minutes, elapsed
        )
    else:
        outcomes["cp_reoptimize"] = StrategyOutcome(schedule=None, solve_time_seconds=elapsed)

    return outcomes


def run_evaluation(
    count: int, seed_start: int, include_buffer: bool, generous_resources: bool, label: str
) -> None:
    stats = {name: StrategyStats() for name in STRATEGIES}
    generation_failures = 0

    print(f"\n=== {label} ===")
    started = time.time()
    for i in range(count):
        seed = seed_start + i
        outcomes = run_one_scenario(seed, include_buffer, generous_resources)
        if outcomes is None:
            generation_failures += 1
            continue
        for name in STRATEGIES:
            outcome = outcomes[name]
            s = stats[name]
            s.total += 1
            s.solve_times.append(outcome.solve_time_seconds)
            if outcome.schedule is None:
                s.infeasible_count += 1
                continue
            if outcome.conflict_count == 0:
                s.conflict_free_count += 1
                s.absorbed_fractions.append(outcome.proportion_delay_absorbed)
                s.overtime_minutes.append(outcome.total_overtime_minutes)

        if (i + 1) % 50 == 0 or (i + 1) == count:
            print(f"  ...{i + 1}/{count} scenarios processed")

    elapsed = time.time() - started

    print(f"\nScenarios generated: {count - generation_failures}/{count} "
          f"({generation_failures} infeasible at generation, skipped)")
    print(f"Total wall time: {elapsed:.1f}s\n")

    header = f"{'strategy':<20} {'conflict-free':>14} {'infeasible':>11} {'delay absorbed':>18} {'overtime(min)':>16} {'latency(s)':>11}"
    print(header)
    print("-" * len(header))
    for name in STRATEGIES:
        s = stats[name]
        if s.total == 0:
            continue
        conflict_free_rate = s.conflict_free_count / s.total
        n = len(s.absorbed_fractions)
        absorbed_mean = statistics.mean(s.absorbed_fractions) if s.absorbed_fractions else float("nan")
        overtime_mean = statistics.mean(s.overtime_minutes) if s.overtime_minutes else float("nan")
        latency_mean = statistics.mean(s.solve_times)
        print(
            f"{name:<20} {conflict_free_rate:>13.1%} {s.infeasible_count:>11} "
            f"{absorbed_mean:>13.1%} (n={n:<3}) {overtime_mean:>11.1f} (n={n:<3}) {latency_mean:>11.4f}"
        )

    print(
        "\n'delay absorbed' and 'overtime' are computed ONLY over conflict-free outcomes (n shown) — "
        "a schedule with a precedence or resource conflict isn't physically realizable, so comparing "
        "its nominal end time to the original plan would be meaningless, not merely optimistic.\n"
        "'infeasible' for cp_reoptimize means CP-SAT PROVED no revised schedule could satisfy "
        "every locked activity and resource constraint at once — a correct refusal, not a failure; "
        "see conflicting_pinned_activity_ids on the ReoptimizationResult for which activities were responsible. "
        "The other three strategies cannot report this; they always produce *a* schedule, "
        "which is exactly why their conflict-free rate is the metric that matters most for them."
    )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--count", type=int, default=200, help="number of scenarios to generate, per configuration")
    parser.add_argument("--seed-start", type=int, default=0)
    parser.add_argument(
        "--only", choices=["tight", "buffered", "generous"], default=None,
        help="run only one configuration instead of all three (default: run and print all three)",
    )
    args = parser.parse_args()

    if args.only in (None, "tight"):
        run_evaluation(
            args.count, args.seed_start, include_buffer=False, generous_resources=False,
            label="Original generator (no deliberate slack between activities)",
        )
    if args.only in (None, "buffered"):
        run_evaluation(
            args.count, args.seed_start, include_buffer=True, generous_resources=False,
            label="With realistic contingency buffer (generate_scenario(..., include_buffer=True))",
        )
    if args.only in (None, "generous"):
        run_evaluation(
            args.count, args.seed_start, include_buffer=False, generous_resources=True,
            label="With generous resources — 2 units of every role (generate_scenario(..., generous_resources=True))",
        )


if __name__ == "__main__":
    main()
