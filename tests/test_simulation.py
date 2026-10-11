"""
Each test isolates one kind of cascade Objective 4 asks the simulation to
predict: no disruption, precedence-caused delay, and resource-caused
delay between activities that have no precedence relationship at all.
"""

from scheduling_engine.models import (
    Activity,
    Resource,
    ResourceRequirement,
    ResourceType,
    Schedule,
    ScheduledActivity,
)
from scheduling_engine.simulation import simulate_cascade
from scheduling_engine.twin import CheckIn, CheckInType, OperationalDigitalTwin


def _crew(id_: str, capacity: int = 1) -> Resource:
    return Resource(id=id_, name=id_, type=ResourceType.STAFF, role="crew", capacity=capacity)


def test_no_disruption_means_no_predicted_cascade():
    a = Activity("a", "e1", "A", 60, requirements=[ResourceRequirement("crew")])
    b = Activity("b", "e1", "B", 30, predecessors=["a"], requirements=[ResourceRequirement("crew")])
    schedule = Schedule(
        is_feasible=True,
        activities={
            "a": ScheduledActivity("a", 0, 60, ["crew-1"]),
            "b": ScheduledActivity("b", 60, 90, ["crew-1"]),
        },
    )
    twin = OperationalDigitalTwin(schedule)  # nothing checked in: both NOT_STARTED

    result = simulate_cascade([a, b], [_crew("crew-1")], schedule, twin, now_minutes=0)

    assert result.delay_minutes == {}
    assert result.resource_wait_minutes == {}
    assert result.predicted_activities["a"].start_minutes == 0
    assert result.predicted_activities["b"].start_minutes == 60


def test_precedence_cascade_from_a_known_overrun():
    # a is already running (checked in on time) but is predicted to run 40
    # minutes over. b depends on a directly, so b must shift by the same
    # 40 minutes.
    a = Activity("a", "e1", "A", 60, requirements=[ResourceRequirement("crew")])
    b = Activity("b", "e1", "B", 30, predecessors=["a"], requirements=[ResourceRequirement("crew")])
    schedule = Schedule(
        is_feasible=True,
        activities={
            "a": ScheduledActivity("a", 0, 60, ["crew-1"]),
            "b": ScheduledActivity("b", 60, 90, ["crew-1"]),
        },
    )
    twin = OperationalDigitalTwin(schedule)
    twin.record_check_in(CheckIn("a", CheckInType.STARTED, reported_at_minutes=0))

    result = simulate_cascade(
        [a, b], [_crew("crew-1")], schedule, twin, now_minutes=10,
        predicted_extra_duration_minutes={"a": 40},
    )

    assert result.delay_minutes["b"] == 40
    assert result.predicted_activities["b"].start_minutes == 100  # 60 + 40
    # b's delay here is entirely precedence-caused, not resource-caused —
    # it was never waiting on the resource once ready, since a releases it
    # exactly as b becomes ready for it.
    assert result.resource_wait_minutes.get("b", 0) == 0


def test_resource_contention_cascade_between_unrelated_activities():
    # b and c have NO precedence relationship to each other at all — the
    # only thing connecting them is that they share the one crew. In the
    # original plan b runs first, then c. If b overruns, c must wait for
    # the crew to free up, even though nothing about c's own preconditions
    # changed. This is the "across ... shared resources" half of
    # Objective 4 that a pure precedence-forward-shift would miss.
    b = Activity("b", "e1", "B", 60, requirements=[ResourceRequirement("crew")])
    c = Activity("c", "e1", "C", 30, requirements=[ResourceRequirement("crew")])
    schedule = Schedule(
        is_feasible=True,
        activities={
            "b": ScheduledActivity("b", 0, 60, ["crew-1"]),
            "c": ScheduledActivity("c", 60, 90, ["crew-1"]),
        },
    )
    twin = OperationalDigitalTwin(schedule)
    twin.record_check_in(CheckIn("b", CheckInType.STARTED, reported_at_minutes=0))

    result = simulate_cascade(
        [b, c], [_crew("crew-1")], schedule, twin, now_minutes=0,
        predicted_extra_duration_minutes={"b": 25},
    )

    # c was always going to wait ~60 minutes for the crew under the
    # original plan too; what's new is the extra 25 minutes caused by b
    # overrunning — that's the number a planner actually needs to see.
    assert result.resource_wait_minutes["c"] == 25
    assert result.delay_minutes["c"] == 25
    assert result.predicted_activities["c"].start_minutes == 85  # 60 + 25


