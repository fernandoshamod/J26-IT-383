"""
Demo scenario for the dashboard: the proposal's eleven-activity Perera
wedding (Section 1.1) plus a concurrent corporate launch that shares the
florist and AV crew (cross-event conflicts, FR-06).
"""

from __future__ import annotations

from dataclasses import replace
from pathlib import Path

from examples.run_example import build_concurrent_corporate_event, build_resources, build_wedding
from api.forecast import forecast
from scheduling_engine.duration_prediction import with_predicted_durations
from scheduling_engine.models import Event
from scheduling_engine.solver import solve_planning_phase
from scheduling_engine.operations import EventOperations
from scheduling_engine.twin import ActivityState, CheckInType

SETUP_EARLIEST_START = 8 * 60  # venue opens 08:00
CORPORATE_LAUNCH_START = 10 * 60 + 30  # the launch is announced to guests for 10:30
# The ceremony has zero slack around the client's fixed times, so it gets a
# tighter tolerance than the default (Objective 3: per-activity thresholds).
TOLERANCE_BY_ACTIVITY = {"ceremony": 5}


def build_demo_events() -> list[Event]:
    wedding = build_wedding()
    wedding = replace(wedding, activities=[
        replace(a, earliest_start_minutes=SETUP_EARLIEST_START) if a.id == "venue_setup" else a
        for a in wedding.activities
    ])
    corporate = build_concurrent_corporate_event()
    corporate = replace(corporate, activities=[
        replace(a, fixed_start_minutes=CORPORATE_LAUNCH_START) if a.id == "corp_event" else a
        for a in corporate.activities
    ])
    return [wedding, corporate]


PLANNING_MODES = ("planner", "predicted")


def new_operations(audit_path: Path | None = None, mode: str = "planner") -> EventOperations:
    """Plan the demo day. mode="planner" uses the planner's own durations;
    mode="predicted" uses the ML duration model's predictions (Section
    4.2.1). The forecast is computed either way, so the dashboard can
    always show both side by side."""
    if mode not in PLANNING_MODES:
        raise ValueError(f"unknown planning mode {mode!r}")
    events = build_demo_events()
    resources = build_resources()
    planner_schedule = solve_planning_phase(events, resources)
    fc = forecast(events, planner_schedule)
    if mode == "predicted":
        events = [with_predicted_durations(e, fc.predicted) for e in events]
    ops = EventOperations(events, resources, tolerance_minutes=10,
                          tolerance_by_activity=TOLERANCE_BY_ACTIVITY, audit_path=audit_path)
    ops.plan()
    ops.mode = mode
    ops.forecast = fc
    ops.planner_end = max(s.end_minutes for s in planner_schedule.activities.values())
    if mode == "predicted":
        changed = sum(1 for d in fc.durations if d["predicted"] is not None and d["predicted"] != d["planner"])
        ops.audit.record(ops.now, "schedule.planned", "system",
                         f"Planned with ML-predicted durations: {changed} activities re-estimated by the "
                         f"duration model; day ends {_hhmm(max(s.end_minutes for s in ops.schedule.activities.values()))} "
                         f"vs {_hhmm(ops.planner_end)} with planner estimates")
    return ops


def _hhmm(m: int) -> str:
    return f"{m // 60:02d}:{m % 60:02d}"


def play_on_time(ops: EventOperations, until: int, silent: set[str] = frozenset(),
                 late_start: dict[str, int] | None = None, no_completion: set[str] = frozenset()) -> None:
    """Fast-forward the event to `until`: every activity whose planned start
    or end falls before `until` checks in exactly on plan — except those in
    `silent` (vendor never confirms: the sensor-free detection case),
    `no_completion` (starts on time, never confirms finishing: an overrun)
    and `late_start` (confirms N minutes late: the known-delay case).
    Check-ins are replayed in time order, as they'd arrive on the day."""
    late_start = late_start or {}
    # Anything that can't have started yet: downstream of an unconfirmed
    # activity, OR waiting for a crew/vendor that is still busy on one.
    blocked = _blocked(ops, set(silent) | set(no_completion))
    pending: list[tuple[int, str, CheckInType]] = []
    for aid, s in ops.schedule.activities.items():
        state = ops.twin.state_of(aid).state
        if aid in silent or aid in blocked:
            continue
        start = s.start_minutes + late_start.get(aid, 0)
        end = start + (s.end_minutes - s.start_minutes)
        if state is ActivityState.NOT_STARTED and start <= until:
            pending.append((start, aid, CheckInType.STARTED))
            if end <= until and aid not in no_completion:
                pending.append((end, aid, CheckInType.COMPLETED))
        elif state is ActivityState.IN_PROGRESS and end <= until and aid not in no_completion:
            pending.append((end, aid, CheckInType.COMPLETED))
    for at, aid, kind in sorted(pending, key=lambda x: (x[0], x[2] is CheckInType.STARTED)):
        ops.check_in(aid, kind, at)
    ops.tick(until)


def _blocked(ops: EventOperations, held: set[str]) -> set[str]:
    """Activities that can't have started while `held` activities are
    unconfirmed: their precedence descendants, and anything planned to use
    the same resource after them (the resource is still busy). Repeated
    until nothing new is added, since a blocked activity blocks its own
    successors and resources in turn."""
    blocked: set[str] = set()
    frontier = set(held)
    while frontier:
        new = _descendants(ops, frontier)
        for h in frontier:
            hs = ops.schedule.activities[h]
            for aid, s in ops.schedule.activities.items():
                if (aid != h and s.start_minutes >= hs.start_minutes
                        and set(s.assigned_resource_ids) & set(hs.assigned_resource_ids)):
                    new.add(aid)
        frontier = new - blocked - held
        blocked |= new
    return blocked - held


def _descendants(ops: EventOperations, roots: set[str]) -> set[str]:
    successors: dict[str, list[str]] = {}
    for a in ops.activities:
        for pred in a.predecessors:
            successors.setdefault(pred, []).append(a.id)
    seen: set[str] = set()
    stack = list(roots)
    while stack:
        for nxt in successors.get(stack.pop(), []):
            if nxt not in seen:
                seen.add(nxt)
                stack.append(nxt)
    return seen


# One-click demo scenarios for the dashboard: (title, what it shows, play kwargs builder).
def scenario_kwargs(name: str, ops: EventOperations) -> dict:
    s = ops.schedule.activities
    if name == "late_catering":
        # Known delay, absorbed by slack before the fixed 14:00 guest arrival.
        return dict(until=s["guest_arrival"].start_minutes, late_start={"catering_load_in": 40})
    if name == "setup_overrun":
        # Setup crew never confirms finishing; 40 min later the shared AV crew
        # is the bottleneck between the wedding and the corporate launch.
        return dict(until=s["venue_setup"].end_minutes + 30, no_completion={"venue_setup"})
    if name == "silent_photographer":
        # Photographer starts but never confirms; detected from silence alone.
        return dict(until=s["photos"].end_minutes + 20, no_completion={"photos"})
    raise ValueError(f"unknown scenario {name!r}")
