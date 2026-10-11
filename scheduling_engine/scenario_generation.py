"""
Synthetic scenario generation for disruption-handling evaluation
(proposal Section 3.3.2 "Synthetic scenario generation"; Objective 6;
Section 3.6 "200 generated scenarios containing disruptions of known
type, magnitude and timing").

The proposal is explicit that this is a declared stand-in, not real-world
data: "no public dataset of event activity durations exists... its use
will be declared explicitly wherever results are reported, and no
synthetic result will be presented as a real-world measurement" (Section
3.3.2). The duration ranges, resource roles and branching probabilities
below are plausible placeholders for what Section 3.3.2's practitioner
interviews would eventually supply (three-point duration estimates per
activity type) — they are declared here, not derived from data.

Structure mirrors Section 1.1's own description of a typical event ("a
single mid-sized wedding reception involves somewhere between eleven and
fifteen distinct activities"): mostly sequential, with occasional
branches sharing resources rather than precedence (like the example's
decor/sound-check pair).
"""

from __future__ import annotations

import random
from dataclasses import dataclass

from scheduling_engine.models import (
    Activity,
    Event,
    Resource,
    ResourceRequirement,
    ResourceType,
    Schedule,
)
from scheduling_engine.solver import solve_planning_phase
from scheduling_engine.twin import CheckIn, CheckInType, OperationalDigitalTwin

# Declared placeholder ranges — see module docstring.
ACTIVITY_COUNT_RANGE = (11, 15)
DURATION_MINUTES_RANGE = (15, 90)
BRANCH_PROBABILITY = 0.3  # chance an activity's predecessor isn't simply "the one before it"
LOCK_PROBABILITY = 0.5  # chance one later-half activity gets planner-locked after the initial solve

# Declared placeholder range for planner contingency buffer (see
# `include_buffer` on generate_scenario). A real planner routinely pads
# a timeline with a few minutes of slack between activities specifically
# so a small delay doesn't immediately cascade — the base generator (with
# include_buffer=False, the default, kept for every result already
# produced before this was added) has NO such padding, since CP-SAT with
# no objective just finds the first feasible packing, which tends to be
# back-to-back. Declared, not elicited — same disclosure as every other
# placeholder range in this module.
BUFFER_MINUTES_RANGE = (0, 20)

ROLE_CAPACITIES = {
    "crew": 2,
    "av_crew": 1,
    "catering_crew": 2,
    "photographer": 1,
    "officiant": 1,
}
# For testing the "resource scarcity, not precedence tightness, is the
# real bottleneck" hypothesis (see evaluate_disruption_handling.py):
# every role gets a second unit, including the three that are normally
# singletons (av_crew, photographer, officiant). Declared, not elicited,
# same as ROLE_CAPACITIES itself — this is a deliberately generous
# counterfactual to isolate resource scarcity as a variable, not a claim
# about what a real venue actually staffs.
GENEROUS_ROLE_CAPACITIES = {role: 2 for role in ROLE_CAPACITIES}
ROLE_TURNAROUND_MINUTES = {"av_crew": 10}


