# PP1 Admin Demo Steps

1. Start backend from the project root: `venv\Scripts\python.exe -m uvicorn backend.main:app --reload --port 8000`.
2. Start frontend: `cd frontend` then `npm run dev`.
3. Open `http://127.0.0.1:5173/#admin`.
4. Show Dashboard counts and the scope notice.
5. Open Vendor Management, search a vendor name, select a category and use Next/Previous.
6. Open Service Options and show the synthetic-data warning, category filter and LKR price column.
7. Open Event Management and show records persisted by the existing SQLite API.
8. Open AI Model Overview and explain that 100% test accuracy uses rule-derived labels and is not real-world validation.
9. Open Report Generator, select each report type, click Download PDF, and open the downloaded file. Use CSV only for the tabular vendor/event summaries.
10. Demonstrate persistence separately through the planner: create/update an event, refresh, reopen My Events, and inspect `backend/planovision.db` with `sqlite3 backend/planovision.db "select * from events;"`. Delete only a temporary test record after confirmation.

This is an academic administration demonstration, not a secured production admin portal.
