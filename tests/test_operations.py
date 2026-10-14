"""The live-operations loop (FR-08..FR-16) and its HTTP API."""

import json

import pytest
from fastapi.testclient import TestClient

from api import app as api_module
from api.scenario import SETUP_EARLIEST_START, new_operations, play_on_time
from scheduling_engine.integration import TOPIC_COST_SIGNAL, AuditLog
from scheduling_engine.operations import OperationsError
from scheduling_engine.twin import CheckInType


@pytest.fixture
def ops():
    return new_operations()


def _photos_overrun(ops, minutes=20):
    """Everything on time up to photos, whose completion never arrives."""
    photos = ops.schedule.activities["photos"]
    play_on_time(ops, photos.start_minutes, silent={"photos"})
    ops.check_in("photos", CheckInType.STARTED, photos.start_minutes)
    ops.tick(photos.end_minutes + minutes)
    return photos


def test_plan_starts_at_venue_opening_with_no_conflicts(ops):
    assert ops.now == SETUP_EARLIEST_START
    assert ops.schedule_version == 1
    assert ops.pending_proposal is None
    assert "0 conflicts" in ops.audit.entries[0].summary


def test_on_time_check_ins_raise_no_disruption(ops):
    play_on_time(ops, ops.schedule.activities["ceremony"].end_minutes)
    assert ops.pending_proposal is None
    assert not [e for e in ops.audit.entries if e.kind == "disruption.detected"]


def test_missing_confirmation_produces_a_proposal_but_changes_nothing_yet(ops):
    """FR-10 sensor-free detection, FR-11 simulation, FR-13 nothing applied
    until the planner decides."""
    _photos_overrun(ops)
    p = ops.pending_proposal
    assert p is not None
    assert any(d.activity_id == "photos" and d.type.value == "missing_completion_confirmation" for d in p.trigger)
    assert p.predicted_extra_duration == {"photos": 20}
    assert p.do_nothing_delay["dinner_service"] == 20  # simulated cascade
    assert p.is_feasible and p.solve_seconds < 5      # NFR-01
    assert ops.schedule_version == 1                  # not applied yet


def test_confirm_applies_plan_publishes_cost_signal_and_notifies(ops):
    _photos_overrun(ops)
    p = ops.pending_proposal
    ops.confirm(p.id, "dinuja", "client agreed")
    assert ops.schedule_version == 2
    assert ops.schedule.activities["dinner_service"].start_minutes == p.revised.activities["dinner_service"].start_minutes
    # Written back into the twin as the new reference, with history kept.
    assert ops.twin.state_of("ceremony").state.value == "completed"
    # FR-14: Component 4 received exactly one cost signal, via the bus.
    assert len(ops.component4.received) == 1
    assert ops.component4.received[0]["cost_signal"]["total_delay_minutes"] == p.cost_signal.total_delay_minutes
    assert [m.topic for m in ops.bus.history].count(TOPIC_COST_SIGNAL) == 1
    # FR-15: everyone assigned to a moved activity got a message.
    notified = {(n.resource_id, n.activity_id) for n in ops.notifications.outbox}
    for change in p.changes:
        for rid in change.resource_ids:
            assert (rid, change.activity_id) in notified
    # No longer overdue against the NEW plan, so no new proposal.
    assert ops.pending_proposal is None


def test_overrun_beyond_the_revised_plan_triggers_again(ops):
    _photos_overrun(ops)
    ops.confirm(ops.pending_proposal.id, "dinuja")
    ops.tick(ops.now + 30)
    assert ops.pending_proposal is not None


def test_new_check_in_supersedes_a_stale_proposal(ops):
    """Regression: confirming a proposal computed before newer check-ins
    could undo what had just happened."""
    _photos_overrun(ops)
    first = ops.pending_proposal
    ops.check_in("photos", CheckInType.COMPLETED)  # photographer finally confirms
    assert first.status == "superseded"
    with pytest.raises(OperationsError):
        ops.confirm(first.id, "dinuja")


def test_rejected_divergence_is_not_reproposed_but_a_new_one_is(ops):
    _photos_overrun(ops)
    ops.reject(ops.pending_proposal.id, "dinuja", "photographer says 5 more minutes")
    ops.tick(ops.now + 1)
    assert ops.pending_proposal is None
    ops.tick(ops.schedule.activities["dinner_service"].start_minutes + 60)  # now dinner is badly overdue too
    assert ops.pending_proposal is not None


def test_locked_activity_is_respected_or_named_when_impossible(ops):
    """FR-07/FR-12: a lock is never silently broken."""
    entertainment = ops.schedule.activities["entertainment"].start_minutes
    ops.lock("entertainment", entertainment, "dinuja")
    _photos_overrun(ops, minutes=120)  # far too much delay to keep the lock
    p = ops.pending_proposal
    assert not p.is_feasible
    assert "entertainment" in p.conflicting_locked_ids
    with pytest.raises(OperationsError):
        ops.confirm(p.id, "dinuja")


