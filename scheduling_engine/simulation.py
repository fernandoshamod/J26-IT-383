"""
Discrete-event disruption simulation (proposal Section 4.2.2; Objective 4;
Table 4's method choice).

Why SimPy specifically, not a plain "shift everything later" loop: a
disruption doesn't only push along the precedence chain, it also pushes
along *shared resources*. If activity B is delayed, and activity C (which
has nothing to do with B) needs the same photographer, C is now delayed
too — not because of precedence, but because the resource is still busy.
Objective 4's own wording asks for the cascade "across dependent
activities and shared resources", not just the first of those. SimPy
models each activity as a process that waits for its predecessors AND
then separately queues for its assigned resources, so resource-caused
delay falls out of the simulation rather than needing to be hand-coded —
exactly the behaviour Table 4 credits discrete-event simulation with
("naturally represents dependency propagation and resource contention")
over Monte Carlo (which would only give a probability distribution over
outcomes, not *which* activities are affected and in what order).

Responsibility boundary: this module does not invent how large a
disruption is — that's the twin's job (OperationalDigitalTwin,
Section 4.2.2) to detect and, eventually, a duration-prediction model's
job to estimate. This module only propagates a disruption of a given,
already-quantified size through the dependency and resource structure,
and reports what shifts as a result. Deciding what to DO about the
cascade is re-optimisation (Objective 5), not built yet.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import simpy

from scheduling_engine.models import Activity, Resource, Schedule, ScheduledActivity
from scheduling_engine.twin import ActivityState, OperationalDigitalTwin


@dataclass
class CascadeResult:
    """Predicted outcome of letting a disruption play out with no
    re-optimisation — i.e. what Objective 5 has to improve upon.
    """

    predicted_activities: dict[str, ScheduledActivity] = field(default_factory=dict)
    # Only activities that were still NOT_STARTED at simulation time:
    # completed/in-progress activities' deviation is already known fact,
    # reported by the twin, not a prediction this module is making.
    delay_minutes: dict[str, int] = field(default_factory=dict)  # predicted_end - planned_end
    # How much EXTRA waiting-for-a-resource this activity now faces,
    # beyond whatever waiting was already baked into the original plan —
    # e.g. an activity that was always going to queue behind another for
    # 20 minutes isn't "newly" delayed by that 20; only time beyond it,
    # caused by this disruption specifically, counts here. See the
    # baseline comparison in simulate_cascade for how this is isolated.
    resource_wait_minutes: dict[str, int] = field(default_factory=dict)


def _baseline_precedence_ready(activity: Activity, schedule: Schedule) -> int:
    """When would this activity have become ready under the ORIGINAL
    plan, considering precedence alone (no resource waiting, no "now"
    floor — there is no "now" in a plan that hasn't started yet)? This is
    the same formula `live()` uses for the live simulation, applied to
    the undisturbed schedule, so the two are directly comparable.
    """
    floors = [activity.earliest_start_minutes]
    if activity.predecessors:
        floors.append(
            max(
                schedule.activities[p].end_minutes + activity.min_lag_minutes.get(p, 0)
                for p in activity.predecessors
            )
        )
    pinned = activity.pinned_start_minutes()
    if pinned is not None:
        floors.append(pinned)
    return max(floors)


def simulate_cascade(
    activities: list[Activity],
    resources: list[Resource],
    schedule: Schedule,
    twin: OperationalDigitalTwin,
    now_minutes: int,
    predicted_extra_duration_minutes: dict[str, int] | None = None,
) -> CascadeResult:
    """Run the plan forward from `now_minutes`, holding completed/
    in-progress activities at their observed (twin) times, and letting
    everything still NOT_STARTED compete for precedence and resources as
    SimPy processes.

    `predicted_extra_duration_minutes` is how a disruption's magnitude
    enters the simulation: e.g. if the twin reports a vendor's activity
    is running 20 minutes over, pass {"that_activity_id": 20} so the
    cascade reflects the delay actually being predicted, not just a start
    time that happens to be late. Activities not named here use exactly
    their original planned duration.
    """
    extra_duration = predicted_extra_duration_minutes or {}
    env = simpy.Environment()

    resource_by_id = {r.id: r for r in resources}
    simpy_resources = {r.id: simpy.Resource(env, capacity=r.capacity) for r in resources}
    finish_time: dict[str, int] = {}
    ready_time: dict[str, int] = {}
    done_event: dict[str, simpy.Event] = {a.id: env.event() for a in activities}
    predicted: dict[str, ScheduledActivity] = {}
    simulated_ids: set[str] = set()

    def release_after_turnaround(rid: str, req, release_at: int) -> None:
        """A resource stays blocked for `min_turnaround_minutes` after the
        activity's own end — mirroring the padded "block interval" the
        solver uses (solver.py) — without that padding affecting the
        activity's own finish time or holding up its done_event. Run as
        its own process per resource so two resources with different
        turnarounds on the same activity each release independently.
        """
        if release_at > env.now:
            yield env.timeout(release_at - env.now)
        simpy_resources[rid].release(req)

    def anchor(activity_id: str, start: int, end: int, assigned_resource_ids: list[str]) -> None:
        """Represents an activity whose outcome is already known (from
        the twin) rather than something to simulate. It still has to
        claim its assigned resource(s) and hold them until `end`, exactly
        like a live activity would — otherwise a not-yet-started activity
        competing for the same resource would wrongly see it as free, and
        the whole point of this module (catching resource-caused cascade
        delay, not just precedence-caused delay) would silently not work.
        """
        requests = [simpy_resources[rid].request() for rid in assigned_resource_ids]
        if requests:
            yield simpy.AllOf(env, requests)
        remaining = end - env.now
        if remaining > 0:
            yield env.timeout(remaining)
        for rid, req in zip(assigned_resource_ids, requests):
            release_at = end + resource_by_id[rid].min_turnaround_minutes
            env.process(release_after_turnaround(rid, req, release_at))
        finish_time[activity_id] = end
        ready_time[activity_id] = start
        predicted[activity_id] = ScheduledActivity(activity_id, start, end, assigned_resource_ids)
        done_event[activity_id].succeed()

    def live(activity: Activity) -> None:
        if activity.predecessors:
            yield simpy.AllOf(env, [done_event[p] for p in activity.predecessors])
        precedence_ready = max(
            (finish_time[p] + activity.min_lag_minutes.get(p, 0) for p in activity.predecessors),
            default=now_minutes,
        )
        floors = [precedence_ready, now_minutes, activity.earliest_start_minutes]
        pinned = activity.pinned_start_minutes()
        if pinned is not None:
            # A fixed/locked start is a floor here, not an exact pin: the
            # original plan only guaranteed it when every other
            # constraint allowed it. If this disruption's precedence
            # delay pushes past the pin, that IS the disruption's effect
            # on this activity — e.g. a client-fixed ceremony time now at
            # risk — and must show up as predicted delay, not be masked.
            floors.append(pinned)
        ready_at = max(floors)
        if ready_at > env.now:
            yield env.timeout(ready_at - env.now)
        ready_time[activity.id] = env.now

        assigned_resource_ids = schedule.activities[activity.id].assigned_resource_ids
        requests = [simpy_resources[rid].request() for rid in assigned_resource_ids]
        if requests:
            yield simpy.AllOf(env, requests)

        start = env.now
        duration = activity.duration_minutes + extra_duration.get(activity.id, 0)
        yield env.timeout(duration)
        end = env.now

        for rid, req in zip(assigned_resource_ids, requests):
            release_at = end + resource_by_id[rid].min_turnaround_minutes
            env.process(release_after_turnaround(rid, req, release_at))

        finish_time[activity.id] = end
        predicted[activity.id] = ScheduledActivity(activity.id, start, end, assigned_resource_ids)
        done_event[activity.id].succeed()

    for a in activities:
        state = twin.state_of(a.id)
        assigned_resource_ids = schedule.activities[a.id].assigned_resource_ids
        if state.state is ActivityState.COMPLETED:
            env.process(anchor(a.id, state.actual_start_minutes, state.actual_end_minutes, assigned_resource_ids))
        elif state.state is ActivityState.IN_PROGRESS:
            predicted_end = (
                state.actual_start_minutes + a.duration_minutes + extra_duration.get(a.id, 0)
            )
            env.process(anchor(a.id, state.actual_start_minutes, predicted_end, assigned_resource_ids))
        else:
            simulated_ids.add(a.id)
            env.process(live(a))

    env.run()

    activity_by_id = {a.id: a for a in activities}
    delay_minutes: dict[str, int] = {}
    resource_wait_minutes: dict[str, int] = {}
    for activity_id in simulated_ids:
        activity = activity_by_id[activity_id]
        planned = schedule.activities[activity_id]

        delta = predicted[activity_id].end_minutes - planned.end_minutes
        if delta != 0:
            delay_minutes[activity_id] = delta

        # How much of this activity's wait for its resource is NEW,
        # caused by this disruption, versus wait that was already part of
        # the original plan (e.g. it was always going to queue behind
        # something). Comparing the predicted wait to a same-formula
        # baseline computed from the original plan isolates just the
        # disruption's own contribution.
        predicted_wait = predicted[activity_id].start_minutes - ready_time[activity_id]
        baseline_ready = _baseline_precedence_ready(activity, schedule)
        baseline_wait = planned.start_minutes - baseline_ready
        extra_wait = predicted_wait - baseline_wait
        if extra_wait > 0:
            resource_wait_minutes[activity_id] = extra_wait

    return CascadeResult(
        predicted_activities=predicted,
        delay_minutes=delay_minutes,
        resource_wait_minutes=resource_wait_minutes,
    )
