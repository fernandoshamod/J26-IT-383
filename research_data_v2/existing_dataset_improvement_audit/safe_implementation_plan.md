# Safe implementation plan — proposal only

**Status:** audit complete; no implementation authorized. PP1 is 2026-10-22. Keep the active datasets, backend, model and verified backups frozen through the demo.

## Gate 0: preserve the current baseline

1. Keep the verified PP1 backup untouched. Record SHA-256 of the active model, synthetic option file, vendor profile file, compatibility matrix and backend files before any later experiment.
2. Copy only the proposed input datasets into a separate experiment directory after approval. Every derived row must retain a source ID, provenance label, generation version and is_vendor_confirmed=false unless independently verified.
3. Keep the exact saved Philadelphia request and 22 varied requests in [package_generation_test_results.csv](./package_generation_test_results.csv) as baseline cases. Record present candidate counts, package counts, statuses, selected option IDs, ranking order, warnings and response times.

## Gate 1: low-risk cleaning and lineage, after PP1

1. Create a city/state canonicalization map from the 38 observed variant groups. Preserve all 57,549 option IDs and vendor IDs. Confirm the same normalized keys and candidate counts before/after. The expected gain is cleaner displayed locations, **not** more packages.
2. Document the 31 historical duplicate-ID rows in the raw repaired vendor file; confirm the active profile remains 18,430 unique IDs and every active option resolves to exactly one profile. Do not rewrite active business IDs.
3. Validate the five model columns and enforced model hash. An option-only edit must not touch real_vendor_profiles.csv or the Random Forest artifact.

## Gate 2: explicitly synthetic coverage experiment, only with separate approval

1. Choose target category/location gaps from [location_coverage.csv](./location_coverage.csv), starting with Audio Visual and Entertainment. Review original Yelp category evidence for each candidate vendor. Treat that evidence as a lead, not verified service availability.
2. Define a documented simulator rule and a new generation version for any additional option rows. Do not duplicate IDs, copy options between locations without a declared service-area rule, or fabricate verified prices/availability.
3. Measure sensitivity by category, location, budget and guest count. Keep the original frozen baseline side by side. Stop if the synthetic expansion is presented as real market evidence.

## Regression and acceptance gate

- All seven backend input schemas and referential checks pass; option IDs are unique, profile IDs unique, and every option vendor ID joins.
- The saved model hash, five feature names, rule-derived label disclosure and prediction code remain unchanged. If profiles/features/labels change, request a separate model review and possible retraining decision.
- The exact Philadelphia event still returns valid packages under the same constraints. Record any changes in package IDs, vendor IDs, ranks, score components, feasibility and search-limit flags; do not assume identical results after adding option rows.
- Arabi's unchanged baseline remains a truthful no-match. If a proposed experimental dataset produces a package, prove each added option's simulation provenance and capacity/budget validity.
- Repeat all 23 scenarios and the focused backend tests; check frontend display and runtime. Investigate any HTTP error, missing diagnostic, duplicated vendor within a package, or invalid price.
- Candidate cap, node cap, compatibility rules, feasibility rules, ranking weights and response fields remain unchanged unless separately approved.
- Review results with the project owner. Publish a new dataset version only after acceptance. Retain the frozen PP1 inputs for reproducibility and rollback.

## Presentation decision

For PP1, retain the working demo and disclose synthetic prices, unverified offerings/availability, bounded search and variable latency. Use this audit as evidence of a measured post-PP1 improvement path. Do not use a new dataset or a production data patch before approval.