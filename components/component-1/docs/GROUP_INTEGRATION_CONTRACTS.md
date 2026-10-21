# Proposed group integration contracts — NOT IMPLEMENTED

## Observed interfaces and ownership

Read-only C3 revision b4676b7a16664ab4dd4d584157a279d5fc620832 was inspected. Its [models](https://github.com/fernandoshamod/J26-IT-383/blob/b4676b7a16664ab4dd4d584157a279d5fc620832/scheduling_engine/models.py), [custom event input](https://github.com/fernandoshamod/J26-IT-383/blob/b4676b7a16664ab4dd4d584157a279d5fc620832/api/custom_event.py), [operational twin](https://github.com/fernandoshamod/J26-IT-383/blob/b4676b7a16664ab4dd4d584157a279d5fc620832/scheduling_engine/twin.py) and [operations](https://github.com/fernandoshamod/J26-IT-383/blob/b4676b7a16664ab4dd4d584157a279d5fc620832/scheduling_engine/operations.py) distinguish scheduling state from C1 geometry. Older comments that adaptation is unbuilt do not override current reoptimization/proposal source.

C1 owns source-image candidates, reviewed spatial geometry/versions, generated layouts, spatial feasibility and permission-aware spatial repairs. C3 owns timed activities, predecessors/lags, staff/equipment/vendor resource schedules, check-ins, disruptions and schedule proposals. C1 NSGA-II/EAG-APR and C3 CP-SAT/operational rescheduling are distinct algorithms. Spatial Twin polygons are not C3 ActivityState/check-in/time-deviation records. C3 must not mutate C1 approved polygons; C1 must not mark C3 tasks completed or assign schedule times without a converter. Components 2 and 4 have no inspectable contracts in the audited repo: their ownership and interfaces require team input, not invented assumptions.

C3 current Resource: id/name/type/role/capacity/min_turnaround_minutes. Activity: event_id/duration/requirements/predecessors/min_lags/earliest/fixed/locked starts. Schedule: feasibility, activity start/end/assigned resources, makespan, solve time and conflict IDs. Times are integer minute offsets from a shared epoch. Current custom input uses name, opens_at HH:MM, activities and resources; after references are one-based row positions. It does not accept this proposed shared venue/layout/event envelope.

C1 current backend exposes /health, /contracts, /images, /analyses and versioned/review/layout operations documented in app/frontend/contracts/openapi-1.1.0.json. Companion has /event-projects and /layout-edits; Scene compiler /scene/compile-and-optimize is controlled. C1 Vite rewrites /api to backend, /companion to companion and passes /scene. C3 currently owns /api/state, /api/reset, /api/plan/mode, /api/plan/custom, /api/checkins, /api/my-tasks/{resource_id}, /api/people, /api/clock, /api/proposals/{id}/confirm or reject, /api/activities/{activity_id}/lock and demo routes. Combining their /api roots without a gateway causes collisions. Keep independent Python environments: C1 CPU PyTorch/pymoo is not C3 OR-Tools/SimPy/XGBoost dependency set.

## Proposed exchange and API namespace

The committed JSON schemas and illustrative examples under contracts/ are proposals only. No endpoint, converter, auth gateway or C1-to-C3 adapter implements them. Schema examples contain placeholder hashes and pending feasibility; they are not executable evidence or an approved layout.

Proposed future gateway namespaces: /api/component-1/v1 and /api/component-3/v1. Suggested exchanges are POST /api/component-1/v1/layout-requests, GET /api/component-1/v1/layouts/{id}, POST /api/component-1/v1/layouts/{id}/approval, POST /api/component-1/v1/layouts/{id}/repair and POST /api/component-3/v1/layout-handoffs. These endpoints do not exist today. Keep existing /health and native APIs separate during integration; an actual adapter must translate current field names and error formats explicitly.

Shared event_id is minted by the agreed owning group service; mapping to C3 generated internal IDs is mandatory. venue_id plus integer version identifies geometry; layout_id/version/sha256 plus venue_version identifies a layout. No component may guess compatibility from venue names. Event type may describe the full vision, but capability admission must refuse unsupported execution, not silently treat all events as Wedding.

All geometry uses metres and local x-right/y-down plan coordinates; source pixels require an explicit calibrated transform. Polygon rings must close, have positive area, avoid self-intersections and use the same origin/frame. JSON schema checks shape only: use geometric and semantic validators for containment/clearance and calibration. Wall/door/window class groups are not individual stock items. C1 room regions do not equal C3 activities.

Time converter: require offset-bearing ISO start, IANA timezone, shared UTC epoch, integer start_offset_minutes and duration_minutes. The example 10:00 Asia/Colombo is 04:30Z and offset 270 from midnight UTC. Reject conflicting dates/offsets, subminute rounding ambiguity and C3 HH:MM day rollover unless the adapter explicitly handles them. Keep C3 after-row positions mapped to stable activity IDs.

Resource converter: map object class and stable stock IDs to C3 roles using a team-reviewed mapping. Chairs in items are not persons, role count is not capacity, and movable geometry status is not operational availability. Aggregate quantities must agree with object inventory/demand; non-spatial staff/vendor resources remain C3-owned. A stock or time conflict must return an explicit incompatibility, not fabricate resources.

## Version, authority and change governance

Future approval states: draft, pending, approved, rejected, revoked, stale. Current local strings/check boxes and synthetic authority records are unauthenticated; authenticated=false in examples. A future gateway needs verified identities, role/permission checks, planner-approved lock ownership, per-request authorization, audit logs and replay/idempotency policy. Hashes show integrity, not measurement truth or identity.

Approved geometry/layout changes increment versions, invalidate old layout certificates and mark downstream schedules stale. Operational disruptions may request a C1 repair using the exact source/layout/constraint hashes, permitted groups, locks and minimal-relocation preferences. C1 rechecks feasibility and produces alternatives/explanations; C3 approval never implies C1 spatial approval. Define atomic acceptance/rollback and event ordering before connecting services. Never remove lock/authority/refusal checks for interoperability.

Proposed errors include SCHEMA_INVALID, UNSUPPORTED_CAPABILITY, STALE_VENUE_VERSION, STALE_LAYOUT, MISSING_AUTHORITY, INFEASIBLE and DEPENDENCY_UNAVAILABLE with request ID, component, retryable flag and details. Use 422 for invalid/unsupported requests, 409 for version conflicts, 401/403 for authenticated authorization failures, and 503 for unavailable dependencies. This is recommended behavior, not current status-code parity.

## Acceptance before claiming integration

Agree shared ownership with all four members; implement adapters; validate positive and negative schema/units/time/resource/permission/stale-version cases; run real C1 and C3 together with separate dependencies and gateway namespaces; confirm unchanged member routes and approval invariants. Actual C3 service execution, adapters, shared authentication and cross-component end-to-end transactions are NOT VERIFIED here.