def generate_scenario(
    seed: int, include_buffer: bool = False, generous_resources: bool = False
) -> tuple[Event, list[Resource], Schedule]:
    """Build a randomized but plausible event, solve it, and return the
    event, its resource pool, and the resulting (already-locked-if-chosen)
    schedule — the "undisturbed baseline" a disruption is then injected
    against by `inject_disruption`.

    `include_buffer` (default False, matching every result produced
    before this option existed) adds a declared, randomised contingency
    gap (`BUFFER_MINUTES_RANGE`) as a minimum lag after each precedence
    edge, so the generated schedule carries the kind of planner-built-in
    slack a real timeline usually has, rather than CP-SAT's default
    back-to-back packing.

    `generous_resources` (default False) swaps in `GENEROUS_ROLE_CAPACITIES`
    (2 units of every role) instead of the normal `ROLE_CAPACITIES` (which
    has three singleton roles). Use either flag to compare against the
    original results, not to replace them — see
    evaluate_disruption_handling.py, which runs and reports all
    configurations side by side.
    """
    rng = random.Random(seed)
    n = rng.randint(*ACTIVITY_COUNT_RANGE)
    role_capacities = GENEROUS_ROLE_CAPACITIES if generous_resources else ROLE_CAPACITIES
    roles = list(role_capacities)

    activities: list[Activity] = []
    for i in range(n):
        predecessors = []
        min_lag_minutes = {}
        if i > 0:
            if i > 1 and rng.random() < BRANCH_PROBABILITY:
                predecessors = [f"a{rng.randint(0, i - 1)}"]
            else:
                predecessors = [f"a{i - 1}"]
            if include_buffer:
                min_lag_minutes = {predecessors[0]: rng.randint(*BUFFER_MINUTES_RANGE)}
        num_requirements = rng.choice([1, 1, 2])  # usually one role, sometimes two
        requirement_roles = rng.sample(roles, num_requirements)
        activities.append(
            Activity(
                id=f"a{i}",
                event_id="scenario",
                name=f"Activity {i}",
                duration_minutes=rng.randint(*DURATION_MINUTES_RANGE),
                predecessors=predecessors,
                min_lag_minutes=min_lag_minutes,
                requirements=[ResourceRequirement(role=r) for r in requirement_roles],
            )
        )

    resources = [
        Resource(
            id=f"{role}-{unit}",
            name=f"{role}-{unit}",
            type=ResourceType.STAFF,
            role=role,
            capacity=1,
            min_turnaround_minutes=ROLE_TURNAROUND_MINUTES.get(role, 0),
        )
        for role, capacity in role_capacities.items()
        for unit in range(1, capacity + 1)
    ]

    event = Event("scenario", "Generated scenario", activities)
    schedule = solve_planning_phase([event], resources, minimize_makespan=False)
    if not schedule.is_feasible:
        return event, resources, schedule  # caller checks is_feasible and skips

    # Optionally lock one later-half activity at the time the initial
    # solve already gave it — representing a planner confirming a time
    # after the fact, not a constraint that shaped the original solve.
    if rng.random() < LOCK_PROBABILITY and n > 2:
        locked_index = rng.randint(n // 2, n - 1)
        locked_activity = activities[locked_index]
        locked_activity.locked_start_minutes = schedule.activities[locked_activity.id].start_minutes
        schedule = solve_planning_phase([event], resources, minimize_makespan=False)

    return event, resources, schedule


@dataclass
class DisruptionScenario:
    event: Event
    resources: list[Resource]
    schedule: Schedule
    disrupted_activity_id: str
    injected_delay_minutes: int
    now_minutes: int
    twin: OperationalDigitalTwin
    predicted_extra_duration_minutes: dict[str, int]


# Declared placeholder range for injected disruption magnitude.
DISRUPTION_MAGNITUDE_RANGE = (10, 60)


def _transitive_descendants(activities: list[Activity], root_id: str) -> set[str]:
    """Every activity reachable from `root_id` by following precedence
    forward — i.e. everything that could possibly be affected by root_id
    running late. Used instead of sorting by start time to decide who's
    "downstream" of the disruption: two activities can share the exact
    same planned start (parallel branches off a common predecessor), and
    a start-time sort can't tell them apart, but precedence can.
    """
    successors_of: dict[str, list[str]] = {a.id: [] for a in activities}
    for a in activities:
        for pred_id in a.predecessors:
            successors_of[pred_id].append(a.id)

    descendants: set[str] = set()
    frontier = list(successors_of[root_id])
    while frontier:
        activity_id = frontier.pop()
        if activity_id in descendants:
            continue
        descendants.add(activity_id)
        frontier.extend(successors_of[activity_id])
    return descendants


def inject_disruption(
    event: Event, resources: list[Resource], schedule: Schedule, seed: int
) -> DisruptionScenario:
    """Pick one activity with at least one true precedence-descendant and
    have it overrun by a random, declared amount — a "missing completion
    confirmation" disruption (Section 1.4's own detection mechanism).

    Every other activity's check-in state needs BOTH of two conditions
    checked together, not either alone (both were tried separately during
    development and each was wrong in its own way):

      - A true precedence-descendant of the disrupted activity must stay
        NOT_STARTED regardless of its OWN planned time, because it
        genuinely cannot have started — its predecessor chain runs
        through the disrupted activity, which hasn't really finished yet.
        Checking only "is this activity's planned end before now_minutes"
        would mark a tightly-following descendant "completed on time"
        even though its real predecessor was still overrunning at that
        moment — a causality violation baked into the input data.
      - Everything else (not a descendant) is decided purely by comparing
        its OWN planned start/end against `now_minutes` — the same single
        clock a real twin would use. Checking only "is this a descendant"
        would mark an unrelated, still-in-the-future activity "completed"
        just because it wasn't downstream of the disruption, which is a
        temporal impossibility of its own (claiming something finished
        before its planned start has even arrived) and wrongly anchors a
        still-adjustable future activity as an immovable fact.
    """
    rng = random.Random(seed)
    descendants_by_id = {a.id: _transitive_descendants(event.activities, a.id) for a in event.activities}
    candidates = [a for a in event.activities if descendants_by_id[a.id]]
    disrupted = rng.choice(candidates)
    delay = rng.randint(*DISRUPTION_MAGNITUDE_RANGE)
    now_minutes = schedule.activities[disrupted.id].end_minutes + delay
    affected = descendants_by_id[disrupted.id]

    twin = OperationalDigitalTwin(schedule, default_tolerance_minutes=10)
    for a in event.activities:
        planned = schedule.activities[a.id]
        if a.id == disrupted.id:
            twin.record_check_in(CheckIn(a.id, CheckInType.STARTED, planned.start_minutes))
            continue  # this one's completion is never confirmed — the disruption itself
        if a.id in affected:
            continue  # genuinely can't have started yet — left NOT_STARTED
        if planned.start_minutes <= now_minutes:
            twin.record_check_in(CheckIn(a.id, CheckInType.STARTED, planned.start_minutes))
        if planned.end_minutes <= now_minutes:
            twin.record_check_in(CheckIn(a.id, CheckInType.COMPLETED, planned.end_minutes))

    return DisruptionScenario(
        event=event,
        resources=resources,
        schedule=schedule,
        disrupted_activity_id=disrupted.id,
        injected_delay_minutes=delay,
        now_minutes=now_minutes,
        twin=twin,
        predicted_extra_duration_minutes={disrupted.id: delay},
    )
