from scheduling_engine.conflict_detection import verify_schedule
from scheduling_engine.scenario_generation import (
    ACTIVITY_COUNT_RANGE,
    generate_scenario,
    inject_disruption,
)
from scheduling_engine.twin import DivergenceType


def test_generated_scenarios_are_feasible_with_declared_activity_count():
    for seed in range(10):
        event, resources, schedule = generate_scenario(seed)
        assert schedule.is_feasible
        assert ACTIVITY_COUNT_RANGE[0] <= len(event.activities) <= ACTIVITY_COUNT_RANGE[1]
        assert verify_schedule(event.activities, resources, schedule.activities) == []


def test_buffered_scenarios_are_also_feasible_and_conflict_free():
    for seed in range(10):
        event, resources, schedule = generate_scenario(seed, include_buffer=True)
        assert schedule.is_feasible
        assert verify_schedule(event.activities, resources, schedule.activities) == []


def test_buffer_actually_adds_a_gap_versus_the_unbuffered_schedule():
    # Not a guarantee for every single activity (resource contention can
    # still force a tighter fit here and there), but on average a
    # buffered schedule should run later than its unbuffered twin — if it
    # didn't, the buffer parameter would be a no-op, which is exactly the
    # kind of silent-failure this test exists to catch.
    import statistics

    unbuffered_ends = []
    buffered_ends = []
    for seed in range(15):
        _, _, plain_schedule = generate_scenario(seed, include_buffer=False)
        _, _, buffered_schedule = generate_scenario(seed, include_buffer=True)
        if not (plain_schedule.is_feasible and buffered_schedule.is_feasible):
            continue
        unbuffered_ends.append(max(s.end_minutes for s in plain_schedule.activities.values()))
        buffered_ends.append(max(s.end_minutes for s in buffered_schedule.activities.values()))

    assert statistics.mean(buffered_ends) > statistics.mean(unbuffered_ends)


def test_generous_resources_scenarios_are_also_feasible_and_conflict_free():
    for seed in range(10):
        event, resources, schedule = generate_scenario(seed, generous_resources=True)
        assert schedule.is_feasible
        assert verify_schedule(event.activities, resources, schedule.activities) == []


def test_generous_resources_actually_doubles_singleton_role_capacity():
    _, resources, _ = generate_scenario(0, generous_resources=True)
    capacity_by_role: dict[str, int] = {}
    for r in resources:
        capacity_by_role[r.role] = capacity_by_role.get(r.role, 0) + r.capacity
    # av_crew, photographer and officiant are capacity-1 singletons in the
    # normal generator — if this parameter were a no-op, they'd still be.
    assert capacity_by_role["av_crew"] == 2
    assert capacity_by_role["photographer"] == 2
    assert capacity_by_role["officiant"] == 2


def test_disruption_injection_produces_the_expected_divergence():
    event, resources, schedule = generate_scenario(seed=1)
    scenario = inject_disruption(event, resources, schedule, seed=1)

    divergences = scenario.twin.detect_divergence(scenario.now_minutes)
    matching = [
        d for d in divergences
        if d.activity_id == scenario.disrupted_activity_id
        and d.type is DivergenceType.MISSING_COMPLETION_CONFIRMATION
    ]
    assert len(matching) == 1
    assert matching[0].delta_minutes == scenario.injected_delay_minutes


def test_consumable_buffer_is_slack_not_a_rule():
    """The buffer shapes the plan, but the re-optimiser may consume it; and
    nothing may start before its planned time."""
    event, _, schedule = generate_scenario(3, include_buffer=True, consumable_buffer=True)
    assert schedule.is_feasible
    assert all(a.min_lag_minutes == {} for a in event.activities)
    for a in event.activities:
        assert a.earliest_start_minutes >= schedule.activities[a.id].start_minutes
    # The plan itself still contains the padding: same plan as the
    # enforced-buffer version of the same seed.
    _, _, padded = generate_scenario(3, include_buffer=True)
    assert {k: v.start_minutes for k, v in schedule.activities.items()} == \
           {k: v.start_minutes for k, v in padded.activities.items()}
