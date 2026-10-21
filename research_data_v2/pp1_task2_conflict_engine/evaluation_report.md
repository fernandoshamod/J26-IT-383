# Controlled synthetic evaluation results

This report transcribes the executed [evaluation_results.json](./evaluation_results.json), generated on 2026-10-17 by [evaluate.py](./evaluate.py) using the 12 independently labeled [fixture cases](./fixtures.json). It is **SYNTHETIC_TEST** evaluation only.

| Measure | Executed result |
|---|---:|
| Cases | 12 |
| Exact three-way statuses | 12/12 |
| Known binary cases | 8 |
| Expected pending cases | 4 |
| Correctly identified conflicts (TP) | 6 |
| Missed conflicts (FN) | 0 |
| False conflict warnings on known compatible cases (FP) | 0 |
| Correct non-conflicts (TN) | 2 |
| Predicted pending | 4 |
| Conflict precision | 1.000 |
| Conflict recall | 1.000 |
| Conflict F1 | 1.000 |
| Total in-process case execution | 2.232 ms |
| Mean per case | 0.186 ms |
| Median per case | 0.17905 ms |

**Definitions:** A conflict is the positive class. Precision = TP/(TP+FP) = 6/6. Recall = TP/(TP+FN) = 6/6. F1 = 2PR/(P+R) = 1. Pending fixture cases have no binary conflict ground truth and are excluded from the binary denominator; their three-way status is evaluated separately. If a metric denominator were zero, the script would emit JSON null, not zero. A false conflict warning is a predicted conflict on one of the two known compatible cases. These values measure deterministic implementation agreement with hand-authored cases, **not** real-world prediction quality.

Timing uses `perf_counter_ns` around each in-process engine call on this local test environment. It excludes fixture loading, API routing, network, model inference, browser rendering and startup. A separate run will have different timings.