def test_fixed_start_absorbs_a_disruption_when_there_is_enough_slack():
    # b is fixed/locked well after a's natural finish, i.e. the plan has
    # slack baked in (like a ceremony fixed for the afternoon after a
    # morning setup). A moderate overrun on a should simply disappear
    # into that slack rather than visibly delaying b.
    a = Activity("a", "e1", "A", 60, requirements=[ResourceRequirement("crew")])
    b = Activity("b", "e1", "B", 30, predecessors=["a"], fixed_start_minutes=200,
                 requirements=[ResourceRequirement("crew")])
    schedule = Schedule(
        is_feasible=True,
        activities={
            "a": ScheduledActivity("a", 0, 60, ["crew-1"]),
            "b": ScheduledActivity("b", 200, 230, ["crew-1"]),
        },
    )
    twin = OperationalDigitalTwin(schedule)
    twin.record_check_in(CheckIn("a", CheckInType.STARTED, reported_at_minutes=0))

    result = simulate_cascade(
        [a, b], [_crew("crew-1")], schedule, twin, now_minutes=10,
        predicted_extra_duration_minutes={"a": 50},  # a ends at 110, still well under 200
    )

    assert "b" not in result.delay_minutes
    assert result.predicted_activities["b"].start_minutes == 200


def test_fixed_start_no_longer_absorbs_a_large_enough_disruption():
    # Same setup, but now a's overrun is big enough to eat through all the
    # slack before b's fixed time — b's pin can no longer hold, and that
    # must show up as a predicted delay, not be silently masked.
    a = Activity("a", "e1", "A", 60, requirements=[ResourceRequirement("crew")])
    b = Activity("b", "e1", "B", 30, predecessors=["a"], fixed_start_minutes=200,
                 requirements=[ResourceRequirement("crew")])
    schedule = Schedule(
        is_feasible=True,
        activities={
            "a": ScheduledActivity("a", 0, 60, ["crew-1"]),
            "b": ScheduledActivity("b", 200, 230, ["crew-1"]),
        },
    )
    twin = OperationalDigitalTwin(schedule)
    twin.record_check_in(CheckIn("a", CheckInType.STARTED, reported_at_minutes=0))

    result = simulate_cascade(
        [a, b], [_crew("crew-1")], schedule, twin, now_minutes=10,
        predicted_extra_duration_minutes={"a": 200},  # a ends at 260, past b's pin of 200
    )

    assert result.delay_minutes["b"] == 60  # starts at 260 instead of 200, same duration
    assert result.predicted_activities["b"].start_minutes == 260


def test_resource_turnaround_matches_the_plan_with_no_disruption():
    # Regression test: the simulator must respect min_turnaround_minutes
    # exactly like the solver does, or else "nothing was disrupted" would
    # still show predicted times drifting away from the plan — which
    # happened during development because the first version of this
    # simulator released a resource immediately at an activity's end,
    # ignoring turnaround entirely. a and b have no precedence relation
    # to each other (same as the original turnaround-respecting plan
    # solver.py produces for two unrelated activities sharing one
    # turnaround-constrained resource), so the hand-built schedule below
    # fixes which one the plan put first rather than leaving it to
    # chance.
    a = Activity("a", "e1", "A", 30, requirements=[ResourceRequirement("av_crew")])
    b = Activity("b", "e1", "B", 30, requirements=[ResourceRequirement("av_crew")])
    resources = [Resource("av-1", "av-1", ResourceType.STAFF, "av_crew", min_turnaround_minutes=10)]
    schedule = Schedule(
        is_feasible=True,
        activities={
            "a": ScheduledActivity("a", 0, 30, ["av-1"]),
            "b": ScheduledActivity("b", 40, 70, ["av-1"]),  # 30 + 10 turnaround gap
        },
    )
    twin = OperationalDigitalTwin(schedule)  # nothing checked in — nothing disrupted

    result = simulate_cascade([a, b], resources, schedule, twin, now_minutes=0)

    assert result.delay_minutes == {}
    for activity_id, planned in schedule.activities.items():
        predicted = result.predicted_activities[activity_id]
        assert predicted.start_minutes == planned.start_minutes
        assert predicted.end_minutes == planned.end_minutes
