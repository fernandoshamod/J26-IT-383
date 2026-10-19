from scheduling_engine.baselines import naive_forward_shift, no_reschedule
from scheduling_engine.conflict_detection import ConflictType, verify_schedule
from scheduling_engine.models import Activity, Resource, ResourceRequirement, ResourceType, Schedule, ScheduledActivity

CREW = [Resource("crew-1", "Crew 1", ResourceType.STAFF, "crew")]


def test_no_reschedule_only_touches_the_disrupted_activity_and_conflicts():
    a = Activity("a", "e1", "A", 60, requirements=[ResourceRequirement("crew")])
    b = Activity("b", "e1", "B", 30, predecessors=["a"], requirements=[ResourceRequirement("crew")])
    schedule = Schedule(
        is_feasible=True,
        activities={
            "a": ScheduledActivity("a", 0, 60, ["crew-1"]),
            "b": ScheduledActivity("b", 60, 90, ["crew-1"]),
        },
    )

    revised = no_reschedule(schedule, "a", delay_minutes=40)

    assert revised.activities["a"].end_minutes == 100
    assert revised.activities["b"].start_minutes == 60  # untouched, now physically impossible

    conflicts = verify_schedule([a, b], [], revised.activities)
    assert any(c.type == ConflictType.PRECEDENCE_VIOLATION for c in conflicts)


def test_naive_forward_shift_moves_everything_from_the_disruption_onward():
    a = Activity("a", "e1", "A", 60, requirements=[ResourceRequirement("crew")])
    b = Activity("b", "e1", "B", 30, predecessors=["a"], requirements=[ResourceRequirement("crew")])
    c = Activity("c", "e1", "C", 20, predecessors=["b"], requirements=[ResourceRequirement("crew")])
    schedule = Schedule(
        is_feasible=True,
        activities={
            "a": ScheduledActivity("a", 0, 60, ["crew-1"]),
            "b": ScheduledActivity("b", 60, 90, ["crew-1"]),
            "c": ScheduledActivity("c", 90, 110, ["crew-1"]),
        },
    )

    revised = naive_forward_shift(schedule, "a", delay_minutes=40)

    assert revised.activities["a"].end_minutes == 100
    assert revised.activities["b"].start_minutes == 100
    assert revised.activities["c"].start_minutes == 130
    assert verify_schedule([a, b, c], CREW, revised.activities) == []


def test_naive_forward_shift_ignores_a_lock_and_that_shows_up_as_a_conflict():
    # This is the documented weakness, not a bug: Table 5's naive
    # baseline doesn't know about locks, so a locked activity downstream
    # of the disruption gets pushed anyway — which must surface as a
    # LOCKED_ACTIVITY_MOVED conflict when independently verified.
    a = Activity("a", "e1", "A", 60, requirements=[ResourceRequirement("crew")])
    locked = Activity(
        "locked", "e1", "Locked", 30, predecessors=["a"], locked_start_minutes=60,
        requirements=[ResourceRequirement("crew")],
    )
    schedule = Schedule(
        is_feasible=True,
        activities={
            "a": ScheduledActivity("a", 0, 60, ["crew-1"]),
            "locked": ScheduledActivity("locked", 60, 90, ["crew-1"]),
        },
    )

    revised = naive_forward_shift(schedule, "a", delay_minutes=40)

    assert revised.activities["locked"].start_minutes == 100
    conflicts = verify_schedule([a, locked], [], revised.activities)
    assert any(c.type == ConflictType.LOCKED_ACTIVITY_MOVED for c in conflicts)
