"""
Planning phase -> execution phase handoff, demonstrated concretely.

Solves the same wedding from run_example.py, then plays it forward as a
live event: most activities check in on time, but — echoing the
proposal's own example in Section 1.1 — the catering crew's load-in runs
forty minutes late, and is reported as such; separately, the sound and
lighting check's completion is never confirmed at all, standing in for a
staff member who simply forgot to check in. The twin is expected to tell
these two situations apart.

Run from the repository root:
    python -m examples.run_twin_example
"""

from examples.run_example import build_resources, build_wedding
from scheduling_engine import (
    CheckIn,
    CheckInType,
    OperationalDigitalTwin,
    solve_planning_phase,
)


def main() -> None:
    wedding = build_wedding()
    resources = build_resources()
    schedule = solve_planning_phase([wedding], resources)
    assert schedule.is_feasible

    twin = OperationalDigitalTwin(schedule, default_tolerance_minutes=10)

    setup = schedule.activities["venue_setup"]
    decor = schedule.activities["decor"]
    sound_check = schedule.activities["sound_check"]
    catering = schedule.activities["catering_load_in"]

    print("Planned vs. what actually gets reported:\n")

    # venue_setup and decor: check in exactly on plan.
    twin.record_check_in(CheckIn("venue_setup", CheckInType.STARTED, setup.start_minutes))
    twin.record_check_in(CheckIn("venue_setup", CheckInType.COMPLETED, setup.end_minutes))
    twin.record_check_in(CheckIn("decor", CheckInType.STARTED, decor.start_minutes))
    twin.record_check_in(CheckIn("decor", CheckInType.COMPLETED, decor.end_minutes))

    # sound_check: starts on time, but nobody ever confirms it finished.
    twin.record_check_in(CheckIn("sound_check", CheckInType.STARTED, sound_check.start_minutes))

    # catering_load_in: the vendor checks in forty minutes late.
    actual_catering_start = catering.start_minutes + 40
    twin.record_check_in(CheckIn("catering_load_in", CheckInType.STARTED, actual_catering_start))

    # "Now" is 15 minutes after sound_check was due to finish, and right
    # as the late catering crew is getting started.
    now_minutes = sound_check.end_minutes + 15

    divergences = twin.detect_divergence(now_minutes)

    print(f"Checked at t={now_minutes} minutes:\n")
    if not divergences:
        print("  No divergence detected.")
    for d in divergences:
        print(
            f"  [{d.type.value}] {d.activity_id}: planned {d.planned_minutes}, "
            f"reference {d.reference_minutes}, delta {d.delta_minutes:+d} min"
        )


if __name__ == "__main__":
    main()
