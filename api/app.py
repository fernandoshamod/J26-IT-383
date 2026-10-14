"""
HTTP API for the planner dashboard and the vendor/staff check-in page.

Thin by design: every endpoint calls one method of EventOperations
(scheduling_engine/operations.py), where all the logic and its tests live.

Run from the repository root:
    python -m uvicorn api.app:app --reload
then open http://127.0.0.1:8000  (API docs: http://127.0.0.1:8000/docs)
"""

from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from api.forecast import model_card
from api.scenario import PLANNING_MODES, new_operations, play_on_time, scenario_kwargs
from scheduling_engine.conflict_detection import verify_schedule
from scheduling_engine.integration import to_jsonable
from scheduling_engine.operations import EventOperations, OperationsError
from scheduling_engine.twin import CheckInType

ROOT = Path(__file__).resolve().parent.parent
STATIC_DIR = Path(__file__).resolve().parent / "static"
AUDIT_PATH = ROOT / "logs" / "audit.jsonl"

app = FastAPI(title="Component 3 — Event Planning and Dynamic Resource Optimization",
              description="Live scheduling, digital twin, disruption simulation and re-optimisation "
                          "(J26-IT-383, Component 3).")
MODE = "planner"
ops: EventOperations = new_operations(AUDIT_PATH, MODE)


class CheckInRequest(BaseModel):
    activity_id: str
    type: CheckInType
    at_minutes: int | None = Field(None, description="when it was tapped; defaults to the current clock")
    by: str | None = Field(None, description="resource id of the person checking in")
    client_id: str | None = Field(None, description="unique per check-in; repeats are ignored (safe retries)")
    queued_offline: bool = False


class ClockRequest(BaseModel):
    advance_minutes: int | None = None
    to_minutes: int | None = None


class DecisionRequest(BaseModel):
    planner: str = "planner"
    note: str = ""


class LockRequest(BaseModel):
    start_minutes: int | None = Field(None, description="defaults to its current planned start")
    planner: str = "planner"


class ModeRequest(BaseModel):
    mode: str = Field(description='"planner" (planner estimates) or "predicted" (ML durations)')


class PlayRequest(BaseModel):
    until_minutes: int
    silent: list[str] = []
    late_start: dict[str, int] = {}
    no_completion: list[str] = []


def _hhmm(m: int) -> str:
    return f"{m // 60:02d}:{m % 60:02d}"


def _proposal_view(p) -> dict:
    view = to_jsonable(p)
    view.pop("revised", None)  # changes[] carries what the UI needs
    return view


def snapshot() -> dict:
    """Everything the dashboard renders, in one response."""
    activities = []
    for a in ops.activities:
        planned = ops.schedule.activities[a.id]
        state = ops.twin.state_of(a.id)
        activities.append(dict(
            id=a.id, event_id=a.event_id, name=a.name,
            planned_start=planned.start_minutes, planned_end=planned.end_minutes,
            resources=planned.assigned_resource_ids, predecessors=a.predecessors,
            state=state.state.value, actual_start=state.actual_start_minutes, actual_end=state.actual_end_minutes,
            fixed_start=a.fixed_start_minutes, locked_start=a.locked_start_minutes,
            tolerance=ops.twin.tolerance_for(a.id),
        ))
    activities.sort(key=lambda x: x["planned_start"])
    pending = ops.pending_proposal
    confirmed = [p for p in ops.proposals if p.status == "confirmed"]
    events_by_resource: dict[str, set[str]] = {}
    for a in ops.activities:
        for rid in ops.schedule.activities[a.id].assigned_resource_ids:
            events_by_resource.setdefault(rid, set()).add(a.event_id)
    return dict(
        clock=dict(now=ops.now, now_hhmm=_hhmm(ops.now), schedule_version=ops.schedule_version),
        events=[dict(id=e.id, name=e.name) for e in ops.events],
        activities=activities,
        resources=[dict(id=r.id, name=r.name, type=r.type.value, role=r.role,
                        turnaround=r.min_turnaround_minutes) for r in ops.resources],
        divergences=to_jsonable(ops.twin.detect_divergence(ops.now)),
        pending_proposal=_proposal_view(pending) if pending else None,
        last_confirmed=_proposal_view(confirmed[-1]) if confirmed else None,
        conflicts=to_jsonable(verify_schedule(ops.activities, ops.resources, ops.schedule.activities)),
        shared_resources=sorted(r for r, evs in events_by_resource.items() if len(evs) > 1),
        ml=dict(mode=ops.mode, card=model_card(), durations=ops.forecast.durations,
                vendor_risk=ops.forecast.vendor_risk, planner_end=ops.planner_end,
                plan_end=max(s.end_minutes for s in ops.schedule.activities.values())),
        proposals=[dict(id=p.id, status=p.status, created_at_minute=p.created_at_minute,
                        decided_by=p.decided_by) for p in ops.proposals],
        notifications=to_jsonable(ops.notifications.outbox[-50:]),
        component4_received=ops.component4.received[-20:],
        audit=to_jsonable(list(ops.audit.entries[-80:])),
        bus=to_jsonable(ops.bus.history[-50:]),
    )


