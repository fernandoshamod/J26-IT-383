# V1 data lineage and provenance

## Source and joins

1. Original Yelp business JSONL: `D:\Yelp-JSON (1)\Yelp JSON\yelp_dataset\yelp_academic_dataset_business.json` (150,346 business rows). All 18,430 unique IDs in [real_vendor_profiles.csv](../../hybrid_simulation_v1/real_vendor_profiles.csv) join to an original business_id. Direct fields checked: name, city/state, latitude/longitude, stars, review_count, is_open, categories, attributes, hours. Exact direct-field comparison is summarized in [audit_summary.md](./audit_summary.md).
2. Original Yelp review JSONL: `D:\Yelp-JSON (1)\Yelp JSON\yelp_dataset\yelp_academic_dataset_review.json` (6,990,280 review rows). The selected profiles carry collected_review_count, mean_review_rating, rating_std, latest_review_date, and has_review_data. [review_summary_verification.csv](../../review_summary_verification.csv) reports 18,430 matching summary checks and 2,141,120 review records across selected businesses. The audit independently streams the source for two business IDs; a full independent group-by over all selected IDs was not performed.
3. [vendor_recommendation_dataset_ids_checked.csv](../../vendor_recommendation_dataset_ids_checked.csv) is the declared input in [dataset_manifest.json](../../hybrid_simulation_v1/dataset_manifest.json). The manifest's source SHA-256 is compared in [source_integrity_report.md](./source_integrity_report.md). [build_hybrid_dataset.py](../../build_hybrid_dataset.py) copies that table to the 18,430-row profile table, expands each semicolon-separated service category to a vendor-service pair, and creates three Basic/Standard/Premium options per pair. 57,549 options imply 19,183 vendor-service pairs; 684 vendors have more than one service.
4. [hybrid_vendor_service_dataset.csv](../../hybrid_simulation_v1/hybrid_vendor_service_dataset.csv) is a many-to-one flattening of synthetic options with prefixed profile fields. It is not an independent source. The [field provenance table](../../hybrid_simulation_v1/field_provenance.csv) distinguishes derived scores and synthetic option fields, but its generic label for profile fields is weaker than a row-level source citation.

## Field-level status

| Fields | Observed rule/source | Class | Caveat |
|---|---|---|---|
| business_id, name, city/state, categories, stars, review_count, is_open, attributes, hours | Direct match to original Yelp business record for all selected IDs under compared representation | REAL_PUBLIC | Historical public listing, not a current event-service assertion |
| latitude/longitude | Yelp coordinates copied into CSV with decimal precision reduction | DERIVED from REAL_PUBLIC | 4,618/4,588 exact float mismatches; max errors < 5e-8 degrees |
| caters, price_range | Apparent extraction from Yelp attributes | DERIVED | Field extraction rule not found; Yelp price range is not an event quote |
| service_categories, matched_categories | Classification from source categories/attributes in preexisting profile | DERIVED / partly UNKNOWN | No complete original selection/classification script located; profile label alone does not confirm an offered event service |
| collected_review_count, mean_review_rating, rating_std, latest_review_date, has_review_data | Aggregates/flags linked by business_id to Yelp reviews | DERIVED | Existing verification table covers all selected IDs; independent raw-stream spot check covers two |
| risk_level, risk_score, rating_score, review_score, stability_score, vendor_score, vendor_rank | Review-rule labels and ranking; notebook gives Low=100, Medium=60, High=20; vendor_score = 0.4 rating + 0.3 normalized review count + 0.2 risk score + 0.1 stability | DERIVED | No observed service failure labels; score is not real operational risk |
| option ID/tier, supported_event_types, price/basis, min billable guests/hours, max_guests, city/state, setup space/power/time, backup, features | Seed-42 generator and illustrative USD assumptions in [build_hybrid_dataset.py](../../build_hybrid_dataset.py) | SYNTHETIC_TEST | Not vendor confirmed; simulated city/state copy does not prove service radius |
| USD_TO_LKR=330.777 and estimated event cost | [loader](../../backend/engine/package_data_loader.py) and [validator](../../backend/engine/validation_helpers.py) | DERIVED from SYNTHETIC_TEST | Rate is hardcoded with date 2026-10-13; no actual quote |
| event templates, availability, collaboration labels | Seed-42 generator | SYNTHETIC_TEST | Historical SIMEVT only; random pair conflicts are not collaboration history |

The ID repair audit records 235 initially corrupted `#NAME?` IDs, of which 204 were repaired by name/city/state and 31 ambiguous rows used coordinate matching. Current profile IDs all resolve to the original business source, but the repair evidence is itself an important lineage step. No unmatched option-to-profile IDs, duplicate current profile IDs, or duplicate option IDs were found. The legacy [vendor_risk_dataset.csv](../../vendor_risk_dataset.csv) has known duplicate/unmatched IDs according to the earlier PP1 audit and should not be treated as a clean lineage base.

## Unverified provenance

The exact original selection logic that chose the 18,430 businesses and assigned all seven service labels was not found in executable source. The extracted `caters` and `price_range` transformation rules were not recovered. The [notebook](../../notebooks/01_vendor_dataset_audit.ipynb) starts with already cleaned CSVs for much of this path; it verifies downstream scoring but is not a complete raw-source ETL specification. Review summaries are supported by a separate verification CSV, yet that CSV has no source hash embedded in each row. V2 should preserve a source-file hash, extraction code version, transformation version, and source business/review IDs for every derived record.



## Independent raw-review spot check

A bounded-memory pass over the original review JSONL rechecked two selected IDs: `GXFMD0Z4jEVZBCsbPf4CTQ` has 6,160 reviews, mean 4.4462662337662335, and latest timestamp 2022-01-18 17:25:09; `_ab50qdWOk0DdB6XOrBitw` has 7,673 reviews, mean 4.124983709109865, and latest timestamp 2022-01-17 08:54:49. Both counts and means match the profile/verification table to recorded precision. Their recorded standard deviations (0.864990272 and 1.067772563) use **sample** standard deviation (ddof=1); the stream spot check's population deviations were 0.8649200589 and 1.0677029807. The profile latest timestamps are truncated to minutes. This verifies two examples, not all 18,430 raw-review aggregates independently.

