"""
Planning-phase scheduling engine (proposal Section 4.2.1, Objectives 1 & 2).

Formulates event scheduling as a Constraint Satisfaction Problem and solves
it with Google OR-Tools CP-SAT, per the method comparison in Table 3 of the
proposal: CP-SAT either returns a schedule that satisfies every stated
constraint, or proves none exists. It never returns a schedule that quietly
violates a constraint, which is why it was chosen over a genetic algorithm
or simulated annealing (both of which handle constraints as objective
penalties and can return an infeasible result if the penalty is
outweighed).

What "variables" means here:
  - start/end time of every activity               -> decision variables
  - which concrete resource covers each requirement -> decision variables
  - activity duration                               -> INPUT data, not a
    decision variable. It is supplied by the (separate) duration-prediction
    model described in Section 4.2.1; this module's job stops at consuming
    that estimate, not producing it.

Constraints modelled, each traceable to a line in the proposal:
  - precedence                      (Section 4.2.1; FR-04)
  - resource exclusivity / capacity (FR-04, FR-05, FR-06)
  - minimum turnaround per resource (Section 4.2.1)
  - fixed externally-imposed times  (FR-04)
  - planner-locked activities       (FR-07)
"""

from __future__ import annotations

from dataclasses import dataclass

from ortools.sat.python import cp_model

from scheduling_engine.models import (
    Activity,
    Event,
    Resource,
    Schedule,
    ScheduledActivity,
)


class SchedulingDataError(ValueError):
    """Raised for problems in the input data itself (e.g. an activity asks
    for a role no resource has), as opposed to the schedule being
    infeasible. These are caught before the solver ever runs, because a
    missing resource type is a data-entry mistake, not a scheduling
    conflict, and the two should never be reported to a planner the same
    way.
    """


@dataclass
class _ActivityVars:
    activity: Activity
    start: cp_model.IntVar
    end: cp_model.IntVar


def _compute_default_horizon(events: list[Event], resources: list[Resource]) -> int:
    """A safe (if loose) upper bound on the schedule length: every
    activity run back-to-back after the latest fixed/locked/earliest
    point, with every one of them also incurring the worst-case
    turnaround. No feasible schedule can need more room than this, so
    using it as the variable domain's upper bound never cuts off a real
    solution — it only affects how large the search space is, not
    correctness.
    """
    all_activities = [a for e in events for a in e.activities]
    total_duration = sum(a.duration_minutes for a in all_activities)
    max_turnaround = max((r.min_turnaround_minutes for r in resources), default=0)
    total_turnaround_padding = len(all_activities) * max_turnaround
    latest_floor = 0
    for a in all_activities:
        latest_floor = max(latest_floor, a.earliest_start_minutes)
        pinned = a.pinned_start_minutes()
        if pinned is not None:
            latest_floor = max(latest_floor, pinned)
    return latest_floor + total_duration + total_turnaround_padding + 1