def test_check_in_validation(ops):
    with pytest.raises(OperationsError):
        ops.check_in("venue_setup", CheckInType.COMPLETED)  # not started
    ops.check_in("venue_setup", CheckInType.STARTED)
    with pytest.raises(OperationsError):
        ops.check_in("venue_setup", CheckInType.STARTED)
    with pytest.raises(OperationsError):
        ops.check_in("no_such_activity", CheckInType.STARTED)


def test_audit_log_is_append_only_and_persisted(tmp_path):
    path = tmp_path / "audit.jsonl"
    log = AuditLog(path)
    log.record(600, "disruption.detected", "system", "photos overdue", {"delta": 20})
    log.record(601, "schedule.changed", "planner:dinuja", "confirmed")
    lines = [json.loads(l) for l in path.read_text(encoding="utf-8").splitlines()]
    assert [l["sequence"] for l in lines] == [1, 2]
    assert lines[0]["details"] == {"delta": 20}
    assert isinstance(log.entries, tuple)  # callers get a read-only view


def test_api_full_disruption_story(monkeypatch, tmp_path):
    monkeypatch.setattr(api_module, "AUDIT_PATH", tmp_path / "audit.jsonl")
    client = TestClient(api_module.app)
    state = client.post("/api/reset").json()
    photos = next(a for a in state["activities"] if a["id"] == "photos")

    state = client.post("/api/demo/play", json={"until_minutes": photos["planned_end"] + 20,
                                                "silent": ["photos"]}).json()
    assert state["pending_proposal"] is None or state["pending_proposal"]["id"]
    # photos never even confirmed its START: still detected, from silence alone.
    proposal = state["pending_proposal"]
    assert proposal is not None
    assert any(t["activity_id"] == "photos" for t in proposal["trigger"])

    state = client.post(f"/api/proposals/{proposal['id']}/confirm", json={"planner": "dinuja"}).json()
    assert state["clock"]["schedule_version"] == 2
    assert state["component4_received"]
    assert state["notifications"]
    assert any(e["kind"] == "schedule.changed" for e in state["audit"])

    bad = client.post("/api/checkins", json={"activity_id": "nope", "type": "started"})
    assert bad.status_code == 409
    assert client.post("/api/clock", json={}).status_code == 422


def test_disruption_absorbed_by_slack_does_not_interrupt_the_planner(ops):
    """Catering 40 min late, before the fixed 14:00 guest arrival: slack
    absorbs it, so it's logged but no proposal is raised."""
    play_on_time(ops, ops.schedule.activities["guest_arrival"].start_minutes, late_start={"catering_load_in": 40})
    assert ops.pending_proposal is None
    assert not ops.proposals
    kinds = [e.kind for e in ops.audit.entries]
    assert "disruption.detected" in kinds and "disruption.absorbed" in kinds


def test_completed_activities_are_not_reported_as_changes(ops):
    photos = ops.schedule.activities["photos"]
    play_on_time(ops, photos.start_minutes, silent={"photos"}, late_start={"catering_load_in": 40})
    ops.check_in("photos", CheckInType.STARTED, photos.start_minutes)
    ops.tick(photos.end_minutes + 20)
    changed = {c.activity_id for c in ops.pending_proposal.changes}
    assert "catering_load_in" not in changed  # finished hours ago
    assert {"photos", "dinner_service"} <= changed


def test_growing_disruption_supersedes_the_pending_proposal(ops):
    """A proposal sized for a 20-min overrun is stale once it's 40 min."""
    _photos_overrun(ops, minutes=20)
    first = ops.pending_proposal
    ops.tick(ops.now + 20)
    assert first.status == "superseded"
    assert ops.pending_proposal.predicted_extra_duration["photos"] == 40


def test_setup_overrun_scenario_protects_the_fixed_corporate_launch():
    """Demo scenario B: doing nothing would start the other client's fixed
    10:30 launch late; re-optimisation keeps it and moves the sound check."""
    from api.scenario import CORPORATE_LAUNCH_START, scenario_kwargs
    ops = new_operations()
    play_on_time(ops, **scenario_kwargs("setup_overrun", ops))
    kinds = [e.kind for e in ops.audit.entries]
    assert kinds.index("disruption.absorbed") < kinds.index("proposal.created")  # 15 min absorbed, 30 min not
    p = ops.pending_proposal
    assert any("corp_event" in v for v in p.do_nothing_violations)
    assert p.revised.activities["corp_event"].start_minutes == CORPORATE_LAUNCH_START
    assert p.revised.activities["sound_check"].start_minutes >= p.revised.activities["corp_event"].end_minutes
    assert p.revised.activities["guest_arrival"].start_minutes == 14 * 60