def _apply(action):
    try:
        action()
    except OperationsError as e:
        raise HTTPException(status_code=409, detail=str(e))
    return snapshot()


@app.get("/api/state")
def get_state() -> dict:
    return snapshot()


@app.post("/api/reset")
def reset() -> dict:
    global ops
    ops = new_operations(AUDIT_PATH, MODE)
    return snapshot()


@app.post("/api/plan/mode")
def set_mode(req: ModeRequest) -> dict:
    """Re-plan the day with planner estimates or ML-predicted durations."""
    global ops, MODE
    if req.mode not in PLANNING_MODES:
        raise HTTPException(status_code=422, detail=f"mode must be one of {PLANNING_MODES}")
    MODE = req.mode
    ops = new_operations(AUDIT_PATH, MODE)
    return snapshot()


@app.post("/api/checkins")
def post_check_in(req: CheckInRequest) -> dict:
    return _apply(lambda: ops.check_in(req.activity_id, req.type, req.at_minutes, req.by,
                                       req.client_id, req.queued_offline))


@app.get("/api/my-tasks/{resource_id}")
def my_tasks(resource_id: str) -> dict:
    """Small payload for the vendor/staff phone page: just this person's
    tasks and the clock (kept light for weak mobile signal)."""
    resource = next((r for r in ops.resources if r.id == resource_id), None)
    if resource is None:
        raise HTTPException(status_code=404, detail=f"unknown resource {resource_id!r}")
    divergence = {d.activity_id: d for d in ops.twin.detect_divergence(ops.now) if d.delta_minutes > 0}
    tasks = []
    for a in ops.activities:
        planned = ops.schedule.activities[a.id]
        if resource_id not in planned.assigned_resource_ids:
            continue
        state = ops.twin.state_of(a.id)
        d = divergence.get(a.id)
        tasks.append(dict(id=a.id, name=a.name, event=next(e.name for e in ops.events if e.id == a.event_id),
                          planned_start=planned.start_minutes, planned_end=planned.end_minutes,
                          state=state.state.value, actual_start=state.actual_start_minutes,
                          actual_end=state.actual_end_minutes,
                          overdue_minutes=d.delta_minutes if d else 0, fixed=a.pinned_start_minutes() is not None))
    tasks.sort(key=lambda t: t["planned_start"])
    return dict(resource=dict(id=resource.id, name=resource.name, role=resource.role),
                clock=dict(now=ops.now, now_hhmm=_hhmm(ops.now), schedule_version=ops.schedule_version),
                tasks=tasks)


@app.get("/api/people")
def people() -> list[dict]:
    """Who can check in (for the phone page's sign-in list)."""
    return [dict(id=r.id, name=r.name, type=r.type.value) for r in ops.resources]


@app.post("/api/clock")
def post_clock(req: ClockRequest) -> dict:
    if (req.advance_minutes is None) == (req.to_minutes is None):
        raise HTTPException(status_code=422, detail="give exactly one of advance_minutes / to_minutes")
    target = ops.now + req.advance_minutes if req.advance_minutes is not None else req.to_minutes
    return _apply(lambda: ops.tick(target))


@app.post("/api/proposals/{proposal_id}/confirm")
def confirm(proposal_id: int, req: DecisionRequest) -> dict:
    return _apply(lambda: ops.confirm(proposal_id, req.planner, req.note))


@app.post("/api/proposals/{proposal_id}/reject")
def reject(proposal_id: int, req: DecisionRequest) -> dict:
    return _apply(lambda: ops.reject(proposal_id, req.planner, req.note))


@app.post("/api/activities/{activity_id}/lock")
def lock(activity_id: str, req: LockRequest) -> dict:
    def action():
        start = req.start_minutes
        if start is None:
            ops.activity(activity_id)  # raises if unknown
            start = ops.schedule.activities[activity_id].start_minutes
        ops.lock(activity_id, start, req.planner)
    return _apply(action)


@app.post("/api/demo/play")
def demo_play(req: PlayRequest) -> dict:
    """Demo helper: everyone checks in on time up to `until_minutes`, except
    `silent` activities (never confirm) and `late_start` ones."""
    return _apply(lambda: play_on_time(ops, req.until_minutes, set(req.silent), req.late_start,
                                       set(req.no_completion)))


@app.post("/api/demo/scenario/{name}")
def demo_scenario(name: str) -> dict:
    """Reset, then play one of the scripted demo scenarios (see api/scenario.py)."""
    global ops
    ops = new_operations(AUDIT_PATH, MODE)
    try:
        kwargs = scenario_kwargs(name, ops)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    return _apply(lambda: play_on_time(ops, **kwargs))


if STATIC_DIR.exists():
    app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


@app.get("/checkin", include_in_schema=False)
def checkin_page():
    return FileResponse(STATIC_DIR / "checkin.html")


@app.get("/", include_in_schema=False)
def index():
    page = STATIC_DIR / "index.html"
    return FileResponse(page) if page.exists() else RedirectResponse("/docs")
