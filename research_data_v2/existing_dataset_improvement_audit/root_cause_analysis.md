# Existing dataset audit: measured root causes

Checked 2026-10-18. This is a read-only audit of production inputs. Scripts in this folder read CSVs in chunks of at most 10,000 rows; the inventory counts CSV records with a streaming reader. Live requests used POST /api/packages/generate-dynamic against the running FastAPI server, sequentially. The exact saved Philadelphia request was sent first, unchanged.

## What the backend actually reads

The dynamic route reads synthetic_service_options.csv, real_vendor_profiles.csv, models/vendor_risk_random_forest.pkl, and vendor_compatibility_matrix.csv. The separate sample-event route also reads synthetic_event_requirements.csv; feasibility reads synthetic_availability.csv and synthetic_collaboration_scenarios.csv. Full schemas, byte sizes, and row counts are in [dataset_inventory.csv](./dataset_inventory.csv). The audit found 111 CSV/JSON files under hybrid_simulation_v1/, research_data_v2/, data/, and dataset/; the inventory also lists the live model and root compatibility matrix. The data/ and dataset/ trees are not read by the current backend routes.

| Live input | Rows | Bytes | Role |
| --- | ---: | ---: | --- |
| hybrid_simulation_v1/synthetic_service_options.csv | 57,549 | 18,639,627 | Dynamic service candidates and simulated prices/areas |
| hybrid_simulation_v1/real_vendor_profiles.csv | 18,430 | 22,894,128 | Vendor join and five model features |
| hybrid_simulation_v1/synthetic_event_requirements.csv | 30 | 4,106 | Existing sample-event route |
| hybrid_simulation_v1/synthetic_availability.csv | 191 | 19,144 | Sample-event availability evidence |
| hybrid_simulation_v1/synthetic_collaboration_scenarios.csv | 330 | 57,210 | Sample-event collaboration evidence |
| vendor_compatibility_matrix.csv | 15 | 447 | Static service-category scores |
| models/vendor_risk_random_forest.pkl | binary | 448,937 | Saved model |

## Provenance and integrity

The source provenance table marks vendor profile/review fields as user-supplied profile or review features. Identifiers, names, Yelp category text, geography, ratings, review counts, attributes, and hours are source-derived fields; service_categories and matched_categories are inferred category mappings, not verified offerings. risk_level, risk_score, vendor_score and rank are derived rules/scores. In synthetic_service_options.csv, business_id is a profile foreign key; service categories, option tiers, prices, capacity, locations, event-type support, and setup fields are synthetic simulation metadata. Neither the synthetic service row nor a Yelp category proves an actual vendor offering.

Active inputs have zero duplicate profile business IDs, zero duplicate service_option_ids, and zero option vendor IDs without a profile. The 57,549 repeated business IDs across option rows are expected because vendors have multiple option tiers/categories. The 31 duplicate-ID rows in data/raw/vendor_recommendation_dataset_ids_repaired.csv are historical: the live profile file and cleaned source copies have zero. The two independent 1,000-row Yelp sample files have 923 review business IDs absent from the 1,000-business subset; these subsets are not active backend foreign keys. Relevant numeric fields and five model features had zero nonblank parse errors or out-of-domain values in measured checks. Blank min_billable_guests, max_guests and min_billable_hours occur in rows with other pricing bases; they are structural, not blanket errors. See [data_quality_report.csv](./data_quality_report.csv).

There are 704 distinct raw city/state labels, but only 663 after the same trim/casefold normalization used by candidate selection. Thirty-eight normalized locations have multiple raw spellings/cases (79 raw labels). The locations endpoint deduplicates raw strings, so these variants can appear separately in the selector. Candidate matching already normalizes them; label cleanup alone will not create additional package coverage.

## Coverage, price, and capacity

The API supports **seven** service categories. There is no canonical group of five in its schema. Of 704 raw city/state labels, 213 have at least 3 categories, 52 have at least 5 of 7, and only 7 have all 7. For the explicitly defined five-category set Audio Visual, Catering, Decoration, Entertainment and Photography, exactly 7 raw city/state labels support all five. This set is an audit definition, not an API-defined core. Counts by normalized location may be lower because raw labels merge. [location_coverage.csv](./location_coverage.csv) has the actual service-row counts for each raw city/state; [service_coverage.csv](./service_coverage.csv) summarizes categories.

| Category | Options | Vendors | Cities (raw city names) | Share of option rows |
| --- | ---: | ---: | ---: | ---: |
| Catering | 48,435 | 16,145 | 653 | 84.16% |
| Event Planning | 4,017 | 1,339 | 266 | 6.98% |
| Decoration | 2,646 | 882 | 245 | 4.60% |
| Photography | 1,401 | 467 | 133 | 2.43% |
| Equipment Rental | 552 | 184 | 74 | 0.96% |
| Entertainment | 462 | 154 | 55 | 0.80% |
| Audio Visual | 36 | 12 | 8 | 0.06% |

