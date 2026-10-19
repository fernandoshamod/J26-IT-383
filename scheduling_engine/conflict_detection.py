"""
Independent schedule verification (proposal Section 3.6 "Correctness
validation"; FR-03, FR-06).

Section 3.6 is explicit that a schedule must be checked "rather than
relying on the solver's own feasibility report, so that a defect in the
constraint model ... is detected rather than concealed." This module is
that check: it re-derives conflicts from plain Python by walking the same
Activity/Resource data the solver used, without importing anything from
solver.py or OR-Tools. If a bug in solver.py's constraint-building ever
produced a schedule CP-SAT itself (wrongly) called feasible, this module
is independent of that bug and would still catch it.

It is also reused directly for FR-06 ("detect resource double-bookings and
turnaround violations across concurrent events") on any schedule that
didn't come from the solver at all — e.g. one a planner edited by hand.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from scheduling_engine.models import Activity, Resource, ScheduledActivity


class ConflictType(str, Enum):
    PRECEDENCE_VIOLATION = "precedence_violation"
    FIXED_TIME_VIOLATION = "fixed_time_violation"
    LOCKED_ACTIVITY_MOVED = "locked_activity_moved"
    RESOURCE_OVERCOMMIT = "resource_overcommit"
    TURNAROUND_VIOLATION = "turnaround_violation"
    WRONG_ASSIGNMENT = "wrong_assignment"


@dataclass(frozen=True)
class Conflict:
    type: ConflictType
    message: str
    activity_ids: tuple[str, ...]


def verify_schedule(
    activities: list[Activity],
    resources: list[Resource],
    scheduled: dict[str, ScheduledActivity],
) -> list[Conflict]:
    """Check `scheduled` against every constraint in the proposal's
    planning-phase model. Returns an empty list iff the schedule is
    conflict-free. Does not require that `scheduled` cover every activity
    in `activities`; activities with no entry are simply skipped (treated
    as not-yet-scheduled, not as an error) — this keeps the function also
    usable on partial / in-progress schedules.
    """
    conflicts: list[Conflict] = []
    activity_by_id = {a.id: a for a in activities}

    conflicts.extend(_check_precedence(activity_by_id, scheduled))
    conflicts.extend(_check_pinned_times(activity_by_id, scheduled))
    conflicts.extend(_check_resource_capacity(activity_by_id, resources, scheduled))
    conflicts.extend(_check_assignments(activity_by_id, resources, scheduled))
    return conflicts


def _check_assignments(
    activity_by_id: dict[str, Activity],
    resources: list[Resource],
    scheduled: dict[str, ScheduledActivity],
) -> list[Conflict]:
    """FR-05: the RIGHT resources were allocated — each requirement ("2 x
    catering_crew") is met by that many distinct resources of that role,
    and nothing unknown or unneeded is assigned. Added after a
    hand-edited schedule giving speeches to the photographer passed
    unnoticed: the solver never makes this mistake, but a verifier that
    is meant not to trust the solver must check it too.
    """
    conflicts: list[Conflict] = []
    resource_by_id = {r.id: r for r in resources}
    for a in activity_by_id.values():
        s = scheduled.get(a.id)
        if s is None:
            continue
        assigned = list(dict.fromkeys(s.assigned_resource_ids))
        unknown = [rid for rid in assigned if rid not in resource_by_id]
        for rid in unknown:
            conflicts.append(Conflict(ConflictType.WRONG_ASSIGNMENT,
                                      f"{a.id} is assigned unknown resource {rid}", (a.id,)))
        roles_needed = {req.role for req in a.requirements}
        for req in a.requirements:
            have = sum(1 for rid in assigned if rid in resource_by_id and resource_by_id[rid].role == req.role)
            if have < req.count:
                conflicts.append(Conflict(ConflictType.WRONG_ASSIGNMENT,
                                          f"{a.id} needs {req.count} x {req.role} but has {have}", (a.id,)))
        for rid in assigned:
            if rid in resource_by_id and resource_by_id[rid].role not in roles_needed:
                conflicts.append(Conflict(ConflictType.WRONG_ASSIGNMENT,
                                          f"{a.id} is assigned {rid} ({resource_by_id[rid].role}), "
                                          f"a role it does not need", (a.id,)))
    return conflicts


def _check_precedence(
    activity_by_id: dict[str, Activity],
    scheduled: dict[str, ScheduledActivity],
) -> list[Conflict]:
    conflicts = []
    for a in activity_by_id.values():
        succ = scheduled.get(a.id)
        if succ is None:
            continue
        for pred_id in a.predecessors:
            pred = scheduled.get(pred_id)
            if pred is None:
                continue
            lag = a.min_lag_minutes.get(pred_id, 0)
            required_start = pred.end_minutes + lag
            if succ.start_minutes < required_start:
                conflicts.append(
                    Conflict(
                        type=ConflictType.PRECEDENCE_VIOLATION,
                        message=(
                            f"{a.id} starts at {succ.start_minutes} but predecessor "
                            f"{pred_id} ends at {pred.end_minutes} (+{lag} min lag): "
                            f"must start at or after {required_start}"
                        ),
                        activity_ids=(pred_id, a.id),
                    )
                )
    return conflicts


def _check_pinned_times(
    activity_by_id: dict[str, Activity],
    scheduled: dict[str, ScheduledActivity],
) -> list[Conflict]:
    conflicts = []
    for a in activity_by_id.values():
        s = scheduled.get(a.id)
        if s is None:
            continue
        if a.fixed_start_minutes is not None and s.start_minutes != a.fixed_start_minutes:
            conflicts.append(
                Conflict(
                    type=ConflictType.FIXED_TIME_VIOLATION,
                    message=(
                        f"{a.id} has an externally fixed start of "
                        f"{a.fixed_start_minutes} but is scheduled at {s.start_minutes}"
                    ),
                    activity_ids=(a.id,),
                )
            )
        if a.locked_start_minutes is not None and s.start_minutes != a.locked_start_minutes:
            conflicts.append(
                Conflict(
                    type=ConflictType.LOCKED_ACTIVITY_MOVED,
                    message=(
                        f"{a.id} was locked at {a.locked_start_minutes} but is "
                        f"scheduled at {s.start_minutes}"
                    ),
                    activity_ids=(a.id,),
                )
            )
    return conflicts


def _check_resource_capacity(
    activity_by_id: dict[str, Activity],
    resources: list[Resource],
    scheduled: dict[str, ScheduledActivity],
) -> list[Conflict]:
    """Sweep-line check: for each resource, walk the (padded-by-turnaround)
    busy intervals of every activity assigned to it in time order,
    tracking how many are simultaneously active. Flag the point where
    that count exceeds the resource's capacity.
    """
    conflicts: list[Conflict] = []
    resource_by_id = {r.id: r for r in resources}

    busy_intervals_by_resource: dict[str, list[tuple[int, int, str]]] = {}
    for a in activity_by_id.values():
        s = scheduled.get(a.id)
        if s is None:
            continue
        for resource_id in s.assigned_resource_ids:
            resource = resource_by_id.get(resource_id)
            turnaround = resource.min_turnaround_minutes if resource else 0
            busy_intervals_by_resource.setdefault(resource_id, []).append(
                (s.start_minutes, s.end_minutes + turnaround, a.id)
            )

    for resource_id, intervals in busy_intervals_by_resource.items():
        resource = resource_by_id.get(resource_id)
        capacity = resource.capacity if resource else 1

        events = []
        for start, end, activity_id in intervals:
            events.append((start, 1, activity_id))
            events.append((end, -1, activity_id))
        # Process interval ends before starts at the same timestamp (-1
        # sorts before +1), so a resource that frees up at minute 50 and
        # is reused starting at minute 50 is NOT flagged as a double-booking.
        events.sort(key=lambda e: (e[0], e[1]))

        active_count = 0
        active_ids: set[str] = set()
        for _, delta, activity_id in events:
            if delta == 1:
                active_count += 1
                active_ids.add(activity_id)
                if active_count > capacity:
                    conflicts.append(
                        Conflict(
                            type=ConflictType.RESOURCE_OVERCOMMIT,
                            message=(
                                f"Resource {resource_id} (capacity {capacity}) is "
                                f"committed to {active_count} activities at once: "
                                f"{sorted(active_ids)}"
                            ),
                            activity_ids=tuple(sorted(active_ids)),
                        )
                    )
            else:
                active_count -= 1
                active_ids.discard(activity_id)

    return conflicts
