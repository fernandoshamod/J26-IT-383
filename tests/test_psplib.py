from scheduling_engine.conflict_detection import verify_schedule
from scheduling_engine.psplib import parse_sm, to_scheduling_model
from scheduling_engine.solver import solve_planning_phase

INSTANCE_PATH = "data/psplib/j30/j301_1.sm"


def test_parse_sm_matches_the_file_by_hand():
    # Values transcribed directly from data/psplib/j30/j301_1.sm, so this
    # test fails loudly if the parser ever misreads the column layout.
    instance = parse_sm(INSTANCE_PATH)

    assert len(instance.jobs) == 32  # 30 real jobs + dummy source + dummy sink
    assert instance.resource_capacities == [12, 13, 4, 12]
    assert instance.critical_path_lower_bound == 38

    job1 = next(j for j in instance.jobs if j.id == 1)
    assert job1.duration == 0
    assert job1.successors == [2, 3, 4]

    job2 = next(j for j in instance.jobs if j.id == 2)
    assert job2.duration == 8
    assert job2.resource_requests == [4, 0, 0, 0]
    assert job2.successors == [6, 11, 15]


def test_converted_instance_solves_feasibly_with_no_conflicts():
    instance = parse_sm(INSTANCE_PATH)
    event, resources = to_scheduling_model(instance)

    schedule = solve_planning_phase([event], resources, time_limit_seconds=10.0)

    assert schedule.is_feasible
    # Resource contention can only push the makespan out, never below the
    # critical path computed with resources ignored — if this ever fails
    # it means the constraint model is wrong, not that the solver is slow.
    assert schedule.makespan_minutes >= instance.critical_path_lower_bound

    conflicts = verify_schedule(event.activities, resources, schedule.activities)
    assert conflicts == []
