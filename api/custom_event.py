"""
Planner-entered events: turn what a person types into the dashboard's
"Build event" form into engine objects, check it, and plan it.

All checking happens here, not in the page, so any future UI can reuse it.
Every problem is reported in plain words naming the activity involved,
because a person typing an event needs to know what to fix:

  * every activity has a name and a duration of 1-1440 minutes;
  * "comes after" only names activities that exist, and never forms a loop
    (A after B after A can never be scheduled);
  * every needed role is provided by at least that many resources;
  * fixed times are real clock times (HH:MM).

Whether the event can actually be scheduled (for example two fixed times
that clash) is then decided by the CP-SAT solver, which names the
conflicting fixed activities when it can't (FR-03).
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path

from api.forecast import Forecast
from scheduling_engine.models import Activity, Event, Resource, ResourceRequirement, ResourceType
from scheduling_engine.operations import EventOperations, OperationsError
from scheduling_engine.solver import solve_planning_phase

MAX_ACTIVITIES_PER_EVENT = 40
MAX_RESOURCES = 120


@dataclass
class RequirementSpec:
    role: str
    count: int = 1


@dataclass
class ActivitySpec:
    name: str
    duration_minutes: int
    after: list[int] = field(default_factory=list)       # row numbers (1-based) of earlier activities
    needs: list[RequirementSpec] = field(default_factory=list)
    fixed_time: str | None = None                        # "HH:MM"


@dataclass
class ResourceSpec:
    name: str
    role: str
    type: str = "staff"                                  # staff / vendor / equipment
    turnaround_minutes: int = 0


@dataclass
class EventSpec:
    name: str
    opens_at: str = "08:00"                              # nothing starts before this
    activities: list[ActivitySpec] = field(default_factory=list)


def _clock(text: str, what: str) -> int:
    m = re.fullmatch(r"\s*(\d{1,2}):(\d{2})\s*", text or "")
    if not m or int(m.group(1)) > 23 or int(m.group(2)) > 59:
        raise OperationsError(f"{what}: “{text}” is not a time — use HH:MM, e.g. 14:30")
    return int(m.group(1)) * 60 + int(m.group(2))


def _hhmm(m: int) -> str:
    return f"{m // 60:02d}:{m % 60:02d}"


def _slug(text: str) -> str:
    s = re.sub(r"[^a-z0-9]+", "_", text.lower()).strip("_")
    return s or "item"


def build(event_spec: EventSpec, resource_specs: list[ResourceSpec],
          taken_ids: set[str] = frozenset()) -> tuple[Event, list[Resource]]:
    """Validate and convert. Raises OperationsError with a plain-language
    message naming what to fix."""
    if not event_spec.name.strip():
        raise OperationsError("Give the event a name.")
    if not event_spec.activities:
        raise OperationsError("Add at least one activity.")
    if len(event_spec.activities) > MAX_ACTIVITIES_PER_EVENT:
        raise OperationsError(f"At most {MAX_ACTIVITIES_PER_EVENT} activities per event.")
    if not resource_specs:
        raise OperationsError("Add at least one staff member, vendor or piece of equipment.")
    if len(resource_specs) > MAX_RESOURCES:
        raise OperationsError(f"At most {MAX_RESOURCES} resources.")
    opens = _clock(event_spec.opens_at, "Venue opens")

    event_id = _slug(event_spec.name)
    while event_id in taken_ids:
        event_id += "_2"

    # Resources: unique ids, known type, sensible turnaround.
    resources: list[Resource] = []
    used: set[str] = set(taken_ids)
    for i, r in enumerate(resource_specs, start=1):
        if not r.name.strip() or not r.role.strip():
            raise OperationsError(f"Resource row {i}: give it a name and a role.")
        if r.type not in {t.value for t in ResourceType}:
            raise OperationsError(f"Resource {r.name}: type must be staff, vendor or equipment.")
        if not 0 <= r.turnaround_minutes <= 240:
            raise OperationsError(f"Resource {r.name}: turnaround must be 0–240 minutes.")
        rid = _slug(r.name)
        while rid in used:
            rid += "_2"
        used.add(rid)
        resources.append(Resource(rid, r.name.strip(), ResourceType(r.type), _slug(r.role),
                                  min_turnaround_minutes=r.turnaround_minutes))
    units_by_role: dict[str, int] = {}
    for r in resources:
        units_by_role[r.role] = units_by_role.get(r.role, 0) + 1

    # Activities.
    n = len(event_spec.activities)
    ids = [f"{event_id}-{i:02d}-{_slug(a.name)}"[:64] for i, a in enumerate(event_spec.activities, start=1)]
    activities: list[Activity] = []
    for i, (a, aid) in enumerate(zip(event_spec.activities, ids), start=1):
        label = f"Row {i} ({a.name.strip() or 'no name'})"
        if not a.name.strip():
            raise OperationsError(f"Row {i}: give the activity a name.")
        if not 1 <= a.duration_minutes <= 1440:
            raise OperationsError(f"{label}: duration must be 1–1440 minutes.")
        for row in a.after:
            if not 1 <= row <= n:
                raise OperationsError(f"{label}: “after” row {row} doesn’t exist (your activity rows are 1–{n}).")
            if row == i:
                raise OperationsError(f"{label} can’t come after itself — its “After rows” contains {i}, its own row number.")
        if not a.needs:
            raise OperationsError(f"{label}: choose at least one role it needs.")
        # The same role listed twice ("Needs crew x2", "Also needs crew") means
        # that many people of that role in total, so add the counts together.
        totals: dict[str, int] = {}
        shown: dict[str, str] = {}
        for need in a.needs:
            if need.count < 1:
                raise OperationsError(f"{label}: the number needed must be at least 1.")
            role = _slug(need.role)
            totals[role] = totals.get(role, 0) + need.count
            shown.setdefault(role, need.role)
        reqs = []
        for role, count in totals.items():
            have = units_by_role.get(role, 0)
            if have < count:
                raise OperationsError(f"{label} needs {count} × {shown[role]} in total, but only {have} "
                                      f"resource(s) have that role. Add more, or need fewer "
                                      f"(“Also needs” is for a second, different role).")
            reqs.append(ResourceRequirement(role, count))
        fixed = _clock(a.fixed_time, f"{label}, fixed time") if a.fixed_time else None
        if fixed is not None and fixed < opens:
            raise OperationsError(f"{label} is fixed at {a.fixed_time}, before the venue opens at {event_spec.opens_at}.")
        activities.append(Activity(aid, event_id, a.name.strip(), a.duration_minutes, requirements=reqs,
                                   predecessors=[ids[r - 1] for r in sorted(set(a.after))],
                                   earliest_start_minutes=opens, fixed_start_minutes=fixed))

    _reject_loops(activities, event_spec)
    return Event(event_id, event_spec.name.strip(), activities), resources


def _reject_loops(activities: list[Activity], spec: EventSpec) -> None:
    """A loop in "comes after" (A after B, B after A) can never be scheduled."""
    index = {a.id: i for i, a in enumerate(activities, start=1)}
    preds = {a.id: a.predecessors for a in activities}
    state: dict[str, int] = {}  # 1 = visiting, 2 = done

    def visit(aid: str, path: list[str]) -> None:
        if state.get(aid) == 2:
            return
        if state.get(aid) == 1:
            loop = path[path.index(aid):] + [aid]
            names = " → ".join(f"{index[x]} ({spec.activities[index[x] - 1].name})" for x in loop)
            raise OperationsError(f"“Comes after” forms a loop, which can never be scheduled: {names}.")
        state[aid] = 1
        for p in preds[aid]:
            visit(p, path + [aid])
        state[aid] = 2

    for a in activities:
        visit(a.id, [])


def plan_custom(event_spec: EventSpec, resource_specs: list[ResourceSpec],
                with_events: list[Event] = (), with_resources: list[Resource] = (),
                audit_path: Path | None = None) -> EventOperations:
    """Build the planner's event (optionally alongside other events that
    share resources with it), plan it with CP-SAT, and return the live
    service ready for check-ins. Raises OperationsError when the input is
    invalid or no schedule exists (naming the conflicting fixed times)."""
    taken = {e.id for e in with_events} | {r.id for r in with_resources}
    event, resources = build(event_spec, resource_specs, taken)
    # A resource with the same name as an existing one is the same person/kit.
    existing = {r.name.lower(): r for r in with_resources}
    merged = list(with_resources) + [r for r in resources if r.name.lower() not in existing]
    all_events = [*with_events, event]
    trial = solve_planning_phase(all_events, merged)
    if not trial.is_feasible:
        by_id = {a.id: a for e in all_events for a in e.activities}
        named = [f"{by_id[i].name} ({_hhmm(by_id[i].pinned_start_minutes())})"
                 for i in trial.conflicting_pinned_activity_ids if i in by_id]
        if named:
            raise OperationsError("No schedule can meet these fixed times together: " + ", ".join(named)
                                  + ". Move one of them, or remove a “comes after” link between them.")
        if trial.status_name == "UNKNOWN":
            raise OperationsError("The solver ran out of time before finding a schedule. Try fewer activities.")
        raise OperationsError("No schedule exists with these activities and resources. Check that the "
                              "needed roles have enough people for the work that must overlap.")
    ops = EventOperations(all_events, merged, tolerance_minutes=10, audit_path=audit_path)
    ops.plan()
    ops.mode = "custom"
    ops.forecast = Forecast()
    ops.planner_end = max(s.end_minutes for s in ops.schedule.activities.values())
    ops.audit.record(ops.now, "schedule.planned", "planner",
                     f"Planner-entered event “{event.name}” planned: {len(event.activities)} activities"
                     + (f", alongside {len(with_events)} other event(s)" if with_events else ""))
    return ops
