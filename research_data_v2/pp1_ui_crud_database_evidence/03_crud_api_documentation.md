# 03 CRUD API documentation

Base URL: `http://127.0.0.1:8000`

## Endpoints

| Operation | Endpoint | Success |
|---|---|---|
| Create | `POST /api/events` | `201 Created` |
| Read list | `GET /api/events` | `200 OK` |
| Read one | `GET /api/events/{event_id}` | `200 OK`, `404` if absent |
| Update | `PUT /api/events/{event_id}` | `200 OK`, `404` if absent |
| Delete | `DELETE /api/events/{event_id}` | `204 No Content`, `404` if absent |
| Generate packages | `POST /api/packages/generate-dynamic` | Existing endpoint preserved; accepts optional persisted `event_id` |

## Request JSON

```json
{"event_type":"Wedding","event_date":"2026-12-15","start_time":"10:00","end_time":"18:00","city":"Philadelphia","state":"PA","guest_count":50,"budget_lkr":1000000,"top_k":2,"required_services":["Photography","Decoration"]}
```

## Create response shape

```json
{"event":{"event_id":"USER-<12 HEX>","event_type":"Wedding","event_date":"2026-12-15","start_time":"10:00:00","end_time":"18:00:00","city":"Philadelphia","state":"PA","guest_count":50,"budget_lkr":1000000.0,"top_k":2,"required_services":["Photography","Decoration"],"created_at":"...","updated_at":"..."},"storage":"sqlite"}
```

The frontend sends the returned `event_id` to the existing package-generation endpoint. The recommendation response keeps that same ID.
