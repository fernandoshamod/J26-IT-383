# 05 PP1 live demo steps

1. Start the backend: `cd D:\Vendor-Intelligence-System; & .\venv\Scripts\python.exe -m uvicorn backend.main:app --host 127.0.0.1 --port 8000`.
2. Start the frontend: `cd frontend; npm run dev`.
3. Open the Vite URL shown in the terminal, choose **Create Event**, complete the four steps and submit.
4. The frontend first calls `POST /api/events`; note the returned `USER-*` ID in DevTools Network.
5. It then calls `POST /api/packages/generate-dynamic` with the same `event_id`; open Recommendations and show the returned packages.
6. Open **My Events**. The saved event is loaded by `GET /api/events`, not localStorage.
7. Expand **Technical details** to show the ID and timestamp.
8. Choose **Edit**, change guest count or budget, submit, and show the `PUT /api/events/{id}` response and changed card.
9. Refresh the browser; My Events should still show the record.
10. Stop and restart the backend, refresh My Events, and show that the record remains.
11. For a test record only, choose **Delete**, accept the confirmation, and show `204 No Content`; verify it is absent from My Events and `select * from events`.
12. Keep the research demo pages read-only. State that recommendation data and vendor availability are request-time/synthetic, not persisted or real-world verified.
