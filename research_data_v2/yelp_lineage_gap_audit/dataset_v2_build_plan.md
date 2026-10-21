# Proposed Dataset V2 build plan

**Approval gate:** This is a proposal. Do not execute the V2 build or change production until the audit findings are approved.

1. Freeze V1 source hashes, manifest, source code rules, and scenario definitions. Confirm the local Yelp agreement and the institution's interpretation before broader redistribution or public release.
2. Reconstruct a deterministic Yelp business selection and category-classification specification. Validate all 18,430 business-ID joins and the 235 documented ID repairs. Preserve raw categories, attributes, and matched rule terms. Review ambiguous classifications manually.
3. Stream the review JSONL and recompute counts, means, sample standard deviations, and latest dates for selected IDs. Compare with the existing verification table. Record source hash and formula version. Keep review text under controlled access.
4. After approval, stage new versioned tables with field-level evidence. Import traceable business fields and derived review features. Carry V1 options, capacities, prices, availability, and collaboration only in a clearly marked SYNTHETIC_TEST partition. Leave actual quotes, service areas, capacity, resources, and availability UNKNOWN until evidence exists.
5. Investigate coverage using the observed gaps. For Bensalem 500, test sensitivity to documented capacity/pricing assumptions and seek actual capacity/quote evidence. For Belle Chasse, validate Entertainment service classifications and documented service radius. Do not invent offers or broaden city matching without evidence.
6. Collect independent operational evidence where feasible: consented dated quotes, capacity confirmations, time-specific availability, shared resource assignments, venue constraints, and named vendor-pair event records. Define failures and adjudication before model training.
7. Evaluate V1 and V2 on frozen identical scenario inputs and a shared vendor/location cohort; report expanded coverage separately. Keep synthetic expected outcomes separate from real observed outcomes. Measure coverage, unknown/abstention rate, feasible-package rate under each model, ranking quality with independent labels, latency, and provenance completeness.
8. Gate any production integration after separate rights, data-quality, API, performance, and rollback review.

**Acceptance checks:** unique keys; zero broken FKs; source hashes recorded; every operational field has provenance; no synthetic value promoted to real; null/UNKNOWN retained; review aggregate tolerance specified; no source overwrite; evaluation labels independent of the generator. See [schema proposal](./dataset_v2_schema_proposal.md).
