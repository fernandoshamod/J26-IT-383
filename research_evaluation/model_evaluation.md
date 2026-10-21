# Random Forest artifact evaluation

The original notebook specifies `train_test_split(test_size=0.20, random_state=42, stratify=y)` on `data/cleaned/vendor_profiles_missingness_checked.csv`. The checked source and current profile rows match exactly on IDs, five features and labels, in the same order. The saved artifact contains the same feature order, class labels and rule-derived target metadata. This is a **reconstruction of the notebook holdout**, not an independent real-world test. Original held-out row IDs were not stored separately, so the split identity rests on the notebook recipe and unchanged ordered input.

Training rows: 14744; reconstructed test rows: 3686. Features: ['stars', 'review_count', 'collected_review_count', 'mean_review_rating', 'rating_std']. Model SHA-256: `4eed156cfdf677b992b8c36350c21c968d7cb4d532a8afd302ca1b697aea3e6a`.

| Metric | Value |
|---|---:|
| Accuracy | 1.0000 |
| Macro precision | 1.0000 |
| Macro recall | 1.0000 |
| Macro F1 | 1.0000 |
| Weighted F1 | 1.0000 |

| Class | Support | Precision | Recall | F1 |
|---|---:|---:|---:|---:|
| High | 576 | 1.0000 | 1.0000 | 1.0000 |
| Low | 408 | 1.0000 | 1.0000 | 1.0000 |
| Medium | 2702 | 1.0000 | 1.0000 | 1.0000 |

Confusion matrix, rows=true and columns=predicted, order ['High', 'Low', 'Medium']:

| True / predicted | High | Low | Medium |
|---|---:|---:|---:|
| High | 576 | 0 | 0 |
| Low | 0 | 408 | 0 |
| Medium | 0 | 0 | 2702 |

**Interpretation:** Risk labels were deterministic rules derived from related review features. A perfect score can indicate learning those rules, label leakage or circular evaluation. It does not establish ability to predict verified real-world vendor failures. The vendor risk CSV also has known ID anomalies; production inference joins to unique profile IDs. No retraining was performed.
