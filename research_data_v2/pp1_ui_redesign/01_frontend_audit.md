# 01 Frontend audit

Verified against the current source on 2026-10-21.

## Application structure

- [App.jsx](../../frontend/src/App.jsx) owns hash navigation, saved-event loading, event generation, comparison selection and feasibility state.
- [AppShell.jsx](../../frontend/src/components/AppShell.jsx) owns the persistent sidebar, top bar, responsive mobile drawer and footer.
- [UI.jsx](../../frontend/src/components/UI.jsx) provides shared Icon, Badge, StatusBadge, PageHeader, Kpi, EmptyState, Notice, Loading and ProgressBar components.
- Event-management pages are [EventWizard.jsx](../../frontend/src/pages/EventWizard.jsx), [SavedEvents.jsx](../../frontend/src/pages/SavedEvents.jsx), [PackageViews.jsx](../../frontend/src/pages/PackageViews.jsx) and [FeasibilityDashboard.jsx](../../frontend/src/pages/FeasibilityDashboard.jsx).
- Research/evaluation pages are [AdminPages.jsx](../../frontend/src/pages/AdminPages.jsx), [VendorConflictResearch.jsx](../../frontend/src/pages/VendorConflictResearch.jsx) and [PublicPages.jsx](../../frontend/src/pages/PublicPages.jsx) methodology content.
- API calls are centralized in [api.js](../../frontend/src/services/api.js).

## Classification

| Area | Classification | Finding |
|---|---|---|
| Dashboard | Essential and functional | Redesigned to show actual SQLite event counts, upcoming saved events and current request state. |
| Create Event | Essential and functional | Existing four-step validation and save/generate flow preserved; visual hierarchy improved. |
| My Events | Essential and functional | Existing backend CRUD integration preserved and restyled. |
| Recommendations | Essential and functional | Existing package generation, comparison selection and research warnings preserved. |
| Compare Packages | Essential and functional | Existing comparison route and data remain accessible. |
| Feasibility | Essential and functional | Existing simulation/verification boundary remains explicit. |
| Research routes | Research/evaluation content | Grouped under Research & Evaluation, away from the primary event journey. |
| Landing marketing page | Redundant for primary journey | Preserved in source as `Landing`, but the default `home` route now opens the functional Dashboard. |
| `user-dashboard` route | Compatibility route | Preserved for old hashes and renders the same dashboard component. |
| UI components | Shared and used | All shared UI exports remain available; no component was deleted without reference analysis. |
| localStorage/mock event data | Not used | Event data continues to load from the backend SQLite API. |

No backend endpoints, model artifacts, datasets, research evidence or recommendation algorithms were removed or changed.