def solve_planning_phase(
    events: list[Event],
    resources: list[Resource],
    horizon_minutes: int | None = None,
    time_limit_seconds: float = 30.0,
    minimize_makespan: bool = True,
) -> Schedule:
    """Build the CP-SAT model from `events`/`resources` and solve it.

    `minimize_makespan` (default True) asks CP-SAT to keep searching after
    the first feasible schedule until it can prove the makespan is as
    short as possible, or the time limit is hit. The proposal's actual
    hard requirement is feasibility — every constraint satisfied — not a
    minimal makespan, so this is a secondary, optional preference. Turn
    it off to stop at the first feasible schedule found, which matters
    when a resource is modelled as many interchangeable identical units
    (see psplib.py): CP-SAT then has to additionally prove that no
    reassignment among symmetric, functionally-identical units could
    shave time off, which is a much harder search than finding feasibility
    itself and produces no planner-visible difference in the result.

    Returns a Schedule. Read `schedule.is_feasible` first:
      - True: every activity has a start/end and a resource assignment
        that satisfies every modelled constraint.
      - False with status_name == "INFEASIBLE": CP-SAT has *proven* no
        feasible schedule exists. `conflicting_pinned_activity_ids` names
        the fixed/locked activities whose pinned times are jointly
        responsible (FR-03's "report infeasibility with the conflicting
        constraints identified" — scoped here to pinned-time conflicts,
        the human-introduced case the proposal calls out in Section
        3.6.1, rather than a full constraint-level diagnosis).
      - False with status_name == "UNKNOWN": the time limit was reached
        before the solver could either find a schedule or prove there is
        none. This is NOT the same as infeasible and must not be reported
        to a user as such.
    """
    horizon = (
        horizon_minutes
        if horizon_minutes is not None
        else _compute_default_horizon(events, resources)
    )

    model = cp_model.CpModel()
    all_activities = [a for e in events for a in e.activities]
    resource_by_role: dict[str, list[Resource]] = {}
    for r in resources:
        resource_by_role.setdefault(r.role, []).append(r)

    activity_vars: dict[str, _ActivityVars] = {}
    for a in all_activities:
        start = model.new_int_var(a.earliest_start_minutes, horizon, f"start_{a.id}")
        end = model.new_int_var(a.earliest_start_minutes, horizon, f"end_{a.id}")
        model.new_interval_var(start, a.duration_minutes, end, f"interval_{a.id}")
        activity_vars[a.id] = _ActivityVars(activity=a, start=start, end=end)

    # --- Fixed / locked times, via assumptions -----------------------
    # Pinning the start through an assumption literal does two things at
    # once: during a feasible solve it behaves exactly like a hard
    # `start == pinned_value` constraint, and during an infeasible solve
    # it lets us ask CP-SAT *which* pins are mutually responsible, via
    # sufficient_assumptions_for_infeasibility(). A plain hard constraint
    # could not give us that second part.
    pin_literal_to_activity_id: dict[int, str] = {}
    pin_literals: list[cp_model.IntVar] = []
    for a in all_activities:
        pinned = a.pinned_start_minutes()
        if pinned is None:
            continue
        lit = model.new_bool_var(f"pin_{a.id}")
        model.add(activity_vars[a.id].start == pinned).only_enforce_if(lit)
        pin_literals.append(lit)
        pin_literal_to_activity_id[lit.index] = a.id
    if pin_literals:
        model.add_assumptions(pin_literals)

    # --- Precedence ----------------------------------------------------
    for a in all_activities:
        for pred_id in a.predecessors:
            if pred_id not in activity_vars:
                raise SchedulingDataError(
                    f"Activity {a.id!r} lists unknown predecessor {pred_id!r}"
                )
            lag = a.min_lag_minutes.get(pred_id, 0)
            model.add(activity_vars[a.id].start >= activity_vars[pred_id].end + lag)

    # --- Resource assignment + exclusivity + turnaround -----------------
    # For every (activity, candidate resource) pair we create one boolean
    # "is this resource covering this requirement" variable, and one
    # optional interval gated by that boolean. The optional interval's
    # size is padded by the resource's minimum turnaround, so the
    # resource is modelled as still "busy" for that long after the
    # activity's real end — while the activity's own end (used above for
    # precedence) stays the true, unpadded end. Turnaround is a property
    # of the resource's availability, not of when the activity's output
    # is considered complete, so the two must not be conflated.
    resource_blocks: dict[str, list[cp_model.IntervalVar]] = {}
    assign_lookup: dict[tuple[str, str], cp_model.IntVar] = {}
    for a in all_activities:
        for req in a.requirements:
            candidates = resource_by_role.get(req.role, [])
            if not candidates:
                raise SchedulingDataError(
                    f"Activity {a.id!r} requires role {req.role!r}, "
                    "but no resource with that role was supplied"
                )
            assign_vars = []
            for r in candidates:
                assign = model.new_bool_var(f"assign_{a.id}_{r.id}")
                assign_vars.append(assign)

                block_end = model.new_int_var(
                    0, horizon + r.min_turnaround_minutes, f"block_end_{a.id}_{r.id}"
                )
                block = model.new_optional_interval_var(
                    activity_vars[a.id].start,
                    a.duration_minutes + r.min_turnaround_minutes,
                    block_end,
                    assign,
                    f"block_{a.id}_{r.id}",
                )
                resource_blocks.setdefault(r.id, []).append(block)
            model.add(sum(assign_vars) == req.count)
            # Keep a handle so we can read back which resource was chosen.
            for r, assign in zip(candidates, assign_vars):
                assign_lookup[(a.id, r.id)] = assign

    for r in resources:
        blocks = resource_blocks.get(r.id, [])
        if not blocks:
            continue
        if r.capacity == 1:
            model.add_no_overlap(blocks)
        else:
            model.add_cumulative(blocks, demands=[1] * len(blocks), capacity=r.capacity)

    # --- Objective -------------------------------------------------------
    # The makespan variable is always created so it can be read back and
    # reported (e.g. compared against a known lower bound), regardless of
    # whether the solver is asked to actually minimise it.
    makespan = model.new_int_var(0, horizon, "makespan")
    model.add_max_equality(makespan, [v.end for v in activity_vars.values()])
    if minimize_makespan:
        model.minimize(makespan)

    solver = cp_model.CpSolver()
    solver.parameters.max_time_in_seconds = time_limit_seconds
    solver.parameters.num_search_workers = 8
    status = solver.solve(model)
    status_name = solver.status_name(status)

    if status in (cp_model.OPTIMAL, cp_model.FEASIBLE):
        scheduled: dict[str, ScheduledActivity] = {}
        for a in all_activities:
            vars_ = activity_vars[a.id]
            assigned = [
                r.id
                for req in a.requirements
                for r in resource_by_role.get(req.role, [])
                if (a.id, r.id) in assign_lookup
                and solver.value(assign_lookup[(a.id, r.id)]) == 1
            ]
            scheduled[a.id] = ScheduledActivity(
                activity_id=a.id,
                start_minutes=solver.value(vars_.start),
                end_minutes=solver.value(vars_.end),
                assigned_resource_ids=assigned,
            )
        return Schedule(
            is_feasible=True,
            activities=scheduled,
            makespan_minutes=solver.value(makespan),
            solve_time_seconds=solver.wall_time,
            status_name=status_name,
        )

    if status == cp_model.INFEASIBLE:
        core = solver.sufficient_assumptions_for_infeasibility()
        conflicting_ids = sorted(
            {pin_literal_to_activity_id[i] for i in core if i in pin_literal_to_activity_id}
        )
        return Schedule(
            is_feasible=False,
            solve_time_seconds=solver.wall_time,
            status_name=status_name,
            conflicting_pinned_activity_ids=conflicting_ids,
        )

    # UNKNOWN (time limit hit) or MODEL_INVALID: no proof either way.
    return Schedule(
        is_feasible=False,
        solve_time_seconds=solver.wall_time,
        status_name=status_name,
    )
