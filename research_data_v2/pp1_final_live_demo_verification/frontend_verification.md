# Frontend verification

Live browser: `http://127.0.0.1:5173/`, 18 October 2026. Browser event IDs differ from the separate direct API request because each generation creates a new USER event. Screenshots were captured in this run.

| Check | Result | Observation |
|---|---|---|
| Event creation | PASS | Wizard accepted exact saved event fields, including `top_k=3`, and displayed them on Review & generate. |
| Package generation | PASS | Browser event `USER-C11D90621A2B` returned three packages and `search limit reached`. [Screenshot](./recommendations.png). |
| Vendor intelligence | PASS | Current-session table displayed four selected vendors and model classes Low, Low, Low, Medium. [Screenshot](./vendor_intelligence.png). |
| Package comparison | PASS | Selected PKG-0001 and PKG-0002; comparison showed costs, vendor difference, scores and eight pending checks each. [Screenshot](./comparison.png). |
| Explanations | PASS | Recommendation cards displayed “Why this package?”, coverage, cost, score and pending checks. Research-detail expansion was NOT_VERIFIED. |
| Feasibility details | PASS | Dedicated check displayed `VERIFICATION_REQUIRED`, 10 passed, 8 pending, 0 failed, and named capacity, availability, scheduling, collaboration and venue checks. [Screenshot](./feasibility.png). |
| Edit Event and Regenerate | PASS | Edited budget from LKR 1,000,000 to LKR 900,000. New event `USER-53E03F4163C6` showed Session revision 2, three packages and recalculated remaining budget and scores. [Screenshot](./regenerated.png). |
| No-match recovery | PASS | Separate LKR 1 budget test produced event `USER-24CE82B169CD`, zero packages, minimum observed cost LKR 244,874.21 and Edit event guidance. Edited back to LKR 1,000,000; new event `USER-FD9EDC4C4C5F` returned three packages. [Screenshot](./no_match.png). |

The no-match budget is a **separate recovery test**, not a substitution for the saved demo request. No application error was observed. One browser automation click timed out because the sidebar was outside the viewport; opening the menu resolved it. Browser requests were not individually timed. The direct HTTP timing is in [API evidence](./api_response_evidence.json).
