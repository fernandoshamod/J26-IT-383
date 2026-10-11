"""
Real-Time Operational Digital Twin (proposal Section 4.2.2; Objective 3;
FR-08, FR-09, FR-10).

This is the handoff point between the two phases your Section 4.1
architecture diagram shows: a `Schedule` produced by solver.py (Section
4.2.1, the planning phase) becomes the reference state this twin compares
the live event against (Section 4.2.2, the execution phase). Nothing in
this module calls the solver — the twin only watches and reports
divergence. Producing a *revised* schedule in response is a separate,
later subsystem (adaptive re-optimisation, Objective 5), not built yet.

The central design point, directly from Section 1.4's novelty claim: an
event venue has no sensors, so the only facts this twin can ever know are
the check-ins staff and vendors choose to report. That means there are
two, genuinely different, ways an activity's timing can diverge from plan:

  1. An explicit check-in arrives, but at a time that doesn't match the
     plan (e.g. "a catering vendor arrives forty minutes late" — the
     proposal's own example, Section 1.1). The system *knows* a delay
     happened because it was told.

  2. No check-in arrives at all, even though the plan says the activity
     should already have started or finished. The system cannot know
     *why* — only that the confirmation it expected is overdue. Section
     1.4 calls this out explicitly: the absence itself is the signal.
     This is what removes the dependency on sensor hardware that the
     manufacturing digital-twin literature (Section 1.2.2) assumes.

Both are handled below, and both are reported as a Divergence — but as
distinct types, because a planner needs to know which kind of problem
they're looking at: "I was told about a delay" is a different situation
from "I've heard nothing and should have by now."
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from scheduling_engine.models import Schedule


class CheckInType(str, Enum):
    STARTED = "started"
    COMPLETED = "completed"


@dataclass(frozen=True)
class CheckIn:
    """A single report from a vendor/staff mobile check-in (FR-08)."""

    activity_id: str
    type: CheckInType
    reported_at_minutes: int


class ActivityState(str, Enum):
    NOT_STARTED = "not_started"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"


@dataclass
class ActivityTwinState:
    activity_id: str
    state: ActivityState = ActivityState.NOT_STARTED
    actual_start_minutes: int | None = None
    actual_end_minutes: int | None = None


class DivergenceType(str, Enum):
    # No check-in received at all, past tolerance — the sensor-free signal.
    MISSING_START_CONFIRMATION = "missing_start_confirmation"
    MISSING_COMPLETION_CONFIRMATION = "missing_completion_confirmation"
    # A check-in WAS received, but its timing misses the plan by more than
    # tolerance — a known, reported delay (or early arrival).
    START_TIME_DEVIATION = "start_time_deviation"
    END_TIME_DEVIATION = "end_time_deviation"


@dataclass(frozen=True)
class Divergence:
    activity_id: str
    type: DivergenceType
    planned_minutes: int
    reference_minutes: int  # the check-in time, or "now" for a missing-confirmation divergence
    delta_minutes: int  # signed: positive = late/overdue, negative = early


class OperationalDigitalTwin:
    """Live state for one planning-phase Schedule, plus divergence
    detection against it.

    `default_tolerance_minutes` is the Objective 3 "tolerance threshold at
    which divergence constitutes a disruption" — small timing noise (a
    vendor confirming two minutes later than planned) is normal and must
    not trigger every downstream mechanism a real disruption would.
    `tolerance_minutes_by_activity` lets specific activities (e.g. a fixed
    ceremony time with zero slack) use a tighter threshold than the rest.
    """

    def __init__(
        self,
        schedule: Schedule,
        default_tolerance_minutes: int = 10,
        tolerance_minutes_by_activity: dict[str, int] | None = None,
    ) -> None:
        if not schedule.is_feasible:
            raise ValueError("cannot build a twin from a non-feasible schedule")
        self.schedule = schedule
        self._default_tolerance_minutes = default_tolerance_minutes
        self._tolerance_overrides = tolerance_minutes_by_activity or {}
        self._states: dict[str, ActivityTwinState] = {
            activity_id: ActivityTwinState(activity_id) for activity_id in schedule.activities
        }
        self._check_ins: list[CheckIn] = []

    def tolerance_for(self, activity_id: str) -> int:
        return self._tolerance_overrides.get(activity_id, self._default_tolerance_minutes)

    def state_of(self, activity_id: str) -> ActivityTwinState:
        return self._states[activity_id]

    def record_check_in(self, check_in: CheckIn) -> None:
        if check_in.activity_id not in self._states:
            raise KeyError(f"{check_in.activity_id!r} is not in this twin's schedule")
        state = self._states[check_in.activity_id]
        if check_in.type is CheckInType.STARTED:
            state.state = ActivityState.IN_PROGRESS
            state.actual_start_minutes = check_in.reported_at_minutes
        else:
            state.state = ActivityState.COMPLETED
            state.actual_end_minutes = check_in.reported_at_minutes
        self._check_ins.append(check_in)

    def detect_divergence(self, now_minutes: int) -> list[Divergence]:
        """Compare live state against the plan as of `now_minutes`
        (absolute minutes on the shared timeline — see models.py). Called
        repeatedly as the event progresses; it is not a one-shot check.
        """
        divergences: list[Divergence] = []
        for activity_id, planned in self.schedule.activities.items():
            state = self._states[activity_id]
            tolerance = self.tolerance_for(activity_id)

            if state.actual_start_minutes is None:
                overdue = now_minutes - planned.start_minutes
                if overdue > tolerance:
                    divergences.append(
                        Divergence(
                            activity_id=activity_id,
                            type=DivergenceType.MISSING_START_CONFIRMATION,
                            planned_minutes=planned.start_minutes,
                            reference_minutes=now_minutes,
                            delta_minutes=overdue,
                        )
                    )
            else:
                start_delta = state.actual_start_minutes - planned.start_minutes
                if abs(start_delta) > tolerance:
                    divergences.append(
                        Divergence(
                            activity_id=activity_id,
                            type=DivergenceType.START_TIME_DEVIATION,
                            planned_minutes=planned.start_minutes,
                            reference_minutes=state.actual_start_minutes,
                            delta_minutes=start_delta,
                        )
                    )

            if state.state is ActivityState.IN_PROGRESS:
                overdue = now_minutes - planned.end_minutes
                if overdue > tolerance:
                    divergences.append(
                        Divergence(
                            activity_id=activity_id,
                            type=DivergenceType.MISSING_COMPLETION_CONFIRMATION,
                            planned_minutes=planned.end_minutes,
                            reference_minutes=now_minutes,
                            delta_minutes=overdue,
                        )
                    )
            elif state.state is ActivityState.COMPLETED:
                end_delta = state.actual_end_minutes - planned.end_minutes
                if abs(end_delta) > tolerance:
                    divergences.append(
                        Divergence(
                            activity_id=activity_id,
                            type=DivergenceType.END_TIME_DEVIATION,
                            planned_minutes=planned.end_minutes,
                            reference_minutes=state.actual_end_minutes,
                            delta_minutes=end_delta,
                        )
                    )

        return divergences
