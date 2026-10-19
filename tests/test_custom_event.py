"""Planner-entered events (the dashboard's Build event form)."""

import pytest
from fastapi.testclient import TestClient

from api import app as api_module
from api.custom_event import ActivitySpec as A, EventSpec, RequirementSpec as R, ResourceSpec as Res, build, plan_custom
from scheduling_engine.conflict_detection import verify_schedule
from scheduling_engine.operations import OperationsError
from scheduling_engine.twin import CheckInType

STAFF = [Res("Crew A", "setup crew"), Res("Crew B", "setup crew"), Res("DJ", "dj", "vendor", 10),
         Res("Host", "host")]


def birthday(**changes):
    acts = [A("Hall setup", 60, [], [R("setup crew", 2)]),
            A("Sound check", 20, [1], [R("dj")]),
            A("Guests arrive", 30, [1, 2], [R("host")], "16:00"),
            A("Party and music", 90, [3], [R("dj")]),
            A("Clean-up", 45, [4], [R("setup crew", 2)])]
    spec = EventSpec("Nimal's birthday", "13:00", acts)
    for k, v in changes.items():
        setattr(spec, k, v)
    return spec


def test_birthday_plans_conflict_free_after_opening_with_fixed_time_kept():
    ops = plan_custom(birthday(), STAFF)
    s = ops.schedule.activities
    acts = ops.activities
    assert verify_schedule(acts, ops.resources, s) == []
    assert min(x.start_minutes for x in s.values()) >= 13 * 60
    arrive = next(a for a in acts if a.name == "Guests arrive")
    assert s[arrive.id].start_minutes == 16 * 60


@pytest.mark.parametrize("spec_change, message", [
    (dict(activities=[A("Setup", 60, [3], [R("setup crew")])]), "doesn’t exist"),
    (dict(activities=[A("A", 30, [2], [R("host")]), A("B", 30, [1], [R("host")])]), "loop"),
    (dict(activities=[A("Setup", 60, [], [R("setup crew", 5)])]), "only 2"),
    (dict(activities=[A("Setup", 60, [], [R("chef")])]), "only 0"),
    (dict(activities=[A("Setup", 60, [], [R("host")], "25:00")]), "not a time"),
    (dict(activities=[A("Setup", 60, [], [R("host")], "09:00")]), "before the venue opens"),
    (dict(activities=[A("Setup", 0, [], [R("host")])]), "1–1440"),
    (dict(activities=[A("Setup", 30, [], [])]), "at least one role"),
    (dict(name=" "), "name"),
])
def test_invalid_input_is_explained(spec_change, message):
    with pytest.raises(OperationsError, match=message):
        build(birthday(**spec_change), STAFF)


def test_clashing_fixed_times_are_named_in_plain_words():
    acts = birthday().activities
    acts[3].fixed_time = "15:00"        # party fixed BEFORE guests (16:00) — it must come after them
    with pytest.raises(OperationsError) as err:
        plan_custom(birthday(activities=acts), STAFF)
    assert "Guests arrive (16:00)" in str(err.value) and "Party and music (15:00)" in str(err.value)


def test_custom_event_can_share_staff_with_the_demo_day():
    from api.scenario import build_demo_events
    from examples.run_example import build_resources
    spec = birthday(opens_at="08:00", activities=[A("Stage dressing", 45, [], [R("florist")], "11:00")])
    ops = plan_custom(spec, [Res("Florist", "florist", "vendor")], build_demo_events(), build_resources())
    assert len(ops.events) == 3
    assert sum(r.name == "Florist" for r in ops.resources) == 1          # same florist, not a copy
    assert verify_schedule(ops.activities, ops.resources, ops.schedule.activities) == []


def test_custom_event_runs_through_the_live_loop():
    ops = plan_custom(birthday(), STAFF)
    first = min(ops.activities, key=lambda a: ops.schedule.activities[a.id].start_minutes)
    s = ops.schedule.activities[first.id]
    ops.check_in(first.id, CheckInType.STARTED, s.start_minutes)
    ops.tick(s.end_minutes + 30)                                         # setup crew never confirms finishing
    assert any(e.kind == "disruption.detected" for e in ops.audit.entries)


def test_api_plan_custom(monkeypatch, tmp_path):
    monkeypatch.setattr(api_module, "AUDIT_PATH", tmp_path / "audit.jsonl")
    client = TestClient(api_module.app)
    body = {"name": "Office party", "opens_at": "17:00",
            "activities": [{"name": "Setup", "duration_minutes": 40, "needs": [{"role": "crew", "count": 1}]},
                           {"name": "Party", "duration_minutes": 120, "after": [1], "needs": [{"role": "crew"}]}],
            "resources": [{"name": "Kamal", "role": "crew"}]}
    state = client.post("/api/plan/custom", json=body).json()
    assert [e["name"] for e in state["events"]] == ["Office party"]
    assert state["conflicts"] == [] and len(state["activities"]) == 2
    body["activities"][1]["after"] = [5]
    bad = client.post("/api/plan/custom", json=body)
    assert bad.status_code == 409 and "doesn’t exist" in bad.json()["detail"]
    client.post("/api/reset")
