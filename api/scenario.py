"""
Demo scenario for the dashboard: the proposal's eleven-activity Perera
wedding (Section 1.1) plus a concurrent corporate launch that shares the
florist and AV crew (cross-event conflicts, FR-06).
"""

from __future__ import annotations

from dataclasses import replace
from pathlib import Path

from examples.run_example import build_concurrent_corporate_event, build_resources, build_wedding
from scheduling_engine.models import Event
from scheduling_engine.operations import EventOperations
from scheduling_engine.twin import ActivityState, CheckInType

SETUP_EARLIEST_START = 8 * 60  # venue opens 08:00
# The ceremony has zero slack around the client's fixed times, so it gets a
# tighter tolerance than the default (Objective 3: per-activity thresholds).
TOLERANCE_BY_ACTIVITY = {"ceremony": 5}


def build_demo_events() -> list[Event]:
    wedding = build_wedding()
    wedding = replace(wedding, activities=[
        replace(a, earliest_start_minutes=SETUP_EARLIEST_START) if a.id == "venue_setup" else a
        for a in wedding.activities
    ])
    return [wedding, build_concurrent_corporate_event()]


def new_operations(audit_path: Path | None = None) -> EventOperations:
    ops = EventOperations(build_demo_events(), build_resources(), tolerance_minutes=10,
                          tolerance_by_activity=TOLERANCE_BY_ACTIVITY, audit_path=audit_path)
    ops.plan()
    return ops


def play_on_time(ops: EventOperations, until: int, silent: set[str] = frozenset(),
                 late_start: dict[str, int] | None = None) -> None:
    """Fast-forward the event to `until`: every activity whose planned start
    or end falls before `until` checks in exactly on plan — except those in
    `silent` (vendor never confirms: the sensor-free detection case) and
    those in `late_start` (confirms N minutes late: the known-delay case).
    Check-ins are replayed in time order, as they'd arrive on the day."""
    late_start = late_start or {}
    pending: list[tuple[int, str, CheckInType]] = []
    for aid, s in ops.schedule.activities.items():
        state = ops.twin.state_of(aid).state
        if aid in silent:
            continue
        start = s.start_minutes + late_start.get(aid, 0)
        end = start + (s.end_minutes - s.start_minutes)
        if state is ActivityState.NOT_STARTED and start <= until:
            pending.append((start, aid, CheckInType.STARTED))
            if end <= until:
                pending.append((end, aid, CheckInType.COMPLETED))
        elif state is ActivityState.IN_PROGRESS and end <= until:
            pending.append((end, aid, CheckInType.COMPLETED))
    for at, aid, kind in sorted(pending, key=lambda x: (x[0], x[2] is CheckInType.STARTED)):
        ops.check_in(aid, kind, at)
    ops.tick(until)
