"""
Adaptive re-optimisation (proposal Section 4.2.2; Objective 5; FR-12,
FR-14). The last piece of the execution-phase loop: simulation.py answers
"what happens if nothing changes"; this module answers "what's the best
revised schedule, and what does it cost."

Scope boundary with Component 4 (financial intelligence): this module
does not calculate money. Table 8 (Individual Responsibility Boundary)
assigns "financial forecasting and what-if simulation" to Component 4,
not this one. What this module owes Component 4, per FR-14 and the
cross-component interface in Section 4.3, is the *operational* facts a
cost model needs as input — which activities ended up later than
planned, by how much in total, and which resources now run into overtime
— packaged as `CostSignal`. Turning those facts into a currency amount
is Component 4's job.

Why this re-solves only the REMAINING activities, not the whole event
again: completed and in-progress activities are facts now, not decisions
— re-litigating when venue_setup happened this morning is meaningless.
They enter this model as fixed constants (their own resource occupancy
included, so a not-yet-started activity correctly queues behind them),
exactly mirroring simulation.py's anchoring, but here feeding a CP-SAT
model rather than a SimPy one.

Why minimise total lateness, not makespan: Objective 5's job is to claw
back as much of an injected disruption as possible (directly the
proposal's own "proportion of injected delay absorbed" metric), not to
produce the shortest event physically possible — an unaffected activity
that was never going to be late shouldn't get reshuffled just because
makespan could theoretically shrink by a minute elsewhere. Minimising
summed lateness relative to the ORIGINAL plan is the textbook objective
for reactive/repair scheduling.

Why TERMINAL activities' lateness is weighted far more heavily than
everyone else's: a plain, equally-weighted sum of lateness has a real
failure mode, caught during the 200-scenario evaluation (Section 3.6)
rather than reasoned out in advance — it can make the event's actual
*ending* later than if nothing had been done, if that frees up slack for
several *intermediate* activities to avoid lateness instead. The sum
goes down; the thing the client actually experiences gets worse. The
proposal's own "proportion of injected delay absorbed" (Table 6) is
framed around what's "passed downstream to the client" — i.e. the end of
the event, not the sum of every intermediate activity's lateness — so the
activities nobody else depends on (no other activity lists them as a
predecessor) get a large weight multiplier, making their lateness the
effective first-priority objective, with everyone else's lateness still
minimised as a secondary, tie-breaking concern rather than ignored.

Why warm-started: `model.add_hint(...)` seeds the search at the original
plan's own start times and resource assignments. CP-SAT doesn't have to
honour a hint, but starting from "keep everything where it was" is
usually close to optimal when only one activity has actually slipped, so
it's a legitimate way to help the solver reach the 5-second target rather
than searching from nothing each time.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from ortools.sat.python import cp_model

from scheduling_engine.models import Activity, Resource, Schedule, ScheduledActivity
from scheduling_engine.solver import SchedulingDataError
from scheduling_engine.twin import ActivityState, OperationalDigitalTwin


@dataclass(frozen=True)
class CostSignal:
    """Operational facts for Component 4 to cost, not a cost itself."""

    total_delay_minutes: int
    delayed_activity_ids: tuple[str, ...] = field(default_factory=tuple)
    # Per resource, how many minutes past its ORIGINAL planned last use it
    # is now needed for — the direct driver of overtime/vendor-extension cost.
    resource_overtime_minutes: dict[str, int] = field(default_factory=dict)


@dataclass
class ReoptimizationResult:
    is_feasible: bool
    schedule: Schedule | None = None
    cost_signal: CostSignal | None = None
    solve_time_seconds: float = 0.0
    status_name: str = ""
    # Mirrors Schedule.conflicting_pinned_activity_ids (solver.py): which
    # locked/fixed activities are jointly responsible when no revised
    # schedule can satisfy all of them. FR-12 singles out locked
    # activities specifically as a hard requirement, so if honouring one
    # is literally impossible given what's already happened, the planner
    # needs to be told which ones, not just "infeasible".
    conflicting_pinned_activity_ids: list[str] = field(default_factory=list)


def reoptimize(
    activities: list[Activity],
    resources: list[Resource],
    schedule: Schedule,
    twin: OperationalDigitalTwin,
    now_minutes: int,
    predicted_extra_duration_minutes: dict[str, int] | None = None,
    time_limit_seconds: float = 5.0,
) -> ReoptimizationResult:
    extra_duration = predicted_extra_duration_minutes or {}
    activity_by_id = {a.id: a for a in activities}
    resource_by_id = {r.id: r for r in resources}
    resource_by_role: dict[str, list[Resource]] = {}
    for r in resources:
        resource_by_role.setdefault(r.role, []).append(r)

    # --- Split into "already happened / happening" (fixed facts) vs
    # "still to be decided" (what this model actually solves for). ---
    anchored_end: dict[str, int] = {}
    anchored_assignment: dict[str, list[str]] = {}
    to_solve: list[Activity] = []
    for a in activities:
        state = twin.state_of(a.id)
        original = schedule.activities[a.id]
        if state.state is ActivityState.COMPLETED:
            anchored_end[a.id] = state.actual_end_minutes
            anchored_assignment[a.id] = original.assigned_resource_ids
        elif state.state is ActivityState.IN_PROGRESS:
            anchored_end[a.id] = (
                state.actual_start_minutes + a.duration_minutes + extra_duration.get(a.id, 0)
            )
            anchored_assignment[a.id] = original.assigned_resource_ids
        else:
            to_solve.append(a)

    anchored_start: dict[str, int] = {
        a.id: (
            twin.state_of(a.id).actual_start_minutes
            if twin.state_of(a.id).actual_start_minutes is not None
            else anchored_end[a.id]
        )
        for a in activities
        if a.id in anchored_end
    }

    horizon = (
        max([now_minutes, *anchored_end.values()], default=now_minutes)
        + sum(a.duration_minutes + extra_duration.get(a.id, 0) for a in to_solve)
        + len(to_solve) * max((r.min_turnaround_minutes for r in resources), default=0)
        + 1
    )

    model = cp_model.CpModel()
    starts: dict[str, cp_model.IntVar] = {}
    ends: dict[str, cp_model.IntVar] = {}
    for a in to_solve:
        floor = max(now_minutes, a.earliest_start_minutes)
        starts[a.id] = model.new_int_var(floor, horizon, f"start_{a.id}")
        ends[a.id] = model.new_int_var(floor, horizon, f"end_{a.id}")
        duration = a.duration_minutes + extra_duration.get(a.id, 0)
        model.new_interval_var(starts[a.id], duration, ends[a.id], f"interval_{a.id}")
        model.add_hint(starts[a.id], schedule.activities[a.id].start_minutes)

    # --- Fixed/locked pins, via assumptions (identical technique to
    # solver.py, and for the identical reason: enforced when feasible,
    # diagnosable by name when not). ---
    pin_literal_to_activity_id: dict[int, str] = {}
    pin_literals: list[cp_model.IntVar] = []
    for a in to_solve:
        pinned = a.pinned_start_minutes()
        if pinned is None:
            continue
        lit = model.new_bool_var(f"pin_{a.id}")
        model.add(starts[a.id] == pinned).only_enforce_if(lit)
        pin_literals.append(lit)
        pin_literal_to_activity_id[lit.index] = a.id
    if pin_literals:
        model.add_assumptions(pin_literals)

    # --- Precedence: a predecessor may itself be a fixed, anchored fact
    # rather than a variable, in which case its end is just a constant
    # lower bound rather than another model variable. ---
    for a in to_solve:
        for pred_id in a.predecessors:
            lag = a.min_lag_minutes.get(pred_id, 0)
            if pred_id in anchored_end:
                model.add(starts[a.id] >= anchored_end[pred_id] + lag)
            elif pred_id in starts:
                model.add(starts[a.id] >= ends[pred_id] + lag)
            else:
                raise SchedulingDataError(f"Activity {a.id!r} lists unknown predecessor {pred_id!r}")

    # --- Resources: each resource's constraint covers BOTH the anchored
    # facts (as plain fixed intervals — not decisions, just occupancy
    # that already exists) and the candidate assignments for activities
    # still to be decided (the same optional-interval-per-candidate
    # pattern as solver.py). ---
    resource_blocks: dict[str, list] = {}
    assign_lookup: dict[tuple[str, str], cp_model.IntVar] = {}

    for activity_id, resource_ids in anchored_assignment.items():
        for rid in resource_ids:
            turnaround = resource_by_id[rid].min_turnaround_minutes
            block = model.new_interval_var(
                anchored_start[activity_id],
                (anchored_end[activity_id] - anchored_start[activity_id]) + turnaround,
                anchored_end[activity_id] + turnaround,
                f"anchored_block_{activity_id}_{rid}",
            )
            resource_blocks.setdefault(rid, []).append(block)

    for a in to_solve:
        for req in a.requirements:
            candidates = resource_by_role.get(req.role, [])
            if not candidates:
                raise SchedulingDataError(
                    f"Activity {a.id!r} requires role {req.role!r}, "
                    "but no resource with that role was supplied"
                )
            assign_vars = []
            originally_assigned = set(schedule.activities[a.id].assigned_resource_ids)
            for r in candidates:
                assign = model.new_bool_var(f"assign_{a.id}_{r.id}")
                assign_vars.append(assign)
                model.add_hint(assign, 1 if r.id in originally_assigned else 0)

                duration = a.duration_minutes + extra_duration.get(a.id, 0)
                block_end = model.new_int_var(
                    0, horizon + r.min_turnaround_minutes, f"block_end_{a.id}_{r.id}"
                )
                block = model.new_optional_interval_var(
                    starts[a.id],
                    duration + r.min_turnaround_minutes,
                    block_end,
                    assign,
                    f"block_{a.id}_{r.id}",
                )
                resource_blocks.setdefault(r.id, []).append(block)
                assign_lookup[(a.id, r.id)] = assign
            model.add(sum(assign_vars) == req.count)

    for r in resources:
        blocks = resource_blocks.get(r.id, [])
        if not blocks:
            continue
        if r.capacity == 1:
            model.add_no_overlap(blocks)
        else:
            model.add_cumulative(blocks, demands=[1] * len(blocks), capacity=r.capacity)

    # --- Objective: minimise the WORST (max) lateness among terminal
    # activities first, total lateness everywhere second as a tie-break —
    # see module docstring for why. A weighted SUM over terminal
    # activities was tried first and wasn't enough: with more than one
    # terminal activity, summing still lets the solver sacrifice one of
    # them heavily if that's cheaper in total than spreading the delay
    # evenly, which is exactly backwards when what's actually being
    # evaluated is the single worst client-facing delay, not a sum across
    # possibly-unrelated endpoints. ---
    terminal_ids = {a.id for a in activities} - {p for a in activities for p in a.predecessors}
    BIG_WEIGHT = 1000
    lateness_vars = []
    terminal_lateness_vars = []
    for a in to_solve:
        planned_end = schedule.activities[a.id].end_minutes
        lateness = model.new_int_var(0, horizon, f"lateness_{a.id}")
        model.add(lateness >= ends[a.id] - planned_end)
        lateness_vars.append(lateness)
        if a.id in terminal_ids:
            terminal_lateness_vars.append(lateness)

    if terminal_lateness_vars:
        max_terminal_lateness = model.new_int_var(0, horizon, "max_terminal_lateness")
        model.add_max_equality(max_terminal_lateness, terminal_lateness_vars)
    else:
        max_terminal_lateness = 0  # every terminal activity is already anchored; nothing left to protect
    if lateness_vars:
        model.minimize(BIG_WEIGHT * max_terminal_lateness + sum(lateness_vars))

    solver = cp_model.CpSolver()
    solver.parameters.max_time_in_seconds = time_limit_seconds
    solver.parameters.num_search_workers = 8
    status = solver.solve(model)
    status_name = solver.status_name(status)

    if status == cp_model.INFEASIBLE:
        core = solver.sufficient_assumptions_for_infeasibility()
        conflicting_ids = sorted(
            {pin_literal_to_activity_id[i] for i in core if i in pin_literal_to_activity_id}
        )
        return ReoptimizationResult(
            is_feasible=False,
            solve_time_seconds=solver.wall_time,
            status_name=status_name,
            conflicting_pinned_activity_ids=conflicting_ids,
        )
    if status not in (cp_model.OPTIMAL, cp_model.FEASIBLE):
        return ReoptimizationResult(is_feasible=False, solve_time_seconds=solver.wall_time, status_name=status_name)

    revised: dict[str, ScheduledActivity] = {}
    for activity_id in anchored_end:
        revised[activity_id] = ScheduledActivity(
            activity_id, anchored_start[activity_id], anchored_end[activity_id], anchored_assignment[activity_id]
        )
    for a in to_solve:
        assigned = [
            r.id
            for req in a.requirements
            for r in resource_by_role.get(req.role, [])
            if (a.id, r.id) in assign_lookup and solver.value(assign_lookup[(a.id, r.id)]) == 1
        ]
        revised[a.id] = ScheduledActivity(a.id, solver.value(starts[a.id]), solver.value(ends[a.id]), assigned)
    revised_schedule = Schedule(is_feasible=True, activities=revised, solve_time_seconds=solver.wall_time, status_name=status_name)

    cost_signal = _build_cost_signal(activities, resources, schedule, revised_schedule, to_solve)

    return ReoptimizationResult(
        is_feasible=True,
        schedule=revised_schedule,
        cost_signal=cost_signal,
        solve_time_seconds=solver.wall_time,
        status_name=status_name,
    )


def _build_cost_signal(
    activities: list[Activity],
    resources: list[Resource],
    original: Schedule,
    revised: Schedule,
    to_solve: list[Activity],
) -> CostSignal:
    total_delay = 0
    delayed_ids = []
    for a in to_solve:
        delta = revised.activities[a.id].end_minutes - original.activities[a.id].end_minutes
        if delta > 0:
            total_delay += delta
            delayed_ids.append(a.id)

    resource_overtime: dict[str, int] = {}
    for r in resources:
        original_last_use = max(
            (s.end_minutes for s in original.activities.values() if r.id in s.assigned_resource_ids),
            default=None,
        )
        revised_last_use = max(
            (s.end_minutes for s in revised.activities.values() if r.id in s.assigned_resource_ids),
            default=None,
        )
        if original_last_use is None or revised_last_use is None:
            continue
        overtime = revised_last_use - original_last_use
        if overtime > 0:
            resource_overtime[r.id] = overtime

    return CostSignal(
        total_delay_minutes=total_delay,
        delayed_activity_ids=tuple(sorted(delayed_ids)),
        resource_overtime_minutes=resource_overtime,
    )
