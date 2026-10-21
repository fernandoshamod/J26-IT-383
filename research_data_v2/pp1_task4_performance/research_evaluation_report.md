# Research evaluation evidence and claim boundaries

## Implemented production path
Every tested request generated a new USER event from current synthetic option records. The generator selected eligible services, searched bounded combinations, validated budget and simulation feasibility, ranked using fixed cost/rule-risk/category-compatibility weights, and produced explanations. Costs are estimated LKR values from synthetic USD option assumptions. Candidate truncation means results are not globally exhaustive.

## Existing research evaluation
`../../research_evaluation/run_evaluation.py` and `metrics.py` rerank the **same evaluated package pool** by cost for the baseline. That isolates ranking within the selected pool but is **not** the proposal's Criteria-Based Individual Vendor Selection baseline. The production candidate selector already reserves risk-favored options. The existing 35-scenario historical evaluation remains unchanged; its figures are not new live measurements. The signed proposal PDF was not available in the Task 1 audit, so exact FR1–FR13 and performance targets cannot be authenticated.

## Model and compatibility
Random Forest labels reproduce rule-derived review-feature classes. Classification performance on those labels cannot establish real-world vendor failure prediction or recommendation accuracy. The current rule-risk score is a favorability score: higher is more favorable, not more dangerous. The 15 compatibility rules are service-category heuristics. For packages with the same service categories, compatibility can be constant; they do not prove two named vendors collaborated.

## Standalone conflict and shadow evidence
Task 2 reported 12/12 correct three-way statuses on controlled, independently labeled SYNTHETIC_TEST fixtures; its binary conflict precision/recall/F1 were 1.0 on eight known fixture cases. Those values are implementation checks, not field accuracy. Task 3 assessed six fresh USER packages: zero evidence-supported conflicts, six pending assessments, zero source-ID mapping failures. Missing vendor-pair, availability, schedule and resource evidence preclude a verified real-world conclusion.

## Task 4 findings
The measured local warm path spent roughly 1.3–1.7 s loading source options, 0.9–1.5 s selecting candidates, and 1.3–1.8 s in the risk stage. The request-local selector prototype reduced median full-path time for two multi-service scenarios but not reliably for the one-service case. All tested packages and search metadata stayed identical. Results are in `profile_results.json`, `benchmark_comparison.csv`, and `performance_report.md`.

## Remaining evidence
Real-world vendor availability, collaboration, price quotations, operational incidents, venue integration, independent risk outcomes, recommendation ground truth, participant usability/SUS data, and a true individual-vendor baseline are absent or unverified. Do not infer success on those topics from simulation passes or rule-label classification.