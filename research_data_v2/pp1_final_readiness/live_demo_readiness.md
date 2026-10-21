# PP1 final live demo readiness — 2026-10-19

**Verdict: PASS for the research prototype demo, with two WARNINGs.** The exact Philadelphia Wedding request returned three packages through the live API and the React flow. No demo-blocking browser error was observed. Both services were already running; a cold restart was not tested.

| Check | Status | Evidence |
|---|---|---|
| FastAPI backend | PASS | Existing Uvicorn process on port 8000; GET /health returned HTTP 200 and healthy status. |
| React frontend | PASS | Existing Vite process on port 5173; GET / returned HTTP 200 with PlanoVision React. |
| Fresh process startup | WARNING | Both services were already running. This check confirms serving health, not a fresh cold launch from startup commands. |
| Exact saved request | PASS | Read from ../pp1_final_submission/pp1_demo_inputs_and_outputs.json: Wedding; 2026-11-16; 10:00–18:00; Philadelphia, PA; 50 guests; LKR 1,000,000; Photography and Decoration; top_k 3. See [request and timing](./api_run_metadata.json). |
| Live API | PASS | POST /api/packages/generate-dynamic returned HTTP 200, event USER-9491C5970F6D, and three packages under generation.packages. See [actual response](./api_response_raw.json). |
| Response time | WARNING | Direct HTTP request took **7,613.79 ms**, above the proposed five-second target. One measurement, not a latency distribution. |
| Search completeness | WARNING | Search status search_limit_reached; candidate limit reached, node limit not reached; 156 nodes and 138 combinations evaluated. Ranks apply to examined combinations only. |
| Browser event flow | PASS | Exact review inputs and Top-K 3 generated three cards with explanations and search-limit and synthetic-data notices. Browser event ID USER-133CA2161A83, from a separate live call. |
| Comparison | PASS | Two packages selected and compared at /#comparison, including costs, vendors, scores and evidence cautions. |
| Feasibility | PASS | /#feasibility for PKG-0001 showed VERIFICATION_REQUIRED: 10 simulated checks passed, 8 pending, 0 failed. |
| Vendor intelligence | PASS | /#admin-vendors listed returned vendors, model risk classes, and rule-derived/synthetic evidence. |
| Research pages | PASS | /#admin-model, /#admin-compatibility, and /#admin-conflicts loaded without a visible page error. |
| Saved Random Forest hash | PASS | SHA-256: 4EED156CFDF677B992B8C36350C21C968D7CB4D532A8AFD302CA1B697AEA3E6A; matches pinned digest in ../../backend/engine/risk_signals.py and live API audit. No retraining. |
| Sri Lankan pilot and research demo isolation | PASS | Backend points to hybrid_simulation_v1/real_vendor_profiles.csv, hybrid_simulation_v1/synthetic_service_options.csv, and saved model. No Sri Lankan pilot file references found under backend/ or frontend/. Conflict demo remains a separate /#admin-conflicts route. This is a code-reference check. |

## Actual direct API package results

Amounts are synthetic estimated LKR costs, not vendor quotations. Risk classes are Random Forest predictions of rule-derived review labels, not verified real-world reliability.

| Package | Estimated cost | Score | Vendors and predicted risk | Feasibility |
|---|---:|---:|---|---|
| PKG-0001 | LKR 305,535.41 | 84.7786 | Photography: Minibooths (FQ_QUyrwtnaEdxUxruZkXg), Low; Decoration: Petit Jardin En Ville (_t_UwNkwAinJSljDDYvnoQ), Low | VERIFICATION_REQUIRED; 8 pending |
| PKG-0002 | LKR 328,001.78 | 83.8799 | Photography: Minibooths (FQ_QUyrwtnaEdxUxruZkXg), Low; Decoration: Carl Alan Floral Designs LTD (P7MHW-EtCdp3eVF2P_nX0A), Low | VERIFICATION_REQUIRED; 8 pending |
| PKG-0003 | LKR 244,874.21 | 79.2050 | Photography: Minibooths (FQ_QUyrwtnaEdxUxruZkXg), Low; Decoration: Riehs Florist (zwl7iLwHBTdkb5-0gNgGFg), Medium | VERIFICATION_REQUIRED; 8 pending |

The API explains that each package covers both services with distinct vendors. The explanation reports estimated cost, remaining budget, ranking with effective cost/risk/category-compatibility weights 0.4/0.4/0.2, rule-derived risk favorability, and category compatibility of 85/100. Category compatibility is not vendor collaboration evidence. Each package asks for vendor capacity, date/time availability, setup/travel, collaboration, and venue confirmation. Exact explanations and verification steps are in [the response](./api_response_raw.json).

## PP1 demo sequence

1. http://127.0.0.1:5173/#create-event — review the exact Philadelphia input and set Top-K to **3** (initial browser value was 10).
2. http://127.0.0.1:5173/#recommendations — generate and show the three cards, explanations and bounded-search warning.
3. http://127.0.0.1:5173/#comparison — first select two packages on Recommendations.
4. http://127.0.0.1:5173/#feasibility — first use Check feasibility on a returned package.
5. http://127.0.0.1:5173/#admin-vendors — show current-request vendor evidence.
6. http://127.0.0.1:5173/#admin-model — show saved model evidence.
7. Optional isolated research views: http://127.0.0.1:5173/#admin-compatibility and http://127.0.0.1:5173/#admin-conflicts.

Recommendation, comparison, feasibility, and vendor evidence pages depend on current browser-session state. Opening them before generation correctly showed empty-state guidance. Ordinary automation clicks timed out on the hidden shared page; DOM-dispatched clicks advanced the form and completed generation. No application error was visible.

**Examiner disclosure:** Service options, service areas, prices, and availability are synthetic or unverified. Feasibility is a simulation, not a booking. Category compatibility is not historical collaboration, and risk classes do not establish real-world vendor reliability. The Sri Lankan OSM pilot does not feed this Philadelphia demo.


