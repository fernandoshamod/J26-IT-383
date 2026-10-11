"""
Worked example matching the scenario described in the proposal's Abstract
and Section 1.1: a mid-sized wedding reception, modelled as the eleven
activities named there, run alongside a second, smaller concurrent event
that happens to need the same florist — to show cross-event conflict
avoidance (Objective 2 / FR-06), not just within-event correctness.

Run from the repository root:
    python examples/run_example.py
"""

from scheduling_engine import (
    Activity,
    Event,
    Resource,
    ResourceRequirement,
    ResourceType,
    solve_planning_phase,
    verify_schedule,
)


def build_wedding() -> Event:
    # Durations are illustrative placeholders standing in for the
    # proposal's planned duration-prediction model (Section 4.2.1); this
    # example only needs to exercise the solver, not predict anything.
    activities = [
        Activity("venue_setup", "wedding", "Venue setup", 90,
                 requirements=[ResourceRequirement("setup_crew", count=2)]),
        Activity("decor", "wedding", "Floral and decor installation", 60,
                 predecessors=["venue_setup"],
                 requirements=[ResourceRequirement("florist")]),
        Activity("sound_check", "wedding", "Sound and lighting check", 30,
                 predecessors=["venue_setup"],
                 requirements=[ResourceRequirement("av_crew")]),
        Activity("catering_load_in", "wedding", "Catering load-in", 45,
                 predecessors=["decor"],
                 requirements=[ResourceRequirement("catering_crew", count=2)]),
        Activity("guest_arrival", "wedding", "Guest arrival and welcome", 30,
                 predecessors=["decor", "sound_check"],
                 fixed_start_minutes=14 * 60,  # client fixed this at 2:00 PM
                 requirements=[ResourceRequirement("usher")]),
        Activity("ceremony", "wedding", "Ceremony", 30,
                 predecessors=["guest_arrival"],
                 requirements=[ResourceRequirement("officiant"), ResourceRequirement("photographer")]),
        Activity("photos", "wedding", "Photography session", 45,
                 predecessors=["ceremony"],
                 requirements=[ResourceRequirement("photographer")]),
        Activity("dinner_service", "wedding", "Dinner service", 60,
                 predecessors=["photos", "catering_load_in"],
                 requirements=[ResourceRequirement("catering_crew", count=2)]),
        Activity("speeches", "wedding", "Speeches", 20,
                 predecessors=["dinner_service"],
                 requirements=[ResourceRequirement("av_crew")]),
        Activity("entertainment", "wedding", "Entertainment", 90,
                 predecessors=["speeches"],
                 requirements=[ResourceRequirement("av_crew")]),
        Activity("strike", "wedding", "Strike and load-out", 60,
                 predecessors=["entertainment"],
                 requirements=[ResourceRequirement("setup_crew", count=2)]),
    ]
    return Event("wedding", "Blooming Moments — Perera Wedding", activities)


def build_concurrent_corporate_event() -> Event:
    # A same-day product launch that happens to book the same florist for
    # its own decor, forcing the solver to arbitrate between two events
    # rather than within one.
    activities = [
        Activity("corp_decor", "corp_launch", "Stage decor", 45,
                 earliest_start_minutes=9 * 60,
                 requirements=[ResourceRequirement("florist")]),
        Activity("corp_event", "corp_launch", "Launch event", 120,
                 predecessors=["corp_decor"],
                 requirements=[ResourceRequirement("av_crew")]),
    ]
    return Event("corp_launch", "Acme Product Launch", activities)


def build_resources() -> list[Resource]:
    return [
        Resource("setup-1", "Setup crew A", ResourceType.STAFF, "setup_crew"),
        Resource("setup-2", "Setup crew B", ResourceType.STAFF, "setup_crew"),
        Resource("florist-1", "Florist", ResourceType.VENDOR, "florist"),
        Resource("av-1", "AV crew", ResourceType.STAFF, "av_crew", min_turnaround_minutes=10),
        Resource("catering-1", "Catering crew A", ResourceType.VENDOR, "catering_crew"),
        Resource("catering-2", "Catering crew B", ResourceType.VENDOR, "catering_crew"),
        Resource("usher-1", "Usher", ResourceType.STAFF, "usher"),
        Resource("officiant-1", "Officiant", ResourceType.VENDOR, "officiant"),
        Resource("photographer-1", "Photographer", ResourceType.VENDOR, "photographer"),
    ]


def format_minutes(total_minutes: int) -> str:
    hours, minutes = divmod(total_minutes, 60)
    return f"{hours:02d}:{minutes:02d}"


def main() -> None:
    wedding = build_wedding()
    corp_launch = build_concurrent_corporate_event()
    resources = build_resources()
    all_activities = wedding.activities + corp_launch.activities

    schedule = solve_planning_phase([wedding, corp_launch], resources)

    print(f"Status: {schedule.status_name} | feasible: {schedule.is_feasible}")
    if not schedule.is_feasible:
        print("Conflicting pinned activities:", schedule.conflicting_pinned_activity_ids)
        return

    print(f"Solve time: {schedule.solve_time_seconds:.3f}s | makespan: {schedule.makespan_minutes} min\n")
    for activity in sorted(all_activities, key=lambda a: schedule.activities[a.id].start_minutes):
        s = schedule.activities[activity.id]
        print(
            f"  [{activity.event_id:<12}] {format_minutes(s.start_minutes)}-"
            f"{format_minutes(s.end_minutes)}  {activity.name:<30} "
            f"<- {', '.join(s.assigned_resource_ids)}"
        )

    conflicts = verify_schedule(all_activities, resources, schedule.activities)
    print(f"\nIndependent verification: {len(conflicts)} conflict(s) found.")
    for c in conflicts:
        print(" ", c.message)


if __name__ == "__main__":
    main()
