from scheduling_engine.models import (
    Activity,
    Resource,
    ResourceRequirement,
    ResourceType,
    Schedule,
    ScheduledActivity,
)
from scheduling_engine.reoptimization import reoptimize
from scheduling_engine.twin import CheckIn, CheckInType, OperationalDigitalTwin


def _crew(id_: str) -> Resource:
    return Resource(id=id_, name=id_, type=ResourceType.STAFF, role="crew", capacity=1)


def test_reoptimize_absorbs_a_simple_precedence_cascade_and_reports_its_cost():
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

    result = reoptimize(
        [a, b], [_crew("crew-1")], schedule, twin, now_minutes=10,
        predicted_extra_duration_minutes={"a": 40},
    )

    assert result.is_feasible
    assert result.schedule.activities["b"].start_minutes == 100  # 60 + 40
    assert result.cost_signal.total_delay_minutes == 40
    assert result.cost_signal.delayed_activity_ids == ("b",)


def test_reoptimize_protects_a_locked_activity_by_reassigning_its_resource():
    # P overruns badly enough to eat into L's locked start time. The
    # ORIGINAL plan happened to put both on the same crew, but a second,
    # identical crew exists and is free the whole time. A re-optimiser
    # that only ever shifts TIME (never resource assignment) would have
    # to either delay L (violating its lock) or fail. This checks that
    # ours instead moves L onto the free crew and keeps its locked time
    # exactly as planned — FR-07 locks an activity's time, not which
    # resource serves it.
    p = Activity("p", "e1", "P", 60, requirements=[ResourceRequirement("crew")])
    l = Activity(
        "l", "e1", "L", 30, locked_start_minutes=70, requirements=[ResourceRequirement("crew")]
    )
    resources = [_crew("crew-1"), _crew("crew-2")]
    schedule = Schedule(
        is_feasible=True,
        activities={
            "p": ScheduledActivity("p", 0, 60, ["crew-1"]),
            "l": ScheduledActivity("l", 70, 100, ["crew-1"]),
        },
    )
    twin = OperationalDigitalTwin(schedule)
    twin.record_check_in(CheckIn("p", CheckInType.STARTED, reported_at_minutes=0))

    result = reoptimize(
        [p, l], resources, schedule, twin, now_minutes=10,
        predicted_extra_duration_minutes={"p": 40},  # p now ends at 100, well past l's lock of 70
    )

    assert result.is_feasible
    assert result.schedule.activities["l"].start_minutes == 70  # lock honoured
    assert result.schedule.activities["l"].assigned_resource_ids == ["crew-2"]  # reassigned, not delayed
    assert "l" not in result.cost_signal.delayed_activity_ids


def test_reoptimize_reports_which_locked_activity_is_unsatisfiable():
    # Same disruption, but now only one crew exists at all — there is no
    # resource to reassign L onto, so honouring its lock is genuinely
    # impossible, and that must be reported by name, not just as a bare
    # "infeasible".
    p = Activity("p", "e1", "P", 60, requirements=[ResourceRequirement("crew")])
    l = Activity(
        "l", "e1", "L", 30, locked_start_minutes=70, requirements=[ResourceRequirement("crew")]
    )
    schedule = Schedule(
        is_feasible=True,
        activities={
            "p": ScheduledActivity("p", 0, 60, ["crew-1"]),
            "l": ScheduledActivity("l", 70, 100, ["crew-1"]),
        },
    )
    twin = OperationalDigitalTwin(schedule)
    twin.record_check_in(CheckIn("p", CheckInType.STARTED, reported_at_minutes=0))

    result = reoptimize(
        [p, l], [_crew("crew-1")], schedule, twin, now_minutes=10,
        predicted_extra_duration_minutes={"p": 40},
    )

    assert not result.is_feasible
    assert result.conflicting_pinned_activity_ids == ["l"]
