"""
Live event operations: the closed loop of proposal Section 4.2.2, run as
one service the API and dashboard drive.

    check-in (FR-08) -> digital twin (FR-09) -> divergence (FR-10)
      -> simulate the do-nothing cascade (FR-11)
      -> re-optimise the remainder (FR-12, locks respected)
      -> PROPOSAL shown to the planner with both outcomes (FR-13)
      -> planner confirms -> revised plan written back into the twin as the
         new reference, cost signal published for Component 4 (FR-14),
         affected staff/vendors notified (FR-15)
    ... every step recorded in the audit log (FR-16).

Nothing changes the live schedule without the planner's confirmation
(FR-13): the system proposes, a person decides. That is a deliberate
design choice: an event planner is accountable to the client in a way an
optimiser is not, and an unexpected automatic change on event day would
erode trust in the tool.

Time: `now` is a minute on the shared event timeline (models.py). In a
real deployment it comes from the wall clock; in the demo it's advanced
by hand so a whole event day can be shown in minutes.
"""

from __future__ import annotations

import itertools
import time
from dataclasses import dataclass, field, replace
from pathlib import Path

from scheduling_engine.conflict_detection import verify_schedule
from scheduling_engine.integration import (
    TOPIC_CHECK_IN,
    TOPIC_COST_SIGNAL,
    TOPIC_DISRUPTION,
    TOPIC_DISRUPTION_ABSORBED,
    TOPIC_PROPOSAL,
    TOPIC_PROPOSAL_REJECTED,
    TOPIC_PROPOSAL_SUPERSEDED,
    TOPIC_SCHEDULE_CHANGED,
    TOPIC_SCHEDULE_PLANNED,
    AuditLog,
    Component4Stub,
    EventBus,
    NotificationService,
)
from scheduling_engine.models import Activity, Event, Resource, Schedule
from scheduling_engine.reoptimization import CostSignal, reoptimize
from scheduling_engine.simulation import simulate_cascade
from scheduling_engine.solver import solve_planning_phase
from scheduling_engine.twin import (
    ActivityState,
    CheckIn,
    CheckInType,
    Divergence,
    DivergenceType,
    OperationalDigitalTwin,
)


class OperationsError(ValueError):
    """A request that can't be applied (unknown id, wrong state, ...)."""


@dataclass
class ActivityChange:
    activity_id: str
    activity_name: str
    old_start: int
    old_end: int
    new_start: int
    new_end: int
    resource_ids: list[str]


@dataclass
class Proposal:
    """What the planner sees before deciding (FR-13)."""

    id: int
    created_at_minute: int
    trigger: list[Divergence]
    predicted_extra_duration: dict[str, int]
    # Do nothing: what the simulation predicts if the plan is left alone.
    do_nothing_delay: dict[str, int]
    do_nothing_end: int
    do_nothing_violations: list[str]
    # Re-optimise: the revised plan and what it costs operationally.
    is_feasible: bool
    revised: Schedule | None
    changes: list[ActivityChange]
    revised_end: int | None
    cost_signal: CostSignal | None
    conflicting_locked_ids: list[str]
    solve_seconds: float
    status: str = "pending"  # pending / confirmed / rejected / superseded
    decided_by: str | None = None
    decision_note: str | None = None


def _divergence_key(d: Divergence) -> tuple[str, str]:
    return (d.activity_id, d.type.value)


def _is_disruptive(d: Divergence) -> bool:
    # Early arrivals/finishes are divergence, not disruption.
    return d.delta_minutes > 0


