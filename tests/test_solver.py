"""
Each test here isolates exactly one constraint from Section 4.2.1 of the
proposal, so that a failure points straight at which part of the model
broke — and so each test doubles as a runnable example of what that
constraint means in practice.
"""

from scheduling_engine.conflict_detection import ConflictType, verify_schedule
from scheduling_engine.models import (
    Activity,
    Event,
    Resource,
    ResourceRequirement,
    ResourceType,
)
from scheduling_engine.solver import SchedulingDataError, solve_planning_phase


def _staff(id_: str, role: str, **kwargs) -> Resource:
    return Resource(id=id_, name=id_, type=ResourceType.STAFF, role=role, **kwargs)


def test_precedence_is_respected():
    setup = Activity(
        id="setup",
        event_id="e1",
        name="Venue setup",
        duration_minutes=60,
        requirements=[ResourceRequirement(role="crew")],
    )
    ceremony = Activity(
        id="ceremony",
        event_id="e1",
        name="Ceremony",
        duration_minutes=30,
        predecessors=["setup"],
        requirements=[ResourceRequirement(role="crew")],
    )
    event = Event(id="e1", name="Wedding", activities=[setup, ceremony])
    resources = [_staff("crew-1", "crew"), _staff("crew-2", "crew")]

    schedule = solve_planning_phase([event], resources)

    assert schedule.is_feasible
    assert schedule.activities["ceremony"].start_minutes >= schedule.activities["setup"].end_minutes
    assert verify_schedule([setup, ceremony], resources, schedule.activities) == []


def test_single_resource_is_not_double_booked_across_concurrent_events():
    # Two unrelated events both want the one available sound technician at
    # the same time. Nothing links them except that shared resource — this
    # is exactly the "double-booking across concurrent events" case FR-06
    # calls out.
    a1 = Activity(
        id="a1",
        event_id="e1",
        name="Soundcheck",
        duration_minutes=60,
        requirements=[ResourceRequirement(role="sound_tech")],
    )
    a2 = Activity(
        id="a2",
        event_id="e2",
        name="Soundcheck",
        duration_minutes=60,
        requirements=[ResourceRequirement(role="sound_tech")],
    )
    events = [
        Event(id="e1", name="Event 1", activities=[a1]),
        Event(id="e2", name="Event 2", activities=[a2]),
    ]
    resources = [_staff("tech-1", "sound_tech")]  # only one — forces a conflict if not handled

    schedule = solve_planning_phase(events, resources)

    assert schedule.is_feasible
    s1, s2 = schedule.activities["a1"], schedule.activities["a2"]
    assert s1.end_minutes <= s2.start_minutes or s2.end_minutes <= s1.start_minutes
    assert verify_schedule([a1, a2], resources, schedule.activities) == []


def test_minimum_turnaround_is_enforced():
    a1 = Activity(
        id="a1", event_id="e1", name="A", duration_minutes=30,
        requirements=[ResourceRequirement(role="av_crew")],
    )
    a2 = Activity(
        id="a2", event_id="e1", name="B", duration_minutes=30,
        requirements=[ResourceRequirement(role="av_crew")],
    )
    event = Event(id="e1", name="Event", activities=[a1, a2])
    # Only one crew exists, and it needs 20 minutes to reset between jobs.
    resources = [_staff("crew-1", "av_crew", min_turnaround_minutes=20)]

    schedule = solve_planning_phase([event], resources)

    s1, s2 = schedule.activities["a1"], schedule.activities["a2"]
    first, second = (s1, s2) if s1.start_minutes <= s2.start_minutes else (s2, s1)
    assert second.start_minutes >= first.end_minutes + 20
    assert verify_schedule([a1, a2], resources, schedule.activities) == []


def test_fixed_time_is_respected():
    ceremony = Activity(
        id="ceremony",
        event_id="e1",
        name="Ceremony",
        duration_minutes=30,
        fixed_start_minutes=960,  # 4:00 PM, as minutes since midnight
        requirements=[ResourceRequirement(role="officiant")],
    )
    event = Event(id="e1", name="Wedding", activities=[ceremony])
    resources = [_staff("officiant-1", "officiant")]

    schedule = solve_planning_phase([event], resources)

    assert schedule.is_feasible
    assert schedule.activities["ceremony"].start_minutes == 960


