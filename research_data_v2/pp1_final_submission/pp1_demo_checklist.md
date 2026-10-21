# Short live demo checklist

## Setup and exact rehearsal event

- [ ] Start the existing FastAPI app and Vite frontend using the project virtual environment and project scripts; verify `/health` and the UI. [Startup guide](../pp1_task5_demo_readiness/system_discovery.md). This pack used an **in-process TestClient**, so presentation-day server and browser startup still require a smoke check.
- [ ] Open **Create Event**. Enter: Wedding; **2026-11-16**; **10:00–18:00**; Philadelphia, PA; **50 guests**; **Photography + Decoration**; **LKR 1,000,000**; **top 3**. The date is future as of 22 October 2026.
- [ ] State that the option prices, capacities, and service-area eligibility are simulations, not vendor quotations or confirmations.

## Three-minute route

1. **Event creation (0:00–0:35).** Submit the exact inputs. Record the new USER ID; it changes per request. Show the [Create Event capture](../pp1_task6_presentation/screenshots/create_event.png) only if the live UI is unavailable.
2. **Dynamic generation (0:35–1:20).** Expect three packages for the checked inputs, but read the *actual* response before asserting success. The focused in-process check returned HTTP 200, `USER-F5F13B227736`, `search_limit_reached`, 3 packages, and 138 examined combinations. Candidate selection was capped at 12 per service; node cap was not hit. Show rank, cost, remaining budget and selected services. [Exact current check](./pp1_demo_inputs_and_outputs.json).
3. **Model prediction (1:20–1:50).** Open a package's research details and the Vendor Intelligence table. Point to a named vendor's Low/Medium/High **model class** and separately to its **rule-derived favorability**. The checked top package had two Low model classes. Say that the class predicts the review rule, not a measured failure outcome. [Model integration](../pp1_final_model_verification/model_integration_trace.md).
4. **Compare (1:50–2:20).** Compare PKG-0001 and PKG-0002 from the *same* request. The checked costs were LKR **305,535.41** and **328,001.78**, with different second option IDs. Explain that the score ranks an examined bounded pool. [Comparison capture](../pp1_task6_presentation/screenshots/comparison.png).
5. **Feasibility (2:20–2:50).** Rerun the top package's **Check feasibility** action. The focused route returned HTTP 200, `VERIFICATION_REQUIRED`, **10 passed in simulation, 8 pending, 0 failed**. Identify pending availability, scheduling, capacity, collaboration and venue checks. [Feasibility capture](../pp1_task6_presentation/screenshots/feasibility.png).
6. **Close (2:50–3:00).** State the scope: one working model, dynamic integration, and simulated package recommendations with unverified real-world suitability.

## Backup and stop rules

- If live submission fails, show only dated existing captures and [previous live HTTP results](../pp1_task5_demo_readiness/demo_execution_results.json); label them as earlier evidence. Do not present saved historical packages as a fresh USER result.
- If the event date is no longer future, choose a later date and **record the changed inputs and observed response** before claiming an exact output.
- If the candidate pool, prices or rankings change, read the new values from the response. Do not promise the same USER ID, ranking or vendor names.
- Avoid using Trader Joe's under Decoration or matt-hair under Photography as validated service examples; those visible category assignments need manual review. [Model audit limitation](../pp1_final_model_verification/limitations.md).
