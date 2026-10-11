"""
The full chain built so far, in one run: solve the plan, detect
divergence from check-ins (twin), then predict the downstream cascade of
that divergence (simulation) — Sections 4.2.1 and 4.2.2 end to end, short
of the one piece not yet built: re-optimisation (Objective 5) actually
deciding what to do about the cascade this prints.

Run from the repository root:
    python -m examples.run_simulation_example
"""

from examples.run_example import build_resources, build_wedding
from scheduling_engine import (
    CheckIn,
    CheckInType,
    DivergenceType,
    OperationalDigitalTwin,
    simulate_cascade,
    solve_planning_phase,
)


def format_minutes(total_minutes: int) -> str:
    hours, minutes = divmod(total_minutes, 60)
    return f"{hours:02d}:{minutes:02d}"


def build_disrupted_wedding():
    """Solve the wedding, then play it forward to the point where photos'
    completion has gone unconfirmed for 20 minutes — shared setup for
    both this module's demo and run_reoptimization_example.py, so the two
    tell the same consistent story rather than drifting apart.

    Returns (wedding, resources, schedule, twin, now_minutes, divergences,
    predicted_extra_duration).
    """
    wedding = build_wedding()
    resources = build_resources()
    schedule = solve_planning_phase([wedding], resources)
    assert schedule.is_feasible

    twin = OperationalDigitalTwin(schedule, default_tolerance_minutes=10)

    def on_time(*activity_ids: str) -> None:
        for activity_id in activity_ids:
            a = schedule.activities[activity_id]
            twin.record_check_in(CheckIn(activity_id, CheckInType.STARTED, a.start_minutes))
            twin.record_check_in(CheckIn(activity_id, CheckInType.COMPLETED, a.end_minutes))

    # Everything up to and including the ceremony proceeds exactly as
    # planned — except catering, which checks in a known 40 minutes late.
    # It happens before the ceremony, where hours of fixed-time slack
    # absorb it harmlessly (see run_twin_example.py for that case on its
    # own). This run is about what happens when a disruption hits AFTER
    # the fixed point, where there's no slack left to absorb into.
    on_time("venue_setup", "decor", "sound_check", "guest_arrival", "ceremony")
    catering = schedule.activities["catering_load_in"]
    catering_duration = catering.end_minutes - catering.start_minutes
    twin.record_check_in(CheckIn("catering_load_in", CheckInType.STARTED, catering.start_minutes + 40))
    twin.record_check_in(
        CheckIn("catering_load_in", CheckInType.COMPLETED, catering.start_minutes + 40 + catering_duration)
    )

    # photos starts on time (the ceremony it depends on wasn't disrupted),
    # but its completion is never confirmed.
    photos = schedule.activities["photos"]
    twin.record_check_in(CheckIn("photos", CheckInType.STARTED, photos.start_minutes))

    now_minutes = photos.end_minutes + 20  # 20 minutes past when photos should have wrapped up
    divergences = twin.detect_divergence(now_minutes)

    # A late but CONFIRMED start (START_TIME_DEVIATION) already propagates
    # correctly through its recorded actual_start_minutes — the activity's
    # own duration is unaffected, so no extra duration is added for it. A
    # missing completion confirmation is different: there's no actual-end
    # data at all, only evidence it's already overdue, so the overdue
    # amount stands in as a conservative duration estimate (what the
    # not-yet-built duration-prediction model would eventually supply).
    predicted_extra_duration = {
        d.activity_id: d.delta_minutes
        for d in divergences
        if d.type is DivergenceType.MISSING_COMPLETION_CONFIRMATION
    }

    return wedding, resources, schedule, twin, now_minutes, divergences, predicted_extra_duration


def main() -> None:
    wedding, resources, schedule, twin, now_minutes, divergences, predicted_extra_duration = (
        build_disrupted_wedding()
    )

    print(f"--- Divergence detected at t={format_minutes(now_minutes)} ---")
    for d in divergences:
        print(f"  [{d.type.value}] {d.activity_id}: {d.delta_minutes:+d} min")

    print(f"\n--- Predicted cascade (no re-optimisation applied) ---")
    result = simulate_cascade(
        wedding.activities, resources, schedule, twin, now_minutes,
        predicted_extra_duration_minutes=predicted_extra_duration,
    )

    if not result.delay_minutes:
        print("  No downstream activity is predicted to shift.")
    for activity_id, delay in sorted(result.delay_minutes.items(), key=lambda kv: -kv[1]):
        predicted = result.predicted_activities[activity_id]
        cause = "resource contention" if result.resource_wait_minutes.get(activity_id) else "precedence"
        print(
            f"  {activity_id:<20} now predicted {format_minutes(predicted.start_minutes)}-"
            f"{format_minutes(predicted.end_minutes)}  ({delay:+d} min, caused by {cause})"
        )


if __name__ == "__main__":
    main()
