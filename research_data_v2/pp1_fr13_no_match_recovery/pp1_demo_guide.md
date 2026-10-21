# PP1 browser demonstration

Start the backend with the project venv: from the project root run .\venv\Scripts\python.exe -m uvicorn backend.main:app --host 127.0.0.1 --port 8000. Start the frontend from frontend with npm run dev. Reuse existing processes if the ports already respond. Check GET /health and open http://127.0.0.1:5173/#create-event. These startup commands were not freshly executed in this task.

1. **Positive flow:** Wedding, Philadelphia PA, future date 2026-11-26, 10:00–18:00, 50 guests, Photography + Decoration, LKR 1,000,000, top 3. The controlled API run returned HTTP 200, 3 packages, candidate counts 165/237 and visible truncation. Do not promise identical USER IDs or timing on stage.
2. **Second positive flow:** Corporate, Philadelphia PA, same future date/time, 40 guests, Photography + Audio Visual, LKR 1,000,000, top 3. Controlled API returned HTTP 200, 3 packages, candidate counts 165/3.
3. **Show the gap:** Corporate, Belle Chasse LA, same date/time, 50 guests, Entertainment + Catering, LKR 1,000,000, top 3. Expect zero packages. Read the source count: 27 location rows, no Entertainment; do not call this a compatibility conflict or budget issue.
4. **FR13 recovery:** choose **Edit event**. Show the prefilled wizard. Change only location to Bensalem PA; save and regenerate. A controlled browser run returned a linked new USER ID and 3 packages. Explain that suggestions identify priceable category coverage but do not guarantee a package.
5. Select two packages, inspect comparison and one dynamic feasibility result. Emphasize simulation passes and pending real-world checks.
6. **Boundary:** edit the current request budget to LKR 1, save and regenerate; show the lower-bound budget diagnosis and absence of stale comparison/feasibility.
7. **Invalid input:** zero budget is rejected by the form/API; controlled API returned HTTP 422.

Do not show Task 2–4 standalone conflict/optimization work as active production features. If the live backend is unavailable, show the [executed JSON evidence](./demo_test_results.json) and state clearly that no live result was obtained. For all slides, synthetic prices are not quotations, rule-derived risk is not real-world failure prediction, and category compatibility is not proven vendor collaboration.