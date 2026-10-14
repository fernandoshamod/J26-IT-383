"""
Multi-event days for the scalability test (proposal NFR-04: "at least five
concurrent events, each with up to 30 activities and 40 resources, without
exceeding the latency requirement" of NFR-01, 5 seconds).

Each event gets 30 resources of its own (setup crews, catering crews,
ushers, ...) plus access to a SHARED pool of 10 (AV crews, florists,
photographers, bands) that every event competes for, so each event has 40
resources available and cross-event contention is real, not incidental.
Events overlap in time on one shared day.

Like scenario_generation.py, the sizes and ranges below are declared
placeholders for a stress test, not elicited data.
"""

from __future__ import annotations

import random

from scheduling_engine.models import Activity, Event, Resource, ResourceRequirement, ResourceType

# Per-event dedicated roles: 30 units in total.
DEDICATED_ROLES = {"setup_crew": 6, "catering_crew": 6, "usher": 5, "security": 4,
                   "cleaner": 4, "decorator": 3, "coordinator": 2}
# Shared across every event: 10 units in total.
SHARED_ROLES = {"av_crew": 3, "florist": 2, "photographer": 3, "band": 2}
SHARED_TURNAROUND = {"av_crew": 10, "photographer": 5}

DURATION_RANGE = (15, 90)
EVENT_OFFSET_RANGE = (0, 180)       # events start within three hours of each other
SHARED_ROLE_PROBABILITY = 0.25      # share of activities that need a shared resource
MAX_PREDECESSOR_DISTANCE = 5        # a predecessor is one of the previous 5 activities
LOCKS_PER_EVENT = 1                 # planner-locked times, set after the first solve


def generate_day(seed: int, n_events: int = 5, activities_per_event: int = 30) -> tuple[list[Event], list[Resource]]:
    rng = random.Random(seed)
    resources: list[Resource] = []
    for role, units in SHARED_ROLES.items():
        for u in range(1, units + 1):
            resources.append(Resource(f"{role}-{u}", f"{role} {u}", ResourceType.VENDOR, role,
                                      min_turnaround_minutes=SHARED_TURNAROUND.get(role, 0)))

    events = []
    for e in range(n_events):
        eid = f"ev{e + 1}"
        for role, units in DEDICATED_ROLES.items():
            for u in range(1, units + 1):
                resources.append(Resource(f"{eid}-{role}-{u}", f"{eid} {role} {u}", ResourceType.STAFF,
                                          f"{eid}:{role}"))
        offset = 8 * 60 + rng.randint(*EVENT_OFFSET_RANGE)
        activities = []
        for i in range(activities_per_event):
            aid = f"{eid}-a{i:02d}"
            preds = []
            if i > 0:
                window = list(range(max(0, i - MAX_PREDECESSOR_DISTANCE), i))
                preds = [f"{eid}-a{j:02d}" for j in rng.sample(window, k=min(len(window), rng.choice([1, 1, 2])))]
            reqs = [ResourceRequirement(f"{eid}:{rng.choice(list(DEDICATED_ROLES))}", count=rng.choice([1, 1, 2]))]
            if rng.random() < SHARED_ROLE_PROBABILITY:
                reqs.append(ResourceRequirement(rng.choice(list(SHARED_ROLES))))
            activities.append(Activity(aid, eid, f"{eid} activity {i:02d}", rng.randint(*DURATION_RANGE),
                                       requirements=reqs, predecessors=preds,
                                       earliest_start_minutes=offset if i == 0 else 0))
        events.append(Event(eid, f"Event {e + 1}", activities))
    return events, resources


def lock_some(events: list[Event], schedule, seed: int) -> list[str]:
    """Lock LOCKS_PER_EVENT later-half activities per event at their planned
    start, as a planner confirming times after the first plan."""
    rng = random.Random(seed + 1)
    locked = []
    for event in events:
        half = event.activities[len(event.activities) // 2:]
        for a in rng.sample(half, k=min(LOCKS_PER_EVENT, len(half))):
            a.locked_start_minutes = schedule.activities[a.id].start_minutes
            locked.append(a.id)
    return locked
