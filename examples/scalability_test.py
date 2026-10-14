"""
Scalability test (proposal NFR-04, against the NFR-01 latency limit).

NFR-04: "The system shall handle at least five concurrent events, each
with up to 30 activities and 40 resources, without exceeding the latency
requirement." NFR-01: "Disruption detection and schedule re-optimisation
shall complete within 5 seconds of the triggering event."

Method, for each day size (1-8 concurrent events, 30 activities each):
  1. Generate a multi-event day (scheduling_engine/scale_generation.py):
     30 own resources per event plus a shared pool of 10 that every event
     competes for, events overlapping in time, one planner-locked
     activity per event.
  2. Plan it with the CP-SAT solver and verify it independently.
  3. Run random disruptions through the LIVE service (EventOperations,
     the same code the dashboard uses): replay on-time check-ins up to an
     activity's planned end, let it overrun by 15-60 min with no
     completion check-in, then time ONE clock tick. That tick does
     everything NFR-01 counts: detection (twin), the do-nothing
     simulation (SimPy) and, when needed, re-optimisation (CP-SAT).
  4. Independently verify every revised schedule.

Outputs: results/scalability/metrics.json and latency_vs_events.png.
Run from the repository root:
    python -m examples.scalability_test            # full run (~1-3 min)
    python -m examples.scalability_test --quick    # smaller, for a smoke test
"""

from __future__ import annotations

import argparse
import json
import random
import statistics
import time
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

from api.scenario import _descendants, play_on_time
from examples.train_prediction_models import ACCENT, INK_MUTED, NEUTRAL, _style
from scheduling_engine.conflict_detection import verify_schedule
from scheduling_engine.operations import EventOperations
from scheduling_engine.scale_generation import generate_day, lock_some
from scheduling_engine.solver import solve_planning_phase

RESULTS_DIR = Path(__file__).resolve().parent.parent / "results" / "scalability"
LATENCY_LIMIT_SECONDS = 5.0
OVERRUN_RANGE = (15, 60)


def plan_day(seed: int, n_events: int, locks: bool):
    events, resources = generate_day(seed, n_events)
    started = time.perf_counter()
    first = solve_planning_phase(events, resources)
    if not first.is_feasible:
        return None
    if locks:
        lock_some(events, first, seed)
    base = EventOperations(events, resources, tolerance_minutes=10)
    base.plan()
    plan_seconds = time.perf_counter() - started
    activities = [a for e in events for a in e.activities]
    plan_conflicts = len(verify_schedule(activities, resources, base.schedule.activities))
    return base, plan_seconds, plan_conflicts


def fork(base: EventOperations) -> EventOperations:
    """A fresh live state on the same plan (no check-ins yet)."""
    ops = EventOperations(base.events, base.resources, tolerance_minutes=base.tolerance_minutes)
    ops.schedule = base.schedule
    ops.twin = ops._new_twin(base.schedule, [])
    ops.now = base.now
    ops.schedule_version = 1
    return ops


def run_trial(base: EventOperations, rng: random.Random) -> dict:
    ops = fork(base)
    candidates = [a for a in ops.activities
                  if _descendants(ops, {a.id}) and a.pinned_start_minutes() is None]
    target = rng.choice(candidates)
    planned_end = ops.schedule.activities[target.id].end_minutes
    overrun = rng.randint(*OVERRUN_RANGE)
    # Everyone on time until the target's planned end; the target never confirms finishing.
    play_on_time(ops, planned_end, no_completion={target.id})
    proposals_before = len(ops.proposals)

    started = time.perf_counter()
    ops.tick(planned_end + overrun)          # detection + simulation + re-optimisation
    latency = time.perf_counter() - started

    new = ops.proposals[proposals_before:]
    absorbed = any(e.kind == "disruption.absorbed" and e.event_minute == ops.now for e in ops.audit.entries)
    outcome = "absorbed" if absorbed and not new else ("proposal" if new else "none")
    result = dict(n_activities=len(ops.activities), activity=target.id, overrun=overrun,
                  latency_seconds=latency, outcome=outcome, feasible=None, revised_conflicts=None,
                  reopt_seconds=None)
    if new:
        p = new[-1]
        result.update(feasible=p.is_feasible, reopt_seconds=p.solve_seconds)
        if p.is_feasible:
            result["revised_conflicts"] = len(verify_schedule(ops.activities, ops.resources, p.revised.activities))
    return result


