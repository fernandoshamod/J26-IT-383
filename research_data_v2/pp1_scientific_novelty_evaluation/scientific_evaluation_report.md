# Scientific baseline evaluation — PP1

Run date: **2026-10-19**. This is an isolated, reproducible experiment on existing synthetic service options and review-derived risk data. The script, outputs and charts are in this folder. Input hashes were recorded before and checked after execution in [summary.json](./summary.json); no production code, dataset, frontend or saved model was changed or retrained. The first script run stopped on an evaluation-only missing budget field; the corrected run completed and generated every result below.

## Design and reproducibility

- **Eight fixed, purposively selected scenarios:** Blackwood NJ, Alton IL, Abington PA, Goleta CA, Belleville IL, Brandon FL, Lansdale PA and West Chester PA. All are Wedding, 2026-11-16, 10:00–18:00, 50 guests, LKR 1,000,000, Photography + Decoration, Top-K 3. These are not a random sample of events or of the Sri Lankan market.
- **Fixed seed:** 42 for the reconstructed model split and 10,000 descriptive bootstrap resamples. Scenario selection and package search are deterministic. The script aborts if default candidate cap 12, node cap 5,000 or ranking weights 0.4/0.4/0.2 differ.
- **Ranking comparison:** The existing generator is run once per event. Its validated complete packages are captured in memory. Cheapest-first and production multi-criterion ranking sort **that exact same examined pool**, with the same feasibility priority and Top-K. The captured multi-criterion ranking is asserted to reproduce production option IDs. Because production candidate selection reserves risk-score slots, this is a **conditional cost-only baseline**, not a neutral full-universe cost baseline.
- **Search reference:** A separate itertools Cartesian enumeration covers **all priceable candidates** for the same eight two-service events, then applies the same distinct-vendor, budget and production feasibility rules. It uses the production factor calculation to compare scores, avoiding a changed objective. All full Cartesian spaces were 9–225 pairs and tractable. Thus “exhaustive” applies to these eight observed input pools only.
- **Timings:** Local in-process timings. Ranking timers exclude candidate loading/search; bounded-search timer includes capture and package explanation, while exhaustive timer omits those. Their absolute times are therefore **not a fair speed comparison** or HTTP latency. The first scenario was not separately warmed; repeat timing trials are needed.
- **Sources:** [script](./run_evaluation.py), [paired ranking rows](./baseline_comparison.csv), [search rows](./search_quality_comparison.csv), [risk comparison](./risk_model_baseline.json), [conflict rows](./conflict_comparison.csv).

Reproduce from the project root with the configured environment:

    & 'D:/Vendor-Intelligence-System/venv/Scripts/python.exe' -B research_data_v2/pp1_scientific_novelty_evaluation/run_evaluation.py

The script rewrites only outputs in this folder. Deterministic package IDs and scores should repeat; measured timings will vary.

## Experiment 1 — package ranking

| Metric | Cheapest eligible | Existing multi-criterion | Interpretation |
|---|---:|---:|---|
| Scenarios with a top package | 8/8 | 8/8 | Paired within each event. |
| Mean top-package estimated cost | LKR 527,572.36 | LKR 528,094.99 | Proposed minus cheapest: **+LKR 522.63** mean, median 0; only Belleville differed, by +LKR 4,181.03. |
| Mean top-package review-rule favorability | 55.0/100 | 57.5/100 | Paired mean **+2.5 points**, median 0; only Belleville improved, by +20 points. This is not real vendor reliability. |
| Mean category compatibility | 85/100 | 85/100 | Same two requested categories in every case, so category score cannot distinguish package choices. |
| Budget and required-service coverage | 8/8 each | 8/8 each | **Enforced by construction** of the common validated package pool; not independent quality evidence. |
| Mean distinct-vendor/slot ratio across displayed Top-3 | 0.5833 | 0.5625 | This diversity definition counts unique vendor IDs across each Top-3 list divided by all vendor slots. It is descriptive; distinct vendors inside each package are enforced. |
| Same top package | — | **7/8** | The remaining event is Belleville IL. |
| Mean ranking-only time | 0.028 ms | 0.777 ms | Tiny single-run local sort timers; no meaningful latency claim. |

The descriptive, event-resampled 95% bootstrap interval for **mean paired cost difference** was [LKR 0, LKR 1,567.89]; for **mean paired risk-rule difference**, [0, 7.5] points. These intervals characterize sensitivity of this purposive eight-event set to resampling; they are **not population confidence intervals**. No significance test is claimed because events were deliberately selected, only one choice changed, and there are no independently sampled user outcomes. The proposed weighted score is not used as sole proof of superiority. See [cost chart](./paired_cost_differences.svg).

## Experiment 2 — bounded search against exhaustive reference

| Metric | Measured result |
|---|---:|
| Scenarios | 8 |
| Candidate cap reached | 5/8 |
| Node cap reached | 0/8 |
| Feasible combinations in exhaustive reference | 173 |
| Feasible combinations examined by bounded DFS | 170 |
| Missed feasible combinations | **3**, all in West Chester PA |
| Best-score regret, mean/median | **0.0000 / 0.0000 points** |
| Bounded and exhaustive best option IDs | Matched in 8/8 observed cases |

The three missed feasible combinations show why a truncated search cannot be called exhaustive even when its best observed score matches the exhaustive reference. These cases do **not** prove zero regret for larger or different events. The bounded timing mean/median was 20.80/13.30 ms; exhaustive mean/median was 3.99/3.94 ms, but different instrumentation and first-run effects prohibit a speed conclusion. See [search chart](./search_regret.svg) and [per-event rows](./search_quality_comparison.csv).

## Experiment 3 — risk-model target validity

The saved Random Forest and a direct reconstruction of its deterministic label rule were both evaluated on the same 3,686-row stratified 20% split (seed 42). **Both achieved accuracy 1.000 and macro-F1 1.000 against the rule-derived labels; model-versus-rule disagreements: 0.** The model was only loaded, never fitted or overwritten. This establishes faithful rule imitation for the reconstructed holdout and no observed advantage over rules-only classification on this target. It says **nothing** about real booking failure, current vendor reliability, calibration or geographic transfer. See [risk JSON](./risk_model_baseline.json) and [existing model audit](../../research_evaluation/model_audit.py).

## Experiment 4 — category score versus operational fixture evidence

The 12 **SYNTHETIC TEST** cases yielded 2 COMPATIBLE_WITH_EVIDENCE, 6 CONFLICT_WITH_EVIDENCE and 4 VERIFICATION_REQUIRED results. Engine statuses matched the fixture-authored expected statuses in **12/12** cases. Two same-category-score groups contained multiple different operational statuses: Photography+Decoration scored 85 and Photography+Photography scored 30 within their respective groups. This demonstrates that a category-only score cannot distinguish the fixture outcomes, whereas supplied synthetic pair/time/resource evidence can. Fixture-label agreement is software consistency, **not** accuracy on real vendor operations. UNKNOWN remains VERIFICATION_REQUIRED. See [case rows](./conflict_comparison.csv).

## Scientific interpretation

**Supported:** The prototype can generate and compare eligible packages; the proposed ranker trades a little simulated cost for higher review-rule favorability in one of eight cases; candidate truncation can omit feasible combinations; the saved model imitates its rules-only target; synthetic operational evidence distinguishes statuses that category score alone cannot.

**Not supported:** superiority over cost-only for real users; calibrated vendor reliability; globally optimal bounded search; valid live availability or collaboration; statistical significance; or transfer to Sri Lankan vendors. Data provenance and bounded-search limitations are central to the PP1 claim.
