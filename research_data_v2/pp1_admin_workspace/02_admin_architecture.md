# Admin Architecture

The workspace is a separate hash-routed area: `#admin`, `#admin/vendors`, `#admin/service-options`, `#admin/events`, `#admin/model` and `#admin/reports`.

`backend/api/admin.py` exposes read-only endpoints over existing sources. `frontend/src/pages/AdminWorkspace.jsx` provides the dashboard, tables, model evidence and report controls. Existing event CRUD remains in `backend/api/events.py` and the planner continues to use the same API.

Data boundaries are explicit: historical vendor profiles, synthetic service options, operational SQLite events and verified research evaluation metadata are labelled separately. Authentication and role-based authorization are not implemented; the route is not a security boundary.
