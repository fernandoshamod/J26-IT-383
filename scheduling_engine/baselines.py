"""
Baseline disruption-response strategies (proposal Table 5, Section 3.4).

Only two of the proposal's three baselines are implemented here. The
third, "greedy heuristic" ("absorb the delay into the nearest activity
possessing slack, then shift the remainder; respect locked activities"),
is not re-implemented separately — it IS what simulate_cascade
(Objective 4) already computes: resource- and precedence-aware forward
propagation with no further intervention naturally absorbs into whatever
slack exists and only shifts what genuinely has to move. Reusing that
already-tested module as the greedy baseline avoids two subtly different
"greedy" implementations drifting apart in the same codebase. See
evaluate_disruption_handling.py for where all three baselines plus the
CP-based re-optimiser are run side by side on identical scenarios.
"""

from __future__ import annotations

from scheduling_engine.models import Schedule, ScheduledActivity


def no_reschedule(schedule: Schedule, disrupted_activity_id: str, delay_minutes: int) -> Schedule:
    """The lower bound: the disruption happens and nothing else is
    touched. Only the disrupted activity's own real (overrun) end is
    recorded; everything else keeps its exact original planned time,
    even where that is now physically impossible. This is expected to
    fail the conflict-free metric — a strategy this naive SHOULD
    double-book resources and violate precedence; that is the point of
    including it, not a flaw in how it's implemented here.
    """
    original = schedule.activities[disrupted_activity_id]
    revised = dict(schedule.activities)
    revised[disrupted_activity_id] = ScheduledActivity(
        disrupted_activity_id,
        original.start_minutes,
        original.end_minutes + delay_minutes,
        original.assigned_resource_ids,
    )
    return Schedule(is_feasible=True, activities=revised)


def naive_forward_shift(schedule: Schedule, disrupted_activity_id: str, delay_minutes: int) -> Schedule:
    """Table 5: "every activity after the disrupted one is shifted later
    by the full delay." Deliberately blind to slack (an activity that
    never needed to move still gets pushed) and to locks (a locked
    activity shifts like anything else) — that blindness is exactly what
    makes this an inferior baseline to measure against.
    """
    disrupted_start = schedule.activities[disrupted_activity_id].start_minutes
    revised = {}
    for activity_id, original in schedule.activities.items():
        if activity_id == disrupted_activity_id:
            revised[activity_id] = ScheduledActivity(
                activity_id,
                original.start_minutes,
                original.end_minutes + delay_minutes,
                original.assigned_resource_ids,
            )
        elif original.start_minutes >= disrupted_start:
            revised[activity_id] = ScheduledActivity(
                activity_id,
                original.start_minutes + delay_minutes,
                original.end_minutes + delay_minutes,
                original.assigned_resource_ids,
            )
        else:
            revised[activity_id] = original
    return Schedule(is_feasible=True, activities=revised)
