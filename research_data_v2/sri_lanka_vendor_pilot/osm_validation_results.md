# OSM pilot validation and engine compatibility

## Actual validator run

Command, from the project root:

    d:/Vendor-Intelligence-System/venv/Scripts/python.exe -B research_data_v2/sri_lanka_vendor_pilot/validate_sri_lanka_dataset.py research_data_v2/sri_lanka_vendor_pilot/osm_sri_lanka_vendor_sample.csv

Exit code **0**. The existing validator returned status **VALID**, **10 rows**, **10 declared non-synthetic rows**, **0 errors** and **0 warnings**. This validates structure and field format; it does not independently verify that a mapped business is active.

| Category | Count |
|---|---:|
| Photography | 7 |
| Catering | 3 |
| Decoration | 0 |
| Entertainment | 0 |
| Audio Visual | 0 |

All 10 rows lack district, province, rating, review_count, mean_review_rating, rating_std, collected_review_count, price_lkr, guest_capacity, service_area and availability_status. Each field is blank in **10/10** rows. All 10 have an OSM element ID in vendor_id, name, category-supporting craft tag documented in the [collection report](./osm_collection_report.md), an addr:city, country, exact source URL, source name, UTC collection time, unverified status and licensed_open_data label.

SHA-256 of sample CSV: **744E342EA9CF6215934754A4077C507C01DFEFFBE6F4DE494D1DAD5E1E8C8E7A**. The separate original template remains header-only, SHA-256 **26A1F1DE4C0CCAF44A00C8635E1FA877F4F76CF07FBD601B54DCCA18EBF87BDF**.

## Existing engine suitability

**Random Forest: 0/10 model-ready.** The [risk signal loader](../../backend/engine/risk_signals.py) expects ordered numeric features stars, review_count, collected_review_count, mean_review_rating and rating_std from the production profile file. The pilot's rating is blank and is not automatically equivalent to stars; the other four inputs are blank. No zeros or guessed values were inserted. Even future complete features would need definition and population checks before interpretation, because the model predicts rule-derived Yelp review-risk labels, not verified Sri Lankan reliability.

**Package generator: 0/10 option-ready.** The [option loader](../../backend/engine/package_data_loader.py) reads a separate production synthetic option file with priced service_option_id, business_id, service category, simulated service city/state, supported event types, capacity and pricing-basis fields. The [candidate filter](../../backend/engine/candidate_selection.py) uses those option fields. These ten mapped business profiles supply none of the required priced option or event/date coverage evidence. An OSM base city cannot be treated as a confirmed service area. The production engine was not changed or called with this pilot.

**Next safe step:** obtain vendor-confirmed service options and permissions in a separate research intake, then review an adapter and unknown-risk behavior before considering integration. Keep the working Philadelphia demo untouched.