@dataclass
class EventOperations:
    events: list[Event]
    resources: list[Resource]
    tolerance_minutes: int = 10
    tolerance_by_activity: dict[str, int] = field(default_factory=dict)
    audit_path: Path | None = None
    reoptimize_time_limit_seconds: float = 5.0

    def __post_init__(self) -> None:
        self.bus = EventBus()
        self.audit = AuditLog(self.audit_path)
        self.notifications = NotificationService(self.bus, {r.id: r.name for r in self.resources})
        self.component4 = Component4Stub(self.bus)
        self.proposals: list[Proposal] = []
        self._proposal_ids = itertools.count(1)
        # (activity, divergence type) -> the delay the planner has already
        # seen and decided on. Re-raised only if it grows by more than the
        # tolerance again: "accepted 20 min late" is not "accepted 80 min".
        self._acknowledged: dict[tuple[str, str], int] = {}
        self.schedule: Schedule | None = None
        self.twin: OperationalDigitalTwin | None = None
        self.now: int = 0
        self.schedule_version = 0
        self._seen_client_ids: set[str] = set()

    # --- lookups ----------------------------------------------------------

    @property
    def activities(self) -> list[Activity]:
        return [a for e in self.events for a in e.activities]

    def activity(self, activity_id: str) -> Activity:
        for a in self.activities:
            if a.id == activity_id:
                return a
        raise OperationsError(f"unknown activity {activity_id!r}")

    @property
    def pending_proposal(self) -> Proposal | None:
        return next((p for p in self.proposals if p.status == "pending"), None)

    def _require_plan(self) -> None:
        if self.schedule is None or self.twin is None:
            raise OperationsError("no live plan yet: call plan() first")

    # --- planning phase ---------------------------------------------------

    def plan(self) -> Schedule:
        """Solve the master schedule and start the twin (Section 4.2.1)."""
        schedule = solve_planning_phase(self.events, self.resources)
        if not schedule.is_feasible:
            self.audit.record(0, "schedule.infeasible", "system",
                              f"No feasible schedule ({schedule.status_name})",
                              {"conflicting_pinned": schedule.conflicting_pinned_activity_ids})
            raise OperationsError(
                f"no feasible schedule ({schedule.status_name}); conflicting fixed/locked activities: "
                f"{schedule.conflicting_pinned_activity_ids}")
        conflicts = verify_schedule(self.activities, self.resources, schedule.activities)
        self.schedule = schedule
        self.twin = self._new_twin(schedule, check_ins=[])
        self.now = min(s.start_minutes for s in schedule.activities.values())
        self.schedule_version = 1
        self.audit.record(self.now, TOPIC_SCHEDULE_PLANNED, "system",
                          f"Master schedule planned: {len(schedule.activities)} activities, "
                          f"{len(conflicts)} conflicts on independent verification, "
                          f"solved in {schedule.solve_time_seconds:.2f}s",
                          {"makespan": schedule.makespan_minutes, "conflicts": len(conflicts)})
        self.bus.publish(TOPIC_SCHEDULE_PLANNED, {"version": 1, "activities": schedule.activities})
        return schedule

    def _new_twin(self, schedule: Schedule, check_ins: list[CheckIn]) -> OperationalDigitalTwin:
        twin = OperationalDigitalTwin(schedule, self.tolerance_minutes, self.tolerance_by_activity)
        for c in check_ins:
            twin.record_check_in(c)
        return twin

    def lock(self, activity_id: str, start_minutes: int, by: str) -> None:
        """FR-07: pin an activity's start so re-optimisation can't move it."""
        a = self.activity(activity_id)
        a.locked_start_minutes = start_minutes
        self.audit.record(self.now, "activity.locked", f"planner:{by}",
                          f"{a.name} locked to start at {_hhmm(start_minutes)}")

    # --- execution phase --------------------------------------------------

    def check_in(self, activity_id: str, kind: CheckInType, at_minutes: int | None = None, by: str | None = None,
                 client_id: str | None = None, queued_offline: bool = False) -> list[Divergence]:
        """FR-08: a vendor/staff confirmation. Returns current divergences.

        NFR-07 (intermittent connectivity): a phone that loses signal keeps
        the check-in with the time it was TAPPED (`at_minutes`) and sends
        it later (`queued_offline`). If a send reached us but the reply was
        lost, the phone sends it again: the same `client_id` is accepted
        once and ignored after, so a retry can never double-count."""
        self._require_plan()
        if client_id is not None and client_id in self._seen_client_ids:
            return self.twin.detect_divergence(self.now)
        a = self.activity(activity_id)
        at = self.now if at_minutes is None else at_minutes
        state = self.twin.state_of(activity_id).state
        if kind is CheckInType.STARTED and state is not ActivityState.NOT_STARTED:
            raise OperationsError(f"{a.name} has already started")
        if kind is CheckInType.COMPLETED and state is not ActivityState.IN_PROGRESS:
            raise OperationsError(f"{a.name} can't complete: it hasn't started")
        self.twin.record_check_in(CheckIn(activity_id, kind, at))
        if client_id is not None:
            self._seen_client_ids.add(client_id)
        self.audit.record(at, TOPIC_CHECK_IN, f"checkin:{by or activity_id}",
                          f"{a.name} {kind.value} at {_hhmm(at)}"
                          + (f" (queued offline, delivered at {_hhmm(self.now)})" if queued_offline else ""))
        self.bus.publish(TOPIC_CHECK_IN, {"activity_id": activity_id, "type": kind, "at": at})
        # A proposal is only valid for the state it was computed from. New
        # facts make it stale: confirming it could undo what just happened.
        pending = self.pending_proposal
        if pending is not None:
            pending.status = "superseded"
            self.audit.record(self.now, TOPIC_PROPOSAL_SUPERSEDED, "system",
                              f"Proposal #{pending.id} superseded by new check-in ({a.name}); recomputing")
        return self.tick(max(self.now, at))

    def tick(self, now: int) -> list[Divergence]:
        """Advance the clock and look for new disruptions. Called by every
        check-in and by the clock (missing confirmations only show up as
        time passes — the sensor-free signal)."""
        self._require_plan()
        self.now = max(self.now, now)
        divergences = self.twin.detect_divergence(self.now)
        new = [d for d in divergences if _is_disruptive(d) and self._is_news(d)]
        pending = self.pending_proposal
        if new and pending is not None and self._outgrows(pending, new):
            # The proposal was sized for a smaller disruption; it's stale.
            pending.status = "superseded"
            self.audit.record(self.now, TOPIC_PROPOSAL_SUPERSEDED, "system",
                              f"Proposal #{pending.id} superseded: the disruption has grown; recomputing")
        if new and self.pending_proposal is None:
            for d in new:
                self.audit.record(self.now, TOPIC_DISRUPTION, "system",
                                  f"{self.activity(d.activity_id).name}: {d.type.value.replace('_', ' ')} "
                                  f"({d.delta_minutes:+d} min)", d)
                self.bus.publish(TOPIC_DISRUPTION, d)
            self._propose([d for d in divergences if _is_disruptive(d)])
        return divergences

    def _outgrows(self, proposal: Proposal, divergences: list[Divergence]) -> bool:
        sized_for = {_divergence_key(d): d.delta_minutes for d in proposal.trigger}
        return any(_divergence_key(d) not in sized_for
                   or d.delta_minutes > sized_for[_divergence_key(d)] + self.twin.tolerance_for(d.activity_id)
                   for d in divergences)

    def _client_facing(self) -> set[str]:
        """Activities whose delay a client actually experiences: fixed or
        locked times, and the last activity of each event (its end time)."""
        has_successor = {p for a in self.activities for p in a.predecessors}
        return {a.id for a in self.activities
                if a.pinned_start_minutes() is not None or a.id not in has_successor}

    def _is_news(self, d: Divergence) -> bool:
        seen = self._acknowledged.get(_divergence_key(d))
        return seen is None or d.delta_minutes > seen + self.twin.tolerance_for(d.activity_id)

    def _acknowledge(self, divergences: list[Divergence]) -> None:
        for d in divergences:
            self._acknowledged[_divergence_key(d)] = d.delta_minutes

    def _propose(self, trigger: list[Divergence]) -> Proposal | None:
        """FR-11 + FR-12: simulate doing nothing, then re-optimise, and
        put both in front of the planner."""
        # A missing COMPLETION means it's still running past its planned
        # end: the overdue time is the minimum extra duration. (A late
        # START needs no extra duration: the recorded actual start, or
        # 'not before now' for a missing one, already shifts it.)
        extra = {d.activity_id: d.delta_minutes for d in trigger
                 if d.type is DivergenceType.MISSING_COMPLETION_CONFIRMATION}
        cascade = simulate_cascade(self.activities, self.resources, self.schedule, self.twin, self.now, extra)
        violations = [c.message for c in verify_schedule(self.activities, self.resources,
                                                         cascade.predicted_activities)]
        do_nothing_delay = {k: v for k, v in cascade.delay_minutes.items() if v > 0}
        client_delay = {k: v for k, v in do_nothing_delay.items() if k in self._client_facing()}
        if not client_delay and not violations:
            # Slack absorbs it: no client-facing time moves, no rule breaks.
            # Internal activities may shift within their slack; that's what
            # slack is for. Record it, don't interrupt the planner.
            self._acknowledge(trigger)
            self.audit.record(self.now, TOPIC_DISRUPTION_ABSORBED, "system",
                              "Simulated: absorbed by slack — no client-facing time moves, no rule broken; "
                              "no action needed", {"trigger": trigger, "internal_shifts": do_nothing_delay})
            return None
        started = time.perf_counter()
        result = reoptimize(self.activities, self.resources, self.schedule, self.twin, self.now, extra,
                            time_limit_seconds=self.reoptimize_time_limit_seconds)
        solve_seconds = time.perf_counter() - started

        changes = []
        if result.is_feasible:
            for a in self.activities:
                # Completed activities are recorded facts, not changes anyone
                # must act on — leave them out of changes and notifications.
                if self.twin.state_of(a.id).state is ActivityState.COMPLETED:
                    continue
                old, new = self.schedule.activities[a.id], result.schedule.activities[a.id]
                if (old.start_minutes, old.end_minutes) != (new.start_minutes, new.end_minutes):
                    changes.append(ActivityChange(a.id, a.name, old.start_minutes, old.end_minutes,
                                                  new.start_minutes, new.end_minutes,
                                                  sorted(set(old.assigned_resource_ids) | set(new.assigned_resource_ids))))
        proposal = Proposal(
            id=next(self._proposal_ids), created_at_minute=self.now, trigger=trigger,
            predicted_extra_duration=extra,
            do_nothing_delay=do_nothing_delay,
            do_nothing_end=max(s.end_minutes for s in cascade.predicted_activities.values()),
            do_nothing_violations=violations,
            is_feasible=result.is_feasible, revised=result.schedule, changes=changes,
            revised_end=(max(s.end_minutes for s in result.schedule.activities.values())
                         if result.is_feasible else None),
            cost_signal=result.cost_signal, conflicting_locked_ids=result.conflicting_pinned_activity_ids,
            solve_seconds=solve_seconds,
        )
        self.proposals.append(proposal)
        summary = (f"Proposal #{proposal.id}: do nothing ends {_hhmm(proposal.do_nothing_end)} with "
                   f"{len(violations)} rule violation(s); re-optimised plan "
                   + (f"ends {_hhmm(proposal.revised_end)}, moves {len(changes)} activities, "
                      f"computed in {solve_seconds:.2f}s" if result.is_feasible
                      else f"is INFEASIBLE (locked: {result.conflicting_pinned_activity_ids})"))
        self.audit.record(self.now, TOPIC_PROPOSAL, "system", summary,
                          {"do_nothing_delay": proposal.do_nothing_delay, "violations": violations,
                           "changes": changes, "cost_signal": result.cost_signal})
        self.bus.publish(TOPIC_PROPOSAL, {"proposal_id": proposal.id, "summary": summary})
        return proposal

    def confirm(self, proposal_id: int, planner: str, note: str = "") -> Proposal:
        """FR-13 decision. Applies the revised plan, writes it back into the
        twin as the new reference (replaying every check-in so far, so no
        observed fact is lost — NFR-03), then publishes the change, the cost
        signal (FR-14) and notifications (FR-15)."""
        p = self._pending(proposal_id)
        if not p.is_feasible:
            raise OperationsError("an infeasible proposal can't be confirmed; unlock or reject it")
        check_ins = list(self.twin.check_ins)
        self.schedule = p.revised
        self.twin = self._new_twin(p.revised, check_ins)
        self.schedule_version += 1
        p.status, p.decided_by, p.decision_note = "confirmed", planner, note
        # Divergence is now measured against the NEW plan, so start fresh:
        # e.g. an activity that overruns even its revised end must trigger again.
        self._acknowledged.clear()

        self.audit.record(self.now, TOPIC_SCHEDULE_CHANGED, f"planner:{planner}",
                          f"Proposal #{p.id} confirmed: schedule v{self.schedule_version}, "
                          f"{len(p.changes)} activities moved" + (f" — {note}" if note else ""),
                          {"changes": p.changes})
        self.bus.publish(TOPIC_SCHEDULE_CHANGED, {"version": self.schedule_version, "proposal_id": p.id,
                                                  "event_minute": self.now, "changes": p.changes})
        self.bus.publish(TOPIC_COST_SIGNAL, {"proposal_id": p.id, "event_minute": self.now,
                                             "schedule_version": self.schedule_version,
                                             "cost_signal": p.cost_signal})
        self.audit.record(self.now, TOPIC_COST_SIGNAL, "system",
                          f"Cost signal sent to Component 4: {p.cost_signal.total_delay_minutes} delay-minutes, "
                          f"{len(p.cost_signal.resource_overtime_minutes)} resource(s) on overtime",
                          {"cost_signal": p.cost_signal})
        # The new plan may already be overdue somewhere; look again.
        self.tick(self.now)
        return p

    def reject(self, proposal_id: int, planner: str, note: str = "") -> Proposal:
        p = self._pending(proposal_id)
        p.status, p.decided_by, p.decision_note = "rejected", planner, note
        # Don't re-propose for the same divergences at the same size; a new
        # or substantially worse one still triggers.
        self._acknowledge(p.trigger)
        self.audit.record(self.now, TOPIC_PROPOSAL_REJECTED, f"planner:{planner}",
                          f"Proposal #{p.id} rejected" + (f" — {note}" if note else ""))
        self.bus.publish(TOPIC_PROPOSAL_REJECTED, {"proposal_id": p.id})
        return p

    def _pending(self, proposal_id: int) -> Proposal:
        p = next((p for p in self.proposals if p.id == proposal_id), None)
        if p is None:
            raise OperationsError(f"unknown proposal {proposal_id}")
        if p.status != "pending":
            raise OperationsError(f"proposal {proposal_id} is already {p.status}")
        return p


def _hhmm(minutes: int) -> str:
    h, m = divmod(int(minutes), 60)
    return f"{h:02d}:{m:02d}"
