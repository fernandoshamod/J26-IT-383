"""
Data model for the planning-phase scheduling engine (proposal Section 4.2.1).

These are plain dataclasses, not CP-SAT variables. The solver (solver.py)
reads these and builds a constraint model from them. Keeping the data model
free of any OR-Tools type means it can be unit-tested, serialised to/from
JSON, and reused by the execution-phase digital twin later without pulling
in the solver.

Timeline convention: every *_minutes field is an absolute integer offset
from a single shared epoch (e.g. minutes since 00:00 on the first day of
the planning horizon). Using one shared timeline — rather than a clock
per event — is what lets the solver see two concurrent events competing
for the same staff member and refuse to double-book them (Objective 2 /
FR-06: conflict detection across concurrent events).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum


class ResourceType(str, Enum):
    STAFF = "staff"
    EQUIPMENT = "equipment"
    VENDOR = "vendor"


@dataclass(frozen=True)
class Resource:
    """A physical thing or person that activities compete for.

    `role` is the matching key used by ResourceRequirement (e.g. both a
    staff member and a subcontracted vendor can satisfy role="sound_tech").

    `capacity` lets one Resource record stand for a pool of identical
    interchangeable units (e.g. 5 identical microphones) rather than
    requiring one record per physical microphone.

    `min_turnaround_minutes` is the minimum time the resource must stay
    blocked *after* an activity ends before it can be reused — e.g. a
    crew needs a break, a hall needs resetting. This is a property of the
    resource, not of the activity.
    """

    id: str
    name: str
    type: ResourceType
    role: str
    capacity: int = 1
    min_turnaround_minutes: int = 0


@dataclass(frozen=True)
class ResourceRequirement:
    """One line of an activity's resource demand, e.g. "2 servers"."""

    role: str
    count: int = 1


@dataclass
class Activity:
    """One schedulable unit of work belonging to one event."""

    id: str
    event_id: str
    name: str
    duration_minutes: int
    requirements: list[ResourceRequirement] = field(default_factory=list)

    # Precedence: this activity cannot start until every id in
    # `predecessors` has finished (plus any extra lag named in
    # `min_lag_minutes`, keyed by predecessor id; default lag is 0,
    # meaning "may start the instant the predecessor ends").
    predecessors: list[str] = field(default_factory=list)
    min_lag_minutes: dict[str, int] = field(default_factory=dict)

    # The earliest absolute minute this activity is allowed to start
    # (e.g. the venue isn't accessible before this).
    earliest_start_minutes: int = 0

    # Externally imposed time (FR-04): the activity MUST start exactly
    # here, full stop — e.g. a ceremony the client has fixed to 4:00 PM.
    fixed_start_minutes: int | None = None

    # Planner-locked (FR-07): same effect as fixed_start_minutes (the
    # solver may not move it) but recorded separately because the
    # *reason* differs — this one was pinned by a human decision, not by
    # the nature of the activity — which matters when we explain an
    # infeasibility back to the planner.
    locked_start_minutes: int | None = None

    def pinned_start_minutes(self) -> int | None:
        """The start time this activity is forced to, if any."""
        if self.fixed_start_minutes is not None:
            return self.fixed_start_minutes
        return self.locked_start_minutes


@dataclass
class Event:
    id: str
    name: str
    activities: list[Activity] = field(default_factory=list)


@dataclass
class ScheduledActivity:
    """One row of solver output: where an activity ended up."""

    activity_id: str
    start_minutes: int
    end_minutes: int
    assigned_resource_ids: list[str] = field(default_factory=list)


@dataclass
class Schedule:
    """Full solver output for a planning run."""

    is_feasible: bool
    activities: dict[str, ScheduledActivity] = field(default_factory=dict)
    makespan_minutes: int | None = None
    solve_time_seconds: float = 0.0
    status_name: str = ""

    # Populated only when is_feasible is False: the ids of the
    # fixed/locked activities whose pinned times are jointly
    # unsatisfiable, per solver.diagnose_infeasibility().
    conflicting_pinned_activity_ids: list[str] = field(default_factory=list)