def test_conflicting_locked_activities_are_proven_infeasible_and_named():
    # Both activities are planner-locked to the same time and both need
    # the one resource that exists. No schedule can satisfy both pins.
    a1 = Activity(
        id="a1", event_id="e1", name="A", duration_minutes=60,
        locked_start_minutes=0,
        requirements=[ResourceRequirement(role="photographer")],
    )
    a2 = Activity(
        id="a2", event_id="e1", name="B", duration_minutes=60,
        locked_start_minutes=0,
        requirements=[ResourceRequirement(role="photographer")],
    )
    event = Event(id="e1", name="Event", activities=[a1, a2])
    resources = [_staff("photographer-1", "photographer")]

    schedule = solve_planning_phase([event], resources)

    assert not schedule.is_feasible
    assert schedule.status_name == "INFEASIBLE"
    assert set(schedule.conflicting_pinned_activity_ids) == {"a1", "a2"}


def test_missing_resource_role_is_a_data_error_not_a_silent_infeasibility():
    a1 = Activity(
        id="a1", event_id="e1", name="A", duration_minutes=30,
        requirements=[ResourceRequirement(role="pyrotechnics")],
    )
    event = Event(id="e1", name="Event", activities=[a1])

    try:
        solve_planning_phase([event], resources=[])
        assert False, "expected SchedulingDataError"
    except SchedulingDataError:
        pass


def test_independent_verification_catches_a_manually_broken_schedule():
    # This does not call the solver at all. It feeds verify_schedule a
    # hand-built, deliberately-wrong schedule, to show the checker catches
    # a violation on its own rather than trusting whatever produced the
    # schedule (Section 3.6: verification must be independent of the
    # solver so a defect in the constraint model is not concealed).
    from scheduling_engine.models import ScheduledActivity

    a1 = Activity(
        id="a1", event_id="e1", name="A", duration_minutes=60,
        requirements=[ResourceRequirement(role="crew")],
    )
    a2 = Activity(
        id="a2", event_id="e1", name="B", duration_minutes=60,
        requirements=[ResourceRequirement(role="crew")],
    )
    resources = [_staff("crew-1", "crew")]
    broken_schedule = {
        "a1": ScheduledActivity("a1", 0, 60, ["crew-1"]),
        "a2": ScheduledActivity("a2", 30, 90, ["crew-1"]),  # overlaps a1 on the same crew
    }

    conflicts = verify_schedule([a1, a2], resources, broken_schedule)

    assert len(conflicts) == 1
    assert conflicts[0].type == ConflictType.RESOURCE_OVERCOMMIT



def test_verifier_catches_wrong_resource_assignment():
    """FR-05: the verifier checks the RIGHT resources were allocated, not
    only that none is double-booked (regression: a hand-edited schedule
    giving one activity the wrong role used to pass)."""
    from scheduling_engine.models import ScheduledActivity
    from scheduling_engine.conflict_detection import ConflictType
    resources = [Resource("p1", "Photographer", ResourceType.VENDOR, "photographer"),
                 Resource("c1", "Crew A", ResourceType.STAFF, "crew"),
                 Resource("c2", "Crew B", ResourceType.STAFF, "crew")]
    acts = [Activity("setup", "e", "Setup", 30, requirements=[ResourceRequirement("crew", count=2)])]
    ok = {"setup": ScheduledActivity("setup", 0, 30, ["c1", "c2"])}
    assert verify_schedule(acts, resources, ok) == []
    wrong = {"setup": ScheduledActivity("setup", 0, 30, ["c1", "p1"])}   # one crew short, photographer not needed
    kinds = [c.type for c in verify_schedule(acts, resources, wrong)]
    assert kinds.count(ConflictType.WRONG_ASSIGNMENT) == 2
    unknown = {"setup": ScheduledActivity("setup", 0, 30, ["c1", "c2", "zz"])}
    assert any("unknown" in c.message for c in verify_schedule(acts, resources, unknown))
