# FR13 edit and regenerate verification

## Actual browser interaction, 17 October 2026

The shared live browser submitted a controlled Corporate event in Belle Chasse LA (2026-11-26, 10:00–18:00, 50 guests, Entertainment + Catering, LKR 1,000,000, top 3). It returned USER-BECE05551069, 0 packages and the displayed NO_SERVICE_COVERAGE explanation. Edit event opened the existing four-step wizard with event type, date, time, location, guests, budget, services and top-K prepopulated.

Changing the location to Bensalem PA and pressing **Cancel edit** left USER-BECE05551069, its Belle Chasse location and its empty result intact. Reopening edit, changing only location to Bensalem PA and pressing **Save changes & regenerate** returned **USER-50DFA61AAC72**, displayed “Session revision 2 — Regenerated from USER-BECE05551069,” and showed three new request-time packages. Its first package was PKG-0001, LKR 677,662.86 with LKR 322,337.14 remaining and VERIFICATION_REQUIRED. The comparison selection count reset to 0.

Two Bensalem packages were selected for comparison; the page displayed the same USER-50DFA61AAC72 and the recorded vendor/option differences. Check feasibility for its PKG-0001 completed through the dynamic API with 11 simulation passes, 7 pending checks and 0 fails. Editing the budget to LKR 1 created **USER-404A88277917**, session revision 3, with 0 packages and BUDGET_INSUFFICIENT diagnostics. The comparison view then had zero selected packages and the new USER ID; feasibility showed “No generated package selected,” with no old USER ID.

A **mocked browser transport race test**, separate from real vendor/API evidence, delayed the first generated response by 2.5 seconds, canceled that edit, and fulfilled a second edit immediately. The displayed result stayed USER-RACE-SECOND at LKR 2,000 after the delayed USER-RACE-FIRST response arrived; the stale ID was absent. The mock route was removed and the browser reloaded afterward. Mock IDs and content must never be presented as real package results.

A separate **mocked browser error test** returned HTTP 503, displayed BACKEND_ERROR with a retryable wizard and kept the user on the form; HTTP 422 displayed INVALID_REQUEST instead. The mock route was removed and the browser reloaded afterward. These are UI-handling tests, not claims about live backend failures.

## Identity and persistence semantics

There is no stored editable event entity or account. This is a client-session revision: save makes a new backend USER request and displays a previous-USER link in React state. Cancel keeps the committed result. A full reload loses draft, result and lineage. No server-side event ID is mutated or persisted; the UI states this explicitly. A new USER ID proves a new request, not necessarily a different option combination for unchanged requirements.

Source: [App.jsx](../../frontend/src/App.jsx), [wizard](../../frontend/src/pages/EventWizard.jsx), [recommendations](../../frontend/src/pages/PackageViews.jsx), and [controlled API results](./demo_test_results.json).
A later genuine browser capture showed [USER-E7065DB671E3 with three Bensalem packages](./screenshots/regenerated_bensalem.png), session revision 2 of USER-644952399619. A separate new Belle Chasse request produced [USER-38A3ACADD4EF with zero packages](./screenshots/belle_chasse_no_match.png), followed by its [prefilled edit form](./screenshots/edit_event_prefilled.png). These captures are separate from the earlier interaction IDs above and were saved directly to this evidence directory.
