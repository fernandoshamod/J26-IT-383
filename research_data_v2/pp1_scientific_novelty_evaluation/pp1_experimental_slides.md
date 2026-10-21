# PP1-ready experimental results slides

## Slide A — Fair paired ranking comparison

**Question:** Does adding review-rule favorability and category score change packages compared with the cheapest eligible multi-vendor package?

- Eight fixed synthetic Wedding scenarios; identical validated package pool and constraints for both rankings.
- Top choice identical in **7/8**. In Belleville IL, the proposed choice cost **LKR 4,181.03 more** and increased review-rule favorability **20 points**.
- Mean paired differences: **+LKR 522.63** cost; **+2.5** review-rule points; medians **0** for both.
- Category compatibility was **85/100** for both on all eight because service categories were fixed.
- Budget and required-service coverage: **8/8 for both, enforced by construction**.

**Say:** “This shows one observed synthetic trade-off. It is not evidence of better real-world decisions.” [Evidence](./baseline_comparison.csv); [cost graph](./paired_cost_differences.svg).

## Slide B — Search quality

- Eight tractable two-service Cartesian spaces, **9–225** pairs each.
- Exhaustive feasible: **173**; bounded examined feasible: **170**.
- Candidate cap hit **5/8**; node cap **0/8**; **three** feasible packages missed.
- Best package matched exhaustive reference in **8/8**, best-score regret **0** within these cases.

**Say:** “The bounded search found the same best result here, but it omitted feasible alternatives; I do not claim global optimality for other events.” [Evidence](./search_quality_comparison.csv); [regret graph](./search_regret.svg).

## Slide C — Model and operational evidence limits

- Reconstructed 3,686-row holdout: saved Random Forest **100% accuracy and macro-F1** against rule-derived labels; exact rules-only baseline **also 100%**.
- Twelve **synthetic** conflict fixtures: 2 compatible within supplied checks, 6 conflicts, 4 verification required; 12/12 matched authored fixture labels.
- A fixed category score gave different operational statuses across fixtures, so category-only score does not establish vendor-pair readiness.
- **No real vendor reliability, availability or booking-feasibility claim.**

**Next evaluation:** Independent vendor outcomes, real operational evidence, Sri Lankan data, fair untruncated baselines and user testing of explanations. [Risk](./risk_model_baseline.json); [conflicts](./conflict_comparison.csv); [full report](./scientific_evaluation_report.md).

## Statistical note for examiner

Eight events were purposefully chosen and only one top choice differed. The reported bootstrap intervals in the [report](./scientific_evaluation_report.md) are descriptive resampling intervals, not population confidence intervals. No p-value or statistical-significance claim is made.
