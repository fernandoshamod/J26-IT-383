"""
Each test is traceable to a specific claim in the proposal:
  - the missing-confirmation tests are the Section 1.4 "sensor-free
    detection" novelty claim itself;
  - the forty-minutes-late test is Section 1.1's own worked example
    ("a catering vendor arrives forty minutes late").
"""

from scheduling_engine.models import Schedule, ScheduledActivity
from scheduling_engine.twin import (
    CheckIn,
    CheckInType,
    DivergenceType,
    OperationalDigitalTwin,
)


def _schedule(**activities: tuple[int, int]) -> Schedule:
    return Schedule(
        is_feasible=True,
        activities={
            activity_id: ScheduledActivity(activity_id, start, end)
            for activity_id, (start, end) in activities.items()
        },
    )


def test_on_time_check_ins_produce_no_divergence():
    schedule = _schedule(catering=(100, 160))
    twin = OperationalDigitalTwin(schedule, default_tolerance_minutes=10)

    twin.record_check_in(CheckIn("catering", CheckInType.STARTED, reported_at_minutes=100))
    twin.record_check_in(CheckIn("catering", CheckInType.COMPLETED, reported_at_minutes=160))

    assert twin.detect_divergence(now_minutes=160) == []


def test_missing_start_confirmation_is_the_detection_signal():
    # No check-in has been received at all. The plan said catering should
    # have started by minute 100; by minute 115, with a 10-minute
    # tolerance, that silence is itself a disruption signal — no sensor
    # involved, exactly Section 1.4's claim.
    schedule = _schedule(catering=(100, 160))
    twin = OperationalDigitalTwin(schedule, default_tolerance_minutes=10)

    divergences = twin.detect_divergence(now_minutes=115)

    assert len(divergences) == 1
    assert divergences[0].type is DivergenceType.MISSING_START_CONFIRMATION
    assert divergences[0].delta_minutes == 15


def test_within_tolerance_is_not_a_disruption():
    schedule = _schedule(catering=(100, 160))
    twin = OperationalDigitalTwin(schedule, default_tolerance_minutes=10)

    # Only 5 minutes overdue, inside the 10-minute tolerance.
    assert twin.detect_divergence(now_minutes=105) == []


def test_explicit_forty_minute_late_arrival_is_a_deviation_not_missing():
    # The proposal's own example (Section 1.1): "a catering vendor arrives
    # forty minutes late". This is a *known* delay, reported via check-in,
    # which must be distinguished from an unexplained silence.
    schedule = _schedule(catering=(100, 160))
    twin = OperationalDigitalTwin(schedule, default_tolerance_minutes=10)

    twin.record_check_in(CheckIn("catering", CheckInType.STARTED, reported_at_minutes=140))
    divergences = twin.detect_divergence(now_minutes=140)

    assert len(divergences) == 1
    assert divergences[0].type is DivergenceType.START_TIME_DEVIATION
    assert divergences[0].delta_minutes == 40


def test_started_on_time_but_completion_confirmation_goes_missing():
    schedule = _schedule(catering=(100, 160))
    twin = OperationalDigitalTwin(schedule, default_tolerance_minutes=10)

    twin.record_check_in(CheckIn("catering", CheckInType.STARTED, reported_at_minutes=100))
    divergences = twin.detect_divergence(now_minutes=180)  # 20 min past planned end

    assert len(divergences) == 1
    assert divergences[0].type is DivergenceType.MISSING_COMPLETION_CONFIRMATION
    assert divergences[0].delta_minutes == 20


def test_per_activity_tolerance_override_is_stricter_for_fixed_times():
    # A ceremony fixed to an exact client-mandated time has no slack, so
    # it can be given a tighter tolerance than the 10-minute default
    # other activities use.
    schedule = _schedule(ceremony=(960, 990))
    twin = OperationalDigitalTwin(
        schedule,
        default_tolerance_minutes=10,
        tolerance_minutes_by_activity={"ceremony": 2},
    )

    # 5 minutes overdue: within the 10-minute default, but NOT within this
    # activity's overridden 2-minute tolerance.
    divergences = twin.detect_divergence(now_minutes=965)

    assert len(divergences) == 1
    assert divergences[0].activity_id == "ceremony"


def test_unknown_activity_check_in_is_rejected():
    schedule = _schedule(catering=(100, 160))
    twin = OperationalDigitalTwin(schedule)

    try:
        twin.record_check_in(CheckIn("nonexistent", CheckInType.STARTED, reported_at_minutes=100))
        assert False, "expected KeyError"
    except KeyError:
        pass