def test_dashboard_and_scenarios_are_served(monkeypatch, tmp_path):
    monkeypatch.setattr(api_module, "AUDIT_PATH", tmp_path / "audit.jsonl")
    client = TestClient(api_module.app)
    page = client.get("/")
    assert page.status_code == 200 and "Disruption console" in page.text
    for name in ("late_catering", "setup_overrun", "silent_photographer"):
        assert client.post(f"/api/demo/scenario/{name}").status_code == 200
    assert client.post("/api/demo/scenario/nope").status_code == 404


def test_ml_planning_mode_uses_predicted_durations(monkeypatch, tmp_path):
    """Section 4.2.1: in "predicted" mode the solver plans with the duration
    model's estimates; the forecast is always available for the dashboard."""
    monkeypatch.setattr(api_module, "AUDIT_PATH", tmp_path / "audit.jsonl")
    client = TestClient(api_module.app)
    planner = client.post("/api/plan/mode", json={"mode": "planner"}).json()
    predicted = client.post("/api/plan/mode", json={"mode": "predicted"}).json()
    try:
        assert predicted["ml"]["mode"] == "predicted"
        setup = next(a for a in predicted["activities"] if a["id"] == "venue_setup")
        forecast = next(d for d in predicted["ml"]["durations"] if d["id"] == "venue_setup")
        assert setup["planned_end"] - setup["planned_start"] == forecast["predicted"]
        assert predicted["ml"]["plan_end"] > planner["ml"]["plan_end"]  # planners underestimate
        assert predicted["conflicts"] == []                            # still conflict-free
        launch = next(d for d in predicted["ml"]["durations"] if d["id"] == "corp_event")
        assert launch["predicted"] is None                             # untrained type: no guess
        assert all(0 <= v["probability"] <= 1 for v in predicted["ml"]["vendor_risk"])
        assert client.post("/api/plan/mode", json={"mode": "nope"}).status_code == 422
    finally:
        client.post("/api/plan/mode", json={"mode": "planner"})


def test_retried_check_in_with_same_client_id_counts_once(ops):
    """NFR-07: a phone that never got the reply sends again; no double count, no error."""
    ops.check_in("venue_setup", CheckInType.STARTED, client_id="abc")
    ops.check_in("venue_setup", CheckInType.STARTED, client_id="abc")  # retry: ignored
    assert [e.kind for e in ops.audit.entries].count("checkin.received") == 1
    with pytest.raises(OperationsError):  # a genuinely NEW duplicate is still refused
        ops.check_in("venue_setup", CheckInType.STARTED, client_id="xyz")


def test_offline_check_in_keeps_tap_time_and_is_marked(ops):
    """The recorded time is when it was tapped, not when it arrived."""
    start = ops.schedule.activities["venue_setup"].start_minutes
    ops.tick(start + 30)  # signal came back 30 min later
    ops.check_in("venue_setup", CheckInType.STARTED, at_minutes=start, by="setup-1", queued_offline=True)
    assert ops.twin.state_of("venue_setup").actual_start_minutes == start
    entry = [e for e in ops.audit.entries if e.kind == "checkin.received"][-1]
    assert entry.actor == "checkin:setup-1" and "queued offline" in entry.summary


def test_phone_endpoints(monkeypatch, tmp_path):
    monkeypatch.setattr(api_module, "AUDIT_PATH", tmp_path / "audit.jsonl")
    client = TestClient(api_module.app)
    client.post("/api/reset")
    assert client.get("/checkin").status_code == 200
    assert any(p["id"] == "photographer-1" for p in client.get("/api/people").json())
    mine = client.get("/api/my-tasks/photographer-1").json()
    assert [t["id"] for t in mine["tasks"]] == ["ceremony", "photos"]  # only this person's tasks
    assert client.get("/api/my-tasks/nobody").status_code == 404
    body = {"activity_id": "venue_setup", "type": "started", "by": "setup-1", "client_id": "k1"}
    assert client.post("/api/checkins", json=body).status_code == 200
    assert client.post("/api/checkins", json=body).status_code == 200  # safe retry


def test_replay_never_starts_work_for_a_crew_that_is_still_busy():
    """Regression (found by the scalability test): replaying "everyone on
    time" checked in the next job of a crew still busy on an overrunning
    activity, telling the engine one crew was in two places at once."""
    from examples.scalability_test import fork, plan_day
    base, _, _ = plan_day(1, 5, False)
    ops = fork(base)
    target = "ev3-a10"
    play_on_time(ops, ops.schedule.activities[target].end_minutes, no_completion={target})
    busy = set(ops.schedule.activities[target].assigned_resource_ids)
    start = ops.schedule.activities[target].start_minutes
    for a in ops.activities:
        s = ops.schedule.activities[a.id]
        if a.id != target and s.start_minutes >= start and busy & set(s.assigned_resource_ids):
            assert ops.twin.state_of(a.id).state.value == "not_started", a.id