The source option distributions are strongly uneven. For a **simulated** 50-guest, 8-hour event, estimated median LKR costs are Catering 885,159, Entertainment 762,507, Decoration 612,664, Photography 585,508, Audio Visual 428,584, Event Planning 639,276, Equipment Rental 357,183. These are calculated using the backend USD-to-LKR rate and pricing bases; they are not quotations. All 48,435 Catering rows carry the simulated catering capacity rule; 16,238 list max_guests below 150. Other categories have no recorded max_guests constraint under the current rule, so capacity is unverified rather than proven unlimited. See [budget_capacity_analysis.csv](./budget_capacity_analysis.csv).

All 191 availability rows refer to SIMEVT sample IDs, with dates from 2027-01-01 through 2027-03-29 and the interval 14:00–18:00. They do not match newly generated USER event IDs; live-user availability remains VERIFICATION_REQUIRED. Availability is not a pre-generation filter. The 330 collaboration rows likewise concern sample events and are synthetic; they do not prove live vendor collaboration.

## Actual filtering and API outcomes

The stage table [candidate_filter_stages.csv](./candidate_filter_stages.csv) applies the same city/state casefold, semicolon event-type membership, Catering-only max_guests filter, and pricing validator as the backend. It records per-service source, location, event-type, capacity, priceable and individually affordable counts. Across 51 service/scenario pairs, event type removed no rows, capacity reduced 7 pairs, and pricing validity removed no rows. The offline priceable counts matched the API candidate counts for all 51 pairs.

The first request was the exact saved Philadelphia Wedding event (2026-11-16, 10:00–18:00, 50 guests, LKR 1,000,000, Photography + Decoration, top_k 3). It returned HTTP 200 and 3 packages. At Philadelphia the source contained 165 Photography and 237 Decoration rows matching the location; all were priceable, with 147 and 193 individually within budget. The backend chose at most 12 per service, so it reported search_limit_reached. This is bounded-search coverage, not a claim of global optimality.

The next 22 requests used existing locations and varied event types, guest counts, budgets and service sets. All 23 requests returned HTTP 200. Eighteen returned packages and five returned none: two had required category groups absent, three failed budget feasibility. Fifteen responses had candidate search limits. Runtime ranged from 1.61 to 6.25 seconds in this sequential run (median 2.92 seconds); prior PP1 measurements have been slower, so this run does not establish a reliable five-second target. Full inputs, statuses, counts, diagnostics, search flags, and times are in [package_generation_test_results.csv](./package_generation_test_results.csv); complete responses are in [api_response_evidence.jsonl](./api_response_evidence.jsonl).

Examples:
- Arabi LA, 150 guests, 1M LKR, Decoration + Catering + Entertainment: 0 Decoration and Entertainment location rows; Catering fell from 12 location rows to 7 capacity-eligible/priceable rows and 0 individually affordable rows. No package is truthful.
- Blackwood NJ, Corporate, Audio Visual + Decoration: 0 Audio Visual location rows. This is category/location coverage, not an ML failure.
- Philadelphia PA, Corporate, 500 guests, Catering + Audio Visual, 1M LKR: Catering fell from 4,701 local rows to 752 capacity-eligible rows; none individually fit the budget. Audio Visual had 3 local options, but the combination cannot fit.
- Nashville TN, 200 guests, Catering + Entertainment, 1M LKR: Catering had 1,057 capacity-eligible rows, 2 individually affordable; Entertainment had 27 priceable rows, 19 affordable. The cheapest combined eligible options exceeded the total budget.
- Belleville IL, 150 guests, three services, 1M LKR: Catering had 68 capacity-eligible rows but 0 individually affordable; the package lower bound exceeded budget.

## Saved Random Forest

The active model loaded with the enforced SHA-256 4eed156cfdf677b992b8c36350c21c968d7cb4d532a8afd302ca1b697aea3e6a. Its required features are stars, review_count, collected_review_count, mean_review_rating and rating_std. All 18,430 profiles have complete, parseable, in-range values in these checks; the model produced five sample predictions. Labels are rule-derived from review features, not independent real-world vendor failure outcomes. Editing only simulated option locations/prices/capacities does not change the model's five input columns, though it changes which vendors are selected and still requires API regression checks. Editing profiles, features, labels or model metadata would require separate model validation and could require retraining; none was performed.

## Measurement limits

These are observations on the current files and 23 specified requests, not a census of every possible event. Location coverage counts do not imply budget-feasible or compatible packages. Stage counts are exact for the tested requests; affordability alone does not prove distinct-vendor or full-package feasibility. The 1,000-row Yelp source samples are incomplete subsets. No vendor offering, price, availability or collaboration was independently verified.