def percentile(values: list[float], q: float) -> float:
    s = sorted(values)
    return s[min(len(s) - 1, int(round(q * (len(s) - 1))))]


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--quick", action="store_true")
    args = parser.parse_args()
    sizes = [1, 3, 5] if args.quick else [1, 2, 3, 4, 5, 6, 8]
    configs = [(n, False) for n in sizes] + [(5, True)]
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    rows = []
    print(f"{'events':>6}{'locks':>6}{'acts':>6}{'res':>6}{'plan s':>8}{'trials':>8}{'median s':>10}{'p95 s':>8}"
          f"{'max s':>8}{'<=5s':>7}{'re-plans':>10}{'re-plan max s':>15}{'absorbed':>10}{'infeas.':>9}{'conflicts':>11}")
    for n_events, locks in configs:
        instances = (2 if args.quick else 3) if n_events == 5 else (1 if args.quick else 2)
        trials_per = (8 if args.quick else 20) if n_events == 5 else (4 if args.quick else 10)
        trials, plan_times, plan_conflicts, n_resources = [], [], 0, 0
        for seed in range(instances):
            planned = plan_day(seed, n_events, locks)
            if planned is None:
                continue
            base, plan_seconds, conflicts = planned
            plan_times.append(plan_seconds)
            plan_conflicts += conflicts
            n_resources = len(base.resources)
            rng = random.Random(1000 + seed)
            trials += [run_trial(base, rng) for _ in range(trials_per)]
        lat = [t["latency_seconds"] for t in trials]
        replans = [t["latency_seconds"] for t in trials if t["feasible"] is True]
        row = dict(
            events=n_events, locks=locks, activities=30 * n_events, resources=n_resources,
            replans=len(replans), replan_latency_max=max(replans) if replans else None,
            plan_seconds_max=max(plan_times), plan_conflicts=plan_conflicts, trials=len(trials),
            latency_median=statistics.median(lat), latency_p95=percentile(lat, 0.95), latency_max=max(lat),
            within_limit_pct=100 * sum(l <= LATENCY_LIMIT_SECONDS for l in lat) / len(lat),
            proposals=sum(t["outcome"] == "proposal" for t in trials),
            absorbed=sum(t["outcome"] == "absorbed" for t in trials),
            infeasible=sum(t["feasible"] is False for t in trials),
            revised_conflicts=sum(t["revised_conflicts"] or 0 for t in trials),
            trial_details=trials,
        )
        rows.append(row)
        print(f"{n_events:>6}{'yes' if locks else 'no':>6}{row['activities']:>6}{n_resources:>6}"
              f"{row['plan_seconds_max']:>8.2f}{len(trials):>8}"
              f"{row['latency_median']:>10.3f}{row['latency_p95']:>8.3f}{row['latency_max']:>8.3f}"
              f"{row['within_limit_pct']:>6.0f}%{row['replans']:>10}{(row['replan_latency_max'] or 0):>15.3f}"
              f"{row['absorbed']:>10}{row['infeasible']:>9}{row['revised_conflicts']:>11}")

    at_size = [r for r in rows if r["events"] == 5]
    verdict = "PASS" if all(r["within_limit_pct"] == 100 and r["revised_conflicts"] == 0 for r in at_size) else "FAIL"
    for r in at_size:
        print(f"\nNFR-04 at 5 events x 30 activities, locks {'on' if r['locks'] else 'off'} "
              f"({r['resources']} resources, {r['trials']} disruptions): worst {r['latency_max']:.3f}s; "
              f"successful re-plans worst {(r['replan_latency_max'] or 0):.3f}s (n={r['replans']}); "
              f"limit {LATENCY_LIMIT_SECONDS:.0f}s; {r['revised_conflicts']} conflicts in revised plans")
    print(f"Verdict: {verdict}")

    curve = [r for r in rows if not r["locks"]]
    fig, ax = plt.subplots(figsize=(7.5, 4))
    x = [r["events"] for r in curve]
    ax.plot(x, [r["latency_max"] for r in curve], color=ACCENT, linewidth=2, marker="o", markersize=7, label="worst case")
    ax.plot(x, [r["latency_median"] for r in curve], color=NEUTRAL, linewidth=2, marker="o", markersize=7, label="median")
    ax.axhline(LATENCY_LIMIT_SECONDS, color=INK_MUTED, linestyle="--", linewidth=1.2, label="NFR-01 limit (5 s)")
    ax.axvline(5, color=INK_MUTED, linestyle=":", linewidth=1)
    ax.text(5.08, LATENCY_LIMIT_SECONDS * 0.55, "NFR-04\nsize", color=INK_MUTED, fontsize=9)
    ax.set_yscale("log")
    ax.set_xticks(x)
    _style(ax, "Disruption handling latency vs concurrent events (30 activities each)",
           "concurrent events", "seconds (log scale): detect + simulate + re-optimise")
    ax.legend(frameon=False, loc="upper left")
    fig.tight_layout()
    fig.savefig(RESULTS_DIR / "latency_vs_events.png", dpi=160)
    plt.close(fig)
    (RESULTS_DIR / "metrics.json").write_text(json.dumps(dict(
        limit_seconds=LATENCY_LIMIT_SECONDS, nfr04_verdict=verdict,
        rows=[{k: v for k, v in r.items() if k != "trial_details"} for r in rows],
        trials={f"{r['events']}_events_locks_{'on' if r['locks'] else 'off'}": r["trial_details"] for r in rows},
    ), indent=2, default=float))
    print("Saved results/scalability/metrics.json and latency_vs_events.png")


if __name__ == "__main__":
    main()
